import os
from typing import Optional
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from db.models import User, ApiKey, UsageRecord
from config import load_config

# Load configuration and define connection URL
config = load_config()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/db_name")

# Creating the SQLAlchemy engine and local session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """
    FastAPI dependency to get a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Retrieves a user by username."""
    return db.query(User).filter(User.username == username).first()

def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Retrieves a user by ID."""
    return db.query(User).filter(User.id == user_id).first()

def get_api_key(db: Session, key: str) -> Optional[ApiKey]:
    """Retrieves information for an API key."""
    return db.query(ApiKey).filter(ApiKey.key == key).first()

def get_api_keys_for_user(db: Session, user_id: str):
    """Retrieves all API keys for a user."""
    return db.query(ApiKey).filter(ApiKey.user_id == user_id).all()

def create_user(db: Session, user: User) -> User:
    """Creates a new user in the database."""
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_api_key(db: Session, api_key: ApiKey) -> ApiKey:
    """Creates a new API key."""
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key

def update_api_key(db: Session, api_key: ApiKey) -> ApiKey:
    """Updates an existing API key."""
    db.merge(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key

def delete_api_key(db: Session, key: str) -> bool:
    """Deletes an API key."""
    api_key = get_api_key(db, key)
    if api_key:
        db.delete(api_key)
        db.commit()
        return True
    return False

def record_api_usage(db: Session, record: UsageRecord) -> None:
    """Records API usage."""
    db.add(record)
    db.commit()

def get_user_usage_stats(db: Session, user_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> dict:
    """
    Retrieves usage statistics for a user.
    If start_date and end_date are provided, filters records accordingly.
    """
    query = db.query(UsageRecord).filter(UsageRecord.user_id == user_id)
    if start_date:
        query = query.filter(UsageRecord.timestamp >= start_date)
    if end_date:
        query = query.filter(UsageRecord.timestamp <= end_date)
    records = query.all()
    
    total_requests = len(records)
    total_tokens_input = sum(record.tokens_input for record in records)
    total_tokens_output = sum(record.tokens_output for record in records)
    avg_processing_time = sum(record.processing_time for record in records) / total_requests if total_requests else 0

    daily_stats = {}
    for record in records:
        day = record.timestamp.strftime("%Y-%m-%d")
        if day not in daily_stats:
            daily_stats[day] = {
                "requests": 0,
                "tokens_input": 0,
                "tokens_output": 0,
                "processing_time": 0
            }
        daily_stats[day]["requests"] += 1
        daily_stats[day]["tokens_input"] += record.tokens_input
        daily_stats[day]["tokens_output"] += record.tokens_output
        daily_stats[day]["processing_time"] += record.processing_time

    return {
        "total_requests": total_requests,
        "total_tokens_input": total_tokens_input,
        "total_tokens_output": total_tokens_output,
        "avg_processing_time": avg_processing_time,
        "daily_stats": daily_stats
    }
def get_all_users(db: Session):
    """Retrieves all users."""
    return db.query(User).all()
def get_all_api_keys(db: Session):
    """Retrieves all API keys."""
    return db.query(ApiKey).all()
def get_all_usage_records(db: Session):
    """Retrieves all usage records."""
    return db.query(UsageRecord).all()
def delete_user(db: Session, user_id: str) -> bool:
    """Deletes a user."""
    user = get_user_by_id(db, user_id)
    if user:
        db.delete(user)
        db.commit()
        return True
    return False
def delete_all_api_keys(db: Session):
    """Deletes all API keys."""
    db.query(ApiKey).delete()
    db.commit()
def delete_all_users(db: Session):
    """Deletes all users."""
    db.query(User).delete()
    db.commit()
def delete_all_usage_records(db: Session):
    """Deletes all usage records."""
    db.query(UsageRecord).delete()
    db.commit()
def delete_all_data(db: Session):
    """Deletes all data from the database."""
    delete_all_api_keys(db)
    delete_all_users(db)
    delete_all_usage_records(db)
def delete_all_data_with_confirmation(db: Session, confirmation_code: str) -> bool:
    """Deletes all data from the database with a confirmation code."""
    if confirmation_code == config.confirmation_code:
        delete_all_data(db)
        return True
    return False
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Retrieves a user by email address."""
    return db.query(User).filter(User.email == email).first()
def get_api_key_by_id(db: Session, key_id: str) -> Optional[ApiKey]:
    """Retrieves an API key by ID."""
    return db.query(ApiKey).filter(ApiKey.id == key_id).first()
def get_usage_records_by_user(db: Session, user_id: str):
    """Retrieves usage records for a user."""
    return db.query(UsageRecord).filter(UsageRecord.user_id == user_id).all()
def get_usage_records_by_api_key(db: Session, api_key_id: str):
    """Retrieves usage records for an API key."""
    return db.query(UsageRecord).filter(UsageRecord.api_key_id == api_key_id).all()
def get_usage_records_by_date(db: Session, date: datetime):
    """Retrieves usage records by date."""
    return db.query(UsageRecord).filter(UsageRecord.timestamp >= date).all()
def get_usage_records_by_date_range(db: Session, start_date: datetime, end_date: datetime):
    """Retrieves usage records by date range."""
    return db.query(UsageRecord).filter(UsageRecord.timestamp >= start_date, UsageRecord.timestamp <= end_date).all()
def get_usage_records_by_api_key_and_date(db: Session, api_key_id: str, date: datetime):
    """Retrieves usage records for an API key by date."""
    return db.query(UsageRecord).filter(UsageRecord.api_key_id == api_key_id, UsageRecord.timestamp >= date).all()
def get_usage_records_by_api_key_and_date_range(db: Session, api_key_id: str, start_date: datetime, end_date: datetime):
    """Retrieves usage records for an API key by date range."""
    return db.query(UsageRecord).filter(UsageRecord.api_key_id == api_key_id, UsageRecord.timestamp >= start_date, UsageRecord.timestamp <= end_date).all()
def get_usage_records_by_user_and_date(db: Session, user_id: str, date: datetime):
    """Retrieves usage records for a user by date."""
    return db.query(UsageRecord).filter(UsageRecord.user_id == user_id, UsageRecord.timestamp >= date).all()
def get_usage_records_by_user_and_date_range(db: Session, user_id: str, start_date: datetime, end_date: datetime):
    """Retrieves usage records for a user by date range."""
    return db.query(UsageRecord).filter(UsageRecord.user_id == user_id, UsageRecord.timestamp >= start_date, UsageRecord.timestamp <= end_date).all()
def get_usage_records_by_api_key_and_user(db: Session, api_key_id: str, user_id: str):
    """Retrieves usage records for an API key by user."""
    return db.query(UsageRecord).filter(UsageRecord.api_key_id == api_key_id, UsageRecord.user_id == user_id).all()
def get_usage_records_by_api_key_and_user_and_date(db: Session, api_key_id: str, user_id: str, date: datetime):
    """Retrieves usage records for an API key by user and date."""
    return db.query(UsageRecord).filter(UsageRecord.api_key_id == api_key_id, UsageRecord.user_id == user_id, UsageRecord.timestamp >= date).all()
def get_usage_records_by_api_key_and_user_and_date_range(db: Session, api_key_id: str, user_id: str, start_date: datetime, end_date: datetime):
    """Retrieves usage records for an API key by user and date range."""
    return db.query(UsageRecord).filter(UsageRecord.api_key_id == api_key_id, UsageRecord.user_id == user_id, UsageRecord.timestamp >= start_date, UsageRecord.timestamp <= end_date).all()
def get_usage_records_by_user_and_api_key(db: Session, user_id: str, api_key_id: str):
    """Retrieves usage records for a user by API key."""
    return db.query(UsageRecord).filter(UsageRecord.user_id == user_id, UsageRecord.api_key_id == api_key_id).all()
def get_usage_records_by_user_and_api_key_and_date(db: Session, user_id: str, api_key_id: str, date: datetime):
    """Retrieves usage records for a user by API key and date."""
    return db.query(UsageRecord).filter(UsageRecord.user_id == user_id, UsageRecord.api_key_id == api_key_id, UsageRecord.timestamp >= date).all()