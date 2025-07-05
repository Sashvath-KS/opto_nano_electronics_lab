import os
import time
import datetime
import numpy as np
import ctypes
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D

# === CONFIGURATION ===
integration_time_sec = 0.02
measurement_duration = 180  # 3 minutes
interval_sec = 1
SAVE_DIR = "short_term_light_degradation"
DLL_PATH = "C:\\Program Files\\IVI Foundation\\VISA\\Win64\\Bin\\TLCCS_64.dll"

os.makedirs(SAVE_DIR, exist_ok=True)

# === LOAD DLL AND DEFINE SPECTROMETER CLASS ===
lib = ctypes.cdll.LoadLibrary(DLL_PATH)

class CCS_Spectrometer:
    def __init__(self):
        self.ccs_handle = ctypes.c_int(0)
        result = lib.tlccs_init(b"USB0::0x1313::0x8087::M00414815::RAW", 1, 1, ctypes.byref(self.ccs_handle))
        if result != 0:
            raise RuntimeError("Failed to open CCS175 device")
        lib.tlccs_setIntegrationTime(self.ccs_handle, ctypes.c_double(integration_time_sec))

    def get_data(self):
        num_pixels = 3648
        wavelengths = (ctypes.c_double * num_pixels)()
        intensities = (ctypes.c_double * num_pixels)()
        lib.tlccs_startScan(self.ccs_handle)
        lib.tlccs_getWavelengthData(self.ccs_handle, 0, ctypes.byref(wavelengths), None, None)
        lib.tlccs_getScanData(self.ccs_handle, ctypes.byref(intensities))
        return np.array(wavelengths), np.array(intensities)

def save_spectrum(wavelengths, intensities, timestamp):
    data = np.column_stack((wavelengths, intensities))
    np.savetxt(os.path.join(SAVE_DIR, f"spectrum_{timestamp}.csv"), data, delimiter=",", header="Wavelength,Intensity", comments='')

def save_plot(wavelengths, intensities, timestamp):
    peak_idx = np.argmax(intensities)
    peak_wavelength = wavelengths[peak_idx]
    peak_intensity = intensities[peak_idx]

    plt.figure()
    plt.plot(wavelengths, intensities, label=f"Peak λ = {peak_wavelength:.1f} nm | {peak_intensity:.2f} a.u.")
    plt.axvline(peak_wavelength, color='r', linestyle='--', alpha=0.6, label="Peak Position")
    plt.plot(peak_wavelength, peak_intensity, 'ro')
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity (a.u.)")
    plt.title(f"PL Spectrum @ {timestamp}")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(SAVE_DIR, f"spectrum_{timestamp}.png"))
    plt.close()

def main():
    spec = CCS_Spectrometer()

    input("Remove sample and press Enter to take background reading...")
    wavelengths, background = spec.get_data()
    input("Insert sample and press Enter to start measurement...")

    plt.ion()
    fig, ax = plt.subplots()
    line, = ax.plot(wavelengths, np.zeros_like(wavelengths))
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Intensity (a.u.)")
    ax.set_title("Live PL Spectrum")

    start_time = time.time()
    times = []
    spectra = []
    peak_intensities = []

    while (time.time() - start_time) < measurement_duration:
        current_time = time.time() - start_time
        timestamp = datetime.datetime.now().strftime("%H-%M-%S")

        _, raw_intensity = spec.get_data()
        spectrum = raw_intensity - background
        spectra.append(spectrum)
        times.append(current_time)
        peak_intensities.append(np.max(spectrum))

        line.set_ydata(spectrum)
        ax.set_ylim(0, np.max(spectrum) * 1.1)
        ax.set_title(f"Live PL Spectrum at t = {current_time:.1f} s")
        fig.canvas.draw()
        fig.canvas.flush_events()

        save_spectrum(wavelengths, spectrum, timestamp)
        save_plot(wavelengths, spectrum, timestamp)

        print(f"Recorded @ {current_time:.1f} s | Max Intensity: {np.max(spectrum):.2f}")
        time.sleep(interval_sec)

    plt.ioff()
    plt.show()

    np.save(os.path.join(SAVE_DIR, "pl_data.npy"), {
        'wavelengths': wavelengths,
        'times': np.array(times),
        'spectra': np.array(spectra),
        'peak_intensities': np.array(peak_intensities)
    })

    # === 3D SURFACE PLOT ===
    T, WL = np.meshgrid(times, wavelengths)
    S = np.array(spectra).T
    fig3d = plt.figure(figsize=(10, 6))
    ax3d = fig3d.add_subplot(111, projection='3d')
    ax3d.plot_surface(WL, T, S, cmap=cm.inferno)
    ax3d.set_xlabel("Wavelength (nm)")
    ax3d.set_ylabel("Time (s)")
    ax3d.set_zlabel("Intensity")
    ax3d.set_title("PL Intensity vs Wavelength vs Time")
    plt.tight_layout()
    plt.savefig(os.path.join(SAVE_DIR, "3D_PL_Surface.png"))
    plt.show()

    # === PEAK INTENSITY VS TIME ===
    plt.figure()
    plt.plot(times, peak_intensities, marker='o', color='green')
    plt.xlabel("Time (s)")
    plt.ylabel("Peak Intensity (a.u.)")
    plt.title("Peak Intensity vs Time (Degradation)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(SAVE_DIR, "peak_intensity_vs_time.png"))
    plt.show()

    # === CONTOUR PLOT ===
    plt.figure(figsize=(10, 6))
    cp = plt.contourf(times, wavelengths, S, levels=100, cmap=cm.inferno)
    plt.xlabel("Time (s)")
    plt.ylabel("Wavelength (nm)")
    plt.title("PL Contour: Wavelength vs Time")
    plt.colorbar(cp, label="Intensity (a.u.)")
    plt.tight_layout()
    plt.savefig(os.path.join(SAVE_DIR, "pl_contour_plot.png"))
    plt.show()

if __name__ == "__main__":
    main()