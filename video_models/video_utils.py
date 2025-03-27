"""
Module for video analysis and non-verbal information extraction
This unified module contains functions for:
1. Video content extraction
2. Video content analysis
3. Non-verbal cues extraction
4. Non-verbal elements analysis
"""

import os
import gc
import time
import torch
import numpy as np
import traceback
from tempfile import NamedTemporaryFile
import logging
from typing import Tuple, List, Optional, Dict, Any, Callable

# Logging configuration
logger = logging.getLogger("video_analyzer")

# Global variables to track model states
internvideo_model_loaded = False
deepseek_model_loaded = False

# Shared constants
INTERNVIDEO_MODEL_PATH = "OpenGVLab/InternVideo2_5_Chat_8B"
DEEPSEEK_MODEL_PATH = "huihui-ai/DeepSeek-R1-Distill-Qwen-14B-abliterated-v2"
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

# Shared utility functions
def build_transform(input_size=448):
    """Creates transformations for input images"""
    from torchvision import transforms as T
    from torchvision.transforms.functional import InterpolationMode
    
    return T.Compose([
        T.Lambda(lambda img: img.convert("RGB") if img.mode != "RGB" else img),
        T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
        T.ToTensor(),
        T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
    ])

def get_dynamic_segments(video_path: str) -> int:
    """Determines the optimal number of segments based on video duration"""
    from decord import VideoReader, cpu
    
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
        
    return min(num_segments, 400)  # Limit to 400 segments

def get_index(bound, fps, max_frame, first_idx=0, num_segments=32):
    """Calculates the indices of images to extract"""
    start_idx = max(first_idx, round(bound[0] * fps)) if bound else 0
    end_idx = min(round(bound[1] * fps), max_frame) if bound else max_frame
    seg_size = float(end_idx - start_idx) / num_segments
    return np.array([int(start_idx + (seg_size / 2) + np.round(seg_size * idx)) for idx in range(num_segments)])

def load_video(video_path: str, num_segments: int = 128, input_size: int = 448, 
               progress: Optional[Callable] = None) -> Tuple[torch.Tensor, List[int]]:
    """Loads and preprocesses video images"""
    from decord import VideoReader, cpu
    from PIL import Image
    
    vr = VideoReader(video_path, ctx=cpu(0))
    max_frame = len(vr) - 1
    fps = float(vr.get_avg_fps())
    
    pixel_values_list = []
    num_patches_list = []
    transform = build_transform(input_size=input_size)
    
    frame_indices = get_index(None, fps, max_frame, num_segments=num_segments)
    
    # Image processing with progress updates
    for i, frame_index in enumerate(frame_indices):
        if i % 10 == 0 and progress:  # Update every 10 images
            progress_val = 0.1 + 0.3 * (i / len(frame_indices))
            progress(progress_val, desc=f"Processing images ({i}/{len(frame_indices)})...")
                
        img = Image.fromarray(vr[frame_index].asnumpy()).convert("RGB")
        pixel_values = transform(img).unsqueeze(0)
        num_patches_list.append(1)
        pixel_values_list.append(pixel_values)
            
    pixel_values = torch.cat(pixel_values_list)
    return pixel_values, num_patches_list

def unload_internvideo_model():
    """Frees memory of the InternVideo model"""
    global internvideo_model_loaded
    if internvideo_model_loaded:
        try:
            import torch
            torch.cuda.empty_cache()
            gc.collect()
            internvideo_model_loaded = False
            return True
        except Exception as e:
            logger.error(f"Error while freeing InternVideo model: {str(e)}")
            return False
    return False

def load_internvideo_model():
    """Loads the InternVideo model if necessary"""
    global internvideo_model_loaded
    
    if not internvideo_model_loaded:
        try:
            from transformers import AutoModel, AutoTokenizer
            
            tokenizer = AutoTokenizer.from_pretrained(INTERNVIDEO_MODEL_PATH, trust_remote_code=True)
            model = AutoModel.from_pretrained(INTERNVIDEO_MODEL_PATH, trust_remote_code=True).half().cuda()
            model = model.to(torch.bfloat16)
            internvideo_model_loaded = True
            return model, tokenizer
        except Exception as e:
            logger.error(f"Error while loading InternVideo model: {str(e)}")
            return None, None
    return None, None

