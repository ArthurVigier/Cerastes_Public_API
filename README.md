Cerastes API: Documentation and Deployment Guide
Table of Contents
Overview
Project Structure
API Endpoints
Integrated AI Models
Deployment Guide
Troubleshooting
Contribution
License
Advanced Features
Overview
Cerastes API is an AI-based video and audio analysis platform, offering advanced processing capabilities for videos, including:

Audio transcription (monologue and multi-speaker)
Manipulation strategy analysis
Non-verbal behavior analysis
Batch processing for large content volumes
This API is designed to be highly configurable, scalable, and usable in various environments (development, production, cloud).

Project Structure
Cerastes_Public_API/
├── api/                  # All FastAPI routers
│   ├── __init__.py       # Routers entry point
│   ├── auth_router.py    # Authentication and API keys management
│   ├── error_handlers.py # Error handlers
│   ├── health_router.py  # Monitoring endpoint
│   ├── inference_router.py # Generic inference endpoint
│   ├── response_models.py  # Pydantic response models
│   ├── subscription_router.py # Subscription management
│   ├── task_router.py       # Tasks and status management
│   ├── transcription_router.py # Transcription endpoints
│   └── video_router.py      # Video analysis endpoints
├── db/                   # Database management
│   ├── __init__.py       # SQLAlchemy configuration
│   ├── init_db.py        # Database initialization
│   ├── migrations/       # Alembic migrations
│   └── models.py         # SQLAlchemy models
├── transcription_models/ # Transcription processing logic
├── video_models/         # Video processing logic
├── prompts/              # System prompts in text format
├── inference_results/    # Inference results storage
├── results/              # General results
├── uploads/              # Temporary storage for uploaded files
├── tests/                # Automated tests
├── auth.py               # Authentication functions
├── auth_models.py        # Authentication models
├── config.py             # Centralized configuration
├── database.py           # Database interface
├── inference_engine.py   # Centralized inference engine
├── main.py               # Main entry point
├── middleware.py         # FastAPI middleware
├── model_manager.py      # AI model manager
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker services composition
├── requirements.txt      # Python dependencies
└── startup.sh            # Startup script

API Endpoints
Authentication

POST /auth/register            # Register a new user
POST /auth/login               # Login and token generation
GET  /auth/me                  # Current user information
POST /auth/api-keys            # Create a new API key
GET  /auth/api-keys            # List user's API keys
PUT  /auth/api-keys/{id}/activate   # Activate an API key
PUT  /auth/api-keys/{id}/deactivate # Deactivate an API key
DELETE /auth/api-keys/{id}     # Delete an API key

Transcription

POST /transcription/monologue     # Start monologue transcription
POST /transcription/multispeaker  # Start multi-speaker transcription
GET  /transcription/tasks/{id}    # Transcription task status
GET  /transcription/tasks         # List transcription tasks

Video Analysis
POST /video/manipulation-analysis  # Start manipulation strategies analysis
POST /video/nonverbal-analysis     # Start non-verbal behavior analysis
GET  /video/tasks/{id}             # Video analysis task status
GET  /video/tasks                  # List video analysis tasks

Generic Inference
POST /inference/start              # Start generic inference
POST /inference/batch              # Start batch inference
GET  /inference/tasks/{id}         # Inference task status
GET  /inference/tasks              # List inference tasks

Tasks
GET  /tasks                       # List all tasks
GET  /tasks/{id}                  # Specific task details
DELETE /tasks/{id}                # Delete a task

Subscriptions
GET  /subscriptions/plans         # List subscription plans
POST /subscriptions/checkout      # Create payment session
POST /subscriptions/webhook       # Webhook for Stripe events
GET  /subscriptions/success       # Redirect after successful payment
GET  /subscriptions/cancel        # Redirect after cancellation

Monitoring
GET  /health                      # API health status
GET  /metrics                     # Prometheus metrics (if enabled)

Integrated AI Models

Audio Transcription: Whisper (tiny, base, small, medium, large)
Diarization: PyAnnote Speaker Diarization
LLM: DeepSeek, Llama2, and other VLLM-compatible models
Vision: InternVideo for video analysis
Segmentation: Sentence Transformers for intelligent text splitting
Deployment Guide

Prerequisites

Docker and Docker Compose
GPU with CUDA (recommended for performance)
At least 16GB RAM (32GB recommended)
PostgreSQL 14+ (for persistent storage)
Configured environment variables

Deployment with Docker
Clone the repository

git clone https://github.com/your-repo/Cerastes_Public_API.git
cd Cerastes_Public_API

Create an .env file

cp .env.example .env
# Edit the .env file with your configurations

Minimum required configuration in .env

# Database
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=mongo  # service name in docker-compose
DB_NAME=cerastes

# Security
SECRET_KEY=your_complex_secret_key

# External API
HUGGINGFACE_TOKEN=your_huggingface_token

# Stripe options (optional)
STRIPE_API_KEY=your_stripe_key
STRIPE_WEBHOOK_SECRET=your_webhook_secret


Launch with Docker Compose

docker-compose up -d

Initialize the database (first run only)

docker-compose exec api python -m db.init_db

