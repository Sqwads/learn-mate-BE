from fastapi import APIRouter, HTTPException, Depends, Query, Header
from app.db.supabase import supabase
from app.schemas.auth import UserResponse, UserIdRequest, LoginResponse
from app.core.security import get_current_user
from app.core.session_cache import create_session, get_user_id_for_token
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4
from datetime import datetime
import logging

# Setup logging
logger = logging.getLogger(__name__)

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str
    school_name: Optional[str] = None
    role: Optional[str] = None

router = APIRouter(tags=["Auth"])

@router.post("/signup", response_model=LoginResponse)
def signup(request: SignupRequest):
    """
    Register a new user account.
    
    Creates both authentication user and profile entry.
    Optionally creates a new school if school_name is provided.
    New users are automatically assigned admin role by default unless a different role is specified.
    
    Args:
    - email: User's email address
    - password: User's password
    - full_name: User's full name
    - school_name: Optional new school name to create
    - role: Optional role (defaults to 'admin' if not specified)
    
    Returns:
    - user_id: The new user's unique identifier
    - token: Session token for authentication
    """
    try:
        logger.info(f"=== SIGNUP REQUEST START ===")
        logger.info(f"Request data: email={request.email}, full_name={request.full_name}, role={request.role}, school_name={request.school_name}")
        
        # Check if user already exists in profiles by email
        existing_user = supabase.table('profiles').select("*").eq('email', request.email).execute()
        if existing_user.data:
            raise HTTPException(
                status_code=400,
                detail="An account with this email already exists. Please login instead."
            )

        # Create auth user in Supabase
        logger.info("Creating auth user...")
        auth_response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password
        })

        if not auth_response.user:
            raise HTTPException(
                status_code=400,
                detail="Signup failed. Please try again."
            )

        user_id = str(auth_response.user.id)
        logger.info(f"Auth user created with ID: {user_id}")

        # Check if profile already exists for this user_id (from previous failed attempt)
        existing_profile = supabase.table('profiles').select("*").eq('id', user_id).execute()
        
        if existing_profile.data:
            # Profile already exists, just log them in
            logger.info(f"Profile already exists for user {user_id}, logging in")
            token = create_session(user_id)
            return LoginResponse(user_id=user_id, token=token)

        # Handle school creation if school_name is provided
        final_school_id = None
        
        if request.school_name and request.school_name.strip():
            logger.info(f"School name provided: {request.school_name}")
            # Check if school name already exists
            existing_school = supabase.table("schools").select("id").eq("school_name", request.school_name.strip()).execute()
            
            if existing_school.data:
                logger.warning(f"School already exists: {request.school_name}")
                raise HTTPException(
                    status_code=400,
                    detail="School name already exists. Please use a different name."
                )
            
            # Create new school
            new_school_id = str(uuid4())
            school_data = {
                "id": new_school_id,
                "school_name": request.school_name.strip(),
                "admin_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            try:
                logger.info(f"Creating new school with data: {school_data}")
                school_result = supabase.table("schools").insert(school_data).execute()
                final_school_id = new_school_id
                logger.info(f"School created successfully: {school_result.data}")
            except Exception as school_error:
                logger.error(f"School creation error: {str(school_error)}")
                # Don't fail the entire signup if school creation fails
                # Just log and continue without school
                logger.warning("Continuing signup without school")
                final_school_id = None

        # Build profile data with ALL fields including role and full_name
        role_to_set = request.role if request.role and request.role.strip() else "admin"
        
        profile_data = {
            "id": user_id,
            "email": request.email,
            "full_name": request.full_name,
            "role": role_to_set,  # Include role in initial insert
            "last_login": datetime.utcnow().isoformat()  # Set initial last_login
        }
        
        # Add school_id if available
        if final_school_id:
            profile_data["school_id"] = final_school_id
            logger.info(f"Adding school_id to profile: {final_school_id}")

        try:
            logger.info(f"Creating profile with data: {profile_data}")
            profile_response = supabase.table('profiles').insert(profile_data).execute()
            logger.info(f"Profile created: {profile_response.data}")
            
        except Exception as profile_error:
            # Log the actual error for debugging
            logger.error(f"Profile creation error: {str(profile_error)}")
            logger.error(f"Profile data that failed: {profile_data}")
            raise HTTPException(
                status_code=400,
                detail=f"Profile creation failed: {str(profile_error)}"
            )

        # Create session token for immediate login
        token = create_session(user_id)
        
        logger.info(f"=== SIGNUP REQUEST COMPLETE ===")
        return LoginResponse(user_id=user_id, token=token)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=400,
            detail=f"Signup failed: {str(e)}"
        )

@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """
    Login with email and password to get user ID.
    Uses Supabase authentication.
    Updates last_login timestamp for analytics tracking.
    """
    try:
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })

        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        user_id = str(auth_response.user.id)
        
        # Update last_login timestamp
        try:
            supabase.table("profiles").update({
                "last_login": datetime.utcnow().isoformat()
            }).eq("id", user_id).execute()
            logger.info(f"Updated last_login for user {user_id}")
        except Exception as login_update_error:
            # Log the error but don't fail the login
            logger.warning(f"Failed to update last_login for user {user_id}: {str(login_update_error)}")
        
        # Create a short-lived server-side session token so the client can
        # authenticate subsequent requests without passing raw user ID every time.
        token = create_session(user_id)

        return LoginResponse(user_id=user_id, token=token)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Login failed. Please check your credentials."
        )

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(user_id: Optional[str] = Query(None, description="User ID for authentication"),
                             authorization: Optional[str] = Header(None, alias="Authorization")):
    """
    Get current authenticated user's profile information.

    Requires user_id as query parameter or Authorization header.
    Returns user data including:
    - user_id: User's unique identifier
    - email: User's email address
    - role: User's role (admin, teacher, student, superuser)
    - full_name: User's full name
    - school_id: Associated school ID (if any)
    - school_name: Associated school name (if any)
    """
    # If Authorization Bearer token provided, resolve user_id from cache
    uid = user_id
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        cached_uid = get_user_id_for_token(token)
        if cached_uid:
            uid = cached_uid

    if not uid:
        raise HTTPException(status_code=401, detail="User ID not provided")

    user = get_current_user(uid)
    
    # Map 'id' to 'user_id' to match UserResponse schema
    user_data = dict(user)
    if 'id' in user_data:
        user_data['user_id'] = user_data.pop('id')
    
    return UserResponse(**user_data)