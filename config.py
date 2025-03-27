"""
Centralized configuration for Cerastes API
-------------------------------------------
This module centralizes all application configurations
and loads values from environment variables.
"""

import os
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set
from functools import lru_cache

# Logging configuration
logger = logging.getLogger("config")

# Definition of important paths
BASE_DIR = Path(__file__).parent.absolute()
PROMPTS_DIR = BASE_DIR / "prompts"
UPLOADS_DIR = BASE_DIR / "uploads"
RESULTS_DIR = BASE_DIR / "results"
INFERENCE_RESULTS_DIR = BASE_DIR / "inference_results"
LOGS_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
for directory in [UPLOADS_DIR, RESULTS_DIR, INFERENCE_RESULTS_DIR, LOGS_DIR,
                 UPLOADS_DIR / "video", UPLOADS_DIR / "audio", UPLOADS_DIR / "text"]:
    directory.mkdir(parents=True, exist_ok=True)

# Default configuration
DEFAULT_CONFIG = {
    # General configuration
    "app": {
        "name": "Cerastes API",
        "version": "1.0.0",
        "environment": "development",
        "secret_key": "changeme_in_production",
        "allowed_origins": ["*"],
        "timezone": "UTC"
    },
    
    # Database configuration
    "database": {
        "sqlalchemy_url": "postgresql://postgres:password@localhost:5432/cerastes",
        "pool_size": 10,
        "max_overflow": 20,
        "echo": False,
        "track_modifications": False,
    },
    
    # AI models configuration
    "models": {
        # General LLM configuration
        "llm": {
            "default_model": "huihui-ai/DeepSeek-R1-Distill-Qwen-14B-abliterated-v2",
            "tensor_parallel_size": 1,
            "gpu_memory_utilization": 0.9,
            "quantization": None,
            "max_model_len": 24272,
            "fallback_models": [
                "meta-llama/Llama-2-7b-chat-hf",
                "facebook/opt-6.7b", 
                "bigscience/bloom-7b1"
            ]
        },
        
        # Whisper configuration
        "whisper": {
            "default_size": "medium",  # tiny, base, small, medium, large
            "device": "cuda",  # cuda or cpu
            "language": None,  # specific language or None for auto-detection
            "batch_size": 16
        },
        
        # InternVideo configuration
        "internvideo": {
            "model_path": "OpenGVLab/InternVideo2_5_Chat_8B",
            "input_size": 448,
            "num_frames": 128,
            "trust_remote_code": True
        },
        
        # Diarization configuration
        "diarization": {
            "model_path": "pyannote/speaker-diarization-3.1",
            "huggingface_token": "",
            "min_speakers": 1,
            "max_speakers": 10
        }
    },
    
    # Video processing configuration
    "video": {
        "max_upload_size_mb": 500,
        "allowed_extensions": [".mp4", ".mov", ".avi", ".mkv", ".webm"],
        "extract_frames": 128,
        "max_resolution": 1080,  # resize videos if larger
        "dynamic_segmentation": True  # adapts the number of segments to video duration
    },
    
    # Audio processing configuration
    "audio": {
        "max_upload_size_mb": 100,
        "allowed_extensions": [".mp3", ".wav", ".flac", ".ogg", ".m4a"],
        "sample_rate": 16000,
        "channels": 1
    },
    
    # Segmentation configuration
    "segmentation": {
        "enabled": True,
        "language": "fr",
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "fallback_models": ["paraphrase-multilingual-MiniLM-L12-v2"],
        "max_segments_per_text": 10,
        "target_segments": 6,
        "similarity_threshold": 0.15
    },
    
    # Inference configuration
    "inference": {
        "max_new_tokens": 8000,
        "temperature": 0.53,
        "top_p": 0.93,
        "top_k": 30,
        "timeout_seconds": 300,
        "batch_parallel": True,
        "max_retries": 3,
        "max_cache_size": 50
    },
    
    # API configuration
    "api": {
        "host": "0.0.0.0",
        "port": 8000,
        "workers": 1,
        "debug": False,
        "max_request_size_mb": 10,
        "max_concurrent_tasks": 5,
        "result_storage_dir": "inference_results",
        "log_level": "info",
        "token_expiration_minutes": 30,
        "refresh_token_expiration_days": 7
    },

    # Authentication configuration
    "auth": {
        "jwt_algorithm": "HS256",
        "password_hash_rounds": 12,
        "require_email_verification": False,
        "allow_registration": True,
        "admin_emails": []
    },
    # Post-processors configuration
    "postprocessing": {
        "json_simplifier": {
            "enabled": False,  # Disabled by default
            "model": "huihui-ai/DeepSeek-R1-Distill-Qwen-14B-abliterated-v2",
            "system_prompt": "Translate this json {text} in plain english",
            "max_tokens": 1000,
            "temperature": 0.3,
            "apply_to": ["inference", "video", "transcription"]  # Task types concerned
        }
    },
    
    # External services configuration
    "services": {
        # Stripe
        "stripe": {
            "enabled": False,
            "api_key": "",
            "webhook_secret": "",
            "currency": "usd",
            "success_url": "http://localhost:8000/payment/success",
            "cancel_url": "http://localhost:8000/payment/cancel"
        },
        
        # Email
        "email": {
            "enabled": False,
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "",
            "smtp_password": "",
            "sender_email": "noreply@example.com",
            "use_tls": True
        }
    }
}

