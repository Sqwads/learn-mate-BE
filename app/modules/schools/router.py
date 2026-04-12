from fastapi import APIRouter, Depends, HTTPException
from app.db.supabase import supabase
from app.schemas.schools import SchoolCreate, SchoolResponse, SchoolDelete
from app.core.dependencies import require_admin
from app.core.security import get_current_user
from uuid import uuid4
from datetime import datetime

router = APIRouter(tags=["Schools"])

@router.post("/", response_model=SchoolResponse)
def create_school(
    school: SchoolCreate,
    user: dict = Depends(require_admin)
):
    """
    Register a new school. Only admins can create schools.
    """
    try:
        # Check if school name already exists
        existing = supabase.table("schools").select("id").eq("school_name", school.school_name).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="School name already exists")

        # Verify admin_user_id exists and is an admin
        admin_profile = supabase.table("profiles").select("id, role").eq("id", str(school.admin_user_id)).execute()
        if not admin_profile.data:
            raise HTTPException(status_code=400, detail="Admin user not found")
        if admin_profile.data[0]["role"] != "admin":
            raise HTTPException(status_code=400, detail="Specified user is not an admin")

        school_id = str(uuid4())
        school_data = {
            "id": school_id,
            "school_name": school.school_name,
            "admin_id": str(school.admin_user_id),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        # Insert school
        result = supabase.table("schools").insert(school_data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create school")
        
        # Update the admin's profile with the school_id
        profile_update = supabase.table("profiles").update({
            "school_id": school_id
        }).eq("id", str(school.admin_user_id)).execute()
        
        if not profile_update.data:
            raise HTTPException(status_code=500, detail="Failed to assign admin to school")
        
        # CRITICAL FIX: Verify the update was successful by re-querying
        verify = supabase.table("profiles").select("id, school_id").eq("id", str(school.admin_user_id)).execute()
        if not verify.data or verify.data[0].get("school_id") != school_id:
            raise HTTPException(status_code=500, detail="School assignment verification failed")
        
        # ADDITIONAL FIX: Update auth user metadata to sync JWT
        try:
            supabase.auth.admin.update_user_by_id(
                str(school.admin_user_id),
                {
                    "user_metadata": {
                        "school_id": school_id
                    }
                }
            )
        except Exception as auth_error:
            print(f"Warning: Failed to update auth metadata: {auth_error}")
            # Don't fail the request, but log the warning

        return SchoolResponse(**result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        print(f"Create school error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/admin/schools", response_model=list[SchoolResponse])
def get_all_schools(user: dict = Depends(require_admin)):
    """
    Get all schools. Only admins can view all schools.
    """
    try:
        result = supabase.table("schools").select("*").execute()
        return [SchoolResponse(**school) for school in result.data]
    except Exception as e:
        print(f"Get schools error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/delete", status_code=204)
def delete_school(
    delete_data: SchoolDelete,
    user: dict = Depends(require_admin)
):
    """
    Delete a school and all associated users. Only admins can delete schools.
    Requires admin_id and school_id in request body.
    """
    try:
        # Verify the school exists
        school = supabase.table("schools").select("id, admin_id").eq("id", str(delete_data.school_id)).execute()
        if not school.data:
            raise HTTPException(status_code=404, detail="School not found")
        
        # Verify the admin_id matches the school's admin
        if school.data[0]["admin_id"] != str(delete_data.admin_id):
            raise HTTPException(
                status_code=403, 
                detail="Admin ID does not match the school's admin"
            )
        
        # Verify the requesting user is the admin
        if user["id"] != str(delete_data.admin_id):
            raise HTTPException(
                status_code=403, 
                detail="You can only delete schools where you are the admin"
            )
        
        # Delete all users associated with the school
        supabase.table("profiles").delete().eq("school_id", str(delete_data.school_id)).execute()
        
        # Delete the school
        supabase.table("schools").delete().eq("id", str(delete_data.school_id)).execute()
        
        return None  # 204 No Content
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete school error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")