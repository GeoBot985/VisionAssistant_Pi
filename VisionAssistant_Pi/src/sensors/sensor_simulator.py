"""
sensor_simulator.py — Intelligent live data generator for testing VisionAssist
Simulates ToF (8×8 grid) and Ultrasonic distance cycles, calling sensor_processor directly.
"""

import time, math, random
from datetime import datetime
from sensors import sensor_processor as sp


# === CONFIG ===
MODE = "oscillate"   # "steady", "approach", "oscillate", "random"
UPDATE_RATE_HZ = 1   # updates per second
CYCLE_TIME = 10      # seconds per full oscillation
TOF_GRID = 64        # 8x8 ToF array
TOF_BASE_M = 1.5     # max range (m)
TOF_MIN_M = 0.15     # closest (m)
US_BASE_CM = 150     # max ultrasonic (cm)
US_MIN_CM = 20
NOISE_TOF = 0.03     # ±m noise
NOISE_US = 2.0       # ±cm noise


def simulate_distance(t):
    """Return synthetic ToF(m) and US(cm) values based on time + mode."""
    if MODE == "steady":
        d_m = TOF_BASE_M
    elif MODE == "approach":
        # gradually move closer until loop end
        phase = (t % CYCLE_TIME) / CYCLE_TIME
        d_m = TOF_BASE_M - (TOF_BASE_M - TOF_MIN_M) * phase
    elif MODE == "oscillate":
        # smooth back-and-forth sine wave motion
        phase = (math.sin(t / CYCLE_TIME * 2 * math.pi) + 1) / 2
        d_m = TOF_MIN_M + (TOF_BASE_M - TOF_MIN_M) * phase
    elif MODE == "random":
        d_m = random.uniform(TOF_MIN_M, TOF_BASE_M)
    else:
        d_m = TOF_BASE_M

    d_m += random.uniform(-NOISE_TOF, NOISE_TOF)
    d_m = max(TOF_MIN_M, min(TOF_BASE_M, d_m))

    d_cm = max(US_MIN_CM, min(US_BASE_CM, d_m * 100 + random.uniform(-NOISE_US, NOISE_US)))
    return round(d_m, 2), round(d_cm, 1)


def generate_tof_frame(center_m):
    """Produce an 8×8 frame with gradient depth variation around a central value."""
    frame = []
    for i in range(TOF_GRID):
        # small sinusoidal pattern across grid
        row, col = divmod(i, 8)
        offset = math.sin((row + col) / 4.0) * 0.05
        noise = random.uniform(-NOISE_TOF, NOISE_TOF)
        frame.append(max(0.0, center_m + offset + noise))
    return frame


def main():
    print("🧪 Running intelligent sensor simulator...")
    interval = 1.0 / UPDATE_RATE_HZ
    start_time = time.time()

    try:
        while True:
            t = time.time() - start_time
            tof_m, us_cm = simulate_distance(t)

            tof_entry = {
                "type": "TOF",
                "timestamp": datetime.now(),
                "values": generate_tof_frame(tof_m),
            }
            us_entry = {
                "type": "US",
                "timestamp": datetime.now(),
                "values": [us_cm],
            }

            # send directly to processor
            sp.process_entry(tof_entry)
            sp.process_entry(us_entry)

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n🛑 Simulation stopped.")


if __name__ == "__main__":
    main()
