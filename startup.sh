#!/bin/bash

# Charger les variables d'environnement depuis le fichier .env
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Définition des valeurs par défaut
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-8000}
WORKERS=${WORKERS:-1}
LOG_LEVEL=${LOG_LEVEL:-"info"}
MODEL_NAME=${MODEL_NAME:-"huihui-ai/DeepSeek-R1-Distill-Qwen-14B-abliterated-v2"}
USE_GPU=${USE_GPU:-"true"}
MAX_MODEL_LEN=${MAX_MODEL_LEN:-8000}
PRELOAD_MODELS=${PRELOAD_MODELS:-"true"}
INIT_DB=${INIT_DB:-"false"}

# Valeurs par défaut pour JSONSimplifier
JSON_SIMPLIFIER_ENABLED=${JSON_SIMPLIFIER_ENABLED:-"false"}
JSON_SIMPLIFIER_MODEL=${JSON_SIMPLIFIER_MODEL:-"huihui-ai/DeepSeek-R1-Distill-Qwen-14B-abliterated-v2"}
JSON_SIMPLIFIER_SYSTEM_PROMPT=${JSON_SIMPLIFIER_SYSTEM_PROMPT:-"Translate this JSON {text} into simple English"}
JSON_SIMPLIFIER_APPLY_TO=${JSON_SIMPLIFIER_APPLY_TO:-"inference,video,transcription"}

# Fonction de gestion des erreurs
handle_error() {
  echo "ERREUR: $1"
  exit 1
}

# Vérifier les dépendances critiques
command -v python3 >/dev/null 2>&1 || handle_error "Python3 n'est pas installé"
command -v uvicorn >/dev/null 2>&1 || handle_error "Uvicorn n'est pas installé"

# Créer les répertoires nécessaires
mkdir -p inference_results
mkdir -p logs
mkdir -p uploads/video uploads/audio uploads/text
mkdir -p results/transcriptions
mkdir -p results/video_analysis
mkdir -p postprocessors

# Vérifier si la base de données doit être initialisée
if [ "$INIT_DB" = "true" ]; then
  echo "Initialisation de la base de données..."
  python -m db.init_db || handle_error "Échec de l'initialisation de la base de données"
fi

# Précharger les modèles si nécessaire
if [ "$PRELOAD_MODELS" = "true" ]; then
  echo "Préchargement des modèles..."
  python -c "from model_manager import ModelManager; ModelManager.initialize()" || echo "Avertissement: Échec du préchargement des modèles"
fi

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