# flywheel.py

import time
import json
import warnings
from pymeasure.adapters import VISAAdapter
from pymeasure.instruments.agilent import Agilent33500


class FlywheelController:
    def __init__(self, setup_config_path="config_setup.json"):
        warnings.simplefilter("ignore", FutureWarning)

        with open(setup_config_path) as f:
            config = json.load(f)["flywheel"]

        self.slot_count = config.get("slot_count", 6)
        self.slot_mapping = config.get("slot_mapping", {})
        self.current_slot = 1  # default software-assumed position

        visa_address = config["visa_address"]
        adapter = VISAAdapter(visa_address)
        self.gen = Agilent33500(adapter)

        # Configure function generator
        self.gen.shape = "SQU"
        self.gen.frequency = 1
        self.gen.amplitude = 2.5
        self.gen.offset = 1.25
        self.gen.burst_state = True
        self.gen.burst_count = 1
        self.gen.trigger_source = "BUS"
        self.gen.output = False

    def _pulse_once(self):
        self.gen.output = True
        self.gen.trigger()
        time.sleep(1.2)
        self.gen.output = False

        self.current_slot += 1
        if self.current_slot > self.slot_count:
            self.current_slot = 1

    def go_to_slot(self, target_slot):
        if not (1 <= target_slot <= self.slot_count):
            raise ValueError(f"[Flywheel] Invalid slot {target_slot}")

        if target_slot == self.current_slot:
            return self.current_slot

        max_attempts = self.slot_count
        attempts = 0

        while self.current_slot != target_slot and attempts < max_attempts:
            self._pulse_once()
            attempts += 1

        if self.current_slot != target_slot:
            raise RuntimeError(f"[Flywheel] Failed to reach slot {target_slot}")

        return self.current_slot

    def step(self, n=1):
        for _ in range(n % self.slot_count):
            self._pulse_once()

    def reset_slot(self, known_slot):
        """Forcefully set the current software-tracked slot."""
        if not (1 <= known_slot <= self.slot_count):
            raise ValueError("Invalid slot number")
        self.current_slot = known_slot

    def get_current_slot(self):
        return self.current_slot

    def close(self):
        self.gen.output = False
        self.gen.adapter.connection.close()
        print("[Flywheel] Shutdown complete.")
