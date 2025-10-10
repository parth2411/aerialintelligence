import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # NVIDIA API Configuration
    NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY', '')
    NVIDIA_API_URL = "https://ai.api.nvidia.com/v1/vlm/microsoft/florence-2"
    
    # Telegram Configuration
    TELEGRAM_ENABLED = os.getenv('TELEGRAM_ENABLED', 'true').lower() == 'true'
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Threat Detection Configuration
    THREAT_THRESHOLD = int(os.getenv('THREAT_THRESHOLD', '3'))  # MEDIUM and above
    
    # Classification Configuration
    CLASSIFICATION_TASK = os.getenv('CLASSIFICATION_TASK', '<DETAILED_CAPTION>')
    
    ALERT_COOLDOWN_SECONDS = int(os.getenv('ALERT_COOLDOWN_SECONDS', '10'))
    # Paths
    CAPTURED_FRAMES_DIR = os.getenv('CAPTURED_FRAMES_DIR', './data/captured_frames')
    CLASSIFICATION_RESULTS_DIR = os.getenv('CLASSIFICATION_RESULTS_DIR', './data/classification_results')
    
    @staticmethod
    def validate():
        """Validate required configuration"""
        if not Config.NVIDIA_API_KEY:
            raise ValueError("NVIDIA_API_KEY is required")
        if Config.TELEGRAM_ENABLED and not Config.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required when notifications enabled")
        if Config.TELEGRAM_ENABLED and not Config.TELEGRAM_CHAT_ID:
            raise ValueError("TELEGRAM_CHAT_ID is required when notifications enabled")
        return True

# Validate config on import
try:
    Config.validate()
    print("✅ Configuration loaded successfully")
except ValueError as e:
    print(f"⚠️  Configuration warning: {e}")