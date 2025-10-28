import datetime
import time
import random
import math

# Configuration
UPDATE_RATE_HZ = 5        # how many updates per second
TOF_NOISE_MM = 40         # ± range noise
US_NOISE_CM = 1.5         # ± ultrasonic jitter
TOF_BASE_M = 0.8          # nominal distance to nearest surface (m)
US_BASE_CM = 70           # nominal distance for ultrasonic (cm)
SENSOR_COUNT = 64         # 8x8 ToF grid

def generate_tof_frame(base_m):
    """Generate a realistic 8x8 grid with small variance and subtle gradients."""
    frame = []
    t = time.time()
    # Simulate slow drift and localized noise
    for i in range(SENSOR_COUNT):
        # Create a soft "wave" pattern across the grid
        angle = (i % 8) / 8 * math.pi * 2
        variation = math.sin(angle + t / 2.0) * 0.05  # small oscillation ±0.05 m
        noise = random.uniform(-TOF_NOISE_MM / 1000.0, TOF_NOISE_MM / 1000.0)
        value_m = max(0.0, base_m + variation + noise)
        frame.append(round(value_m, 1))
    return frame

def generate_ultrasonic(base_cm):
    """Simulate single-beam ultrasonic distance."""
    t = time.time()
    slow_wave = math.sin(t / 3.0) * 3.0
    noise = random.uniform(-US_NOISE_CM, US_NOISE_CM)
    return max(0.0, base_cm + slow_wave + noise)

def main():
    print("Simulating ToF and Ultrasonic sensor stream...\n")
    while True:
        # Get both epoch and human-readable timestamps
        timestamp = int(time.time())
        human_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

        # Occasionally simulate an approaching object
        approach_factor = 0.2 * math.sin(time.time() / 5.0)
        tof_frame = generate_tof_frame(TOF_BASE_M + approach_factor)
        us_value = generate_ultrasonic(US_BASE_CM - approach_factor * 100)

        # Format and print both sensors
        tof_payload = ",".join(f"{v:.1f}" for v in tof_frame)
        us_payload = f"{us_value:.1f}"

        print(f"TOF|{human_time}|[{tof_payload}]")
        print(f"US|{human_time}|[{us_payload}]")

        time.sleep(1.0 / UPDATE_RATE_HZ)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
