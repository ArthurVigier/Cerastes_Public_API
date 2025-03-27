"""
Prompt Manager for Cerastes API
------------------------------------------
This module manages the formatting and validation of system prompts.
"""

import logging
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import os

logger = logging.getLogger("prompt_manager")

class PromptManager:
    """Central manager for system prompts with variable substitution."""
    
    def __init__(self, prompts_dir: str = "prompts"):
        """
        Initializes the prompt manager.
        
        Args:
            prompts_dir: Directory containing prompt files
        """
        self.prompts_dir = Path(prompts_dir)
        self.prompts_cache: Dict[str, str] = {}
        self.placeholder_pattern = re.compile(r'\{([a-zA-Z0-9_]+)\}')
        
        # Load prompts at startup
        self._load_prompt_files()
    
    def _load_prompt_files(self) -> None:
        """Loads all prompts from the prompts directory."""
        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory {self.prompts_dir} does not exist")
            return
        
        # Load individual .txt files
        for prompt_file in self.prompts_dir.glob("*.txt"):
            prompt_name = prompt_file.stem
            try:
                with open(prompt_file, "r", encoding="utf-8") as f:
                    self.prompts_cache[prompt_name] = f.read().strip()
                logger.debug(f"Prompt loaded: {prompt_name}")
            except Exception as e:
                logger.error(f"Error loading prompt {prompt_name}: {str(e)}")
        
        # Load the prompts collection JSON file if present
        json_file = self.prompts_dir / "prompts.json"
        if json_file.exists():
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    prompts_data = json.load(f)
                    for key, value in prompts_data.items():
                        self.prompts_cache[key] = value
                logger.debug(f"Prompts collection loaded from {json_file}")
            except Exception as e:
                logger.error(f"Error loading prompts collection: {str(e)}")
    
    def get_prompt(self, prompt_name: str) -> Optional[str]:
        """
        Retrieves a prompt by name without substitution.
        
        Args:
            prompt_name: Name of the prompt to retrieve
            
        Returns:
            The prompt or None if not found
        """
        if prompt_name not in self.prompts_cache:
            logger.warning(f"Prompt not found: {prompt_name}")
            return None
        
        return self.prompts_cache[prompt_name]
    
    def format_prompt(self, prompt_name: str, **kwargs) -> Optional[str]:
        """
        Retrieves a prompt by name and substitutes variables.
        
        Args:
            prompt_name: Name of the prompt to retrieve
            **kwargs: Variables to substitute in the prompt
            
        Returns:
            The formatted prompt or None if not found
        """
        prompt_template = self.get_prompt(prompt_name)
        if not prompt_template:
            return None
        
        # Check that all necessary placeholders are provided
        missing_vars = set()
        for match in self.placeholder_pattern.finditer(prompt_template):
            var_name = match.group(1)
            if var_name not in kwargs:
                missing_vars.add(var_name)
        
        if missing_vars:
            logger.error(f"Missing variables for prompt '{prompt_name}': {', '.join(missing_vars)}")
            return None
        
        # Perform substitution
        try:
            return prompt_template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Error formatting prompt '{prompt_name}': {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error formatting prompt '{prompt_name}': {str(e)}")
            return None
    
    def format_prompt_direct(self, prompt_template: str, **kwargs) -> str:
        """
        Formats a directly provided prompt with variables.
        
        Args:
            prompt_template: The prompt template
            **kwargs: Variables to substitute in the prompt
            
        Returns:
            The formatted prompt
        """
        try:
            return prompt_template.format(**kwargs)
        except Exception as e:
            logger.error(f"Error formatting direct prompt: {str(e)}")
            # Return the original template in case of error
            return prompt_template
    
    def get_placeholder_names(self, prompt_name: str) -> List[str]:
        """
        Extracts placeholder names from a prompt.
        
        Args:
            prompt_name: Name of the prompt
            
        Returns:
            List of placeholder names
        """
        prompt_template = self.get_prompt(prompt_name)
        if not prompt_template:
            return []
        
        return [match.group(1) for match in self.placeholder_pattern.finditer(prompt_template)]
    
    def add_prompt(self, prompt_name: str, prompt_template: str) -> None:
        """
        Adds or updates a prompt in the cache.
        
        Args:
            prompt_name: Name of the prompt
            prompt_template: Prompt template
        """
        self.prompts_cache[prompt_name] = prompt_template
        logger.debug(f"Prompt added/updated: {prompt_name}")

# Singleton instance
prompt_manager = PromptManager()

def get_prompt_manager() -> PromptManager:
    """Retrieves the prompt manager instance."""
    return prompt_manager