@lru_cache()
def load_config() -> Dict[str, Any]:
    """
    Loads configuration from environment variables or uses default values.
    The function is cached to avoid reloading the configuration on each call.
    
    Returns:
        Dict[str, Any]: Complete configuration
    """
    config = DEFAULT_CONFIG.copy()
    
    # ====== General configuration ======
    if os.environ.get("APP_NAME"):
        config["app"]["name"] = os.environ.get("APP_NAME")
    
    if os.environ.get("APP_VERSION"):
        config["app"]["version"] = os.environ.get("APP_VERSION")
    
    if os.environ.get("ENVIRONMENT"):
        config["app"]["environment"] = os.environ.get("ENVIRONMENT")
    
    if os.environ.get("SECRET_KEY"):
        config["app"]["secret_key"] = os.environ.get("SECRET_KEY")
    
    if os.environ.get("CORS_ORIGINS"):
        config["app"]["allowed_origins"] = os.environ.get("CORS_ORIGINS").split(",")
    
    # ====== Database configuration ======
    # Building SQLAlchemy URL
    if os.environ.get("DATABASE_URL"):
        config["database"]["sqlalchemy_url"] = os.environ.get("DATABASE_URL")
    else:
        # Building URL from components
        db_user = os.environ.get("DB_USER", "postgres")
        db_password = os.environ.get("DB_PASSWORD", "password")
        db_host = os.environ.get("DB_HOST", "localhost")
        db_port = os.environ.get("DB_PORT", "5432")
        db_name = os.environ.get("DB_NAME", "cerastes")
        
        config["database"]["sqlalchemy_url"] = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    if os.environ.get("DB_POOL_SIZE"):
        config["database"]["pool_size"] = int(os.environ.get("DB_POOL_SIZE"))
    
    if os.environ.get("DB_MAX_OVERFLOW"):
        config["database"]["max_overflow"] = int(os.environ.get("DB_MAX_OVERFLOW"))
    
    if os.environ.get("DB_ECHO"):
        config["database"]["echo"] = os.environ.get("DB_ECHO").lower() in ["true", "1", "yes"]
    
    # ====== AI models configuration ======
    # LLM
    if os.environ.get("MODEL_NAME"):
        config["models"]["llm"]["default_model"] = os.environ.get("MODEL_NAME")
    
    if os.environ.get("TENSOR_PARALLEL_SIZE"):
        config["models"]["llm"]["tensor_parallel_size"] = int(os.environ.get("TENSOR_PARALLEL_SIZE"))
    
    if os.environ.get("GPU_MEMORY_UTILIZATION"):
        config["models"]["llm"]["gpu_memory_utilization"] = float(os.environ.get("GPU_MEMORY_UTILIZATION"))
    
    if os.environ.get("QUANTIZATION"):
        config["models"]["llm"]["quantization"] = os.environ.get("QUANTIZATION")
    
    if os.environ.get("MAX_MODEL_LEN"):
        config["models"]["llm"]["max_model_len"] = int(os.environ.get("MAX_MODEL_LEN"))
    
    # Whisper
    if os.environ.get("WHISPER_MODEL_SIZE"):
        config["models"]["whisper"]["default_size"] = os.environ.get("WHISPER_MODEL_SIZE")
    
    if os.environ.get("WHISPER_DEVICE"):
        config["models"]["whisper"]["device"] = os.environ.get("WHISPER_DEVICE")
    
    if os.environ.get("WHISPER_LANGUAGE"):
        config["models"]["whisper"]["language"] = os.environ.get("WHISPER_LANGUAGE")
    
    # Diarization
    if os.environ.get("HUGGINGFACE_TOKEN"):
        config["models"]["diarization"]["huggingface_token"] = os.environ.get("HUGGINGFACE_TOKEN")
    
    if os.environ.get("DIARIZATION_MODEL"):
        config["models"]["diarization"]["model_path"] = os.environ.get("DIARIZATION_MODEL")
    
    # ====== Segmentation configuration ======
    if os.environ.get("USE_SEGMENTATION") is not None:
        config["segmentation"]["enabled"] = os.environ.get("USE_SEGMENTATION").lower() in ["true", "1", "yes"]
    
    if os.environ.get("SEGMENTATION_LANGUAGE"):
        config["segmentation"]["language"] = os.environ.get("SEGMENTATION_LANGUAGE")
    
    if os.environ.get("SEGMENTATION_MODEL"):
        config["segmentation"]["model_name"] = os.environ.get("SEGMENTATION_MODEL")
    
    # ====== Inference configuration ======
    if os.environ.get("MAX_NEW_TOKENS"):
        config["inference"]["max_new_tokens"] = int(os.environ.get("MAX_NEW_TOKENS"))
    
    if os.environ.get("TEMPERATURE"):
        config["inference"]["temperature"] = float(os.environ.get("TEMPERATURE"))
    
    if os.environ.get("TOP_P"):
        config["inference"]["top_p"] = float(os.environ.get("TOP_P"))
    
    if os.environ.get("TOP_K"):
        config["inference"]["top_k"] = int(os.environ.get("TOP_K"))
    
    if os.environ.get("TIMEOUT_SECONDS"):
        config["inference"]["timeout_seconds"] = int(os.environ.get("TIMEOUT_SECONDS"))
    
    if os.environ.get("BATCH_PARALLEL") is not None:
        config["inference"]["batch_parallel"] = os.environ.get("BATCH_PARALLEL").lower() in ["true", "1", "yes"]
    
    if os.environ.get("MAX_RETRIES"):
        config["inference"]["max_retries"] = int(os.environ.get("MAX_RETRIES"))
    
    if os.environ.get("MAX_CACHE_SIZE"):
        config["inference"]["max_cache_size"] = int(os.environ.get("MAX_CACHE_SIZE"))
    
    # ====== API configuration ======
    if os.environ.get("HOST"):
        config["api"]["host"] = os.environ.get("HOST")
    
    if os.environ.get("PORT"):
        config["api"]["port"] = int(os.environ.get("PORT"))
    
    # ====== Post-processors configuration ======
    # JSONSimplifier configuration
    if os.environ.get("JSON_SIMPLIFIER_ENABLED") is not None:
        config["postprocessing"]["json_simplifier"]["enabled"] = \
            os.environ.get("JSON_SIMPLIFIER_ENABLED").lower() in ["true", "1", "yes"]
    
    if os.environ.get("JSON_SIMPLIFIER_MODEL"):
        config["postprocessing"]["json_simplifier"]["model"] = os.environ.get("JSON_SIMPLIFIER_MODEL")
    
    if os.environ.get("JSON_SIMPLIFIER_SYSTEM_PROMPT"):
        config["postprocessing"]["json_simplifier"]["system_prompt"] = os.environ.get("JSON_SIMPLIFIER_SYSTEM_PROMPT")
    
    if os.environ.get("JSON_SIMPLIFIER_APPLY_TO"):
        apply_to = os.environ.get("JSON_SIMPLIFIER_APPLY_TO").split(",")
        config["postprocessing"]["json_simplifier"]["apply_to"] = [t.strip() for t in apply_to]

    if os.environ.get("API_WORKERS"):
        config["api"]["workers"] = int(os.environ.get("API_WORKERS"))
    
    if os.environ.get("API_DEBUG") is not None:
        config["api"]["debug"] = os.environ.get("API_DEBUG").lower() in ["true", "1", "yes"]
    
    if os.environ.get("MAX_REQUEST_SIZE_MB"):
        config["api"]["max_request_size_mb"] = int(os.environ.get("MAX_REQUEST_SIZE_MB"))
    
    if os.environ.get("MAX_CONCURRENT_TASKS"):
        config["api"]["max_concurrent_tasks"] = int(os.environ.get("MAX_CONCURRENT_TASKS"))
    
    if os.environ.get("RESULT_STORAGE_DIR"):
        config["api"]["result_storage_dir"] = os.environ.get("RESULT_STORAGE_DIR")
    
    if os.environ.get("LOG_LEVEL"):
        config["api"]["log_level"] = os.environ.get("LOG_LEVEL").lower()
    
    if os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES"):
        config["api"]["token_expiration_minutes"] = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES"))
    
    if os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS"):
        config["api"]["refresh_token_expiration_days"] = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS"))
    
    # ====== Authentication configuration ======
    if os.environ.get("JWT_ALGORITHM"):
        config["auth"]["jwt_algorithm"] = os.environ.get("JWT_ALGORITHM")
    
    if os.environ.get("PASSWORD_HASH_ROUNDS"):
        config["auth"]["password_hash_rounds"] = int(os.environ.get("PASSWORD_HASH_ROUNDS"))
    
    if os.environ.get("ADMIN_EMAILS"):
        config["auth"]["admin_emails"] = os.environ.get("ADMIN_EMAILS").split(",")
    
    # ====== External services configuration ======
    # Stripe
    if os.environ.get("STRIPE_API_KEY"):
        config["services"]["stripe"]["enabled"] = True
        config["services"]["stripe"]["api_key"] = os.environ.get("STRIPE_API_KEY")
    
    if os.environ.get("STRIPE_WEBHOOK_SECRET"):
        config["services"]["stripe"]["webhook_secret"] = os.environ.get("STRIPE_WEBHOOK_SECRET")
    
    # Email
    if os.environ.get("SMTP_SERVER"):
        config["services"]["email"]["enabled"] = True
        config["services"]["email"]["smtp_server"] = os.environ.get("SMTP_SERVER")
    
    if os.environ.get("SMTP_PORT"):
        config["services"]["email"]["smtp_port"] = int(os.environ.get("SMTP_PORT"))
    
    if os.environ.get("SMTP_USERNAME"):
        config["services"]["email"]["smtp_username"] = os.environ.get("SMTP_USERNAME")
    
    if os.environ.get("SMTP_PASSWORD"):
        config["services"]["email"]["smtp_password"] = os.environ.get("SMTP_PASSWORD")
    
    if os.environ.get("SENDER_EMAIL"):
        config["services"]["email"]["sender_email"] = os.environ.get("SENDER_EMAIL")
    
    return config

