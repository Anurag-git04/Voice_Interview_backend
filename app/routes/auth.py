"""API routes for authentication."""
from fastapi import APIRouter, HTTPException, status, Depends, Request
from datetime import datetime
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
import logging

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.schemas import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
    ProfileResponse
)
from app.db import get_users_collection
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")  # Limit registration attempts
async def register(request: Request, req: RegisterRequest):
    """
    Register a new user.
    
    Creates a new user account with hashed password and returns a JWT token.
    """
    users = get_users_collection()
    
    # Check if user already exists
    existing_user = await users.find_one({"email": req.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash the password
    password_hash = hash_password(req.password)
    
    # Create user document
    user_doc = {
        "email": req.email,
        "password_hash": password_hash,
        "full_name": req.full_name,
        "created_at": datetime.utcnow()
    }
    
    # Insert user into database
    try:
        result = await users.insert_one(user_doc)
        user_id = str(result.inserted_id)
    except DuplicateKeyError:
        # Race condition: another request created the user between our check and insert
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    # Create JWT token
    token_data = {"sub": user_id}
    token = create_access_token(token_data)
    
    logger.info(f"User registered successfully: {req.email}")
    
    return RegisterResponse(
        user_id=user_id,
        email=req.email,
        full_name=req.full_name,
        token=token
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")  # Limit login attempts to prevent brute force
async def login(request: Request, req: LoginRequest):
    """
    Login with email and password.
    
    Verifies credentials and returns a JWT token.
    """
    users = get_users_collection()
    
    # Fetch user by email
    user = await users.find_one({"email": req.email})
    
    # Verify user exists and password is correct
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Create JWT token
    user_id = str(user["_id"])
    token_data = {"sub": user_id}
    token = create_access_token(token_data)
    
    logger.info(f"User logged in successfully: {req.email}")
    
    return LoginResponse(
        token=token,
        email=user["email"],
        full_name=user["full_name"]
    )


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(current_user: dict = Depends(get_current_user)):
    """
    Get current user profile.
    
    Requires valid JWT token in Authorization header.
    """
    return ProfileResponse(
        user_id=str(current_user["_id"]),
        email=current_user["email"],
        full_name=current_user["full_name"],
        created_at=current_user["created_at"]
    )
