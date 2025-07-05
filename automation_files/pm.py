# thorlabs_pm100d.py
import ctypes
from ctypes import c_int, c_double, c_char_p, c_void_p, byref
import time

class PM100D:
    def __init__(self):
        # Hardcoded DLL path
        dll_path = r"C:\Program Files\IVI Foundation\VISA\Win64\Bin\PM100D_64.dll"
        self.lib = ctypes.windll.LoadLibrary(dll_path)
        self.handle = c_void_p()

        # Hardcoded VISA resource string (replace with your actual device ID)
        resource_str = b"USB0::0x1313::0x8072::P2001387::0::INSTR"  #

        # Define argument and return types for functions
        self.lib.PM100D_init.argtypes = [c_char_p, c_int, c_int, ctypes.POINTER(c_void_p)]
        self.lib.PM100D_init.restype = c_int

        status = self.lib.PM100D_init(resource_str, 0, 1, byref(self.handle))
        if status != 0:
            raise RuntimeError(f"Failed to init PM100D: {status}")

        self.lib.PM100D_setWavelength.argtypes = [c_void_p, c_double]
        self.lib.PM100D_measPower.argtypes = [c_void_p, ctypes.POINTER(c_double)]
        self.lib.PM100D_close.argtypes = [c_void_p]

    def set_wavelength(self, wavelength_nm):
        self.lib.PM100D_setWavelength(self.handle, c_double(wavelength_nm))

    def get_power(self):
        val = c_double()
        self.lib.PM100D_measPower(self.handle, byref(val))
        return val.value

    def get_power_over_time(self, duration_s, interval_s=0.05):
        """Sample power repeatedly over `duration_s` seconds"""
        readings = []
        start = time.time()
        while (time.time() - start) < duration_s:
            readings.append(self.get_power())
            time.sleep(interval_s)
        return readings

    def close(self):
        self.lib.PM100D_close(self.handle)
