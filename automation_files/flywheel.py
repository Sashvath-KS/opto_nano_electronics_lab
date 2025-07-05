# flywheel.py

import time
import warnings
from pymeasure.adapters import VISAAdapter
from pymeasure.instruments.agilent import Agilent33500

class FlywheelController:
    def __init__(self, visa_address="USB0::0x0957::0x1607::MY50002588::INSTR", slot_count=6, initial_slot=1):
        warnings.simplefilter("ignore", FutureWarning)
        self.slot_count = slot_count
        self.initial_slot = self.current_slot = initial_slot

        adapter = VISAAdapter(visa_address)
        self.gen = Agilent33500(adapter)

        # Configure waveform generator
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

        # Increment and wrap slot
        self.current_slot += 1
        if self.current_slot > self.slot_count:
            self.current_slot = 1

    def go_to_slot(self, target_slot, delay_s=0.2):
        """
        Rotate to target slot from current known slot.
        Returns: updated current slot
        """
        if not (1 <= target_slot <= self.slot_count):
            raise ValueError(f"Target slot must be in 1 to {self.slot_count}")

        while self.current_slot != target_slot:
            self._pulse_once()
            #if self.current_slot != target_slot:
            #    time.sleep(delay_s)

        return self.current_slot

    def step(self, count=1, delay_s=0.1):
        """Advance N steps forward."""
        for i in range(count % self.slot_count):
            self._pulse_once()
            if i < count - 1:
                time.sleep(delay_s)

    def get_current_slot(self):
        return self.current_slot

    def reset_slot(self, known_slot):
        """Reset the current slot manually if needed."""
        if not (1 <= known_slot <= self.slot_count):
            raise ValueError("Invalid slot number")
        self.current_slot = known_slot

    def close(self):
        self.gen.output = False
        self.gen.adapter.connection.close()