def load_deepseek_model():
    """Loads the DeepSeek model if necessary"""
    global deepseek_model_loaded
    
    if not deepseek_model_loaded:
        try:
            from vllm import LLM
            import torch
            os.environ["VLLM_ALLOW_LONG_MAX_MODEL_LEN"] = "1"
            
            model = LLM(
                model=DEEPSEEK_MODEL_PATH,
                dtype="half",
                tensor_parallel_size=torch.cuda.device_count(),
                gpu_memory_utilization=0.85,
                max_model_len=19760,
                trust_remote_code=True,
                enforce_eager=False,
            )
            deepseek_model_loaded = True
            return model
        except Exception as e:
            logger.error(f"Error while loading DeepSeek model: {str(e)}")
            return None
    return None

# Prompts for different analyses
VIDEO_CONTENT_PROMPT = """# Video Content Extraction Prompt System

## SYSTEM INSTRUCTIONS

You are a specialized system designed to extract and document all observable components from video content. Your purpose is to create a comprehensive, objective record of visual elements without analyzing or interpreting their meaning. This detailed extraction will serve as input for subsequent analytical systems.

## EXTRACTION METHODOLOGY

For each video, proceed through these extraction phases:

1. **Initial Overview**: Identify basic video parameters
2. **Visual Component Extraction**: Document all visual elements sequentially
3. **Temporal Sequencing**: Map the progression of components through time
4. **Component Relationship Mapping**: Note spatial and temporal relationships

## COMPONENT EXTRACTION GUIDELINES

Extract and document each of the following component categories in detail:

### 1. Technical Parameters
- **Video Quality**: Resolution, frame rate, aspect ratio
- **Duration**: Total length, timestamp format
- **Format**: Video codec, container format
- **Technical Issues**: Visible compression artifacts, frame drops, or other technical anomalies

### 2. Visual Composition
- **Shot Types**: Close-up, medium shot, wide shot, extreme close-up, etc.
- **Camera Angles**: High angle, low angle, eye level, bird's eye view, etc.
- **Camera Movements**: Pan, tilt, tracking, zoom, static, handheld, stabilized, etc.
- **Framing**: Rule of thirds positioning, headroom, lead room, symmetry/asymmetry
- **Depth of Field**: Shallow, deep, rack focus events
- **Composition**: Foreground, midground, background elements and their arrangement

### 3. Lighting and Color
- **Lighting Setup**: High-key, low-key, natural, artificial, direction of light
- **Lighting Quality**: Hard, soft, diffused, direct
- **Colorimetry**: Color palette, saturation levels, temperature (warm/cool)
- **Contrast Levels**: High contrast, low contrast
- **Color Grading**: Visible filters, stylistic color treatments
- **Time of Day**: Daytime, nighttime, golden hour, etc.

### 4. Environment and Setting
- **Location Type**: Indoor, outdoor, studio, natural environment
- **Setting Details**: Urban, rural, domestic, public, private
- **Set Design Elements**: Furniture, decorations, props, architectural features
- **Weather Conditions**: If outdoors - clear, cloudy, rainy, snowy, etc.
- **Time Period Indicators**: Modern, historical, futuristic elements

### 5. People and Characters
- **Number of People**: Total count, entries/exits during footage
- **Physical Characteristics**: Age range, gender presentation, ethnicity, clothing, distinctive features
- **Positioning**: Standing, sitting, walking, relative positions between people
- **Facial Expressions**: Detailed documentation of visible expressions (smiling, frowning, neutral, etc.)
- **Body Language**: Posture, gestures, proxemics (physical distance between people)
- **Eye Direction**: Where subjects are looking
- **Physical Actions**: What subjects are physically doing

### 6. Text Elements
- **On-screen Text**: Titles, subtitles, captions, credits, watermarks
- **Text in Scene**: Signs, books, screens, clothing with text
- **Text Style**: Font, size, color, animation
- **Text Positioning**: Where text appears on screen
- **Duration**: How long text remains visible
- **Language**: What language(s) appears in text

### 7. Graphics and Visual Effects
- **Graphic Elements**: Logos, icons, illustrations, diagrams
- **Animation**: Moving graphics, style of animation
- **Visual Effects**: CGI elements, compositing, filters
- **Transitions**: Cuts, dissolves, wipes, fades
- **Screen Graphics**: User interfaces, screens within the video
- **Overlays**: Information graphics, lower thirds, watermarks

### 8. Temporal Elements
- **Editing Pace**: Shot length, cutting patterns
- **Time Manipulation**: Slow motion, time-lapse, freeze frames
- **Sequence of Events**: Chronological documentation of what happens
- **Scene Changes**: Transitions between different locations or settings
- **Timestamp References**: Noting when specific elements appear and disappear

### 9. Production Context (if evident)
- **Production Type**: Professional, amateur, social media, broadcast, film
- **Visible Equipment**: Microphones, lights, reflectors in frame
- **Production Credits**: Visible information about creators

## OUTPUT FORMAT

Structure your extraction in this format:
VIDEO EXTRACTION REPORT
Basic Parameters
* Title (if known): [title]
* Duration: [time]
* Resolution: [resolution]
* Aspect Ratio: [ratio]
Visual Component Timeline
[00:00-00:00] [Detailed description of visual elements during this timeframe] [00:00-00:00] [Next segment description] ...
People and Characters
* Person 1: [Detailed description]
    * Visible at: [Timestamp ranges]
    * Actions: [Description of what they do]
    * Expressions: [Description of notable expressions]
* Person 2: [...]
Text Elements
* [00:00-00:00] [Description of text content, style, position]
* [00:00-00:00] [...]
Graphics and Effects
* [00:00-00:00] [Description of graphics or effects]
* [00:00-00:00] [...]
Technical Elements
* Camera Angles: [List all observed camera angles with timestamps]
* Shot Types: [List all observed shot types with timestamps]
* Camera Movements: [List all observed movements with timestamps]
* Lighting Conditions: [List all observed lighting conditions with timestamps]
* Color Palette: [Description of dominant colors and changes]
* Editing Techniques: [Description of evident editing choices]
Component Relationships
* [Description of notable spatial relationships between elements]
* [Description of notable temporal relationships between elements]


## IMPORTANT GUIDELINES

1. **Record ONLY what is directly observable** in the video
2. **DO NOT analyze, interpret, or evaluate** the content
3. **Avoid subjective judgments** about quality, intent, or meaning
4. **Do not speculate** about anything not visible in the video
5. **Be precise and comprehensive** in documenting all components
6. **Maintain objective, neutral language** throughout
7. **If uncertain about any element**, note the uncertainty rather than guessing
8. **Document timestamps** as accurately as possible
9. **Prioritize completeness** - capture all relevant visual elements
10. **Focus on EXTRACTION ONLY** - leave all analysis to subsequent systems

REMEMBER: Your role is solely to extract and document components, not to analyze them. Provide a comprehensive extraction that will serve as a foundation for later analytical systems.
"""