def get_system_prompts() -> Tuple[Dict[str, str], List[str]]:
    """
    Loads system prompts from the prompts directory.
    Standardizes placeholders and checks their presence.
    
    Returns:
        tuple: A tuple containing (prompts_dict, prompt_order)
            - prompts_dict: Dictionary of prompts
            - prompt_order: Ordered list of prompt names
    """
    system_prompts = {}
    placeholder_pattern = re.compile(r'\{([a-zA-Z0-9_]+)\}')
    
    # List of recognized standard placeholders
    standard_placeholders = {
        "text", "input", "query", "content", "language", "context", 
        "question", "data", "json", "transcript", "audio", "video",
        "instructions", "parameters"
    }
    
    # Default prompts using the {text} placeholder in a standardized way
    default_prompts = {
        "system_1": "Analyze the following text: {text}",
        "system_1_2": "Analyze the coherence of the text: {text}",
        "system_1_2_1": "Evaluate the Markov dynamics of the text: {text}",
        "system_2": "Perform a Jungian analysis of the text: {text}",
        "system_3": "Perform a logical analysis of the text: {text}",
        "system_final": "Synthesize all previous analyses of the text: {text}",
        # Prompts specific to different features
        "nonverbal_analysis": "Analyze the nonverbal behaviors in the following video: {text}",
        "manipulation_analysis": "Identify manipulation strategies in the following content: {text}",
        "transcription_general_analysis": "Analyze the following transcription and identify key points: {text}",
        "image_generation": "Generate an image representing: {text}"
    }
    
    # List of expected prompts in standard order for the processing chain
    expected_prompts = ["system_1", "system_1_2", "system_1_2_1", "system_2", "system_3", "system_final"]
    
    try:
        # Check/create the prompts directory
        if not PROMPTS_DIR.exists():
            logger.warning(f"Prompts directory {PROMPTS_DIR} not found. Creating directory.")
            PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
            
            # Create default prompt files
            for prompt_name, prompt_content in default_prompts.items():
                with open(PROMPTS_DIR / f"{prompt_name}.txt", "w", encoding="utf-8") as f:
                    f.write(prompt_content)
            
            logger.info(f"Default prompts created in {PROMPTS_DIR}")
        
        # Load all available prompts and sort them explicitly by name
        prompt_files = sorted(
            list(PROMPTS_DIR.glob("*.txt")) + list(PROMPTS_DIR.glob("*.j2")),
            key=lambda x: x.stem  # Sort by name without extension
        )
        
        if not prompt_files:
            logger.warning(f"No prompt files found in {PROMPTS_DIR}. Using default values.")
            system_prompts = default_prompts.copy()
        else:
            # Load prompts from files (now sorted)
            for file_path in prompt_files:
                prompt_name = file_path.stem
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        prompt_content = f.read().strip()
                        
                        # Extract placeholders used in the prompt
                        placeholders_found = set(placeholder_pattern.findall(prompt_content))
                        
                        # Check placeholders
                        if not placeholders_found:
                            logger.warning(f"Prompt '{prompt_name}' does not contain any placeholder. "
                                          f"Automatically adding {{text}} placeholder at the end.")
                            prompt_content += " {text}"
                            placeholders_found = {"text"}
                        
                        # Check if used placeholders are standard
                        non_standard_placeholders = placeholders_found - standard_placeholders
                        if non_standard_placeholders:
                            logger.warning(f"Prompt '{prompt_name}' uses non-standard placeholders: "
                                         f"{', '.join(non_standard_placeholders)}. "
                                         f"Recommended standard placeholders are: {', '.join(standard_placeholders)}")
                        
                        # Suggestion if {text} is absent but other placeholders are present
                        if "text" not in placeholders_found and placeholders_found:
                            logger.info(f"Prompt '{prompt_name}' does not use the standard {{text}} placeholder "
                                      f"but uses: {', '.join(placeholders_found)}")
                        
                        system_prompts[prompt_name] = prompt_content
                        logger.debug(f"Prompt '{prompt_name}' loaded from {file_path} "
                                   f"with placeholders: {', '.join(placeholders_found)}")
                        
                except Exception as e:
                    logger.error(f"Error loading prompt {file_path}: {e}")
                    # If the file cannot be read, use the default prompt if it exists
                    if prompt_name in default_prompts:
                        system_prompts[prompt_name] = default_prompts[prompt_name]
                        logger.warning(f"Using default prompt for '{prompt_name}'")
        
        # Check that all expected prompts are present
        missing_prompts = [p for p in expected_prompts if p not in system_prompts]
        if missing_prompts:
            logger.warning(f"Missing prompts in the sequence: {missing_prompts}")
            
            # Add missing prompts from default values
            for prompt_name in missing_prompts:
                if prompt_name in default_prompts:
                    system_prompts[prompt_name] = default_prompts[prompt_name]
                    logger.warning(f"Adding missing default prompt: '{prompt_name}'")
        
        # Check that the order is correct and reorganize if necessary
        ordered_prompts = {}
        for prompt_name in expected_prompts:
            if prompt_name in system_prompts:
                ordered_prompts[prompt_name] = system_prompts[prompt_name]
        
        # Add all other non-standard prompts at the end
        for prompt_name, prompt_content in system_prompts.items():
            if prompt_name not in ordered_prompts:
                ordered_prompts[prompt_name] = prompt_content
                logger.info(f"Non-standard prompt detected: '{prompt_name}'")
        
        # Check if feature-specific prompts are present
        for func_prompt in ["nonverbal_analysis", "manipulation_analysis", "transcription_general_analysis"]:
            if func_prompt not in ordered_prompts and func_prompt in default_prompts:
                ordered_prompts[func_prompt] = default_prompts[func_prompt]
                logger.info(f"Adding missing functional prompt: '{func_prompt}'")
        
        # Build final prompt order
        prompt_order = list(ordered_prompts.keys())
        
        return ordered_prompts, prompt_order
        
    except Exception as e:
        logger.error(f"Critical error loading prompts: {e}")
        # In case of critical error, return default prompts
        return default_prompts, expected_prompts


# Initialize logging before loading configuration
def setup_logging():
    """Configure the application's logging system"""
    log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    
    # Basic format for all handlers
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Root configuration
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Create logs directory if needed
    if not LOGS_DIR.exists():
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # File handler
    file_handler = logging.FileHandler(LOGS_DIR / "cerastes.log")
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Add file handler to root logger
    logging.getLogger().addHandler(file_handler)
    
    # Reduce verbosity level for certain libraries
    for logger_name in ["urllib3", "PIL", "matplotlib"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

# Configure logging before anything else
setup_logging()

# Facilitate access to configuration
config = load_config()
system_prompts, prompt_order = get_system_prompts()

# Expose configuration sections for easy import
app_config = config["app"]
db_config = config["database"]
model_config = config["models"]
video_config = config["video"]
audio_config = config["audio"]
segmentation_config = config["segmentation"]
inference_config = config["inference"]
api_config = config["api"]
auth_config = config["auth"]
services_config = config["services"]
postprocessing_config = config["postprocessing"]