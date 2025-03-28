from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class ApiKeyLevel(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class UsageLimit(BaseModel):
    """Usage limits for different API levels"""
    daily_requests: int = Field(..., description="Maximum number of requests per day")
    monthly_requests: int = Field(..., description="Maximum number of requests per month")
    max_tokens_per_request: int = Field(..., description="Maximum number of tokens per request")
    max_text_length: int = Field(..., description="Maximum text length in characters")
    batch_processing: bool = Field(..., description="Access to batch processing")
    max_concurrent_requests: int = Field(..., description="Maximum number of concurrent requests")
    advanced_models: bool = Field(..., description="Access to advanced models")

# Define User before UserInDB
class User(BaseModel):
    """Model for users"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique user ID")
    username: str = Field(..., description="Username")
    email: EmailStr = Field(..., description="User email")
    hashed_password: str = Field(..., description="Hashed password")
    full_name: Optional[str] = Field(None, description="Full name")
    disabled: bool = Field(default=False, description="Whether the account is disabled")
    roles: List[str] = Field(default_factory=lambda: ["user"], description="User roles")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation date")
    subscription: ApiKeyLevel = Field(default=ApiKeyLevel.FREE, description="Subscription level")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserCreate(BaseModel):
    """Model for user creation"""
    username: str = Field(..., description="Username", min_length=3, max_length=50)
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="Password", min_length=8)
    full_name: Optional[str] = Field(None, description="Full name")
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v

# Now UserInDB can inherit from User
class UserInDB(User):
    """User model for database with hashed password."""
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False  
    subscription_level: str = "free"
    last_login: Optional[datetime] = None
    stripe_customer_id: Optional[str] = None
    
class ApiKey(BaseModel):
    """Model for API keys"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique API key ID")
    key: str = Field(..., description="API key (hashed in the database)")
    name: str = Field(..., description="Descriptive name for the key")
    user_id: str = Field(..., description="ID of the user who owns the key")
    level: ApiKeyLevel = Field(default=ApiKeyLevel.FREE, description="Access level")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation date")
    last_used_at: Optional[datetime] = Field(None, description="Last used date")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    is_active: bool = Field(default=True, description="Whether the key is active")
    usage: Dict[str, int] = Field(default_factory=dict, description="Usage statistics")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TokenData(BaseModel):
    """Data contained in the JWT token"""
    sub: str = Field(..., description="User ID")
    name: Optional[str] = Field(None, description="User name")
    email: Optional[str] = Field(None, description="User email")
    roles: List[str] = Field(default_factory=list, description="User roles")
    api_level: ApiKeyLevel = Field(default=ApiKeyLevel.FREE, description="API level")
    exp: Optional[int] = Field(None, description="Token expiration (timestamp)")

class UserResponse(BaseModel):
    """Model for user response (without sensitive data)"""
    id: str
    username: str
    email: EmailStr
    full_name: Optional[str]
    roles: List[str]
    created_at: datetime
    subscription: ApiKeyLevel
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Token(BaseModel):
    """Model for authentication token"""
    access_token: str
    token_type: str = "bearer"
    expires_at: int
    user: UserResponse

class ApiKeyCreate(BaseModel):
    """Model for API key creation"""
    name: str = Field(..., description="Descriptive name for the key", min_length=3, max_length=50)
    level: Optional[ApiKeyLevel] = Field(None, description="Access level (admin only)")
    expires_at: Optional[datetime] = Field(None, description="Expiration date (optional)")

class ApiKeyResponse(BaseModel):
    """Model for API key response"""
    id: str
    key: str
    name: str
    level: ApiKeyLevel
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UsageRecord(BaseModel):
    """Model for usage recording"""
    user_id: str
    api_key_id: str
    request_path: str
    request_method: str
    tokens_input: int = 0
    tokens_output: int = 0
    processing_time: float
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }