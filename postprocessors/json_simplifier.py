"""
JSON Simplifier Post-processor
--------------------------------
This module contains a post-processor that transforms complex JSON results
into clear English text using an LLM.
"""

import json
import logging
from typing import Dict, Any, Optional
from model_manager import ModelManager

# Logging configuration
logger = logging.getLogger("json_simplifier")

class JSONSimplifier:
    """
    Post-processor that converts complex JSON results into clear English text.
    Uses an LLM model to generate a textual explanation of JSON content.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the post-processor with the specified configuration.
        
        Args:
            config: Post-processor configuration
        """
        self.enabled = config.get("enabled", False)
        self.model_name = config.get("model", "huihui-ai/DeepSeek-R1-Distill-Qwen-14B-abliterated-v2")
        self.system_prompt = config.get("system_prompt", "Translate this json {text} in plain english")
        self.max_tokens = config.get("max_tokens", 1000)
        self.temperature = config.get("temperature", 0.3)
        self.apply_to = config.get("apply_to", ["inference", "video", "transcription"])
        
        # Model initialization (loaded on demand)
        self.model = None
        
        logger.info(f"JSONSimplifier initialized: enabled={self.enabled}, model={self.model_name}")
    
    def should_process(self, task_type: str) -> bool:
        """
        Determines if this post-processor should be applied to the specified task type.
        
        Args:
            task_type: Task type (inference, video, transcription, etc.)
            
        Returns:
            True if the post-processor should be applied, False otherwise
        """
        return self.enabled and task_type in self.apply_to
    
    def process(self, result: Dict[str, Any], task_type: str) -> Dict[str, Any]:
        """
        Processes the JSON result and adds a plain text explanation.
        
        Args:
            result: JSON result to process
            task_type: Type of task that generated this result
            
        Returns:
            JSON result with the explanation added
        """
        if not self.should_process(task_type):
            return result
        
        try:
            # Check if the result contains data to process
            if "result" not in result or not result["result"]:
                logger.warning("No result to simplify found")
                return result
            
            # Load the model if necessary
            if self.model is None:
                logger.info(f"Loading model {self.model_name} for JSON simplification")
                try:
                    model_manager = ModelManager.get_instance()
                    self.model = model_manager.get_model("llm", self.model_name)
                except Exception as e:
                    logger.error(f"Error loading model: {str(e)}")
                    return result
            
            # Prepare the prompt with the JSON
            json_str = json.dumps(result["result"], ensure_ascii=False)
            prompt = self.system_prompt.format(text=json_str)
            
            # Generate the explanation
            logger.info("Generating plain text explanation of JSON")
            explanation = self.model.generate(
                prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Add the explanation to the result
            result["plain_explanation"] = explanation.strip()
            
            logger.info("Plain text explanation generated successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error during JSON simplification: {str(e)}")
            return result