"""
captioner.py — runs inference on an image using BLIP
"""

from PIL import Image
import torch


def generate_caption(model, processor, image_path: str):
    """
    Generate a caption for the given image using the loaded BLIP model.
    """
    image = Image.open(image_path).convert("RGB")

    # Prepare inputs and run model
    inputs = processor(image, "a photo of", return_tensors="pt").to("cpu")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=20)
        caption = processor.decode(out[0], skip_special_tokens=True)

        # Remove leading dataset phrases for natural speech
        caption = caption.strip()
        if caption.lower().startswith("a photo of"):
            caption = caption[10:].strip()
        elif caption.lower().startswith("the photo of"):
            caption = caption[13:].strip()
        elif caption.lower().startswith("an image of"):
            caption = caption[11:].strip()


    # Clean up and return
    del inputs, out
    torch.cuda.empty_cache() if torch.cuda.is_available() else None
    return caption.strip()
