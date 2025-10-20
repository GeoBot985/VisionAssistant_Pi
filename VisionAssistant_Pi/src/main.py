"""
main.py — Vision Caption + Piper Speech Module (fixed capture logic)
Author: Geo & ChatGPT (2025)
"""

import cv2
import time
import subprocess
from pathlib import Path
from vision_caption.blip_model import load_blip
from vision_caption.captioner import generate_caption
from vision_caption.speak_piper import speak_piper



# ------------------------------------------------------------
# 🔊 Piper Text-to-Speech Helper
# ------------------------------------------------------------
def speak_piper(text: str, model_path="~/piper_voices/en_US-amy-medium.onnx"):
    """Speak text using Piper neural TTS."""
    model_path = str(Path(model_path).expanduser())
    try:
        p1 = subprocess.Popen(
            ["piper", "--model", model_path, "--output_audio", "pipe"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        p2 = subprocess.Popen(["aplay"], stdin=p1.stdout,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p1.stdin.write(text.encode("utf-8"))
        p1.stdin.close()
        p1.wait()
        p2.wait()
    except Exception as e:
        print(f"⚠️ Piper TTS error: {e}")


# ------------------------------------------------------------
# 🎥 Capture + Caption Loop
# ------------------------------------------------------------
def main():
    print("🚀 Initializing Vision Caption + Piper TTS module...")

    model, processor = load_blip()
    print("✅ BLIP model loaded and ready.\nPress Enter to capture or 'q' to quit.\n")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not access camera.")
        return

    try:
        while True:
            key = input("Press Enter to capture, or 'q' to quit: ")
            if key.lower() == "q":
                print("👋 Exiting Vision Caption module.")
                break

            # Flush camera buffer (grab a few frames before capture)
            for _ in range(4):
                cap.grab()
            time.sleep(0.3)  # allow camera to update

            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to capture image.")
                continue

            image_path = Path("webcam.jpg")
            cv2.imwrite(str(image_path), frame)
            print("📸 Image captured → webcam.jpg")

            # Generate caption
            t0 = time.time()
            caption = generate_caption(model, processor, str(image_path))
            print(f"🧠 Caption: {caption}")
            print(f"⏱️ Inference Time: {time.time() - t0:.2f} s")

            from vision_caption.speak_piper import speak_piper
            speak_piper(caption)


    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user.")
    finally:
        cap.release()
        print("✅ Camera released. Goodbye.")


if __name__ == "__main__":
    main()
