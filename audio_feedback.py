# audio_feedback.py (PipeWire / PulseAudio safe)
import subprocess
import time

def beep(level):
    tones = {
        "far":   (440, 0.15),
        "mid":   (660, 0.15),
        "near":  (880, 0.10),
        "close": (1200, 0.5),
        "mismatch": (300, 0.3),
    }
    if level not in tones:
        return

    f, d = tones[level]
    try:
        subprocess.run([
            "play", "-n", "synth", str(d), "sin", str(f)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"⚠️ Beep error: {e}")
    time.sleep(0.05)