Configuration Parameters
All parameters are configurable via the config.py file and can be overridden by environment variables. The main sections include:

app: General application configuration
database: Database configuration
models: AI models configuration
video: Video processing parameters
audio: Audio processing parameters
segmentation: Text segmentation configuration
inference: Inference parameters
api: API configuration
auth: Authentication configuration
services: External services configuration
Scaling
For high-load environments, you can:

Increase the number of workers

# In .env
API_WORKERS=4

Use a load balancer like Nginx or Traefik in production

Use Tensor Parallelism for large models

# In .env
TENSOR_PARALLEL_SIZE=2  # Use 2 GPUs for a single model

Monitoring and Logs
Logs are stored in the logs/ folder
Prometheus metrics are available at /metrics if enabled
Health status can be monitored via /health
Troubleshooting
Common Issues
Database connection error
Check connection parameters in .env
Verify that PostgreSQL is running
Check logs with docker-compose logs postgres
CUDA out of memory error
Reduce GPU_MEMORY_UTILIZATION (e.g., to 0.8)
Use a smaller model
Increase available GPU memory
Slow API
Check system resources (CPU, RAM, GPU)
Increase MAX_CONCURRENT_TASKS if resources allow
Check segmentation of large texts
Authentication errors
Verify that SECRET_KEY is properly set
Check JWT token validity
Verify user permissions
For more assistance, consult the detailed logs in the logs/ folder or submit a ticket on the GitHub repository.

Contribution
Contributions are welcome! Please follow these steps:

Fork the repository
Create a feature branch (git checkout -b feature/my-feature)
Add your changes (git commit -am 'Add my feature')
Push to the branch (git push origin feature/my-feature)
Create a Pull Request
License
Dual License Model
This project uses a dual license model:

Main License (GPL v2)
The majority of source code and system prompts are distributed under the GNU General Public License version 2 (GPL v2).
This license allows use, modification, and distribution of the source code, provided that all modifications and derivative code are also distributed under GPL v2.
Video Manipulation Analysis Component (AGPL v3)
The videomanipulation_analyzer module is distributed under the GNU Affero General Public License version 3 (AGPL v3).
In addition to GPL requirements, AGPL requires that the complete source code be made available to users who interact with the software via a network.
Commercial Licenses
Commercial licenses are available for organizations that wish to use Cerastes API without the restrictions of GPL/AGPL licenses:

Standard Commercial License: Allows use of the software without the obligation to share the source code of modifications.
Extended Commercial License: Includes commercial usage rights for the video manipulation analysis module and dedicated technical support.

Note on AI Models Usage
Third-party AI models integrated into this platform (such as Whisper, InternVideo, etc.) are subject to their own licenses. Please consult the respective licenses before any commercial use.

Advanced Features
JSONSimplifier Post-processor
The JSONSimplifier is a post-processor that automatically converts complex JSON results into clear, easy-to-understand textual explanations. It uses an LLM model to transform structured data into natural language.

Configuration
The JSONSimplifier can be configured via environment variables or options in the startup.sh script:

Usage
Enable the JSONSimplifier:

Via environment variables:

export JSON_SIMPLIFIER_ENABLED=true
export JSON_SIMPLIFIER_MODEL="huihui-ai/DeepSeek-R1-Distill-Qwen-14B-abliterated-v2"
export JSON_SIMPLIFIER_SYSTEM_PROMPT="Translate this JSON {text} into simple English"
export JSON_SIMPLIFIER_APPLY_TO="inference,video"

Or directly in command line:

JSON_SIMPLIFIER_ENABLED=true JSON_SIMPLIFIER_APPLY_TO="inference,video" ./startup.sh

Results
When the JSONSimplifier is enabled, API responses will include an additional plain_explanation field containing the natural language explanation of the JSON results.

Examples
Instead of receiving only structured JSON results like:

{
  "result": {
    "analysis": {
      "sentiment": "positive",
      "key_points": ["Point 1", "Point 2", "Point 3"],
      "complexity_score": 0.75
    }
  }
}

You will also receive a simplified explanation:

{
  "result": {
    "analysis": { ... },
  },
  "plain_explanation": "The text has a positive sentiment. It includes 3 key points and has a complexity score of 0.75."
}

This feature is particularly useful for end-user applications or for quick interpretation of analysis results.

Prompt Management System
The prompt management system provides a flexible way to use different types of prompts for your inference tasks. You can use predefined prompts or create custom ones with placeholders.

Available Prompts
The system includes several built-in prompts:

system_1: Basic analysis prompt
system_2: Jungian analysis prompt
system_3: Ethical analysis prompt
And others for specific use cases
Modular Design
Prompts are completely modular - you can use them individually or in sequence:

# Use a single prompt
inference_data = {
    "text": "Your text here",
    "prompt_name": "system_2"  # Use only system_2 prompt
}

# Use a sequence of prompts
inference_data = {
    "text": "Your text here",
    "prompt_sequence": ["system_1", "system_2", "system_final"]
}

Custom Placeholders
You can use custom placeholders in prompts and provide their values at inference time:

# Use custom placeholders
inference_data = {
    "text": "Your text here",
    "prompt_name": "system_3",
    "language": "english",
    "context": "Academic analysis"
}