NONVERBAL_EXTRACTION_PROMPT = """# Enhanced Non-Verbal and Expression Video Extraction System
        
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

NONVERBAL_ANALYSIS_PROMPT_TEMPLATE = """
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

# Main functions
def extract_video_content(video_path: str, progress: Optional[Callable] = None) -> Tuple[str, Optional[str]]:
    """Extracts video content using InternVideo2.5"""
    global internvideo_model_loaded
    
    try:
        if progress:
            progress(0, desc="Loading InternVideo2.5 model...")
        
        # Import necessary libraries
        from transformers import AutoModel, AutoTokenizer
        
        # Model loading
        if not internvideo_model_loaded:
            tokenizer = AutoTokenizer.from_pretrained(INTERNVIDEO_MODEL_PATH, trust_remote_code=True)
            model = AutoModel.from_pretrained(INTERNVIDEO_MODEL_PATH, trust_remote_code=True).half().cuda()
            model = model.to(torch.bfloat16)
            internvideo_model_loaded = True
        else:
            # Get existing instances
            tokenizer = AutoTokenizer.from_pretrained(INTERNVIDEO_MODEL_PATH, trust_remote_code=True)
            model = AutoModel.from_pretrained(INTERNVIDEO_MODEL_PATH, trust_remote_code=True, device_map="auto")
        
        if progress:
            progress(0.5, desc="Determining optimal number of frames...")
        
        # Get the optimal number of segments
        num_segments = get_dynamic_segments(video_path)
        
        if progress:
            progress(0.6, desc="Processing video frames...")
        
        # Loading and processing video frames
        pixel_values, num_patches_list = load_video(video_path, num_segments=num_segments, progress=progress)
        pixel_values = pixel_values.to(torch.bfloat16).to(model.device)
        
        if progress:
            progress(0.7, desc="Building prompt...")
        
        # Building prompt with images
        video_prefix = "".join([f"Frame {i+1}: <image>\n" for i in range(len(num_patches_list))])
        full_prompt = video_prefix + VIDEO_CONTENT_PROMPT
        
        if progress:
            progress(0.8, desc="Running extraction (may take a while)...")
        
        # Running the model
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
            progress(0.9, desc="Saving extraction results...")
        
        # Save to a temporary file
        temp_file = NamedTemporaryFile(delete=False, suffix=".txt", mode="w")
        temp_file.write(result)
        temp_path = temp_file.name
        temp_file.close()
        
        if progress:
            progress(1.0, desc="Extraction completed!")
        
        return result, temp_path
        
    except Exception as e:
        error_msg = f"Error in extraction phase: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return error_msg, None

