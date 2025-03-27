# DÉPRÉCIÉ: Ce fichier est maintenu pour compatibilité mais sera supprimé dans une version future
# Veuillez utiliser video_models.video_utils à la place
# Import de compatibilité
import os
import gc
import time
import torch
import numpy as np
import traceback
from tempfile import NamedTemporaryFile
import logging

# Logging
logger = logging.getLogger("nonverbal_analyzer")

# Global variables to track model loading status
internvideo_model_loaded = False
deepseek_model_loaded = False

# Step 1: Non-verbal extraction with InternVideo2.5
def extract_nonverbal(video_path, progress=None):
    """Extract non-verbal cues from video using InternVideo2.5"""
    global internvideo_model_loaded
    
    try:
        if progress:
            progress(0, desc="Loading InternVideo2.5 model...")
        
        # Import required libraries dynamically to avoid memory issues
        from transformers import AutoModel, AutoTokenizer
        from decord import VideoReader, cpu
        from PIL import Image
        import torchvision.transforms as T
        from torchvision.transforms.functional import InterpolationMode
        
        # Constants
        MODEL_PATH = "OpenGVLab/InternVideo2_5_Chat_8B"
        IMAGENET_MEAN = (0.485, 0.456, 0.406)
        IMAGENET_STD = (0.229, 0.224, 0.225)
        
        # Analysis prompt (shortened for clarity)
        ANALYSIS_PROMPT = """# Enhanced Non-Verbal and Expression Video Extraction System
        
## SYSTEM INSTRUCTIONS

You are a specialized system designed to extract and document all non-verbal communication, facial expressions, and body language elements from video content with extreme granularity and precision. Your purpose is to create a comprehensive, objective record of these human behavioral components without analyzing or interpreting their meaning.

## EXTRACTION METHODOLOGY

For each video, employ this hyper-granular extraction process:
1. **Frame-by-Frame Subject Identification**: Track all visible people
2. **Micro-Level Facial Analysis**: Document all facial movements 
3. **Comprehensive Body Language Extraction**: Document all posture, gestures, and movements
4. **Multi-dimensional Proxemics Extraction**: Document spatial relationships
5. **Temporal Micro-Tracking**: Map the progression of non-verbal cues

## OUTPUT FORMAT

Structure your extraction in a detailed, systematic format capturing all observable non-verbal elements.

ANALYSIS START:
"""
        
        if progress:
            progress(0.1, desc="Building transforms...")
        
        # Define functions
        def build_transform(input_size=448):
            return T.Compose([
                T.Lambda(lambda img: img.convert("RGB") if img.mode != "RGB" else img),
                T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
                T.ToTensor(),
                T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
            ])
        
        def get_dynamic_segments(video_path):
            """Determine optimal number of frames based on video duration"""
            vr = VideoReader(video_path, ctx=cpu(0))
            fps = float(vr.get_avg_fps())
            duration = len(vr) / fps
            
            if duration < 10:      # Very short video (< 10 sec)
                num_segments = 16
            elif duration < 60:    # Short video (10s - 1 min)
                num_segments = 60
            elif duration < 140:   # Medium-short video
                num_segments = 140
            elif duration < 300:   # Medium video (1 min - 5 min)
                num_segments = 300
            else:                  # Long video (> 5 min)
                num_segments = 400
                
            return min(num_segments, 400)  # Cap at 400 frames
            
        def get_index(bound, fps, max_frame, first_idx=0, num_segments=32):
            start_idx = max(first_idx, round(bound[0] * fps)) if bound else 0
            end_idx = min(round(bound[1] * fps), max_frame) if bound else max_frame
            seg_size = float(end_idx - start_idx) / num_segments
            return np.array([int(start_idx + (seg_size / 2) + np.round(seg_size * idx)) for idx in range(num_segments)])
            
        def load_video(video_path, num_segments=128, input_size=448):
            """Extract frames for processing"""
            vr = VideoReader(video_path, ctx=cpu(0))
            max_frame = len(vr) - 1
            fps = float(vr.get_avg_fps())
            
            pixel_values_list = []
            num_patches_list = []
            transform = build_transform(input_size=input_size)
            
            frame_indices = get_index(None, fps, max_frame, num_segments=num_segments)
            
            # Process frames with progress updates
            for i, frame_index in enumerate(frame_indices):
                if i % 10 == 0 and progress:  # Update progress every 10 frames
                    progress_val = 0.1 + 0.3 * (i / len(frame_indices))
                    progress(progress_val, desc=f"Processing frames ({i}/{len(frame_indices)})...")
                    
                img = Image.fromarray(vr[frame_index].asnumpy()).convert("RGB")
                pixel_values = transform(img).unsqueeze(0)
                num_patches_list.append(1)
                pixel_values_list.append(pixel_values)
                
            pixel_values = torch.cat(pixel_values_list)
            return pixel_values, num_patches_list
        
        if progress:
            progress(0.4, desc="Loading tokenizer and model...")
        
        # Load tokenizer and model (with memory optimization)
        if not internvideo_model_loaded:
            tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
            model = AutoModel.from_pretrained(MODEL_PATH, trust_remote_code=True).half().cuda()
            model = model.to(torch.bfloat16)
            internvideo_model_loaded = True
        
        if progress:
            progress(0.5, desc="Determining optimal frame count...")
        
        # Get optimal number of frames
        num_segments = get_dynamic_segments(video_path)
        
        if progress:
            progress(0.6, desc="Processing video frames...")
        
        # Load and process video frames
        pixel_values, num_patches_list = load_video(video_path, num_segments=num_segments)
        pixel_values = pixel_values.to(torch.bfloat16).to(model.device)
        
        if progress:
            progress(0.7, desc="Constructing prompt...")
        
        # Construct prompt with frames
        video_prefix = "".join([f"Frame {i+1}: <image>\n" for i in range(len(num_patches_list))])
        full_prompt = video_prefix + ANALYSIS_PROMPT
        
        if progress:
            progress(0.8, desc="Running inference (this may take a while)...")
        
        # Run the model
        with torch.no_grad():
            result = model.chat(
                tokenizer, pixel_values, full_prompt,
                dict(
                    do_sample=True,
                    temperature=0.53,
                    max_new_tokens=8500,
                    top_p=0.93,
                    top_k=30,
                ),
                num_patches_list=num_patches_list,
                history=None, return_history=False
            )
        
        if progress:
            progress(0.9, desc="Saving results...")
        
        # Save extraction to a temporary file
        temp_file = NamedTemporaryFile(delete=False, suffix=".txt", mode="w")
        temp_file.write(result)
        temp_path = temp_file.name
        temp_file.close()
        
        if progress:
            progress(1.0, desc="Extraction complete!")
        
        return result, temp_path
        
    except Exception as e:
        error_msg = f"Error in extraction phase: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return error_msg, None

