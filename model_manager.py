"""
Centralized AI Models Manager
--------------------------------------
This module provides a unified interface for loading, managing and releasing AI models.
"""

import os
import gc
import logging
import torch
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("model_manager")

# Configuration du logging
logger = logging.getLogger("model_manager")

# Énumération des types de modèles supportés
class ModelType(str, Enum):
    """Types de modèles supportés par le gestionnaire"""
    WHISPER = "whisper"
    INTERNVIDEO = "internvideo"
    DEEPSEEK = "deepseek"
    DIARIZATION = "diarization"
    
class ModelManager:
    """AI model manager with singleton pattern"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the single instance of the manager"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def initialize(cls):
        """Initialize the model manager"""
        cls.get_instance()
        logger.info("ModelManager initialized")
    
    @classmethod
    def cleanup(cls):
        """Clean up all loaded models"""
        if cls._instance:
            cls._instance._cleanup_all_models()
        logger.info("ModelManager cleaned up")
    
    def __init__(self):
        """Initialize the manager with empty dictionaries"""
        self.loaded_models = {}
        self.model_metadata = {}
    
    def get_model(self, model_type: str, model_name: str, **kwargs) -> Any:
        """
        Get a model, load it if not already available
        
        Args:
            model_type: Model type (e.g.: 'whisper', 'internvideo', 'deepseek')
            model_name: Model name/version
            **kwargs: Additional arguments for loading
            
        Returns:
            Model instance
        """
        model_key = f"{model_type}_{model_name}"
        
        # Check if the model is already loaded
        if model_key in self.loaded_models:
            logger.debug(f"Model {model_key} already loaded, reusing")
            return self.loaded_models[model_key]
        
        # Load the model according to its type
        logger.info(f"Loading model {model_key}")
        
        if model_type == "whisper":
            model = self._load_whisper_model(model_name, **kwargs)
        elif model_type == "internvideo":
            model = self._load_internvideo_model(model_name, **kwargs)
        elif model_type == "deepseek":
            model = self._load_deepseek_model(model_name, **kwargs)
        elif model_type == "diarization":
            model = self._load_diarization_model(model_name, **kwargs)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        # Store the model and its metadata
        self.loaded_models[model_key] = model
        self.model_metadata[model_key] = {
            "loaded_at": self._get_current_timestamp(),
            "last_used": self._get_current_timestamp(),
            "type": model_type,
            "name": model_name
        }
        
        return model
    
    def _load_whisper_model(self, model_name, **kwargs):
        """Load a Whisper model"""
        import whisper
        return whisper.load_model(model_name, device="cuda" if torch.cuda.is_available() else "cpu")
    
    def _load_internvideo_model(self, model_name, **kwargs):
        """Load an InternVideo model"""
        from transformers import AutoModel, AutoTokenizer
        
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
        
        if torch.cuda.is_available():
            model = model.half().cuda()
            model = model.to(torch.bfloat16)
        
        return (model, tokenizer)
    
    def _load_deepseek_model(self, model_name, **kwargs):
        """Load a DeepSeek model"""
        from vllm import LLM
        import os
        
        os.environ["VLLM_ALLOW_LONG_MAX_MODEL_LEN"] = "1"
        
        return LLM(
            model=model_name,
            dtype="half",
            tensor_parallel_size=torch.cuda.device_count(),
            gpu_memory_utilization=0.85,
            max_model_len=19760,
            trust_remote_code=True,
            enforce_eager=False,
        )
    
    def _load_diarization_model(self, model_name, **kwargs):
        """Load a diarization model"""
        from pyannote.audio import Pipeline
        
        token = kwargs.get("token") or os.environ.get("HUGGINGFACE_TOKEN", "")
        if not token:
            raise ValueError("A Hugging Face token is required for diarization")
        
        return Pipeline.from_pretrained(model_name, use_auth_token=token)
    
    def unload_model(self, model_type: str, model_name: str) -> bool:
        """
        Unload a specific model
        
        Args:
            model_type: Model type
            model_name: Model name
            
        Returns:
            True if the model was unloaded, False otherwise
        """
        model_key = f"{model_type}_{model_name}"
        
        if model_key in self.loaded_models:
            del self.loaded_models[model_key]
            self.model_metadata.pop(model_key, None)
            
            # Free memory
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info(f"Model {model_key} unloaded")
            return True
        
        return False
    
    def _cleanup_all_models(self):
        """Unload all models and free memory"""
        self.loaded_models.clear()
        self.model_metadata.clear()
        
        # Free memory
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("All models have been unloaded")
    
    def _get_current_timestamp(self):
        """Get the current timestamp"""
        import time
        return time.time()