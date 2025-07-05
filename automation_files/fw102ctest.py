import ctypes
import time
import os

# Absolute path to the DLL
dll_path = r"C:\Program Files (x86)\Thorlabs\FWxC\Sample\Thorlabs_FWxC_PythonSDK\FilterWheel102_win32.dll"

# Load the DLL
fw = ctypes.WinDLL(dll_path)

# Define the function prototypes

# int FW102C_Open()
fw.FW102C_Open.restype = ctypes.c_int

# int FW102C_Close()
fw.FW102C_Close.restype = ctypes.c_int

# int FW102C_SetPosition(int position)
fw.FW102C_SetPosition.argtypes = [ctypes.c_int]
fw.FW102C_SetPosition.restype = ctypes.c_int

# int FW102C_GetPosition()
fw.FW102C_GetPosition.restype = ctypes.c_int

# --------- Usage Example ---------
if fw.FW102C_Open() == 0:
    print("[✓] Filter wheel opened successfully.")

    current_pos = fw.FW102C_GetPosition()
    print(f"[i] Current Position: {current_pos}")

    # Set a new position
    new_pos = 2
    result = fw.FW102C_SetPosition(new_pos)
    if result == 0:
        print(f"[→] Moved to position {new_pos}")
    else:
        print("[!] Failed to move to position.")

    time.sleep(1)  # wait for movement

    current_pos = fw.FW102C_GetPosition()
    print(f"[✓] New Position: {current_pos}")

    fw.FW102C_Close()
    print("[✓] Filter wheel closed.")
else:
    print("[✗] Failed to open filter wheel.")
