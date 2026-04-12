from fastapi import Depends, HTTPException, status, Query
from app.core.security import get_current_user
from app.db.supabase import supabase
from typing import Dict
from uuid import UUID

def require_role(required_role: str):
    """
    Dependency to check if user has the required role.
    """
    def role_checker(user_id: str = Query(..., description="User ID for authentication")):
        user = get_current_user(user_id)
        if user.get("role") != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}"
            )
        return user
    return role_checker

def require_admin(user_id: str = Query(..., description="User ID for authentication")):
    """Require admin role"""
    user = get_current_user(user_id)
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required"
        )
    return user

def require_teacher(user_id: str = Query(..., description="User ID for authentication")):
    """Require teacher role"""
    user = get_current_user(user_id)
    if user.get("role") != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Teacher role required"
        )
    return user

def require_student(user_id: str = Query(..., description="User ID for authentication")):
    """Require student role"""
    user = get_current_user(user_id)
    if user.get("role") != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Student role required"
        )
    return user

def require_admin_or_teacher(user_id: str = Query(..., description="User ID for authentication")):
    """Require admin or teacher role"""
    user = get_current_user(user_id)
    if user.get("role") not in ["admin", "teacher"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Required role: admin or teacher"
        )
    return user

def require_admin_by_uuid(user_id: str = Query(..., description="User ID of the admin user")):
    """
    Dependency to verify admin role by user ID.
    Checks if the provided user ID corresponds to a user with admin role in the profiles table.
    """
    try:
        # Fetch user profile from profiles table using the provided user ID
        profile_response = supabase.table("profiles").select("id, role").eq("id", user_id).execute()

        if not profile_response.data or len(profile_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin user not found"
            )

        profile = profile_response.data[0]

        # Check if role is admin
        if profile.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Admin role required"
            )

        return profile

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Catch any other exceptions (network issues, Supabase errors, etc.)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify admin access"
        )

def require_teacher_by_uuid(user_id: str = Query(..., description="User ID of the teacher user")):
    """
    Dependency to verify teacher role by user ID.
    Checks if the provided user ID corresponds to a user with teacher role in the profiles table.
    """
    try:
        # Fetch user profile from profiles table using the provided user ID
        profile_response = supabase.table("profiles").select("id, role").eq("id", user_id).execute()

        if not profile_response.data or len(profile_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher user not found"
            )

        profile = profile_response.data[0]

        # Check if role is teacher
        if profile.get("role") != "teacher":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Teacher role required"
            )

        return profile

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Catch any other exceptions (network issues, Supabase errors, etc.)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify teacher access"
        )

def require_admin_or_teacher_by_uuid(user_id: str = Query(..., description="User ID of the admin or teacher user")):
    """
    Dependency to verify admin or teacher role by user ID.
    Checks if the provided user ID corresponds to a user with admin or teacher role in the profiles table.
    """
    try:
        # Fetch user profile from profiles table using the provided user ID
        profile_response = supabase.table("profiles").select("id, role").eq("id", user_id).execute()

        if not profile_response.data or len(profile_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not found"
            )

        profile = profile_response.data[0]

        # Check if role is admin or teacher
        if profile.get("role") not in ["admin", "teacher"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Admin or teacher role required"
            )

        return profile

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Catch any other exceptions (network issues, Supabase errors, etc.)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify admin/teacher access"
        )

def get_current_school_id(user_id: str = Query(..., description="User ID of the admin or teacher user")) -> UUID:
    """
    Dependency to get the current user's school_id from their profile.
    Raises 403 if user has no school_id assigned.
    
    This version expects user_id as a Query parameter.
    """
    try:
        # Fetch user's profile with school_id
        profile_response = supabase.table("profiles").select("id, school_id").eq("id", user_id).execute()

        if not profile_response.data or len(profile_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User profile not found"
            )

        profile = profile_response.data[0]
        school_id = profile.get("school_id")

        if not school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not assigned to a school"
            )

        return UUID(school_id)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify school access"
        )

def get_school_id_for_user(user_id: str) -> UUID:
    """
    Helper function to get school_id for a given user_id.
    Use this when user_id is already available (e.g., from path parameter).
    """
    try:
        # Fetch user's profile with school_id
        profile_response = supabase.table("profiles").select("id, school_id").eq("id", user_id).execute()

        if not profile_response.data or len(profile_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User profile not found"
            )

        profile = profile_response.data[0]
        school_id = profile.get("school_id")

        if not school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not assigned to a school"
            )

        return UUID(school_id)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify school access"
        )