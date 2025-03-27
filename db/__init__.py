import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Récupérer l'URL de la base de données depuis une variable d'environnement,
# avec une valeur par défaut pour le développement.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/your_db_name")

# Création de l'engine SQLAlchemy
engine = create_engine(DATABASE_URL)

# Configuration de la session locale
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base déclarative pour nos modèles
Base = declarative_base()

def get_db():
    """
    Fournit une session de base de données pour chaque requête FastAPI.
    Utilisé comme dépendance dans les routes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# Ajoutez ici d'autres fonctions pour interagir avec la base de données,
# comme la création, la mise à jour et la suppression d'utilisateurs, de clés API, etc.
# Vous pouvez également ajouter des fonctions pour récupérer des utilisateurs,
# des clés API, des enregistrements d'utilisation, etc.