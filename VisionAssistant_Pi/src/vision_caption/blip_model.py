"""
blip_model.py — loads the BLIP-base captioning model
"""

from transformers import BlipProcessor, BlipForConditionalGeneration
import torch, time


def load_blip(model_id="Salesforce/blip-image-captioning-base"):
    """
    Loads the BLIP model and processor once.
    Returns: (model, processor)
    """
    print("🚀 Loading BLIP base model...")
    t0 = time.time()

    processor = BlipProcessor.from_pretrained(model_id)
    model = BlipForConditionalGeneration.from_pretrained(
        model_id,
        dtype=torch.float32,
        low_cpu_mem_usage=True
    )
    model.to("cpu")
    torch.set_num_threads(4)
    torch.set_num_interop_threads(4)
    torch.set_grad_enabled(False)

    print(f"✅ Model loaded in {time.time() - t0:.1f}s")
    return model, processor
