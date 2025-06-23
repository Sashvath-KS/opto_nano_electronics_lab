import os
import time
import datetime
import numpy as np
import ctypes
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import messagebox
from tkinter import simpledialog

x = 1.0
intensity_thresh = 0.0
peak_shift_tol = 0.0
PLOT_LIVE = True

SAVE_DIR = "spectra_data"
os.makedirs(SAVE_DIR, exist_ok=True)

DLL_PATH = "C:\\Program Files\\IVI Foundation\\VISA\\Win64\\Bin\\TLCCS_64.dll"
lib = ctypes.cdll.LoadLibrary(DLL_PATH)

class CCS_Spectrometer:
    def __init__(self):
        self.ccs_handle = ctypes.c_int(0)
        result = lib.tlccs_init(b"USB0::0x1313::0x8087::M00414815::RAW", 1, 1, ctypes.byref(self.ccs_handle))
        if result != 0:
            raise RuntimeError("Failed to open CCS175 device")
        integration_time = ctypes.c_double(10.0e-3)
        lib.tlccs_setIntegrationTime(self.ccs_handle, integration_time)

    def get_data(self):
        num_pixels = 3648
        wavelengths = (ctypes.c_double * num_pixels)()
        intensities = (ctypes.c_double * num_pixels)()

        lib.tlccs_startScan(self.ccs_handle)
        lib.tlccs_getWavelengthData(self.ccs_handle, 0, ctypes.byref(wavelengths), ctypes.c_void_p(None), ctypes.c_void_p(None))
        lib.tlccs_getScanData(self.ccs_handle, ctypes.byref(intensities))

        return np.array(wavelengths), np.array(intensities)

def save_spectrum(wavelengths, intensities, timestamp):
    filename = os.path.join(SAVE_DIR, f"spectrum_{timestamp}.csv")
    data = np.column_stack((wavelengths, intensities))
    np.savetxt(filename, data, delimiter=",", header="Wavelength,Intensity", comments='')
    print(f"Saved CSV: {filename}")

def plot_spectrum(wavelengths, intensities, timestamp):
    plt.clf()
    plt.plot(wavelengths, intensities, label=f"Peak: {np.max(intensities):.2f} a.u.")
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity (a.u.)")
    plt.title(f"PL Spectrum @ {timestamp}")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    png_filename = os.path.join(SAVE_DIR, f"spectrum_{timestamp}.png")
    plt.savefig(png_filename)
    print(f"Saved PNG: {png_filename}")

    if PLOT_LIVE:
        plt.pause(0.01)

def gui_input():
    global x, intensity_thresh, peak_shift_tol
    root = tk.Tk()
    root.withdraw()
    try:
        x = float(simpledialog.askstring("Input", "Enter measurement interval (in minutes):"))
        intensity_thresh = float(simpledialog.askstring("Input", "Enter intensity drop threshold (a.u.):"))
        peak_shift_tol = float(simpledialog.askstring("Input", "Enter peak shift tolerance (nm):"))
    except Exception as e:
        messagebox.showerror("Input Error", str(e))
        root.quit()
    root.destroy()

def main():
    gui_input()
    spec = CCS_Spectrometer()
    if PLOT_LIVE:
        plt.ion()
        plt.figure(figsize=(10, 5))

    ref_peak_wavelength = None

    try:
        while True:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            wavelengths, intensities = spec.get_data()
            save_spectrum(wavelengths, intensities, timestamp)
            plot_spectrum(wavelengths, intensities, timestamp)

            peak_intensity = np.max(intensities)
            peak_index = np.argmax(intensities)
            peak_wavelength = wavelengths[peak_index] if 0 <= peak_index < len(wavelengths) else None

            if peak_wavelength is None:
                print("Invalid peak index detected.")
                continue

            print(f"Peak λ = {peak_wavelength:.2f} nm | Intensity = {peak_intensity:.2f} a.u.")

            if ref_peak_wavelength is None:
                ref_peak_wavelength = peak_wavelength

            if peak_intensity < intensity_thresh:
                print(f"ALERT: Peak intensity dropped to {peak_intensity:.2f} a.u. at {timestamp}")

            if abs(peak_wavelength - ref_peak_wavelength) > peak_shift_tol:
                print(f"ALERT: Peak wavelength shifted by {abs(peak_wavelength - ref_peak_wavelength):.2f} nm at {timestamp}")

            print(f"Waiting {x} minutes...\n")
            time.sleep(x * 60)

    except KeyboardInterrupt:
        print("Measurement stopped.")
        if PLOT_LIVE:
            plt.ioff()
            plt.show()

if __name__ == "__main__":
    main()
