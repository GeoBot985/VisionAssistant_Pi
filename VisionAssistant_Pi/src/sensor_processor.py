"""
sensor_processor.py
-------------------
Consumes parsed sensor data from serial_listener and performs:
- smoothing
- sensor fusion (ToF + Ultrasonic)
- mismatch detection
- obstacle detection
- audio signaling
"""

from collections import deque
from datetime import datetime
import statistics
import audio_feedback

# === CONFIGURATION ===
TOF_BUFFER_LEN = 5
US_BUFFER_LEN = 5

# Rolling buffers for smoothing
tof_buffer = deque(maxlen=TOF_BUFFER_LEN)
us_buffer = deque(maxlen=US_BUFFER_LEN)

# Remember last valid readings
last_tof = None
last_us = None
last_zone = None


# === PROCESSING ENTRY ===
def process_entry(entry):
    """
    Handle a parsed sensor entry dict from serial_listener.
    Expected structure:
        {
          "type": "TOF" or "US",
          "timestamp": datetime,
          "values": [floats...]
        }
    """
    global last_tof, last_us

    stype = entry["type"]
    vals = entry["values"]
    ts = entry["timestamp"]

    if stype == "TOF":
        # --- Extract center 4×4 region from 8×8 grid (indexes 27–30, 35–38, 43–46, 51–54) ---
        if len(vals) >= 64:
            center_indices = [27, 28, 29, 30, 35, 36, 37, 38,
                              43, 44, 45, 46, 51, 52, 53, 54]
            center_vals = [vals[i] for i in center_indices if vals[i] > 0]
        else:
            center_vals = vals

        if center_vals:
            avg_tof = sum(center_vals) / len(center_vals)
            tof_buffer.append(avg_tof)
            last_tof = statistics.mean(tof_buffer)

    elif stype == "US":
        dist = vals[0]
        us_buffer.append(dist)
        last_us = statistics.mean(us_buffer)

    # --- Only proceed if both sensors have data ---
    if last_tof is not None and last_us is not None:
        fuse_and_check(ts, last_tof, last_us)


# === SENSOR FUSION + ALERT LOGIC ===
def fuse_and_check(ts, tof_m, us_cm):
    """Fuse ToF and Ultrasonic readings, check mismatch and proximity zones."""
    global last_zone

    us_m = us_cm / 100.0
    fused_distance = min(tof_m, us_m)

    # --- Mismatch detection ---
    # Significant disagreement (30% or more)
    if abs(tof_m - us_m) > 0.3 * min(tof_m, us_m):
        print(f"[{ts.strftime('%H:%M:%S')}] ⚠️  Mismatch: ToF={tof_m:.2f}m  US={us_m:.2f}m")
        audio_feedback.beep("mismatch")

    # --- Zone determination ---
    if fused_distance > 1.5:
        zone = "none"
    elif fused_distance > 1.0:
        zone = "far"
    elif fused_distance > 0.75:
        zone = "mid"
    elif fused_distance > 0.2:
        zone = "near"
    else:
        zone = "close"

    # --- Only trigger when zone changes ---
    if zone != last_zone:
        last_zone = zone
        if zone != "none":
            audio_feedback.beep(zone)
        print(f"[{ts.strftime('%H:%M:%S')}] Zone={zone.upper()} | Fused={fused_distance:.2f} m")


# === TEST HARNESS ===
if __name__ == "__main__":
    # Fake ToF + US sample data for testing
    sample_tof = {"type": "TOF", "timestamp": datetime.now(),
                  "values": [0.7, 0.8, 0.9, 0.8] * 16}  # simulate 64 readings
    sample_us = {"type": "US", "timestamp": datetime.now(),
                 "values": [65.0]}  # cm

    process_entry(sample_tof)
    process_entry(sample_us)
