"""
Middleware for language detection and automatic translation.
This module detects the input language of text, translates it to English if necessary,
then retranslates the response into the original language.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union, Callable
import time
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# For language detection
from langdetect import detect, LangDetectException
from langdetect.detector_factory import DetectorFactory
DetectorFactory.seed = 0  # For consistent results

# For translation
from transformers import MarianMTModel, MarianTokenizer
import torch

# Logging configuration
logger = logging.getLogger("translation_middleware")

# Models storage path
MODELS_CACHE_DIR = "translation_models"

# List of supported languages - ISO 639-1 codes
SUPPORTED_LANGUAGES = {
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ar": "Arabic",
    # Add other languages as needed
}

# Minimum confidence threshold for language detection
LANGUAGE_DETECTION_THRESHOLD = 0.85

class TranslationManager:
    """Translation manager using Hugging Face models."""
    
    def __init__(self):
        self.tokenizers = {}
        self.models = {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"TranslationManager initialized on {self.device}")
    
    def get_model_name(self, source_lang: str, target_lang: str) -> str:
        """Returns the model name for the language pair."""
        if source_lang == "en" and target_lang in SUPPORTED_LANGUAGES:
            return f"Helsinki-NLP/opus-mt-en-{target_lang}"
        elif target_lang == "en" and source_lang in SUPPORTED_LANGUAGES:
            return f"Helsinki-NLP/opus-mt-{source_lang}-en"
        else:
            # Fallback for pairs not directly supported
            return f"Helsinki-NLP/opus-mt-mul-en" if target_lang == "en" else f"Helsinki-NLP/opus-mt-en-mul"
    
    def load_model(self, source_lang: str, target_lang: str) -> None:
        """Loads a translation model for a language pair."""
        model_key = f"{source_lang}-{target_lang}"
        
        if model_key in self.models:
            return
        
        model_name = self.get_model_name(source_lang, target_lang)
        logger.info(f"Loading translation model {model_name}")
        
        try:
            tokenizer = MarianTokenizer.from_pretrained(model_name, cache_dir=MODELS_CACHE_DIR)
            model = MarianMTModel.from_pretrained(model_name, cache_dir=MODELS_CACHE_DIR)
            
            # Move to GPU if available
            if self.device == "cuda":
                model = model.to(self.device)
            
            self.tokenizers[model_key] = tokenizer
            self.models[model_key] = model
            logger.info(f"Model {model_name} loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            raise
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translates text from a source language to a target language."""
        if source_lang == target_lang:
            return text
        
        model_key = f"{source_lang}-{target_lang}"
        
        # Load the model if necessary
        if model_key not in self.models:
            self.load_model(source_lang, target_lang)
        
        tokenizer = self.tokenizers[model_key]
        model = self.models[model_key]
        
        try:
            # Tokenization
            encoded = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            
            # Move to GPU if available
            if self.device == "cuda":
                encoded = {k: v.to(self.device) for k, v in encoded.items()}
            
            # Translation
            translated = model.generate(**encoded)
            
            # Decoding
            result = tokenizer.decode(translated[0], skip_special_tokens=True)
            return result
        except Exception as e:
            logger.error(f"Error during translation: {e}")
            return text  # In case of error, return the original text
    
    def detect_language(self, text: str) -> Optional[str]:
        """Detects the language of a text."""
        if not text or len(text) < 10:
            return None
        
        try:
            detected_lang = detect(text)
            return detected_lang if detected_lang in SUPPORTED_LANGUAGES else None
        except LangDetectException:
            return None
    
    def close(self):
        """Releases resources."""
        self.models.clear()
        self.tokenizers.clear()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

# Instantiate the translation manager
translation_manager = TranslationManager()

