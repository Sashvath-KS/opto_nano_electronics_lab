# testing.py (final version with background correction, plotting, and 3D/summary plots)

import os
import time
import datetime
import numpy as np
from flywheel import FlywheelController
from pm import PM100D
from spectrometer import CCS_Spectrometer
import matplotlib.pyplot as plt
from matplotlib import cm
from utils import save_csv_spectrum

# === CONFIGURATION ===
INTEGRATION_TIME_SEC = 0.5
MEASUREMENT_DURATION_SEC = 600  # 10 minutes
INTERVAL_SEC = 2
SAVE_DIR = "testing"
CSV_DIR = os.path.join(SAVE_DIR, "csv")
PLOT_DIR = os.path.join(SAVE_DIR, "plots")
os.makedirs(CSV_DIR, exist_ok=True)
os.makedirs(PLOT_DIR, exist_ok=True)

# === INITIALIZE DEVICES ===
fw = FlywheelController(initial_slot=1)
pm = PM100D()
spec = CCS_Spectrometer()
spec.set_integration_time(INTEGRATION_TIME_SEC)
spec.set_mask_range(700, 900)

# === CONFIGURE FLYWHEEL ===
print("Configuring flywheel...")
max_power = 0
slot_1 = 1
for _ in range(fw.slot_count):
    p = pm.get_power()
    if p > max_power:
        max_power = p
        slot_1 = fw.get_current_slot()
    fw._pulse_once()
fw.go_to_slot(slot_1)
fw.reset_slot(1)
print(f"Flywheel aligned. Slot 1 = Mirror (Power = {max_power:.3e} W)")

input("Insert sample and press Enter to start experiment...")

# === SETUP PLOTTING ===
plt.ion()
fig, ax = plt.subplots()
wl = np.linspace(700, 900, 1000)
line, = ax.plot(wl, np.zeros_like(wl))
peak_marker, = ax.plot([], [], 'ro')
peak_line = ax.axvline(0, color='r', linestyle='--', alpha=0.5)
ax.set_xlabel("Wavelength (nm)")
ax.set_ylabel("Intensity (a.u.)")
ax.set_xlim(700, 900)

# === MEASUREMENT LOOP ===
times, spectra, peak_intensities, peak_wavelengths, powers = [], [], [], [], []
start_time = time.time()

while (time.time() - start_time) < MEASUREMENT_DURATION_SEC:
    timestamp = datetime.datetime.now().strftime("%H-%M-%S")
    t_elapsed = time.time() - start_time

    fw.go_to_slot(1)
    time.sleep(0.5)
    spec.capture_background()

    fw.go_to_slot(2)
    time.sleep(0.5)
    power = pm.get_power()
    wl, inten = spec.get_spectrum(correct_bg=True)
    if power > 0:
        inten /= power

    peak_idx = np.argmax(inten)
    peak_wl = wl[peak_idx]
    peak_val = inten[peak_idx]

    csv_path = os.path.join(CSV_DIR, f"spectrum_{timestamp}.csv")
    save_csv_spectrum(wl, inten, csv_path)

    plt.figure()
    plt.plot(wl, inten, label=f"Peak λ = {peak_wl:.1f} nm | {peak_val:.2f} a.u.")
    plt.axvline(peak_wl, color='r', linestyle='--', alpha=0.6, label="Peak Position")
    plt.plot(peak_wl, peak_val, 'ro')
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity (a.u.)")
    plt.title(f"PL Spectrum @ {timestamp}")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, f"spectrum_{timestamp}.png"))
    plt.close()

    line.set_data(wl, inten)
    peak_marker.set_data([peak_wl], [peak_val])
    peak_line.set_xdata([peak_wl])
    ax.set_ylim(0, peak_val * 1.2)
    ax.set_title(f"Live PL Spectrum @ t = {t_elapsed:.1f} s")
    fig.canvas.draw()
    fig.canvas.flush_events()

    times.append(t_elapsed)
    spectra.append(inten)
    peak_intensities.append(peak_val)
    peak_wavelengths.append(peak_wl)
    powers.append(power)

    fw.go_to_slot(1)
    time.sleep(INTERVAL_SEC)

plt.ioff()
plt.close()

# === SAVE FINAL DATA ===
data = {
    'wavelengths': wl,
    'times': np.array(times),
    'spectra': np.array(spectra),
    'peak_intensities': np.array(peak_intensities),
    'peak_wavelengths': np.array(peak_wavelengths),
    'powers': np.array(powers)
}
np.save(os.path.join(SAVE_DIR, "experiment_data.npy"), data)

# === FINAL SUMMARY PLOTS ===
T, WL = np.meshgrid(times, wl)
S = np.array(spectra).T

# 3D Surface Plot
fig3d = plt.figure(figsize=(10, 6))
ax3d = fig3d.add_subplot(111, projection='3d')
ax3d.plot_surface(WL, T, S, cmap=cm.inferno)
ax3d.set_xlabel("Wavelength (nm)")
ax3d.set_ylabel("Time (s)")
ax3d.set_zlabel("Intensity")
ax3d.set_title("PL Intensity vs Wavelength vs Time")
plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, "3D_PL_Surface.png"))
plt.close()

# Peak Intensity vs Time
plt.figure()
plt.plot(times, peak_intensities, 'go-')
plt.xlabel("Time (s)")
plt.ylabel("Peak Intensity (a.u.)")
plt.title("Peak Intensity vs Time")
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, "peak_intensity_vs_time.png"))
plt.close()

# Peak Wavelength vs Time
plt.figure()
plt.plot(times, peak_wavelengths, 'bx-')
plt.xlabel("Time (s)")
plt.ylabel("Peak Wavelength (nm)")
plt.title("Peak Wavelength Shift vs Time")
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, "peak_wavelength_vs_time.png"))
plt.close()

# Contour Plot
plt.figure(figsize=(10, 6))
cp = plt.contourf(times, wl, S, levels=100, cmap=cm.inferno)
plt.xlabel("Time (s)")
plt.ylabel("Wavelength (nm)")
plt.title("PL Contour: Wavelength vs Time")
plt.colorbar(cp, label="Intensity (a.u.)")
plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, "pl_contour_plot.png"))
plt.close()

# Overlay of selected spectra
plt.figure()
selected_indices = np.linspace(0, len(times)-1, min(10, len(times)), dtype=int)
for i in selected_indices:
    plt.plot(wl, spectra[i], label=f"t={times[i]:.0f}s")
plt.xlabel("Wavelength (nm)")
plt.ylabel("Intensity (a.u.)")
plt.title("Wavelength vs Intensity for Selected Time Points")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, "wavelength_vs_intensity_overlay.png"))
plt.close()

print("✔ Experiment complete. Data and all summary plots saved.")
