"""Initial migration: Create tables for Users, ApiKeys, and UsageRecords

Revision ID: 0001_initial
Revises: 
Create Date: 2023-03-22 12:00:00.000000

"""
import uuid
from alembic import op
import sqlalchemy as sa

# Revision identifiers, utilisés par Alembic
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

# Définition de l'énumération pour les niveaux d'API
apikeylevel = sa.Enum('free', 'basic', 'premium', 'enterprise', name='apikeylevel')

def upgrade():
    # Création de l'énumération dans la base
    apikeylevel.create(op.get_bind())

    # Création de la table des utilisateurs
    op.create_table(
        'users',
        sa.Column('id', sa.String(), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('username', sa.String(50), nullable=False, unique=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('disabled', sa.Boolean(), nullable=False, default=False),
        sa.Column('roles', sa.JSON(), nullable=True, default='["user"]'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('subscription', apikeylevel, nullable=False, server_default='free'),
    )

    # Création de la table des clés API
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('key', sa.String(), nullable=False, unique=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('level', apikeylevel, nullable=False, server_default='free'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('usage', sa.JSON(), nullable=True, default='{}'),
    )

    # Création de la table des enregistrements d'utilisation
    op.create_table(
        'usage_records',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('api_key_id', sa.String(), sa.ForeignKey('api_keys.id'), nullable=False),
        sa.Column('request_path', sa.String(), nullable=False),
        sa.Column('request_method', sa.String(), nullable=False),
        sa.Column('tokens_input', sa.Integer(), nullable=False, default=0),
        sa.Column('tokens_output', sa.Integer(), nullable=False, default=0),
        sa.Column('processing_time', sa.Float(), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('usage_records')
    op.drop_table('api_keys')
    op.drop_table('users')
    op.execute("DROP TYPE apikeylevel")
    # Supprime l'énumération si elle existe
    # op.execute("DROP TYPE IF EXISTS apikeylevel")
    # Note : L'énumération doit être supprimée après la suppression de toutes les tables qui l'utilisent
    # op.execute("DROP TYPE IF EXISTS apikeylevel")
#         "json_encoders": {
#             datetime: lambda v: v.isoformat()
#         }
#
#
# class UsageLimit(BaseModel):
#     """Modèle pour les limites d'utilisation"""
#     max_tokens_input: int
#     max_tokens_output: int
#     max_text_length: int
#     max_requests_per_day: int
#
#     max_tokens_per_request: int
#     daily_requests: int
#     monthly_requests: int
#     yearly_requests: int
#
#