class TranslationMiddleware(BaseHTTPMiddleware):
    """Middleware for language detection and automatic translation."""
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: List[str] = None,
        exclude_prefixes: List[str] = None,
        text_field_names: List[str] = None
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
        self.exclude_prefixes = exclude_prefixes or ["/static/", "/assets/"]
        self.text_field_names = text_field_names or ["text", "content", "prompt", "transcription"]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Processes requests and responses with language detection and translation."""
        # Check if this path should be excluded
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # Check if it's an inference or transcription request
        if not (request.url.path.startswith("/api/inference") or 
                request.url.path.startswith("/api/transcription")):
            return await call_next(request)
        
        # Check HTTP method
        if request.method != "POST":
            return await call_next(request)
        
        # Get language information from the request
        specified_source_lang = request.query_params.get("language")
        translate_back = request.query_params.get("translate_back", "true").lower() == "true"
        
        # Get the request body
        try:
            body = await self._get_request_body(request)
        except Exception as e:
            logger.error(f"Error retrieving request body: {e}")
            return await call_next(request)
        
        source_lang = None
        needs_translation = False
        text_to_translate = None
        
        # Extract text from potential fields
        for field_name in self.text_field_names:
            if field_name in body:
                text_to_translate = body[field_name]
                break
        
        # If no text is found, continue normally
        if not text_to_translate or not isinstance(text_to_translate, str):
            return await call_next(request)
        
        # Get the source language (specified or detected)
        if specified_source_lang:
            source_lang = specified_source_lang
        else:
            source_lang = translation_manager.detect_language(text_to_translate)
        
        # If the language is not detected or is already English, continue normally
        if not source_lang or source_lang == "en":
            return await call_next(request)
        
        # Non-English language detected, translate
        needs_translation = True
        
        # Log the information
        logger.info(f"Detected language: {source_lang}, translation enabled")
        
        # Translate the text to English for processing
        original_text = text_to_translate
        translated_text = translation_manager.translate(text_to_translate, source_lang, "en")
        
        # Modify the request body with the translated text
        modified_body = body.copy()
        for field_name in self.text_field_names:
            if field_name in modified_body:
                modified_body[field_name] = translated_text
                break
        
        # Modify the request with the new body
        request._body = json.dumps(modified_body).encode()
        
        # Add translation context headers
        request.state.translation_context = {
            "needs_translation": needs_translation,
            "source_lang": source_lang,
            "original_text": original_text,
            "translate_back": translate_back
        }
        
        # Process the request
        start_time = time.time()
        response = await call_next(request)
        processing_time = time.time() - start_time
        
        # If no need to retranslate the response, return directly
        if not needs_translation or not translate_back:
            return response
        
        # Check if it's a JSON response
        if response.headers.get("content-type", "").startswith("application/json"):
            # Get the response content
            response_body = await self._get_response_body(response)
            
            # Find the field containing the result to translate
            fields_to_translate = self._find_text_fields_to_translate(response_body)
            
            # Translate the found fields
            modified_response = response_body.copy()
            for field_path, value in fields_to_translate:
                if isinstance(value, str) and len(value) > 5:
                    translated_value = translation_manager.translate(value, "en", source_lang)
                    self._set_field_value(modified_response, field_path, translated_value)
            
            # Create a new response with the translated content
            return JSONResponse(
                content=modified_response,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        
        return response
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if the path is excluded from the middleware."""
        if path in self.exclude_paths:
            return True
        
        for prefix in self.exclude_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    async def _get_request_body(self, request: Request) -> Dict[str, Any]:
        """Extracts the JSON request body."""
        if not hasattr(request, "_body"):
            body = await request.body()
            request._body = body
        
        body_str = request._body.decode("utf-8")
        if not body_str:
            return {}
        
        try:
            return json.loads(body_str)
        except json.JSONDecodeError:
            return {}
    
    async def _get_response_body(self, response: Response) -> Dict[str, Any]:
        """Extracts the JSON response body."""
        if isinstance(response, JSONResponse):
            return response.body_dict
        
        # For other response types, try to decode the content
        try:
            return json.loads(response.body.decode("utf-8"))
        except Exception:
            return {}
    
    def _find_text_fields_to_translate(self, data: Union[Dict, List], path: List = None) -> List:
        """Finds all text fields in JSON data that need to be translated."""
        if path is None:
            path = []
        
        fields = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = path + [key]
                
                # If it's a potential text field and not a technical field
                if isinstance(value, str) and key in self.text_field_names:
                    fields.append((current_path, value))
                
                # Recursively explore sub-structures
                if isinstance(value, (dict, list)):
                    fields.extend(self._find_text_fields_to_translate(value, current_path))
                    
                # Specifically process transcription segments
                if key == "segments" and isinstance(value, list):
                    for i, segment in enumerate(value):
                        if isinstance(segment, dict) and "text" in segment:
                            segment_path = current_path + [i, "text"]
                            fields.append((segment_path, segment["text"]))
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = path + [i]
                fields.extend(self._find_text_fields_to_translate(item, current_path))
        
        return fields
    
    def _set_field_value(self, data: Dict, path: List, value: Any):
        """Modifies the value of a field in JSON data according to the given path."""
        if not path:
            return
        
        current = data
        for i, key in enumerate(path):
            if i == len(path) - 1:
                current[key] = value
            else:
                current = current[key]