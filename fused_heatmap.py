import serial
import numpy as np
import cv2
import time

# ==== CONFIG ====
PORT = "/dev/ttyUSB0"
BAUD = 115200
GRID_W = GRID_H = 8
FRAME_SIZE = 2 + GRID_W * GRID_H * 2 + 4 + 1   # header + ToF + ultrasonic + checksum
MAX_RANGE_M = 4.0  # meters for color scale

# ==== FOV & COSINE CORRECTION ====
FOV_X = np.deg2rad(45)
FOV_Y = np.deg2rad(45)
angles_x = np.linspace(-FOV_X / 2, FOV_X / 2, GRID_W)
angles_y = np.linspace(-FOV_Y / 2, FOV_Y / 2, GRID_H)
cosine_correction = np.outer(np.cos(angles_y), np.cos(angles_x))

# ==== SPATIAL MEDIAN FILTER ====
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

# ==== SERIAL SETUP ====
ser = serial.Serial(PORT, BAUD, timeout=0.1)
print("Opened", ser.portstr)
print("Listening for combined ToF + Ultrasonic frames... Press ESC to quit.")

def find_frame():
    """Find and parse a valid binary frame."""
    buf = bytearray()
    while True:
        chunk = ser.read(256)
        if not chunk:
            return None, None
        buf.extend(chunk)
        while len(buf) >= FRAME_SIZE:
            idx = buf.find(b'\xAA\x55')
            if idx == -1:
                buf.clear()
                break
            if len(buf) - idx < FRAME_SIZE:
                break
            frame = buf[idx:idx + FRAME_SIZE]
            del buf[:idx + FRAME_SIZE]
            payload, checksum = frame[2:-1], frame[-1]
            if (sum(frame[:-1]) & 0xFF) == checksum:
                tof = np.frombuffer(payload[:GRID_W * GRID_H * 2], dtype=np.uint16).reshape(GRID_H, GRID_W)
                ultrasonic = np.frombuffer(payload[GRID_W * GRID_H * 2: GRID_W * GRID_H * 2 + 4], dtype=np.float32)[0]
                return tof, ultrasonic
    return None, None

# ==== DISPLAY ====
cv2.namedWindow("ToF + Ultrasonic Heatmap", cv2.WINDOW_NORMAL)
cv2.resizeWindow("ToF + Ultrasonic Heatmap", 600, 600)

prev_frame = np.zeros((GRID_H, GRID_W), dtype=np.float32)
decay_rate = 0.7

fps_counter, last_time = 0, time.time()

while True:
    frame_mm, ultrasonic_cm = find_frame()
    if frame_mm is None:
        continue

    frame_m = frame_mm.astype(np.float32) / 1000.0
    corrected = frame_m * cosine_correction

    invalid_mask = (frame_m < 0.05) | (frame_m > 4.0)
    prev_frame = decay_rate * prev_frame + (1 - decay_rate) * corrected
    prev_frame[~invalid_mask] = corrected[~invalid_mask]
    frame_m = prev_frame

    denoised = median3x3(frame_m)

    center_block = denoised[2:6, 2:6]
    valid_center = center_block[(center_block > 0.05) & (center_block < 4.0)]
    tof_center_m = np.mean(valid_center) if valid_center.size else np.nan
    fused_cm = None
    if not np.isnan(tof_center_m) and ultrasonic_cm > 0:
        fused_cm = min(tof_center_m * 100, ultrasonic_cm)

    normalized = np.clip(denoised / MAX_RANGE_M, 0, 1)
    img = cv2.resize(normalized, (400, 400), interpolation=cv2.INTER_NEAREST)
    img_color = cv2.applyColorMap((img * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)

    # Overlay numeric values
    for y in range(GRID_H):
        for x in range(GRID_W):
            val = denoised[y, x]
            if val > 0:
                cv2.putText(img_color, f"{val:.1f}", (x * 50 + 8, y * 50 + 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    if ultrasonic_cm and ultrasonic_cm > 0:
        cv2.putText(img_color, f"Ultrasonic: {ultrasonic_cm:.1f} cm",
                    (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    if fused_cm:
        cv2.putText(img_color, f"Fused front: {fused_cm:.1f} cm",
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    cv2.imshow("ToF + Ultrasonic Heatmap", img_color)

    fps_counter += 1
    if time.time() - last_time >= 1:
        print(f"FPS: {fps_counter}")
        fps_counter, last_time = 0, time.time()

    if cv2.waitKey(1) & 0xFF == 27:  # ESC
        break

ser.close()
cv2.destroyAllWindows()
