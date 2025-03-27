import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Accès au fichier de configuration Alembic (.ini)
config = context.config

# Configuration des logs
fileConfig(config.config_file_name)

# Ajout du chemin parent pour importer vos modèles
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Importer la Base déclarative qui contient target_metadata
from db.models import Base  # Assurez-vous que ce chemin est correct
target_metadata = Base.metadata

def run_migrations_offline():
    """Exécute les migrations en mode 'offline'."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Exécute les migrations en mode 'online'."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
