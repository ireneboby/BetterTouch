import numpy as np
from matplotlib import pyplot as plt

x_high = [150, 156, 157, 158, 167, 164, 157, 151, 158, 150, 169, 137, 171, 162, 161, 167, 167, 161, 135, 172, 161, 135, 172, 157, 172, 165, 174, 168, 179, 182, 169, 170, 166, 163, 168, 182, 149, 175, 156, 168, 159, 151, 170, 154, 169, 162, 167, 183]
x_high = np.array(x_high) + 25
x_low = [151, 154, 156, 158, 171, 172, 165, 153, 167, 157, 174, 141, 181, 215, 8, 6, 4, 5, 5, 1, 4, 2, 3, 0, 2, 4, 3, 1, 3, 3, 0, 4, 7, 3, 4, 180, 183, 169, 153, 172, 154, 170, 161, 161, 180, 153, 160, 171]
x_low = np.array(x_low) + 25
x_e = np.random.uniform(low=13, high=15, size=48)
x_num = np.arange(1, 49)

y_high = [48, 47, 52, 50, 51, 51, 46, 57, 52, 51, 53, 50, 50, 57, 52, 45, 52, 54, 54, 48, 54, 50, 59, 60]
y_high = np.array(y_high) + 25
y_low = [49, 56, 64, 67, 81, 87, 1, 0, 2,  4,  2,  3,  1,  0,  0,  4,  95,  89,  74,  64,  65,  59,  67,  67]
y_low = np.array(y_low) + 25
y_e = np.random.uniform(low=13, high=15, size=24)
y_num = np.arange(49, 73)

plt.style.use("dark_background")

plt.errorbar(x_num, x_high, x_e, marker='^', label="X-Axis (No Obstruction)")
plt.errorbar(x_num, x_low, x_e, marker='^', label="X-Axis (With Obstruction)")

plt.errorbar(y_num, y_high, y_e, marker='^', label="Y-Axis (No Obstruction)")
plt.errorbar(y_num, y_low, y_e, marker='^', label="Y-Axis (With Obstruction)")

plt.ylim(0, 300)
plt.xlabel("Photodiode Position")
plt.ylabel("Analog Reading (mV)") 
plt.title("Photodiode Readings for a Single Scan")
plt.grid()
plt.legend()
plt.show()