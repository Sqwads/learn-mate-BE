from fastapi import APIRouter, Depends, HTTPException, Query
from app.db.supabase import supabase
from app.schemas.profiles import ProfileCreate, ProfileUpdate, ProfileResponse
from app.core.dependencies import require_admin, get_current_school_id, get_school_id_for_user
from app.core.security import get_current_user
from datetime import datetime
from uuid import UUID

router = APIRouter(tags=["Profiles"])

@router.get("/me", response_model=ProfileResponse)
def get_my_profile(user_id: str = Query(..., description="User ID for authentication")):
    """
    Get current user's profile.
    """
    try:
        user = get_current_user(user_id)
        result = supabase.table("profiles").select("*").eq("id", user_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        return ProfileResponse(**result.data[0])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/", response_model=ProfileResponse)
def create_profile(
    profile: ProfileCreate, 
    user_id: str = Query(..., description="User ID for authentication"),
    school_id: UUID = Depends(get_current_school_id)
):
    """
    Create profile on first login. Only the authenticated user can create their own profile.
    Profile is automatically assigned to the user's school.
    """
    try:
        # Validate user exists
        user = get_current_user(user_id)
        
        # Check if profile already exists
        existing = supabase.table("profiles").select("*").eq("id", user_id).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Profile already exists")

        profile_data = {
            "id": user_id,
            "email": profile.email,
            "first_name": profile.first_name,  # Changed from full_name
            "last_name": profile.last_name,    # Added
            "role": profile.role,
            "school_id": str(school_id),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        result = supabase.table("profiles").insert(profile_data).execute()
        return ProfileResponse(**result.data[0])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/me", response_model=ProfileResponse)
def update_my_profile(
    profile: ProfileUpdate, 
    user_id: str = Query(..., description="User ID for authentication")
):
    """
    Update current user's profile. School cannot be changed.
    """
    try:
        user = get_current_user(user_id)
        update_data = {"updated_at": datetime.utcnow().isoformat()}
        
        if profile.first_name is not None:  # Changed from full_name
            update_data["first_name"] = profile.first_name
        if profile.last_name is not None:   # Added
            update_data["last_name"] = profile.last_name
        if profile.role is not None:
            update_data["role"] = profile.role

        result = supabase.table("profiles").update(update_data).eq("id", user_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        return ProfileResponse(**result.data[0])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=list[ProfileResponse])
def get_all_profiles(
    school_id: UUID = Depends(get_current_school_id)
):
    """
    Get all profiles for the current user's school.
    """
    try:
        result = supabase.table("profiles").select("*").eq("school_id", str(school_id)).execute()
        return [ProfileResponse(**profile) for profile in result.data]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{user_id}", response_model=ProfileResponse)
def get_profile(
    user_id: str
):
    """
    Get specific profile by user ID, scoped to school.
    """
    try:
        # Get school_id for this user
        school_id = get_school_id_for_user(user_id)
        
        result = supabase.table("profiles")\
            .select("*")\
            .eq("id", user_id)\
            .eq("school_id", str(school_id))\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Profile not found in your school")
        
        return ProfileResponse(**result.data[0])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{user_id}")
def delete_profile(
    user_id: str
):
    """
    Delete a profile. Only works if the profile belongs to the same school.
    """
    try:
        # Get school_id for this user
        school_id = get_school_id_for_user(user_id)
        
        # Verify profile exists and belongs to school
        check = supabase.table("profiles")\
            .select("*")\
            .eq("id", user_id)\
            .eq("school_id", str(school_id))\
            .execute()
        
        if not check.data:
            raise HTTPException(status_code=404, detail="Profile not found in your school")
        
        result = supabase.table("profiles").delete().eq("id", user_id).execute()
        
        return {"message": "Profile deleted successfully", "deleted_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))