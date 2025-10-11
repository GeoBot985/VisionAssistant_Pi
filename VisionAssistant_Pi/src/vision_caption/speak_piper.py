import subprocess, time
from pathlib import Path

def speak_piper(text, model_path="~/piper_voices/en_US-amy-medium.onnx"):
    model_path = str(Path(model_path).expanduser())
    wav_path = Path("tts_output.wav")
    padded_path = Path("tts_output_padded.wav")

    try:
        # ------------------------------------------------------------
        # 1️⃣ Generate the TTS file
        # ------------------------------------------------------------
        subprocess.run(
            ["piper", "--model", model_path, "--output_file", str(wav_path)],
            input=text.encode("utf-8"),
            check=True
        )

        # ------------------------------------------------------------
        # 2️⃣ Pad the start with 0.3s silence to avoid cut-off
        # ------------------------------------------------------------
        subprocess.run([
            "sox", str(wav_path), str(padded_path), "pad", "0.3", "0"
        ], check=True)

        # ------------------------------------------------------------
        # 3️⃣ Small pre-playback delay (pipewire warm-up)
        # ------------------------------------------------------------
        time.sleep(0.3)

        # ------------------------------------------------------------
        # 4️⃣ Play through PipeWire → Bluetooth default sink
        # ------------------------------------------------------------
        subprocess.run([
            "bash", "-c",
            f"pw-play --target=$(pactl info | awk -F': ' '/Default Sink/ {{print $2}}') '{padded_path}'"
        ], check=True)

    except Exception as e:
        print(f"⚠️ Piper TTS error: {e}")

