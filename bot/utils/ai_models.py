import logging
import os
import io
import torch
from typing import Any
from PIL import Image
from transformers import AutoProcessor, PaliGemmaForConditionalGeneration

import config

logger = logging.getLogger(__name__)

# --- Globals for the loaded VLM ---
model: PaliGemmaForConditionalGeneration | None = None
processor: AutoProcessor | None = None
device = "cuda" if torch.cuda.is_available() else "cpu"


def load_models():
    """
    Loads the main VLM from the local cache.
    Fails if the model is not found.
    """
    global model, processor
    
    try:
        model_id = config.HF_MODEL_ID
        local_path = os.path.join(config.LOCAL_MODELS_BASE_DIR, model_id.replace("/", "_"))
        
        logger.info(f"Loading main VLM from: {local_path}")
        if not os.path.exists(local_path) or not os.listdir(local_path):
             raise OSError(f"Model directory not found or empty at {local_path}")

        processor = AutoProcessor.from_pretrained(local_path)
        model = PaliGemmaForConditionalGeneration.from_pretrained(
            local_path, 
            torch_dtype=torch.bfloat16,
            device_map=device,
            revision="bfloat16",
        ).eval()

        logger.info(f"Main VLM loaded successfully on device: {device}")

    except Exception as e:
        logger.critical(
            f"Model not found or failed to load. "
            f"Please run the download script first: python3 scripts/download.py",
            exc_info=True
        )
        raise SystemExit("Essential models not found. Exiting.")


def analyze_image(image_content: bytes) -> dict[str, Any]:
    """
    Performs generative analysis on image content using policies from the config.
    Returns a dictionary with detection flags.
    """
    if not model or not processor:
        logger.error("AI model is not loaded. Skipping analysis.")
        return {"error": "Model not loaded"}

    try:
        image = Image.open(io.BytesIO(image_content)).convert("RGB")
    except Exception as e:
        logger.error(f"Failed to open image from bytes: {e}")
        return {"error": "Invalid image content"}

    results: dict[str, Any] = {
        "is_nsfw": False,
        "is_violence": False,
        "is_drugs": False,
    }

    try:
        for key, prompt in config.DETECTION_POLICIES.items():
            inputs = processor(text=prompt, images=image, return_tensors="pt").to(device)
            
            with torch.no_grad():
                output = model.generate(**inputs, max_new_tokens=20)
            
            response_text = processor.decode(output[0], skip_special_tokens=True).lower()
            # Remove the prompt from the response to get only the answer
            answer = response_text.replace(prompt.lower(), "").strip()

            logger.debug(f"Policy: '{key}' | Prompt: '{prompt}' | VLM Answer: '{answer}'")

            # Check if any violation keyword is in the model's answer
            if any(keyword in answer for keyword in config.VIOLATION_KEYWORDS):
                results[key] = True

    except Exception as e:
        logger.error(f"Image analysis failed: {e}", exc_info=True)

    return results