import os
import logging
from transformers import AutoProcessor, PaliGemmaForConditionalGeneration

# Go up one level to import config from the root directory
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config

# --- Logging Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def download_main_model():
    """Downloads and saves the main VLM and its processor from Hugging Face."""
    
    os.makedirs(config.LOCAL_MODELS_BASE_DIR, exist_ok=True)
    logger.info(f"Model will be saved to: {config.LOCAL_MODELS_BASE_DIR}")

    model_id = config.HF_MODEL_ID
    local_path = os.path.join(config.LOCAL_MODELS_BASE_DIR, model_id.replace("/", "_"))
    
    logger.info(f"--- Downloading main model: {model_id} ---")

    if os.path.exists(local_path) and os.listdir(local_path):
        logger.info(f"'{model_id}' already exists locally. Skipping.")
    else:
        try:
            os.makedirs(local_path, exist_ok=True)
            logger.info("Downloading model... this may take a while and use a lot of disk space.")
            processor = AutoProcessor.from_pretrained(model_id)
            model = PaliGemmaForConditionalGeneration.from_pretrained(model_id, torch_dtype=torch.bfloat16)
            
            processor.save_pretrained(local_path)
            model.save_pretrained(local_path)
            logger.info(f"Successfully downloaded and saved '{model_id}' to '{local_path}'")
        except Exception as e:
            logger.critical(f"Failed to download {model_id}. Error: {e}", exc_info=True)
            
    logger.info("--- Model download process finished. ---")


if __name__ == "__main__":
    import torch # Add torch import for the script to run standalone
    download_main_model()