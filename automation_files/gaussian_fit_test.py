import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from scipy.optimize import curve_fit

# === CONFIGURATION ===
SAVE_DIR = "triple_cation_testing"
CSV_FILES = sorted([f for f in os.listdir(SAVE_DIR) if f.endswith(".csv")])

if not CSV_FILES:
    raise FileNotFoundError("No CSV files found in the directory.")

# === DEFINE GAUSSIAN ===
def gaussian(x, A, mu, sigma, offset):
    return A * np.exp(-(x - mu)**2 / (2 * sigma**2)) + offset

# === LOAD DATA AND FIT GAUSSIANS ===
spectra = []
times = []
peak_intensities = []
peak_wavelengths = []

for i, fname in enumerate(CSV_FILES):
    timestamp_str = fname.replace("spectrum_", "").replace(".csv", "")
    try:
        h, m, s = map(int, timestamp_str.split("-"))
        total_seconds = h * 3600 + m * 60 + s
    except:
        total_seconds = i  # fallback to index-based time if parsing fails

    data = np.loadtxt(os.path.join(SAVE_DIR, fname), delimiter=",", skiprows=1)
    wavelengths = data[:, 0]
    intensities = data[:, 1]

    spectra.append(intensities)
    times.append(total_seconds)

    # Gaussian fit
    A_guess = np.max(intensities)
    mu_guess = wavelengths[np.argmax(intensities)]
    sigma_guess = 20
    offset_guess = np.min(intensities)

    try:
        popt, _ = curve_fit(gaussian, wavelengths, intensities,
                            p0=[A_guess, mu_guess, sigma_guess, offset_guess],
                            maxfev=5000)
        A_fit, mu_fit, sigma_fit, offset_fit = popt
    except RuntimeError:
        print(f"Fit failed for {fname}, using fallback peak detection.")
        A_fit, mu_fit = A_guess, mu_guess

    peak_intensities.append(A_fit)
    peak_wavelengths.append(mu_fit)

spectra = np.array(spectra)
times = np.array(times)
peak_intensities = np.array(peak_intensities)
peak_wavelengths = np.array(peak_wavelengths)

# === 3D SURFACE PLOT ===
T, WL = np.meshgrid(times, wavelengths)
S = spectra.T
fig3d = plt.figure(figsize=(10, 6))
ax3d = fig3d.add_subplot(111, projection='3d')
ax3d.plot_surface(WL, T, S, cmap=cm.inferno)
ax3d.set_xlabel("Wavelength (nm)")
ax3d.set_ylabel("Time (s)")
ax3d.set_zlabel("Intensity")
ax3d.set_title("PL Intensity vs Wavelength vs Time")
plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, "3D_PL_Surface_from_CSV.png"))
plt.show()

# === PEAK INTENSITY VS TIME ===
plt.figure()
plt.plot(times, peak_intensities, marker='o', color='green')
plt.xlabel("Time (s)")
plt.ylabel("Peak Intensity (a.u.)")
plt.title("Peak Intensity vs Time (Gaussian Fitted)")
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, "peak_intensity_vs_time_from_CSV.png"))
plt.show()

# === PEAK WAVELENGTH VS TIME ===
plt.figure()
plt.plot(times, peak_wavelengths, marker='x', color='blue')
plt.xlabel("Time (s)")
plt.ylabel("Peak Wavelength (nm)")
plt.title("Peak Wavelength Shift vs Time (Gaussian Fitted)")
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, "peak_wavelength_vs_time_from_CSV.png"))
plt.show()

# === CONTOUR PLOT: Wavelength vs Time ===
plt.figure(figsize=(10, 6))
cp = plt.contourf(times, wavelengths, S, levels=100, cmap=cm.inferno)
plt.xlabel("Time (s)")
plt.ylabel("Wavelength (nm)")
plt.title("PL Contour: Wavelength vs Time")
plt.colorbar(cp, label="Intensity (a.u.)")
plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, "pl_contour_from_CSV.png"))
plt.show()

# === MULTI-TIME OVERLAY: Wavelength vs Intensity ===
selected_indices = np.linspace(0, len(times) - 1, min(len(times), 10), dtype=int)
plt.figure()
for i in selected_indices:
    plt.plot(wavelengths, spectra[i], label=f"t={times[i]:.0f}s")
plt.xlabel("Wavelength (nm)")
plt.ylabel("Intensity (a.u.)")
plt.title("Wavelength vs Intensity for Selected Time Points")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, "wavelength_vs_intensity_overlay_from_CSV.png"))
plt.show()

# === OPTIONAL: OVERLAY OF GAUSSIAN FITS ===
plt.figure()
for i in selected_indices:
    raw = spectra[i]
    A_guess = np.max(raw)
    mu_guess = wavelengths[np.argmax(raw)]
    sigma_guess = 20
    offset_guess = np.min(raw)
    try:
        popt, _ = curve_fit(gaussian, wavelengths, raw,
                            p0=[A_guess, mu_guess, sigma_guess, offset_guess],
                            maxfev=5000)
        fit = gaussian(wavelengths, *popt)
        plt.plot(wavelengths, raw, alpha=0.4, label=f"Raw t={times[i]:.0f}s")
        plt.plot(wavelengths, fit, linestyle="--", label=f"Fit t={times[i]:.0f}s")
    except:
        plt.plot(wavelengths, raw, label=f"Raw t={times[i]:.0f}s (no fit)")

plt.xlabel("Wavelength (nm)")
plt.ylabel("Intensity (a.u.)")
plt.title("Gaussian Fits Over Raw Spectra")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(SAVE_DIR, "gaussian_fits_overlay.png"))
plt.show()

print("All plots generated and saved with Gaussian peak fitting.")
