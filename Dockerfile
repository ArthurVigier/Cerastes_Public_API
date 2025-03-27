FROM python:3.10-slim

WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copier le fichier requirements.txt
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier tous les fichiers Python individuels
COPY *.py ./
COPY startup.sh ./

# Copier les dossiers de la nouvelle structure
COPY api/ ./api/
COPY video_models/ ./video_models/
COPY transcription_models/ ./transcription_models/
COPY db/ ./db/
COPY prompts/ ./prompts/

# Créer les répertoires nécessaires
RUN mkdir -p uploads/video uploads/audio inference_results results logs

# Permission d'exécution pour le script de démarrage
RUN chmod +x startup.sh

# Exposer le port
EXPOSE 8000

# Commande de démarrage
CMD ["./startup.sh"]