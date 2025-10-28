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
import time
from event_bus import EVENT_QUEUE, VISION_QUEUE
import numpy as np
import threading

# === SMOOTHING CONFIG ===
decay_rate = 0.7
prev_frame = np.zeros((8, 8), dtype=np.float32)

def median3x3(img):
    s = [
        img,
        np.roll(img, 1, 0), np.roll(img, -1, 0),
        np.roll(img, 1, 1), np.roll(img, -1, 1),
        np.roll(np.roll(img, 1, 0), 1, 1),
        np.roll(np.roll(img, 1, 0), -1, 1),
        np.roll(np.roll(img, -1, 0), 1, 1),
        np.roll(np.roll(img, -1, 0), -1, 1)
    ]
    return np.median(np.stack(s, axis=0), axis=0)


# === CONFIGURATION ===
TOF_BUFFER_LEN = 5
US_BUFFER_LEN = 5

last_vision_trigger = 0
VISION_COOLDOWN = 10  # seconds

tof_buffer = deque(maxlen=TOF_BUFFER_LEN)
us_buffer = deque(maxlen=US_BUFFER_LEN)

last_tof = None
last_us = None
last_zone = None

# Shared for visualizer
last_tof_frame = [0.0] * 64
last_fused_distance = 0.0
last_ultrasonic_cm = 0.0


# === MAIN PROCESS ===
# === MAIN PROCESS ===
def process_entry(entry):
    """Handle a parsed sensor entry dict from serial_listener."""
    global last_tof, last_us, prev_frame, last_tof_frame

    stype = entry["type"]
    vals = entry["values"]
    ts = entry["timestamp"]

    #print(f"[PROC] Got {stype} entry ({len(vals)} values)")

    if stype == "TOF":
        if len(vals) >= 64:
            center_indices = [27, 28, 29, 30, 35, 36, 37, 38,
                              43, 44, 45, 46, 51, 52, 53, 54]
            center_vals = [vals[i] for i in center_indices if vals[i] > 0]
        else:
            center_vals = vals

        # --- reshape and apply smoothing ---
        if len(vals) == 64:
            frame = np.array(vals, dtype=np.float32).reshape((8, 8))

            prev_frame[:] = decay_rate * prev_frame + (1 - decay_rate) * frame
            smoothed = median3x3(prev_frame)

            MAX_RANGE = 4.0
            smoothed = np.clip(smoothed, 0.0, MAX_RANGE)

            arr_min = np.nanmin(smoothed)
            arr_max = np.nanmax(smoothed)
            range_span = arr_max - arr_min if arr_max > arr_min else 1.0

            scaled = 0.9 * (smoothed / MAX_RANGE) + 0.1 * ((smoothed - arr_min) / range_span)
            scaled = np.clip(scaled, 0.0, 1.0)

            last_tof_frame = (scaled * MAX_RANGE).flatten().tolist()

        # ✅ assign numeric ToF mean for fusion
        last_tof = float(np.mean(center_vals)) if center_vals else None


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
    global last_zone, last_fused_distance, last_ultrasonic_cm, last_vision_trigger

    # ✅ Prevent NoneType comparison crash
    if tof_m is None or us_cm is None:
        #print("[WARN] Skipping fusion due to missing sensor data.")
        return

    #print(f"[PROC] fuse_and_check() → ToF={tof_m:.2f}m  US={us_cm:.1f}cm")
    #print(f"[PROC] fuse_and_check() → ToF={tof_m:.2f}m  US={us_cm:.1f}cm")

    us_m = us_cm / 100.0
    fused_distance = min(tof_m, us_m)
    last_fused_distance = fused_distance
    last_ultrasonic_cm = us_cm

    # --- Zone determination ---
    if fused_distance > 2.0:
        zone = "none"
    elif fused_distance > 1.5:
        zone = "far"
    elif fused_distance > 1.0:
        zone = "mid"
    elif fused_distance > 0.35:
        zone = "near"
    else:
        zone = "close"

    # --- Only trigger when zone changes ---
    if zone != last_zone:
        last_zone = zone
        if zone != "none":
            #audio_feedback.beep(zone)
            threading.Thread(target=audio_feedback.beep, args=(zone,), daemon=True).start()
        print(f"[{ts.strftime('%H:%M:%S')}] Zone={zone.upper()} | Fused={fused_distance:.2f} m")

        # 🧠 Vision trigger if very close
        now = time.time()
        if zone == "close" and now - last_vision_trigger > VISION_COOLDOWN:
            last_vision_trigger = now
            VISION_QUEUE.put({"type": "vision_request"})
            print(f"[{ts.strftime('%H:%M:%S')}] 🎥 Vision trigger fired (cooldown ok)")
    
    #print(f"[DEBUG] fuse_and_check() called — ToF={tof_m:.2f} m  US={us_cm:.1f} cm")


# === TEST HARNESS ===
if __name__ == "__main__":
    sample_tof = {"type": "TOF", "timestamp": datetime.now(),
                  "values": [0.7, 0.8, 0.9, 0.8] * 16}
    sample_us = {"type": "US", "timestamp": datetime.now(),
                 "values": [65.0]}
    process_entry(sample_tof)
    process_entry(sample_us)
