"""
Utility to enable or disable the JSONSimplifier post-processor
----------------------------------------------------------------------
This script allows enabling or disabling the JSONSimplifier post-processor
via the command line.
"""

import os
import sys
import json
import argparse
from pathlib import Path

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Enable or disable the JSONSimplifier post-processor"
    )
    
    parser.add_argument(
        "--enable", 
        action="store_true",
        help="Enable the post-processor"
    )
    
    parser.add_argument(
        "--disable", 
        action="store_true",
        help="Disable the post-processor"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        help="Specify the model to use"
    )
    
    parser.add_argument(
        "--apply-to",
        type=str,
        nargs="+",
        choices=["inference", "video", "transcription", "all"],
        help="Specify the task types to apply the post-processor to"
    )
    
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_args()
    
    # Check that either --enable or --disable is specified
    if not args.enable and not args.disable:
        print("Error: You must specify --enable or --disable")
        sys.exit(1)
    
    # Check that --enable and --disable are not both specified
    if args.enable and args.disable:
        print("Error: You cannot specify both --enable and --disable")
        sys.exit(1)
    
    # Load existing configuration
    config_path = os.environ.get("CONFIG_PATH", ".env")
    
    # Prepare modifications
    env_updates = {}
    
    # Update activation state
    if args.enable:
        env_updates["JSON_SIMPLIFIER_ENABLED"] = "true"
        print("Enabling JSONSimplifier post-processor")
    else:
        env_updates["JSON_SIMPLIFIER_ENABLED"] = "false"
        print("Disabling JSONSimplifier post-processor")
    
    # Update the model if specified
    if args.model:
        env_updates["JSON_SIMPLIFIER_MODEL"] = args.model
        print(f"Post-processor model set to: {args.model}")
    
    # Update task types if specified
    if args.apply_to:
        if "all" in args.apply_to:
            tasks = ["inference", "video", "transcription"]
        else:
            tasks = args.apply_to
        
        env_updates["JSON_SIMPLIFIER_APPLY_TO"] = ",".join(tasks)
        print(f"The post-processor will be applied to task types: {', '.join(tasks)}")
    
    # Update the .env file
    try:
        # Load existing content
        env_content = {}
        if Path(config_path).exists():
            with open(config_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_content[key.strip()] = value.strip()
        
        # Update with new values
        env_content.update(env_updates)
        
        # Write updated file
        with open(config_path, "w") as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")
        
        print(f"Configuration updated in {config_path}")
        print("Restart the API to apply changes")
        
    except Exception as e:
        print(f"Error updating configuration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()