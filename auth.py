from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Union
import secrets
import time
import uuid
from pydantic import ValidationError

from auth_models import User, TokenData, ApiKey, ApiKeyLevel, UsageLimit
from database import get_user_by_username, get_user_by_id, get_api_key

# JWT Configuration
SECRET_KEY = "REPLACE_WITH_A_RANDOMLY_GENERATED_SECRET_KEY"  # Change in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Authentication configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Usage limits definition by level
USAGE_LIMITS = {
    ApiKeyLevel.FREE: UsageLimit(
        daily_requests=50,
        monthly_requests=500,
        max_tokens_per_request=4000,
        max_text_length=10000,
        batch_processing=False,
        max_concurrent_requests=1,
        advanced_models=False
    ),
    ApiKeyLevel.BASIC: UsageLimit(
        daily_requests=200,
        monthly_requests=3000,
        max_tokens_per_request=8000,
        max_text_length=50000,
        batch_processing=True,
        max_concurrent_requests=2,
        advanced_models=False
    ),
    ApiKeyLevel.PREMIUM: UsageLimit(
        daily_requests=1000,
        monthly_requests=15000,
        max_tokens_per_request=16000,
        max_text_length=200000,
        batch_processing=True,
        max_concurrent_requests=5,
        advanced_models=True
    ),
    ApiKeyLevel.ENTERPRISE: UsageLimit(
        daily_requests=5000,
        monthly_requests=100000,
        max_tokens_per_request=32000,
        max_text_length=500000,
        batch_processing=True,
        max_concurrent_requests=20,
        advanced_models=True
    )
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies if the password matches the hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generates a password hash."""
    return pwd_context.hash(password)

def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticates a user by username and password."""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def generate_api_key() -> str:
    """Generates a new API key."""
    return f"sk_{secrets.token_hex(32)}"

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Gets the current user from the JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(**payload)
    except (JWTError, ValidationError):
        raise credentials_exception
    
    user = get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    if user.disabled:
        raise HTTPException(status_code=400, detail="User disabled")
    return user

async def validate_api_key(api_key: str = Security(api_key_header)) -> ApiKey:
    """Validates an API key and returns the associated information."""
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "APIKey"},
        )
    
    api_key_info = get_api_key(api_key)
    if api_key_info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "APIKey"},
        )
    
    if not api_key_info.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key disabled",
        )
    
    if api_key_info.expires_at and api_key_info.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key expired",
        )
    
    # Update last used date
    api_key_info.last_used_at = datetime.utcnow()
    
    return api_key_info

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Checks that the current user is active."""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="User disabled")
    return current_user

def check_admin_role(current_user: User = Depends(get_current_active_user)) -> User:
    """Checks that the current user has the administrator role."""
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user

def get_usage_limits(api_level: ApiKeyLevel) -> UsageLimit:
    """Returns usage limits for a given API level."""
    return USAGE_LIMITS[api_level]

def check_usage_limits(api_key_info: ApiKey, text_length: int, token_count: int = 0) -> None:
    """Checks if a request complies with usage limits."""
    limits = get_usage_limits(api_key_info.level)
    
    # Check text length
    if text_length > limits.max_text_length:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Text length exceeded. Maximum: {limits.max_text_length} characters",
        )
    
    # Check token count
    if token_count > limits.max_tokens_per_request and token_count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Token count exceeded. Maximum: {limits.max_tokens_per_request} tokens",
        )
    
    # Check daily limits
    today = datetime.utcnow().strftime("%Y-%m-%d")
    daily_usage = api_key_info.usage.get(today, 0)
    if daily_usage >= limits.daily_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily limit reached. Maximum: {limits.daily_requests} requests per day",
        )
    
    # Check monthly limits
    current_month = datetime.utcnow().strftime("%Y-%m")
    monthly_usage = sum(count for date, count in api_key_info.usage.items() if date.startswith(current_month))
    if monthly_usage >= limits.monthly_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly limit reached. Maximum: {limits.monthly_requests} requests per month",
        )

def authorize_batch_processing(api_key_info: ApiKey) -> None:
    """Checks if the API key has access to batch processing."""
    limits = get_usage_limits(api_key_info.level)
    if not limits.batch_processing:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Batch processing is not available with your current plan",
        )

def authorize_advanced_models(api_key_info: ApiKey) -> None:
    """Checks if the API key has access to advanced models."""
    limits = get_usage_limits(api_key_info.level)
    if not limits.advanced_models:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advanced models are not available with your current plan",
        )

def record_usage(api_key_info: ApiKey) -> None:
    """Records the usage of a request for an API key."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if today in api_key_info.usage:
        api_key_info.usage[today] += 1
    else:
        api_key_info.usage[today] = 1