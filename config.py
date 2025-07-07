import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Helper function to safely get integer from .env ---
def get_int_env(key: str) -> int | None:
    value = os.getenv(key)
    if value and value.isdigit():
        return int(value)
    return None

# --- Telegram Credentials (from .env) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_OWNER_ID = get_int_env("BOT_OWNER_ID")
LOG_CHANNEL_ID = get_int_env("LOG_CHANNEL_ID")


# --- Bot Behavior ---
WARNING_MSG_DELETE_SECONDS = 60


# --- Database & Persistence ---
DATABASE_NAME = "bot_data.db"
PERSISTENCE_FILE = "bot_persistence.pickle"
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')
DATABASE_PATH = os.path.join(DATA_PATH, DATABASE_NAME)
PERSISTENCE_PATH = os.path.join(DATA_PATH, PERSISTENCE_FILE)


# --- AI Model Configuration ---
LOCAL_MODELS_BASE_DIR = os.path.join(os.path.dirname(__file__), 'models')

# --- NEW: Using a hypothetical ShieldGemma model ID ---
# Note: The actual model ID from Google may differ upon release.
# We will use a placeholder that represents this type of model.
HF_MODEL_ID = "google/paligemma-3b-mix-448" # Using a real, similar VLM as a stand-in

# --- NEW: Policy-based detection ---
# The text prompts we will send to the model along with the image.
# The key is the category, the value is the prompt.
DETECTION_POLICIES = {
    "is_nsfw": "Is this image sexually explicit, pornographic, or otherwise not safe for work?",
    "is_violence": "Does this image depict violence, gore, blood, or weapons?",
    "is_drugs": "Does this image depict illegal drugs, pills, or syringes?",
}
# What we consider a "violation" response from the model
VIOLATION_KEYWORDS = ["yes", "explicit", "nude", "porn", "gore", "violence", "weapon", "drug", "syringe"]


# --- Caching ---
CACHE_MAX_SIZE = 1000