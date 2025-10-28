"""
controller.py — VisionAssist runtime orchestrator (multi-thread mode + async vision/audio)
"""
import threading
import multiprocessing
import sys, select, time, subprocess
from pathlib import Path
import cv2
import numpy as np
from queue import Queue

# === SENSOR MODULES ===
from audio_feedback import beep
from sensors.sensor_serial_bridge import run_bridge as sensor_sim_main
from event_bus import EVENT_QUEUE, VISION_QUEUE
from sensors import sensor_processor as sp

# === VISION MODULES ===
from vision_caption.blip_model import load_blip
from vision_caption.captioner import generate_caption

LAST_MANUAL_TRIGGER = 0
VISION_COOLDOWN = 15  # seconds

TTS_QUEUE = Queue()

# ============================================================
# 🎨 FAST OPENCV VISUALIZER
# ============================================================
def visualizer_task():
    print("🖥️ OpenCV visualizer started")

    win = "VisionAssist Heatmap"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, 520, 580)

    CELL = 60
    VMAX_M = 4.0
    font = cv2.FONT_HERSHEY_SIMPLEX

    while True:
        frame = getattr(sp, "last_tof_frame", None)
        fused = float(getattr(sp, "last_fused_distance", 0.0))
        us_cm = float(getattr(sp, "last_ultrasonic_cm", 0.0))

        if frame and len(frame) >= 64:
            data = np.asarray(frame[:64], dtype=np.float32).reshape(8, 8)

            # mild dynamic contrast enhancement
            norm = np.clip(data / VMAX_M, 0, 1)
            dmin, dmax = np.min(data), np.max(data)
            if dmax - dmin > 0.2:
                norm = 0.9 * norm + 0.1 * np.clip((data - dmin) / (dmax - dmin), 0, 1)

            up = cv2.resize(norm, (8 * CELL, 8 * CELL), interpolation=cv2.INTER_NEAREST)
            img = cv2.applyColorMap((up * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)

            for y in range(8):
                for x in range(8):
                    v = data[y, x]
                    if v > 0:
                        color = (255, 255, 255) if v < 2.0 else (0, 0, 0)
                        cv2.putText(img, f"{v:.2f}", (x * CELL + 6, y * CELL + 24),
                                    font, 0.45, color, 1, cv2.LINE_AA)

            # overlay fused + ultrasonic
            cv2.rectangle(img, (0, 8 * CELL - 70), (8 * CELL, 8 * CELL), (0, 0, 0), -1)
            cv2.putText(img, f"Fused: {fused:.2f} m", (10, 8 * CELL - 45),
                        font, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(img, f"Ultrasonic: {us_cm:.1f} cm", (10, 8 * CELL - 20),
                        font, 0.6, (0, 255, 0), 2, cv2.LINE_AA)

            cv2.imshow(win, img)

        # graceful exit on ESC
        if cv2.waitKey(1) & 0xFF == 27:
            break
        time.sleep(0.015)

    cv2.destroyWindow(win)
    print("🛑 Visualizer stopped cleanly")


# ============================================================
# ⌨️  KEYBOARD TRIGGER
# ============================================================
def keyboard_task():
    global LAST_MANUAL_TRIGGER
    print("⌨️  Press Enter anytime to capture manually.")
    while True:
        if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
            _ = sys.stdin.readline().strip()
            now = time.time()
            if now - LAST_MANUAL_TRIGGER > VISION_COOLDOWN:
                LAST_MANUAL_TRIGGER = now
                VISION_QUEUE.put({"type": "vision_request", "source": "manual"})
                print(f"[{time.strftime('%H:%M:%S')}] 🎥 Manual vision trigger fired.")
            else:
                remaining = VISION_COOLDOWN - (now - LAST_MANUAL_TRIGGER)
                print(f"[{time.strftime('%H:%M:%S')}] ⏳ Manual trigger on cooldown ({remaining:.1f}s)")


# ============================================================
# 📡 SENSOR THREAD
# ============================================================
def sensor_task():
    print("📡 Sensor task started (using sensor_serial_bridge)")
    sensor_sim_main()


# ============================================================
# 🔊 AUDIO THREAD  (async Piper)
# ============================================================
def tts_worker():
    """Worker thread that plays each queued text sequentially."""
    model_path = "/home/geo/piper_voices/en_US-amy-medium.onnx"
    while True:
        text = TTS_QUEUE.get()
        if text is None:
            break
        cmd = (
            f'echo "{text}" | '
            f'piper --model {model_path} --output_file - | '
            f'pw-play -'
        )
        try:
            subprocess.run(cmd, shell=True,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[TTS] error: {e}")
        time.sleep(0.1)   # brief gap between sentences

# start once at launch
threading.Thread(target=tts_worker, daemon=True).start()

def speak_piper_async(text: str):
    """Queue text for speech output."""
    if text:
        TTS_QUEUE.put(text)

def audio_task():
    print("🔊 Audio task started", flush=True)
    last_tts_text = ""

    while True:
        event = EVENT_QUEUE.get()
        if event is None:
            break

        etype = event.get("type")

        if etype == "beep":
            try:
                beep(event.get("level", "far"))
            except Exception as e:
                print(f"[ERROR] Beep failed: {e}", flush=True)

        elif etype == "tts":
            text = event.get("text", "").strip()
            if not text or text == last_tts_text:
                continue
            last_tts_text = text
            print(f"[AUDIO] Speaking: {text}", flush=True)
            speak_piper_async(text)


# ============================================================
# 👁️ VISION PROCESS
# ============================================================
def vision_task():
    print("👁️ Vision process started")
    model, processor = load_blip()
    print("✅ Vision model ready (separate process)")

    def run_caption(model, processor, img_path):
        try:
            caption = generate_caption(model, processor, str(img_path))
            EVENT_QUEUE.put({"type": "tts", "text": caption})
            print(f"🖼️ Caption → {caption}")
        except Exception as e:
            print(f"⚠️ Caption error: {e}")

    while True:
        event = VISION_QUEUE.get()
        print(f"[VISION] got event: {event}")
        if event is None:
            break
        if event.get("type") == "vision_request":
            print("📸 Capturing and captioning...")
            img_path = Path("webcam.jpg")
            capture_image(str(img_path))
            if img_path.exists():
                threading.Thread(
                    target=run_caption, args=(model, processor, img_path), daemon=True
                ).start()
            else:
                print("⚠️ Capture failed; no image.")


def capture_image(path="webcam.jpg"):
    cam = cv2.VideoCapture(0)
    ret, frame = cam.read()
    if ret:
        cv2.imwrite(path, frame)
        print(f"📸 Image captured → {path}")
    else:
        print("⚠️ Camera capture failed")
    cam.release()


# ============================================================
# 🧭 CONTROLLER MAIN
# ============================================================
def main():
    print("\n🚀 Starting VisionAssist Controller (multi-thread mode)\n")

    threads = [
        threading.Thread(target=sensor_task, daemon=True),
        threading.Thread(target=audio_task, daemon=True),
        threading.Thread(target=keyboard_task, daemon=True),
        threading.Thread(target=vision_task, daemon=True),
    ]
    for t in threads:
        t.start()

    try:
        visualizer_task()
    except KeyboardInterrupt:
        print("\n🛑 Stopping VisionAssist…")
    finally:
        for _ in threads:
            EVENT_QUEUE.put(None)
            VISION_QUEUE.put(None)
        print("✅ Shutdown complete.")


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")
    main()
