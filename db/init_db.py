from db import engine, Base
from db.models import User, ApiKey, UsageRecord  # Importez ici tous vos modèles nécessaires

def init_db():
    """
    Crée toutes les tables dans la base de données.
    À exécuter lors de la configuration initiale ou après des modifications du schéma.
    """
    Base.metadata.create_all(bind=engine)
    print("Les tables ont été créées avec succès.")

if __name__ == "__main__":
    init_db()
    # Vous pouvez appeler init_db() ici si vous souhaitez
    # l'exécuter directement en tant que script.
    # Cependant, il est généralement préférable de l'appeler
    # depuis un autre module ou un script de migration.
    # Cela permet de garder le code organisé et de séparer
    # les responsabilités.
    