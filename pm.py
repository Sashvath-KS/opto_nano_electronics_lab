# pm.py

import ctypes
from ctypes import c_int, c_double, c_char_p, c_void_p, byref
import json
import time


class PM100D:
    def __init__(self, setup_config_path="config_setup.json"):
        with open(setup_config_path) as f:
            config = json.load(f)["power_meter"]

        dll_path = config["dll_path"]
        resource_str = config["resource_string"].encode()

        self.lib = ctypes.windll.LoadLibrary(dll_path)
        self.handle = c_void_p()

        self.lib.PM100D_init.argtypes = [c_char_p, c_int, c_int, ctypes.POINTER(c_void_p)]
        self.lib.PM100D_init.restype = c_int

        status = self.lib.PM100D_init(resource_str, 0, 1, byref(self.handle))
        if status != 0:
            raise RuntimeError(f"[ERROR] Failed to init PM100D: {status}")

        self.lib.PM100D_setWavelength.argtypes = [c_void_p, c_double]
        self.lib.PM100D_measPower.argtypes = [c_void_p, ctypes.POINTER(c_double)]
        self.lib.PM100D_close.argtypes = [c_void_p]

    def set_wavelength(self, wavelength_nm):
        self.lib.PM100D_setWavelength(self.handle, c_double(wavelength_nm))

    def get_power(self):
        power = c_double()
        self.lib.PM100D_measPower(self.handle, byref(power))
        return power.value

    def get_power_over_time(self, duration_s, interval_s=0.1):
        """Continuously sample power for duration_s seconds."""
        readings = []
        timestamps = []
        start = time.time()
        while (time.time() - start) < duration_s:
            t = time.time() - start
            p = self.get_power()
            readings.append(p)
            timestamps.append(t)
            time.sleep(interval_s)
        return timestamps, readings

    def close(self):
        self.lib.PM100D_close(self.handle)
        print("[PowerMeter] Shutdown complete.")