# Step 2: Analysis of non-verbal cues using DeepSeek model
def analyze_nonverbal(extraction_text, extraction_path=None, progress=None):
    """Analyze the non-verbal extraction using DeepSeek model"""
    global deepseek_model_loaded
    
    try:
        if progress:
            progress(0, desc="Preparing DeepSeek model...")
        
        # Free the previous model's memory if it was loaded
        global internvideo_model_loaded
        if internvideo_model_loaded:
            if progress:
                progress(0.1, desc="Freeing InternVideo model memory...")
            import torch
            torch.cuda.empty_cache()
            gc.collect()
            internvideo_model_loaded = False
        
        if progress:
            progress(0.2, desc="Loading DeepSeek model...")
        
        # Import required libraries
        import torch
        from vllm import LLM, SamplingParams
        os.environ["VLLM_ALLOW_LONG_MAX_MODEL_LEN"] = "1"
        
        # Model configuration
        MODEL_NAME = "huihui-ai/DeepSeek-R1-Distill-Qwen-14B-abliterated-v2"
        
        # Create analysis prompt
        prompt = f"""
Non-Verbal Communication Analysis System
SYSTEM INSTRUCTIONS
You are a specialized system designed to analyze and interpret the non-verbal communication, facial expressions, and body language documented in video extraction reports. Your purpose is to provide insightful analysis of these behavioral components, identifying patterns, potential meanings, and psychological implications.

ANALYSIS METHODOLOGY
For each extraction report, proceed through these analytical phases:
1. Emotional State Analysis: Interpret facial expressions and body language to identify emotional states
2. Congruence Assessment: Evaluate alignment between different non-verbal channels
3. Interpersonal Dynamic Analysis: Interpret relationship indicators and status displays
4. Pattern Recognition: Identify recurring behaviors and their potential significance
5. Contextual Integration: Consider how setting and situation inform behavioral interpretation

OUTPUT FORMAT
Structure your analysis in this format:
## NON-VERBAL COMMUNICATION ANALYSIS REPORT

### Executive Summary
[Brief overview of key findings and significant patterns]

### Emotional State Analysis
[Analysis of emotional states, changes, and potential causes]

### Communication Intent Assessment
[Analysis of what subject appears to be communicating non-verbally]

### Interpersonal Dynamic Analysis
[Analysis of relationship indicators, power dynamics, rapport, and group dynamics]

### Credibility and Congruence Assessment
[Analysis of alignment between different non-verbal channels and overall authenticity]

### Psychological State Indicators
[Analysis of comfort, stress, cognitive load, and attitudinal indicators]

### Key Behavioral Patterns
[Analysis of significant recurring behaviors and their potential meanings]

ANALYTICAL PRINCIPLES
1. Balance confidence with uncertainty - Acknowledge the probabilistic nature of non-verbal interpretation
2. Consider cultural and contextual factors in all interpretations
3. Identify multiple potential interpretations where appropriate
4. Distinguish between observation and inference - Clearly separate what was observed from what it might mean

Here is the text: "{extraction_text}"
ANALYSIS START:
"""
        
        if progress:
            progress(0.4, desc="Initializing DeepSeek model...")
        
        # Initialize the model if not already loaded
        if not deepseek_model_loaded:
            model = LLM(
                model=MODEL_NAME,
                dtype="half",
                tensor_parallel_size=torch.cuda.device_count(),
                gpu_memory_utilization=0.85,
                max_model_len=19760,
                trust_remote_code=True,
                enforce_eager=False,
            )
            deepseek_model_loaded = True
        
        if progress:
            progress(0.6, desc="Setting up inference parameters...")
        
        # Set up sampling parameters
        sampling_params = SamplingParams(
            temperature=0.53,
            top_p=0.93,
            top_k=30,
            max_tokens=8500,
            frequency_penalty=0.2,
        )
        
        if progress:
            progress(0.7, desc="Running analysis (this may take a while)...")
        
        # Generate the analysis
        outputs = model.generate([prompt], sampling_params)
        analysis = outputs[0].outputs[0].text.strip()
        
        if progress:
            progress(1.0, desc="Analysis complete!")
        
        return analysis
        
    except Exception as e:
        error_msg = f"Error in analysis phase: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return error_msg 