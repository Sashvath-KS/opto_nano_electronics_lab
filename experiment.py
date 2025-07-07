# experiment.py

import os
import json
import time
import datetime
import numpy as np
import matplotlib.pyplot as plt
import threading
import queue
from utils import plot_spectra_from_csv

from spectrometer import CCS_Spectrometer
from flywheel import FlywheelController
from pm import PM100D
from utils import (
    save_csv_spectrum,
    plot_steady_state_overlay,
    plot_spectrum_single,
    configure_flywheel_with_powermeter
)


class PLExperiment:
    def __init__(self, user_config="config_user.json", setup_config="config_setup.json"):
        with open(user_config) as f:
            self.user_cfg = json.load(f)

        self.save_dir = self.user_cfg.get("save_directory", "output")
        self.csv_dir = os.path.join(self.save_dir, "csv")
        self.plot_dir = os.path.join(self.save_dir, "plots")
        os.makedirs(self.csv_dir, exist_ok=True)
        os.makedirs(self.plot_dir, exist_ok=True)

        self.spec = CCS_Spectrometer(setup_config)
        self.pm = PM100D(setup_config)
        self.fw = FlywheelController(setup_config)

        if self.user_cfg.get("mask_range_nm"):
            self.spec.set_mask_range(*self.user_cfg["mask_range_nm"])
        self.spec.set_integration_time(self.user_cfg["integration_time_ms"] / 1000)

        if self.user_cfg.get("auto_configure_flywheel", True):
            configure_flywheel_with_powermeter(self.fw, self.pm)

        self.slots = self.fw.slot_mapping
        self.avg_count = self.user_cfg.get("average_count", 1)
        self.enable_averaging = self.user_cfg.get("enable_averaging", False)
        self.bg_mode = self.user_cfg.get("background_mode", "each")  # "each" or "once"

    def average_spectrum(self):
        print(f"[Acquisition] Averaging {self.avg_count} spectra...")
        spectra = [self.spec.get_raw_spectrum()[1] for _ in range(self.avg_count)]
        avg_inten = np.mean(spectra, axis=0)
        wl = self.spec.get_raw_spectrum()[0]
        return wl, avg_inten

    def run_steady_state(self):
        print("[Experiment] Running steady-state PL")
        all_spectra = []
        all_labels = []

        if self.user_cfg.get("background_correction", True) and self.bg_mode == "once":
            print("[Background] Capturing single background...")
            self.fw.go_to_slot(self.slots["mirror"])
            time.sleep(0.5)
            bg_stack = [self.spec.get_raw_spectrum()[1] for _ in range(self.avg_count)] if self.enable_averaging else [self.spec.get_raw_spectrum()[1]]
            background = np.mean(bg_stack, axis=0)

        for i in range(1, self.user_cfg["sample_count"] + 1):
            input(f"\nInsert Sample #{i} and press Enter...")

            if self.user_cfg.get("background_correction", True) and self.bg_mode == "each":
                print("[Background] Capturing background...")
                self.fw.go_to_slot(self.slots["mirror"])
                time.sleep(0.5)
                bg_stack = [self.spec.get_raw_spectrum()[1] for _ in range(self.avg_count)] if self.enable_averaging else [self.spec.get_raw_spectrum()[1]]
                background = np.mean(bg_stack, axis=0)

            self.fw.go_to_slot(self.slots["empty"])
            time.sleep(0.5)

            wl, inten = self.average_spectrum() if self.enable_averaging else self.spec.get_raw_spectrum()

            if self.user_cfg.get("background_correction", True):
                inten = inten - background
                inten = np.clip(inten, 0, None)

            timestamp = datetime.datetime.now().strftime("%H-%M-%S")
            fname = f"spectrum_sample{i}_{timestamp}.csv"
            csv_path = os.path.join(self.csv_dir, fname)
            save_csv_spectrum(wl, inten, csv_path)
            print(f"[Saved] Sample #{i} spectrum saved.")
            plot_path = os.path.join(self.plot_dir, f"sample{i}_spectrum.png")
            plot_spectrum_single(wl, inten, plot_path, label=f"Sample {i}")

            plt.figure()
            plt.plot(wl, inten, label=f"Sample {i}")
            peak_wl = wl[np.argmax(inten)]
            peak_val = np.max(inten)
            plt.axvline(peak_wl, color='r', linestyle='--', label=f"Peak: {peak_wl:.1f} nm")
            plt.text(peak_wl, peak_val, f"{peak_wl:.1f} nm", color='red', fontsize=9, ha='right')
            plt.xlabel("Wavelength (nm)")
            plt.ylabel("Intensity (a.u.)")
            plt.title(f"Live PL - Sample {i}")
            plt.grid(True)
            plt.legend()
            plt.tight_layout()
            plt.show()

            all_spectra.append((wl, inten))
            peak_intensity = np.max(inten)
            peak_wavelength = wl[np.argmax(inten)]
            all_labels.append(f"Sample {i} (peak: {peak_wavelength:.1f} nm, {peak_intensity:.1f} a.u.)")

        plot_steady_state_overlay(all_spectra, all_labels, os.path.join(self.plot_dir, "steady_state_overlay.png"))

        print("\n[Experiment] Steady-state PL complete.")


    def run_degradation_study(self):
        print("[Experiment] Running degradation PL")
        duration = self.user_cfg["degradation_duration_s"]
        interval = self.user_cfg["sampling_interval_s"]
        normalization = self.user_cfg["normalization"]
        flywheel_mode = self.user_cfg["flywheel_mode"]

        t0 = time.time()
        bg = None

        if self.user_cfg.get("background_correction", False) and not self.user_cfg.get("repeated_bg", True):
            self.fw.go_to_slot(self.slots["mirror"])
            time.sleep(0.5)
            bg = [self.spec.get_raw_spectrum()[1] for _ in range(self.avg_count)] if self.enable_averaging else [self.spec.get_raw_spectrum()[1]]
            background = np.mean(bg, axis=0)

        # === Initialize Live Plot ===
        plt.ion()
        fig, ax = plt.subplots()
        line, = ax.plot([], [], label="PL")
        peak_line = ax.axvline(0, color='r', linestyle='--', label="Peak")
        peak_text = ax.text(0, 0, "", color='red', fontsize=9, ha='right')

        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("Intensity (a.u.)")
        ax.set_title("Degradation PL - Live")
        ax.grid(True)
        ax.legend()
        plt.tight_layout()

        while (time.time() - t0) < duration:
            timestamp = datetime.datetime.now().strftime("%H-%M-%S")
            t_elapsed = time.time() - t0

            if flywheel_mode != "skip":
                if normalization == "mirror":
                    self.fw.go_to_slot(self.slots["mirror"])
                    time.sleep(0.5)
                    power = self.pm.get_power()
                    if self.user_cfg.get("background_correction", False) and self.user_cfg.get("repeated_bg", True):
                        bg = [self.spec.get_raw_spectrum()[1] for _ in range(self.avg_count)] if self.enable_averaging else [self.spec.get_raw_spectrum()[1]]
                        background = np.mean(bg, axis=0)
                    self.fw.go_to_slot(self.slots["empty"])
                elif normalization == "beam_splitter":
                    self.fw.go_to_slot(self.slots["beam_splitter"])
                    power = self.pm.get_power()
                else:
                    self.fw.go_to_slot(self.slots["empty"])
                    power = 1.0
            else:
                power = 1.0

            time.sleep(0.5)
            wl, inten = self.average_spectrum() if self.enable_averaging else self.spec.get_raw_spectrum()

            if normalization != "none" and power > 0:
                inten = inten / power

            if self.user_cfg.get("background_correction", False):
                inten = inten - background
                inten = np.clip(inten, 0, None)

            # === Update Live Plot ===
            line.set_data(wl, inten)
            peak_wl = wl[np.argmax(inten)]
            peak_val = np.max(inten)
            peak_line.set_xdata([peak_wl])
            peak_text.set_position((peak_wl, peak_val))
            peak_text.set_text(f"{peak_wl:.1f} nm")

            ax.set_xlim(wl.min(), wl.max())
            ax.set_ylim(0, peak_val * 1.2)

            fig.canvas.draw()
            fig.canvas.flush_events()

            # Save this plot
            plot_path = os.path.join(self.plot_dir, f"degradation_{timestamp}.png")
            plt.savefig(plot_path)

            csv_path = os.path.join(self.csv_dir, f"spectrum_{timestamp}.csv")
            save_csv_spectrum(wl, inten, csv_path)
            print(f"[Saved] t = {t_elapsed:.1f}s")

            plt.pause(0.05)
            time.sleep(interval)

        plt.ioff()
        plt.close()

        # === Summary plots ===
        try:
            plot_spectra_from_csv(
                save_dir=self.csv_dir,
                file_prefix="spectrum_",
                wavelength_range=self.user_cfg.get("mask_range_nm", (None, None)),
                overlay_count=10
            )
        except Exception as e:
            print(f"[Warning] Failed to generate degradation plots: {e}")

        print("\n[Experiment] Degradation study complete.")

    def run_pre_tuning(self):
        print("[Tuning] Starting live spectrum mode...")
        print("Type new integration time in milliseconds, or 'exit' to quit.")

        self.fw.go_to_slot(self.slots["empty"])

        q_data = queue.Queue()

        def stream_callback(wl, inten):
            q_data.put((wl, inten))

        self.spec.start_stream(callback=stream_callback, delay=0.4)

        plt.ion()
        fig, ax = plt.subplots()
        line, = ax.plot([], [], lw=2)
        ax.set_xlim(600, 900)
        ax.set_ylim(0, 1)
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("Intensity (a.u.)")
        ax.set_title("Live PL Spectrum")

        def input_thread_fn():
            while True:
                val = input("> New integration time (ms) or 'exit': ").strip().lower()
                if val == "exit":
                    q_data.put("exit")
                    break
                try:
                    ms = float(val)
                    self.spec.set_integration_time(ms / 1000)
                    print(f"[Tuning] Integration time set to {ms} ms")
                except ValueError:
                    print("[Tuning] Invalid input")

        thread_input = threading.Thread(target=input_thread_fn)
        thread_input.daemon = True
        thread_input.start()

        try:
            while True:
                item = q_data.get()
                if item == "exit":
                    break
                wl, inten = item
                line.set_data(wl, inten)
                ax.set_ylim(0, max(inten) * 1.2)
                ax.set_xlim(wl.min(), wl.max())
                fig.canvas.draw()
                fig.canvas.flush_events()
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("[Tuning] Interrupted.")
        finally:
            self.spec.stop_stream()
            plt.ioff()
            plt.close()
            print("[Tuning] Stopped.")

    def shutdown(self):
        self.spec.shutdown()
        self.pm.close()
        self.fw.close()
