from pm import PM100D
from flywheel import FlywheelController

pm = PM100D()
fw = FlywheelController(initial_slot=1)
print("configuring flywheel...")
L = []
for i in range(fw.slot_count):
	L.append((fw.get_current_slot() , pm.get_power()))
	fw._pulse_once()
	print((fw.get_current_slot() , pm.get_power()))

max = L[0][1] ; slot_1 = L[0][0]
for i,j in L:
	if j>max:
		max = j ; slot_1 = i

fw.go_to_slot(slot_1)
print("flywheel successfully configured. Currently at slot 1 (mirror).")

fw.current_slot = 1


while True:
	print("you are at slot",fw.get_current_slot())
	slot = int(input("input the slot you want to go to: "))
	fw.go_to_slot(slot)
