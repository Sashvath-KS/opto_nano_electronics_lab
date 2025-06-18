import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# Physical constants
h = 6.626e-34  # Planck constant [J·s]
c = 299792458  # Speed of light [m/s]
k = 1.381e-23  # Boltzmann constant [J/K]

# Planck's law function (with overflow protection)
def planck_law(l, T, a):
    exponent = np.clip((h * c) / (l * k * T), 1e-10, 700)
    B = (2 * h * c**2) / (l**5 * np.expm1(exponent))
    return a * B

# Load data
data = np.loadtxt('data.txt', delimiter=',')
independent_variable = data[:, 0] * 1e-9  # Convert nm → meters
measured_quantity = data[:, 1]

# Keep data in 500–950 nm range (adjust as needed)
mask = (independent_variable >= 500e-9) & (independent_variable <= 950e-9)
wavelengths_trimmed = independent_variable[mask]
intensities_trimmed = measured_quantity[mask]

# Normalize intensity
measured_quantity /= np.max(measured_quantity)
intensities_trimmed /= np.max(intensities_trimmed)

lambda_peak = independent_variable[np.argmax(measured_quantity)]
T_wien = (2.898e-3) / lambda_peak  # λ in meters
print(f"Wien-estimated Temperature: {T_wien:.2f} K")

# Initial guess for T and scaling factor
initial_guess = [T_wien, 1.0]

# Fit
parameters, covariance = curve_fit(planck_law, independent_variable, measured_quantity, p0=initial_guess)
errors = np.sqrt(np.diag(covariance))

trim_para , trim_cov = curve_fit(planck_law, wavelengths_trimmed, intensities_trimmed, p0=initial_guess)
trim_errors = np.sqrt(np.diag(trim_cov))

# Goodness of fit: reduced chi-squared
residuals = measured_quantity - planck_law(independent_variable, *parameters)
chi_squared = np.sum((residuals)**2)
dof = len(measured_quantity) - len(parameters)  # degrees of freedom
reduced_chi_squared = chi_squared / dof

print("parameters=",parameters)
print("errors=",errors)
print("reduced_chi_square=",reduced_chi_squared)
print("trimmed parameters=", trim_para)
print("trimmed errors=" , trim_errors)

# Plotting
X = np.linspace(np.min(independent_variable), np.max(independent_variable), 1000)
Y_fit = planck_law(X, *parameters)
Y_wien = planck_law(X, T_wien, parameters[1])
Y_trim = planck_law(X , *trim_para)

plt.figure(figsize=(8, 5))
plt.scatter(independent_variable * 1e9, measured_quantity, s=10, facecolors='none', edgecolors='blue', label='Data')  # back to nm
plt.plot(X * 1e9, Y_fit, color='red', label='Fit')  # back to nm
plt.plot(X * 1e9, Y_wien, label="wien" )
plt.plot(X * 1e9, Y_trim, color = "black",label="trim") 
plt.title("Planck Fit to Spectrometer Data")
plt.xlabel("Wavelength (nm)")
plt.ylabel("Normalized Intensity")
plt.legend()

param_text = (
    f"T = {parameters[0]:.1f} ± {errors[0]:.1f} K\n"
    f"a = {parameters[1]:.3f} ± {errors[1]:.3f}\n"
    f"Reduced χ² = {reduced_chi_squared:.4f}"
)
plt.text(0.95, 0.05, param_text, transform=plt.gca().transAxes,
         fontsize=10, verticalalignment='bottom', horizontalalignment='right',
         bbox=dict(facecolor="white", alpha=0.7, edgecolor="black"))

plt.tight_layout()
plt.show()

