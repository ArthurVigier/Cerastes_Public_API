#!/bin/bash

# Script de démarrage pour l'API d'inférence multi-session
# Utilise les variables d'environnement ou les valeurs par défaut

# Définir les valeurs par défaut
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="8000"
DEFAULT_WORKERS="1"
DEFAULT_LOG_LEVEL="info"
DEFAULT_MODEL="huihui-ai/DeepSeek-R1-Distill-Qwen-14B-abliterated-v2"
DEFAULT_USE_GPU="false"
DEFAULT_MAX_MODEL_LEN="24272"

# Valeurs par défaut pour JSONSimplifier
DEFAULT_JSON_SIMPLIFIER_ENABLED="false"
DEFAULT_JSON_SIMPLIFIER_MODEL="huihui-ai/DeepSeek-R1-Distill-Qwen-14B-abliterated-v2"
DEFAULT_JSON_SIMPLIFIER_SYSTEM_PROMPT="Translate this json {text} in plain english"
DEFAULT_JSON_SIMPLIFIER_APPLY_TO="inference,video,transcription"

# Récupérer les valeurs des variables d'environnement ou utiliser les valeurs par défaut
HOST=${API_HOST:-$DEFAULT_HOST}
PORT=${API_PORT:-$DEFAULT_PORT}
WORKERS=${API_WORKERS:-$DEFAULT_WORKERS}
LOG_LEVEL=${LOG_LEVEL:-$DEFAULT_LOG_LEVEL}
MODEL_NAME=${MODEL_NAME:-$DEFAULT_MODEL}
USE_GPU=${USE_GPU:-$DEFAULT_USE_GPU}
MAX_MODEL_LEN=${MAX_MODEL_LEN:-$DEFAULT_MAX_MODEL_LEN}

# Récupérer les valeurs pour JSONSimplifier
JSON_SIMPLIFIER_ENABLED=${JSON_SIMPLIFIER_ENABLED:-$DEFAULT_JSON_SIMPLIFIER_ENABLED}
JSON_SIMPLIFIER_MODEL=${JSON_SIMPLIFIER_MODEL:-$DEFAULT_JSON_SIMPLIFIER_MODEL}
JSON_SIMPLIFIER_SYSTEM_PROMPT=${JSON_SIMPLIFIER_SYSTEM_PROMPT:-$DEFAULT_JSON_SIMPLIFIER_SYSTEM_PROMPT}
JSON_SIMPLIFIER_APPLY_TO=${JSON_SIMPLIFIER_APPLY_TO:-$DEFAULT_JSON_SIMPLIFIER_APPLY_TO}

# Exporter les variables d'environnement pour qu'elles soient disponibles pour l'application
export JSON_SIMPLIFIER_ENABLED
export JSON_SIMPLIFIER_MODEL
export JSON_SIMPLIFIER_SYSTEM_PROMPT
export JSON_SIMPLIFIER_APPLY_TO

# Créer les répertoires nécessaires
mkdir -p inference_results
mkdir -p logs
mkdir -p uploads/video uploads/audio uploads/text
mkdir -p results/transcriptions
mkdir -p results/video_analysis

echo "Démarrage de l'API d'inférence multi-session..."
echo "Hôte: $HOST"
echo "Port: $PORT"
echo "Workers: $WORKERS"
echo "Niveau de log: $LOG_LEVEL"
echo "Modèle: $MODEL_NAME"
echo "Utilisation du GPU: $USE_GPU"
echo "Longueur maximale du modèle: $MAX_MODEL_LEN"

# Afficher les informations sur JSONSimplifier
echo "Configuration du JSONSimplifier:"
echo "  Activé: $JSON_SIMPLIFIER_ENABLED"
if [ "$JSON_SIMPLIFIER_ENABLED" = "true" ]; then
    echo "  Modèle: $JSON_SIMPLIFIER_MODEL"
    echo "  Types de tâches: $JSON_SIMPLIFIER_APPLY_TO"
fi

# Vérifier si GPU utilisé et afficher les infos
if [ "$USE_GPU" = "true" ]; then
    echo "Vérification des GPU disponibles..."
    if command -v nvidia-smi &> /dev/null; then
        nvidia-smi
    else
        echo "nvidia-smi non disponible. Impossible de vérifier les GPU."
    fi
fi

# Démarrer l'API avec Uvicorn
exec uvicorn main:app --host $HOST --port $PORT --workers $WORKERS --log-level $LOG_LEVEL