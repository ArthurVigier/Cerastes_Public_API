"""
Router for authentication and user management
-------------------------------------------------------------
This module implements routes for authentication, registration
and API user management.
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, validator

# Import authentication models and utilities
from auth_models import User, UserCreate, UserInDB, Token, TokenData
from auth import (
    authenticate_user, 
    create_access_token, 
    get_current_user, 
    get_current_active_user,
    get_password_hash
)
from database import get_db_connection

# Standardized API response models
from .response_models import SuccessResponse, ErrorResponse

# Logging configuration
logger = logging.getLogger("api.auth")

# Create router
auth_router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Access forbidden"},
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Server error"}
    }
)

# Constants
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# OAuth2 Configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# Route-specific models
class RefreshTokenRequest(BaseModel):
    refresh_token: str

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def password_strength(cls, v):
        """Checks password strength"""
        if len(v) < 8:
            raise ValueError('Password must contain at least 8 characters')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v

class PasswordResetRequest(BaseModel):
    email: EmailStr

class UserResponse(BaseModel):
    """Model for user response data"""
    username: str
    email: EmailStr
    is_active: bool
    is_admin: bool
    created_at: datetime
    subscription_level: Optional[str] = None
    last_login: Optional[datetime] = None

# Authentication routes
@auth_router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db = Depends(get_db_connection)
):
    """Generates a JWT access token for authentication"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for user {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_access_token(
        data={"sub": user.username, "refresh": True}, 
        expires_delta=refresh_token_expires
    )
    
    # Update last login date
    db.users.update_one(
        {"username": user.username},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@auth_router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    db = Depends(get_db_connection)
):
    """Refreshes an access token using a refresh token"""
    try:
        # Verify refresh token
        payload = jwt.decode(
            request.refresh_token, 
            os.getenv("SECRET_KEY"), 
            algorithms=[os.getenv("ALGORITHM", "HS256")]
        )
        
        # Verify that it's a refresh token
        if not payload.get("refresh"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Verify that the user still exists
        user_data = db.users.find_one({"username": username})
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Create new access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username}, 
            expires_delta=access_token_expires
        )
        
        # Create new refresh token
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        new_refresh_token = create_access_token(
            data={"sub": username, "refresh": True}, 
            expires_delta=refresh_token_expires
        )
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

@auth_router.post("/register", response_model=UserResponse)
async def register_user(
    user_create: UserCreate,
    db = Depends(get_db_connection)
):
    """Creates a new user"""
    # Check if the user already exists
    existing_user = db.users.find_one({"username": user_create.username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already in use"
        )
        
    # Check if the email already exists
    existing_email = db.users.find_one({"email": user_create.email})
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already in use"
        )
        
    # Hash the password
    hashed_password = get_password_hash(user_create.password)
    
    # Create a new user
    new_user = UserInDB(
        username=user_create.username,
        email=user_create.email,
        hashed_password=hashed_password,
        is_active=True,
        is_admin=False,
        created_at=datetime.utcnow(),
        subscription_level="free"
    ).dict()
    
    # Insert the user into the database
    db.users.insert_one(new_user)
    
    # Return user information without the password
    user_response = UserResponse(
        username=new_user["username"],
        email=new_user["email"],
        is_active=new_user["is_active"],
        is_admin=new_user["is_admin"],
        created_at=new_user["created_at"],
        subscription_level=new_user["subscription_level"]
    )
    
    return user_response

@auth_router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves information about the currently logged in user"""
    return UserResponse(
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at,
        subscription_level=current_user.subscription_level,
        last_login=current_user.last_login
    )

@auth_router.post("/change-password", response_model=SuccessResponse)
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db_connection)
):
    """Changes the password of the connected user"""
    # Verify current password
    user_data = db.users.find_one({"username": current_user.username})
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    user_db = UserInDB(**user_data)
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    if not pwd_context.verify(request.current_password, user_db.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
        
    # Hash the new password
    hashed_password = get_password_hash(request.new_password)
    
    # Update the password
    db.users.update_one(
        {"username": current_user.username},
        {"$set": {"hashed_password": hashed_password}}
    )
    
    return SuccessResponse(
        success=True,
        message="Password changed successfully"
    )

@auth_router.post("/reset-password", response_model=SuccessResponse)
async def request_password_reset(
    request: PasswordResetRequest,
    db = Depends(get_db_connection)
):
    """Request password reset"""
    # Check if email exists
    user = db.users.find_one({"email": request.email})
    if not user:
        # For security reasons, don't indicate if the email exists or not
        return SuccessResponse(
            success=True,
            message="If the email exists, a reset link has been sent"
        )
        
    # TODO: Send an email with a reset link
    # In a real implementation, generate a unique token and send it by email
    
    return SuccessResponse(
        success=True,
        message="If the email exists, a reset link has been sent"
    )

# Administrative routes (restricted access)
@auth_router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db_connection)
):
    """Lists all users (reserved for administrators)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access reserved for administrators"
        )
        
    users = list(db.users.find())
    user_responses = []
    
    for user in users:
        user_responses.append(UserResponse(
            username=user["username"],
            email=user["email"],
            is_active=user["is_active"],
            is_admin=user["is_admin"],
            created_at=user["created_at"],
            subscription_level=user.get("subscription_level", "free"),
            last_login=user.get("last_login")
        ))
        
    return user_responses

@auth_router.delete("/users/{username}", response_model=SuccessResponse)
async def delete_user(
    username: str,
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db_connection)
):
    """Deletes a user (reserved for administrators)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access reserved for administrators"
        )
        
    # Prevent deletion of own account
    if username == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account"
        )
        
    # Check if user exists
    user = db.users.find_one({"username": username})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    # Delete the user
    db.users.delete_one({"username": username})
    
    return SuccessResponse(
        success=True,
        message=f"User {username} deleted successfully"
    )