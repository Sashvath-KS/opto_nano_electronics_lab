# spectrometer.py

import ctypes
import numpy as np
import threading
import time


class CCS_Spectrometer:
    def __init__(self, dll_path="C:\\Program Files\\IVI Foundation\\VISA\\Win64\\Bin\\TLCCS_64.dll",
                 resource_string=b"USB0::0x1313::0x8087::M00414815::RAW", integration_time=1.0, simulate=False):
        self.simulate = simulate
        self.integration_time = integration_time
        self.background = None
        self.mask_range = (None, None)
        self.streaming = False
        self.scan_thread = None
        self._stop_event = threading.Event()

        if not simulate:
            self.lib = ctypes.cdll.LoadLibrary(dll_path)
            self.handle = ctypes.c_int(0)
            result = self.lib.tlccs_init(resource_string, 1, 1, ctypes.byref(self.handle))
            if result != 0:
                raise RuntimeError("Failed to initialize CCS Spectrometer")
            self.set_integration_time(integration_time)
        else:
            print("[SIMULATION MODE] Spectrometer initialized")

    def set_integration_time(self, t_sec):
        self.integration_time = t_sec
        if not self.simulate:
            self.lib.tlccs_setIntegrationTime(self.handle, ctypes.c_double(t_sec))

    def set_mask_range(self, min_wl, max_wl):
        self.mask_range = (min_wl, max_wl)

    def capture_background(self):
        _, bg = self.get_raw_spectrum()
    
        if self.mask_range[0] is not None and self.mask_range[1] is not None:
            wl, _ = self.get_raw_spectrum()
            mask = (wl >= self.mask_range[0]) & (wl <= self.mask_range[1])
            bg = bg[mask]

        self.background = bg
        return self.background

    def get_raw_spectrum(self):
        if self.simulate:
            wl = np.linspace(200, 1100, 3648)
            signal = 100 * np.exp(-((wl - 800) ** 2) / (2 * 30 ** 2)) + np.random.normal(0, 1, wl.shape)
            return wl, signal

        num_pixels = 3648
        wavelengths = (ctypes.c_double * num_pixels)()
        intensities = (ctypes.c_double * num_pixels)()

        self.lib.tlccs_startScan(self.handle)
        self.lib.tlccs_getWavelengthData(self.handle, 0, ctypes.byref(wavelengths), None, None)
        self.lib.tlccs_getScanData(self.handle, ctypes.byref(intensities))

        wl = np.array(wavelengths)
        inten = np.array(intensities)
        return wl, inten

    def get_spectrum(self, correct_bg=True):
        wl, inten = self.get_raw_spectrum()

        if self.mask_range[0] is not None and self.mask_range[1] is not None:
            mask = (wl >= self.mask_range[0]) & (wl <= self.mask_range[1])
            wl, inten = wl[mask], inten[mask]

        if correct_bg and self.background is not None:
            inten = inten - self.background
            inten = np.clip(inten, 0, None)

        return wl, inten

    def track_peak(self, wavelengths, intensities):
        idx = np.argmax(intensities)
        return wavelengths[idx], intensities[idx]

    def start_continuous_stream(self, callback, delay=0.2, correct_bg=True):
        if self.streaming:
            return

        def loop():
            while not self._stop_event.is_set():
                wl, inten = self.get_spectrum(correct_bg=correct_bg)
                callback(wl, inten)
                time.sleep(delay)

        self._stop_event.clear()
        self.streaming = True
        self.scan_thread = threading.Thread(target=loop)
        self.scan_thread.start()

    def stop_continuous_stream(self):
        self._stop_event.set()
        if self.scan_thread is not None:
            self.scan_thread.join()
        self.streaming = False

    def show_live_plot(self, delay=0.6, correct_bg=True, duration=None):
        import matplotlib.pyplot as plt
        import queue

        plt.ion()
        fig, ax = plt.subplots()
        line, = ax.plot([], [], lw=2)
        ax.set_xlim(700, 900)
        ax.set_ylim(0, 1)
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("Intensity (a.u.)")
        ax.set_title("Live PL Spectrum")

        q = queue.Queue()

        def callback(wl, inten):
            q.put((wl, inten))

        self.start_continuous_stream(callback, delay=delay, correct_bg=correct_bg)

        try:
            start = time.time()
            print("Live plotting started. Press Ctrl+C to stop.")
            while True:
                if not q.empty():
                    wl, inten = q.get()
                    line.set_data(wl, inten)
                    ax.set_ylim(0, max(inten) * 1.1)
                    fig.canvas.draw()
                    fig.canvas.flush_events()
                if duration and (time.time() - start) > duration:
                    break
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("Live plotting stopped by user.")
        finally:
            self.stop_continuous_stream()
            plt.ioff()
            plt.show()


    def get_info(self):
        if self.simulate:
            return {
                "serial_number": "SIM00001",
                "model": "CCS175 (Simulated)",
                "pixel_count": 3648,
                "wavelength_range": [200, 1100]
            }
        serial = ctypes.create_string_buffer(64)
        self.lib.tlccs_getInstrumentSerialNumber(self.handle, serial, 64)
        return {
            "serial_number": serial.value.decode(),
            "model": "Thorlabs CCS175",
            "pixel_count": 3648,
            "wavelength_range": [200, 1100]
        }

    def shutdown(self):
        if not self.simulate:
            self.lib.tlccs_close(self.handle)
        print("Spectrometer closed.")
