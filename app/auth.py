"""Authentication utilities: password hashing, JWT encoding/decoding, and user dependency."""
import bcrypt
from jose import jwt, JWTError
from fastapi import HTTPException, Header
from datetime import datetime, timedelta
from typing import Optional
from bson import ObjectId

from app.config import settings
from app.db import get_users_collection


def hash_password(plain: str) -> str:
    """
    Hash a plain-text password using bcrypt.
    
    Args:
        plain: Plain-text password
        
    Returns:
        Hashed password as string
    """
    # Encode password to bytes and hash with bcrypt
    password_bytes = plain.encode('utf-8')
    hashed_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    # Return as string for database storage
    return hashed_bytes.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain-text password against a hashed password.
    
    Args:
        plain: Plain-text password
        hashed: Hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    password_bytes = plain.encode('utf-8')
    hashed_bytes = hashed.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing token payload data
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    # Add issued at time
    iat = datetime.utcnow()
    to_encode["iat"] = iat
    
    # Add expiration time
    expire = iat + timedelta(days=settings.jwt_expiration_days)
    to_encode["exp"] = expire
    
    # Encode the token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT access token.
    
    Args:
        token: JWT token to decode
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user(authorization: str = Header(None)):
    """
    FastAPI dependency to extract and verify the current user from the Authorization header.
    
    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")
        
    Returns:
        User document from database
        
    Raises:
        HTTPException: If authorization fails
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extract Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = parts[1]
    
    # Decode token
    payload = decode_access_token(token)
    
    # Extract user_id from payload
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Fetch user from database
    users = get_users_collection()
    try:
        user = await users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid user ID",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user
