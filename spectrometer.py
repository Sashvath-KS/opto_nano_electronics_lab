# spectrometer.py

import ctypes
import numpy as np
import threading
import time
import json


class CCS_Spectrometer:
    def __init__(self, setup_config_path="config_setup.json"):
        with open(setup_config_path) as f:
            config = json.load(f)["spectrometer"]

        self.simulate = config.get("simulate", False)
        self.integration_time = 0.5
        self.background = None
        self.mask_range = (None, None)
        self.streaming = False
        self._stop_event = threading.Event()
        self.scan_thread = None

        if self.simulate:
            print("[SIMULATION] CCS175 Spectrometer active")
            return

        dll_path = config["dll_path"]
        resource = config["resource_string"].encode()
        self.lib = ctypes.cdll.LoadLibrary(dll_path)
        self.handle = ctypes.c_int(0)

        status = self.lib.tlccs_init(resource, 1, 1, ctypes.byref(self.handle))
        if status != 0:
            raise RuntimeError(f"[ERROR] Could not initialize CCS spectrometer (code {status})")

        self.set_integration_time(0.5)

    def set_integration_time(self, seconds):
        self.integration_time = seconds
        if not self.simulate:
            self.lib.tlccs_setIntegrationTime(self.handle, ctypes.c_double(seconds))

    def set_mask_range(self, min_nm, max_nm):
        self.mask_range = (min_nm, max_nm)

    def capture_background(self):
        _, bg = self.get_raw_spectrum()
        if self.mask_range[0] and self.mask_range[1]:
            wl, _ = self.get_raw_spectrum()
            mask = (wl >= self.mask_range[0]) & (wl <= self.mask_range[1])
            bg = bg[mask]
        self.background = bg
        return bg

    def get_raw_spectrum(self):
        if self.simulate:
            wl = np.linspace(200, 1100, 3648)
            inten = 100 * np.exp(-((wl - 800) ** 2) / (2 * 30 ** 2)) + np.random.normal(0, 1, wl.shape)
            return wl, inten

        num_pixels = 3648
        wavelengths = (ctypes.c_double * num_pixels)()
        intensities = (ctypes.c_double * num_pixels)()

        self.lib.tlccs_startScan(self.handle)
        self.lib.tlccs_getWavelengthData(self.handle, 0, ctypes.byref(wavelengths), None, None)
        self.lib.tlccs_getScanData(self.handle, ctypes.byref(intensities))

        return np.array(wavelengths), np.array(intensities)

    def get_spectrum(self, correct_bg=True):
        wl, inten = self.get_raw_spectrum()

        if self.mask_range[0] and self.mask_range[1]:
            mask = (wl >= self.mask_range[0]) & (wl <= self.mask_range[1])
            wl, inten = wl[mask], inten[mask]

        if correct_bg and self.background is not None:
            inten = inten - self.background
            inten = np.clip(inten, 0, None)

        return wl, inten

    def start_stream(self, callback, delay=0.2, correct_bg=True):
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

    def stop_stream(self):
        self._stop_event.set()
        if self.scan_thread:
            self.scan_thread.join()
        self.streaming = False

    def shutdown(self):
        if not self.simulate:
            self.lib.tlccs_close(self.handle)
        print("[Spectrometer] Shutdown complete.")

    def get_info(self):
        if self.simulate:
            return {
                "serial": "SIM000",
                "model": "CCS175 Simulated",
                "pixels": 3648,
                "wavelength_range": [200, 1100]
            }
        serial = ctypes.create_string_buffer(64)
        self.lib.tlccs_getInstrumentSerialNumber(self.handle, serial, 64)
        return {
            "serial": serial.value.decode(),
            "model": "CCS175",
            "pixels": 3648,
            "wavelength_range": [200, 1100]
        }