def extract_nonverbal(video_path: str, progress: Optional[Callable] = None) -> Tuple[str, Optional[str]]:
    """Extracts non-verbal cues using InternVideo2.5"""
    global internvideo_model_loaded
    
    try:
        if progress:
            progress(0, desc="Loading InternVideo2.5 model...")
        
        # Import necessary libraries
        from transformers import AutoModel, AutoTokenizer
        
        # Model loading
        if not internvideo_model_loaded:
            tokenizer = AutoTokenizer.from_pretrained(INTERNVIDEO_MODEL_PATH, trust_remote_code=True)
            model = AutoModel.from_pretrained(INTERNVIDEO_MODEL_PATH, trust_remote_code=True).half().cuda()
            model = model.to(torch.bfloat16)
            internvideo_model_loaded = True
        else:
            # Get existing instances
            tokenizer = AutoTokenizer.from_pretrained(INTERNVIDEO_MODEL_PATH, trust_remote_code=True)
            model = AutoModel.from_pretrained(INTERNVIDEO_MODEL_PATH, trust_remote_code=True, device_map="auto")
        
        if progress:
            progress(0.5, desc="Determining optimal number of frames...")
        
        # Get the optimal number of segments
        num_segments = get_dynamic_segments(video_path)
        
        if progress:
            progress(0.6, desc="Processing video frames...")
        
        # Loading and processing video frames
        pixel_values, num_patches_list = load_video(video_path, num_segments=num_segments, progress=progress)
        pixel_values = pixel_values.to(torch.bfloat16).to(model.device)
        
        if progress:
            progress(0.7, desc="Building prompt...")
        
        # Building prompt with images
        video_prefix = "".join([f"Frame {i+1}: <image>\n" for i in range(len(num_patches_list))])
        full_prompt = video_prefix + NONVERBAL_EXTRACTION_PROMPT
        
        if progress:
            progress(0.8, desc="Running inference (may take a while)...")
        
        # Running the model
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
        
        # Save to a temporary file
        temp_file = NamedTemporaryFile(delete=False, suffix=".txt", mode="w")
        temp_file.write(result)
        temp_path = temp_file.name
        temp_file.close()
        
        if progress:
            progress(1.0, desc="Extraction completed!")
        
        return result, temp_path
        
    except Exception as e:
        error_msg = f"Error in extraction phase: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return error_msg, None

def analyze_nonverbal(extraction_text: str, extraction_path: Optional[str] = None, 
                     progress: Optional[Callable] = None) -> str:
    """Analyzes non-verbal cues using the DeepSeek model"""
    global deepseek_model_loaded
    
    try:
        if progress:
            progress(0, desc="Preparing DeepSeek model...")
        
        # Free memory of previous model if it was loaded
        global internvideo_model_loaded
        if internvideo_model_loaded:
            if progress:
                progress(0.1, desc="Freeing InternVideo model memory...")
            unload_internvideo_model()
        
        if progress:
            progress(0.2, desc="Loading DeepSeek model...")
        
        # Import necessary libraries
        from vllm import SamplingParams
        
        # Initialize model if not already loaded
        if not deepseek_model_loaded:
            model = load_deepseek_model()
            if model is None:
                raise Exception("Failed to load DeepSeek model")
        
        if progress:
            progress(0.6, desc="Configuring inference parameters...")
        
        # Configure sampling parameters
        sampling_params = SamplingParams(
            temperature=0.53,
            top_p=0.93,
            top_k=30,
            max_tokens=8500,
            frequency_penalty=0.2,
        )
        
        if progress:
            progress(0.7, desc="Running analysis (may take a while)...")
        
        # Prepare analysis prompt
        prompt = NONVERBAL_ANALYSIS_PROMPT_TEMPLATE.format(extraction_text=extraction_text)
        
        # Generate analysis
        outputs = model.generate([prompt], sampling_params)
        analysis = outputs[0].outputs[0].text.strip()
        
        if progress:
            progress(1.0, desc="Analysis completed!")
        
        return analysis
        
    except Exception as e:
        error_msg = f"Error in analysis phase: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return error_msg

