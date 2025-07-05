# utils.py

import os
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib import pyplot as plt

# ============================
# 1. FLYWHEEL CONFIG UTIL
# ============================
def configure_flywheel_with_powermeter(fw, pm):
    """
    Measures intensity at each flywheel position to identify mirror slot (highest power).
    Sets the flywheel to that position and updates current_slot to 1.
    """
    print("Configuring flywheel...")
    measurements = []

    for _ in range(fw.slot_count):
        current = fw.get_current_slot()
        power = pm.get_power()
        measurements.append((current, power))
        fw._pulse_once()

    # Find slot with max power (mirror slot)
    slot_1, _ = max(measurements, key=lambda x: x[1])
    fw.go_to_slot(slot_1)
    fw.current_slot = 1

    print("Flywheel configured. Slot 1 = Mirror")

# ============================
# 2. UNIVERSAL PLOT UTILITIES
# ============================
def plot_spectra_from_csv(
    save_dir=".",
    file_prefix="spectrum_",
    wavelength_range=(None, None),
    overlay_count=10
):
    """
    General-purpose CSV plotting utility for PL degradation.
    - Reads spectra from CSVs
    - Generates 3D surface, contour, peak intensity/wavelength/time graphs
    - Saves plots to SAVE_DIR
    """
    csv_files = sorted(f for f in os.listdir(save_dir) if f.startswith(file_prefix) and f.endswith(".csv"))
    if not csv_files:
        raise FileNotFoundError("No CSV files found in the directory.")

    spectra = []
    times = []
    peak_intensities = []
    peak_wavelengths = []

    for i, fname in enumerate(csv_files):
        timestamp_str = fname.replace(file_prefix, "").replace(".csv", "")
        try:
            h, m, s = map(int, timestamp_str.split("-"))
            total_seconds = h * 3600 + m * 60 + s
        except:
            total_seconds = i  # fallback to index-based time

        data = np.loadtxt(os.path.join(save_dir, fname), delimiter=",", skiprows=1)
        wavelengths = data[:, 0]
        intensities = data[:, 1]

        spectra.append(intensities)
        times.append(total_seconds)
        peak_intensities.append(np.max(intensities))
        peak_wavelengths.append(wavelengths[np.argmax(intensities)])

    spectra = np.array(spectra)
    times = np.array(times)
    peak_intensities = np.array(peak_intensities)
    peak_wavelengths = np.array(peak_wavelengths)

    T, WL = np.meshgrid(times, wavelengths)
    S = spectra.T

    # === 3D SURFACE ===
    fig3d = plt.figure(figsize=(10, 6))
    ax3d = fig3d.add_subplot(111, projection='3d')
    ax3d.plot_surface(WL, T, S, cmap=cm.inferno)
    ax3d.set_xlabel("Wavelength (nm)")
    ax3d.set_ylabel("Time (s)")
    ax3d.set_zlabel("Intensity")
    ax3d.set_title("PL Intensity vs Wavelength vs Time")
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, "3D_PL_Surface.png"))

    # === PEAK INTENSITY ===
    plt.figure()
    plt.plot(times, peak_intensities, 'go-')
    plt.xlabel("Time (s)")
    plt.ylabel("Peak Intensity (a.u.)")
    plt.title("Peak Intensity vs Time")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, "peak_intensity_vs_time.png"))

    # === PEAK WAVELENGTH ===
    plt.figure()
    plt.plot(times, peak_wavelengths, 'bx-')
    plt.xlabel("Time (s)")
    plt.ylabel("Peak Wavelength (nm)")
    plt.title("Peak Wavelength Shift vs Time")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, "peak_wavelength_vs_time.png"))

    # === CONTOUR ===
    plt.figure(figsize=(10, 6))
    cp = plt.contourf(times, wavelengths, S, levels=100, cmap=cm.inferno)
    plt.xlabel("Time (s)")
    plt.ylabel("Wavelength (nm)")
    plt.title("PL Contour: Wavelength vs Time")
    plt.colorbar(cp, label="Intensity (a.u.)")
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, "pl_contour_plot.png"))

    # === OVERLAY ===
    plt.figure()
    selected_indices = np.linspace(0, len(times)-1, min(overlay_count, len(times)), dtype=int)
    for i in selected_indices:
        plt.plot(wavelengths, spectra[i], label=f"t={times[i]:.0f}s")
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity (a.u.)")
    plt.title("Overlay: Wavelength vs Intensity")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, "wavelength_vs_intensity_overlay.png"))

    print(f"✔ All plots saved in '{save_dir}'")

def save_csv_spectrum(wavelengths, intensities, filepath):
    """
    Saves spectrum data to a CSV file with header.
    """
    data = np.column_stack((wavelengths, intensities))
    np.savetxt(filepath, data, delimiter=",", header="Wavelength,Intensity", comments='')

def plot_all_from_csv(directory):
    """
    Wrapper around `plot_spectra_from_csv` with default settings.
    """
    plot_spectra_from_csv(save_dir=directory)

