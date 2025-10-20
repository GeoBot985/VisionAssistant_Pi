"""
controller.py — VisionAssist runtime orchestrator (with live sensor simulator)
"""
import threading
import queue
import time
from pathlib import Path
import cv2

#--demo visualization
import matplotlib
matplotlib.use("TkAgg")   # or "Qt5Agg" if you have Qt installed
import matplotlib.pyplot as plt


# === SENSOR MODULES ===
from audio_feedback import beep
from sensors.sensor_simulator import main as sensor_sim_main
from sensors.sensor_processor import process_entry

# === VISION MODULES ===
from vision_caption.speak_piper import speak_piper
from vision_caption.blip_model import load_blip
from vision_caption.captioner import generate_caption

# === GLOBAL QUEUE ===
from event_bus import EVENT_QUEUE

# === VISUALIZER THREAD ===
import matplotlib.pyplot as plt
import numpy as np
from sensors import sensor_processor as sp

LAST_MANUAL_TRIGGER = 0
VISION_COOLDOWN = 10  # seconds (same cooldown as sensors)



def visualizer_task():
    """Live 8×8 heatmap of ToF readings."""
    print("🖥️ Visualizer thread started")

    plt.ion()
    fig, ax = plt.subplots(figsize=(4, 4))
    img = ax.imshow(np.zeros((8, 8)), vmin=0.0, vmax=1.5, cmap="plasma")
    plt.title("VisionAssist ToF Distance Map (m)")
    plt.colorbar(img, ax=ax)
    plt.tight_layout()

    try:
        while True:
            frame = getattr(sp, "last_tof_frame", [0.0]*64)
            if frame and len(frame) >= 64:
                data = np.array(frame[:64]).reshape((8, 8))
                img.set_data(data)
                ax.draw_artist(ax.patch)
                ax.draw_artist(img)
                fig.canvas.flush_events()
            plt.pause(0.1)
    except KeyboardInterrupt:
        print("\n🛑 Visualizer stopped.")
    finally:
        plt.close(fig)


def keyboard_task():
    """Wait for Enter key and push a manual vision event via event bus."""
    global LAST_MANUAL_TRIGGER
    print("⌨️  Press Enter anytime to capture manually.")
    while True:
        if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
            _ = sys.stdin.readline().strip()
            now = time.time()
            if now - LAST_MANUAL_TRIGGER > VISION_COOLDOWN:
                LAST_MANUAL_TRIGGER = now
                EVENT_QUEUE.put({"type": "vision_request", "source": "manual"})
                print(f"[{time.strftime('%H:%M:%S')}] 🎥 Manual vision trigger fired.")
            else:
                remaining = VISION_COOLDOWN - (now - LAST_MANUAL_TRIGGER)
                print(f"[{time.strftime('%H:%M:%S')}] ⏳ Manual trigger on cooldown ({remaining:.1f}s)")



# ============================================================
# 🧩 SENSOR THREAD (simulator-driven)
# ============================================================
def sensor_task():
    """Continuously generate fake ToF + US frames and feed processor."""
    print("📡 Sensor task started (using sensors/sensor_simulator.py)")
    sensor_sim_main()  # runs until stopped; calls sensor_processor internally


# ============================================================
# 🔊 AUDIO THREAD
# ============================================================
def audio_task():
    print("🔊 Audio task started")
    while True:
        event = EVENT_QUEUE.get()
        if event is None:
            break
        if event.get("type") == "beep":
            beep(event.get("level", "far"))
        elif event.get("type") == "tts":
            speak_piper(event.get("text", ""))
    print("🔊 Audio task stopped")


# ============================================================
# 👁️ VISION THREAD
# ============================================================
def vision_task():
    print("👁️ Vision thread started")
    model, processor = load_blip()
    print("✅ Vision model ready")

    while True:
        event = EVENT_QUEUE.get()
        if event is None:
            break

        print(f"[DEBUG] Vision thread received event: {event}")  # 👈 ADD THIS

        if event.get("type") == "vision_request":
            print("📸 Vision request received — capturing and captioning...")
            img_path = Path("webcam.jpg")
            capture_image(str(img_path))                 # 👈 take a new picture
            if img_path.exists():
                caption = generate_caption(model, processor, str(img_path))
                EVENT_QUEUE.put({"type": "tts", "text": caption})
                print(f"🖼️ Caption generated → {caption}")
            else:
                print("⚠️ Capture failed; no image available")

    print("👁️ Vision task stopped")

def capture_image(path="webcam.jpg"):
    """Capture a single frame from the default camera."""
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
    print("\n🚀 Starting VisionAssist Controller (Live Simulation Mode)\n")

    # background threads for sensors, audio, and vision
    threads = [
        threading.Thread(target=sensor_task, daemon=True),
        threading.Thread(target=audio_task, daemon=True),
        threading.Thread(target=vision_task, daemon=True),
        threading.Thread(target=keyboard_task, daemon=True),  # 👈 added
    ]

    for t in threads:
        t.start()

    # 🖥️ run visualizer on main thread so TkAgg is happy
    try:
        visualizer_task()
    except KeyboardInterrupt:
        print("\n🛑 Stopping VisionAssist…")
    finally:
        for _ in threads:
            EVENT_QUEUE.put(None)
        time.sleep(0.5)
        print("✅ Shutdown complete.")



if __name__ == "__main__":
    main()