def analyze_manipulation_strategies(extraction_text: str, extraction_path: Optional[str] = None, 
                                   progress: Optional[Callable] = None) -> str:
    """Analyzes video manipulation strategies using the DeepSeek model"""
    global deepseek_model_loaded
    
    try:
        if progress:
            progress(0, desc="Preparing DeepSeek model...")
        
        # Free memory of previous model if it was loaded
        global internvideo_model_loaded
        if internvideo_model_loaded:
            if progress:
                progress(0.1, desc="Freeing InternVideo model memory...")
            unload_internvideo_model()
        
        if progress:
            progress(0.2, desc="Loading DeepSeek model...")
        
        # Import necessary libraries
        from vllm import SamplingParams
        
        # Initialize model if not already loaded
        if not deepseek_model_loaded:
            model = load_deepseek_model()
            if model is None:
                raise Exception("Failed to load DeepSeek model")
        
        if progress:
            progress(0.6, desc="Configuring inference parameters...")
        
        # Configure sampling parameters
        sampling_params = SamplingParams(
            temperature=0.53,
            top_p=0.93,
            top_k=30,
            max_tokens=8500,
            frequency_penalty=0.2,
        )
        
        if progress:
            progress(0.7, desc="Running analysis (may take a while)...")
        
        # Prepare analysis prompt
        prompt = f"""
Video Manipulation Strategies Analysis System
SYSTEM INSTRUCTIONS
You are a specialized system designed to analyze video content extractions and identify potential persuasion, manipulation, and influence strategies employed in the video. Your purpose is to objectively identify and explain these strategies without making any political judgments.

ANALYSIS METHODOLOGY
For each video extraction report, proceed through these analytical phases:
1. Narrative Structure Analysis: Identify how the story is constructed
2. Visual and Production Technique Analysis: Examine camera work, editing, lighting, etc.
3. Emotional Appeal Analysis: Identify emotional triggers and psychological techniques
4. Rhetorical Strategy Analysis: Identify persuasion and argument techniques
5. Information Presentation Analysis: Examine how facts, evidence, and claims are presented

OUTPUT FORMAT
Structure your analysis in this format:
## VIDEO MANIPULATION STRATEGIES ANALYSIS REPORT

### Executive Summary
[Brief overview of key findings and significant manipulation strategies detected]

### Narrative Structure
[Analysis of storytelling approach, framing techniques, perspective control]

### Visual and Production Techniques
[Analysis of camera angles, editing choices, visual symbolism, color psychology]

### Emotional Appeal Strategies
[Analysis of emotional triggers, psychological techniques, identity appeals]

### Rhetorical and Linguistic Strategies
[Analysis of language patterns, argument structures, rhetorical devices]

### Information Management Techniques
[Analysis of evidence presentation, information selection/omission, source handling]

### Audience Targeting
[Analysis of how content targets specific audiences or demographics]

### Manipulation Risk Assessment
[Assessment of overall manipulation potential and ethical considerations]

PRINCIPLES FOR ANALYSIS
1. Maintain political neutrality - Focus on techniques, not ideological positions
2. Distinguish between persuasion and manipulation
3. Consider context and audience expectations
4. Document evidence for each identified strategy
5. Acknowledge normal vs. problematic uses of influence techniques

Here is the video extraction text: "{extraction_text}"
ANALYSIS START:
"""
        
        # Generate analysis
        outputs = model.generate([prompt], sampling_params)
        analysis = outputs[0].outputs[0].text.strip()
        
        if progress:
            progress(1.0, desc="Analysis completed!")
        
        return analysis
        
    except Exception as e:
        error_msg = f"Error in analysis phase: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return error_msg