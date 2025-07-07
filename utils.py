# utils.py

import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm

def configure_flywheel_with_powermeter(fw, pm):
    print("[Flywheel Config] Detecting mirror slot via power meter...")
    measurements = []
    for _ in range(fw.slot_count):
        slot = fw.get_current_slot()
        power = pm.get_power()
        measurements.append((slot, power))
        fw._pulse_once()
    best_slot, best_power = max(measurements, key=lambda x: x[1])
    fw.go_to_slot(best_slot)
    fw.reset_slot(1)
    print(f"[Flywheel Config] Mirror aligned to Slot 1 (was Slot {best_slot}, {best_power:.3e} W)")

def save_csv_spectrum(wavelengths, intensities, filepath):
    data = np.column_stack((wavelengths, intensities))
    np.savetxt(filepath, data, delimiter=",", header="Wavelength,Intensity", comments='')

def plot_spectra_from_csv(
    save_dir,
    file_prefix="spectrum_",
    wavelength_range=(None, None),
    overlay_count=10
):
    csv_files = sorted(f for f in os.listdir(save_dir) if f.startswith(file_prefix) and f.endswith(".csv"))
    if not csv_files:
        raise FileNotFoundError("No CSV spectra found.")

    spectra = []
    times = []
    peak_intensities = []
    peak_wavelengths = []

    for i, fname in enumerate(csv_files):
        timestamp_str = fname.replace(file_prefix, "").replace(".csv", "")
        try:
            h, m, s = map(int, timestamp_str.split("-"))
            t_sec = h * 3600 + m * 60 + s
        except:
            t_sec = i

        data = np.loadtxt(os.path.join(save_dir, fname), delimiter=",", skiprows=1)
        wl = data[:, 0]
        inten = data[:, 1]

        spectra.append(inten)
        times.append(t_sec)
        peak_intensities.append(np.max(inten))
        peak_wavelengths.append(wl[np.argmax(inten)])

    spectra = np.array(spectra)
    times = np.array(times)
    peak_intensities = np.array(peak_intensities)
    peak_wavelengths = np.array(peak_wavelengths)

    if spectra.shape[1] < 2:
        print("[Plotting] Only one spectrum — skipping 3D/contour.")
        return

    T, WL = np.meshgrid(times, wl)
    S = spectra.T

    fig3d = plt.figure(figsize=(10, 6))
    ax3d = fig3d.add_subplot(111, projection='3d')
    ax3d.plot_surface(WL, T, S, cmap=cm.inferno)
    ax3d.set_xlabel("Wavelength (nm)")
    ax3d.set_ylabel("Time (s)")
    ax3d.set_zlabel("Intensity")
    ax3d.set_title("PL Intensity vs Wavelength vs Time")
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, "3D_PL_Surface.png"))

    plt.figure()
    plt.plot(times, peak_intensities, 'go-')
    plt.xlabel("Time (s)")
    plt.ylabel("Peak Intensity (a.u.)")
    plt.title("Peak Intensity vs Time")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, "peak_intensity_vs_time.png"))

    plt.figure()
    plt.plot(times, peak_wavelengths, 'bx-')
    plt.xlabel("Time (s)")
    plt.ylabel("Peak Wavelength (nm)")
    plt.title("Peak Wavelength Shift vs Time")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, "peak_wavelength_vs_time.png"))

    plt.figure(figsize=(10, 6))
    cp = plt.contourf(times, wl, S, levels=100, cmap=cm.inferno)
    plt.xlabel("Time (s)")
    plt.ylabel("Wavelength (nm)")
    plt.title("PL Contour: Wavelength vs Time")
    plt.colorbar(cp, label="Intensity (a.u.)")
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, "pl_contour_plot.png"))

    plt.figure()
    selected = np.linspace(0, len(times)-1, min(overlay_count, len(times)), dtype=int)
    for i in selected:
        plt.plot(wl, spectra[i], label=f"t={times[i]:.0f}s")
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity (a.u.)")
    plt.title("Overlay: Spectra over Time")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, "wavelength_vs_intensity_overlay.png"))

    print(f"[Plots] Summary plots saved in '{save_dir}'")

def plot_spectrum_single(wavelengths, intensities, save_path, label="Sample"):
    plt.figure()
    plt.plot(wavelengths, intensities, label=label)
    peak_wl = wavelengths[np.argmax(intensities)]
    peak_val = np.max(intensities)
    plt.axvline(peak_wl, color='r', linestyle='--', label=f"Peak: {peak_wl:.1f} nm")
    plt.text(peak_wl, peak_val, f"{peak_wl:.1f} nm", color='red', fontsize=9, ha='right')
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity (a.u.)")
    plt.title(f"PL Spectrum - {label}")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()

def plot_steady_state_overlay(spectra_list, labels, save_path):
    plt.figure()
    for (wl, inten), label in zip(spectra_list, labels):
        plt.plot(wl, inten, label=label)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity (a.u.)")
    plt.title("Steady-State PL Spectra Overlay")
    plt.grid(True)
    plt.legend(fontsize="small")
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
