import serial
import numpy as np
import time
from datetime import datetime
from sensors import sensor_processor as sp  # ✅ unified import (critical)
from event_bus import EVENT_QUEUE

PORT = "/dev/ttyUSB0"
BAUD = 115200
GRID_W = GRID_H = 8
FRAME_SIZE = 2 + GRID_W * GRID_H * 2 + 4 + 1
HEADER = b"\xAA\x55"
RECONNECT_DELAY = 3.0

def run_bridge():
    """Continuously read binary sensor frames and feed VisionAssist processor."""
    ser = None
    last_fps_print = time.time()
    frames = 0

    while True:
        try:
            if ser is None or not ser.is_open:
                print(f"🔌 Connecting to {PORT} @ {BAUD}...")
                ser = serial.Serial(PORT, BAUD, timeout=0.1)
                print("✅ Serial connection established.")

            buf = bytearray()
            while True:
                chunk = ser.read(256)
                if not chunk:
                    time.sleep(0.01)  # or 0.02 to yield CPU
                    continue
                buf.extend(chunk)

                while len(buf) >= FRAME_SIZE:
                    idx = buf.find(HEADER)
                    if idx == -1:
                        buf.clear()
                        break
                    if len(buf) - idx < FRAME_SIZE:
                        break

                    frame = buf[idx:idx + FRAME_SIZE]
                    del buf[:idx + FRAME_SIZE]

                    payload, checksum = frame[2:-1], frame[-1]
                    if (sum(frame[:-1]) & 0xFF) != checksum:
                        print("⚠️  Bad checksum, skipping frame.")
                        continue

                    # --- Parse ToF + Ultrasonic ---
                    tof = np.frombuffer(payload[:GRID_W * GRID_H * 2],
                                        dtype=np.uint16).astype(np.float32)
                    tof /= 1000.0  # mm → m

                    ultrasonic = np.frombuffer(
                        payload[GRID_W * GRID_H * 2 : GRID_W * GRID_H * 2 + 4],
                        dtype=np.float32
                    )[0]

                    # ✅ Add frame limiter here
                    now = time.time()
                    if 'last_frame_time' not in locals():
                        last_frame_time = now
                    if now - last_frame_time < 0.05:   # 20 Hz cap
                        continue
                    last_frame_time = now

                    ts = datetime.now()
                    sp.process_entry({"type": "TOF", "timestamp": ts, "values": tof.tolist()})
                    sp.process_entry({"type": "US", "timestamp": ts, "values": [ultrasonic]})


                    #print(f"[BRIDGE] Sent frame → ToF avg={np.mean(tof):.2f}m | US={ultrasonic:.1f}cm")


                    frames += 1
                    if time.time() - last_fps_print >= 1.0:
                        #print(f"📡 FPS: {frames}")
                        frames, last_fps_print = 0, time.time()

        except Exception as e:
            print(f"💥 Serial bridge error: {e}")
            if ser:
                ser.close()
            ser = None
            print(f"🔁 Reconnecting in {RECONNECT_DELAY}s…")
            time.sleep(RECONNECT_DELAY)
