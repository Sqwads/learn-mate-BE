import os
import logging
from fastapi import Depends, HTTPException, status, Query
from app.db.supabase import supabase
from app.core.config import settings
from uuid import UUID

logger = logging.getLogger(__name__)

def get_current_user(user_id: str = Query(..., description="User ID for authentication")):
    """
    Fetches user profile information by user ID.

    Args:
        user_id: User ID from query parameter

    Returns:
        dict: User profile data with id, email, role, full_name, school_id, and school_name

    Raises:
        HTTPException: 401 if user profile not found
    """
    try:
        # Validate UUID format
        try:
            UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID format"
            )

        # Fetch user profile from profiles table with school information
        profile_response = supabase.table("profiles").select(
            "id, full_name, email, role, school_id, schools(school_name)"
        ).eq("id", user_id).execute()

        # Check for errors returned by Supabase client
        if hasattr(profile_response, 'error') and profile_response.error:
            logger.error("Supabase error fetching profile: %s", profile_response.error)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Upstream error fetching profile"
            )

        if not profile_response.data or len(profile_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )

        profile = profile_response.data[0]

        # Ensure required fields are present
        if not profile.get("role"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User profile incomplete. Role information missing."
            )

        # Extract school name from the joined data
        school_name = None
        if profile.get("schools") and isinstance(profile["schools"], dict):
            school_name = profile["schools"].get("school_name")

        return {
            "id": profile["id"],
            "email": profile["email"],
            "role": profile["role"],
            "full_name": profile.get("full_name"),
            "school_id": profile.get("school_id"),
            "school_name": school_name
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception("Unexpected error in get_current_user")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error while fetching profile: {str(e)}"
        )