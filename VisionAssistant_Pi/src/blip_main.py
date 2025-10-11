"""
blip_main.py — Offline image captioning with BLIP-base
Author: Geo & ChatGPT (2025)
"""

import time, torch
from pathlib import Path
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
from vision_caption.captioner import generate_caption
from vision_caption.speak_piper import speak_piper

# Optimize CPU threads for Raspberry Pi 5 (4 cores)
torch.set_num_threads(4)
torch.set_num_interop_threads(4)
torch.set_grad_enabled(False)


def main():
    # ------------------------------------------------------------
    # CONFIGURATION
    # ------------------------------------------------------------
    model_id = "Salesforce/blip-image-captioning-base"
    image_path = Path(__file__).resolve().parents[2] / "data" / "sample_images" / "robot.jpg"

    # ------------------------------------------------------------
    # LOAD MODEL
    # ------------------------------------------------------------
    print("🚀 Loading BLIP base model...")
    t0 = time.time()
    processor = BlipProcessor.from_pretrained(model_id)
    model = BlipForConditionalGeneration.from_pretrained(
        model_id,
        torch_dtype=torch.float32,
        low_cpu_mem_usage=True
    ).to("cpu")

    print(f"✅ Model loaded in {time.time() - t0:.1f}s")

    # ------------------------------------------------------------
    # VERIFY IMAGE
    # ------------------------------------------------------------
    if not image_path.exists():
        print(f"❌ Image not found: {image_path}")
        return
    image = Image.open(image_path).convert("RGB")

    # ------------------------------------------------------------
    # GENERATE CAPTION
    # ------------------------------------------------------------
    print("🧠 Generating caption...")
    start_time = time.time()
    caption = generate_caption(model, processor, str(image_path))
    elapsed = time.time() - start_time
    print(f"🕒 Caption generated in {elapsed:.2f} seconds")

    # ------------------------------------------------------------
    # SPEAK RESULT
    # ------------------------------------------------------------
    print("🗣️ Speaking caption...")
    speak_piper(caption)

    # ------------------------------------------------------------
    # DISPLAY
    # ------------------------------------------------------------
    print("--------------------------------------------------")
    print("🖼️ Caption:")
    print(caption)
    print("--------------------------------------------------")


if __name__ == "__main__":
    main()
