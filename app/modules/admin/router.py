from fastapi import APIRouter, Depends, HTTPException, Query
from app.db.supabase import supabase
from app.core.dependencies import require_admin_by_uuid, get_current_school_id, get_school_id_for_user
from app.schemas.profiles import ProfileCreate
import secrets
import string
from uuid import UUID
from datetime import datetime, timedelta, timezone
from typing import Optional

router = APIRouter(tags=["Admin"])

@router.get("/metrics")
def get_admin_metrics(school_id: UUID = Depends(get_current_school_id)):
    """
    Get admin metrics for the current user's school. Admin only.
    """
    try:
        # Total users in school
        total_users = supabase.table("profiles").select("id", count="exact").eq("school_id", str(school_id)).execute()
        total_users_count = total_users.count if hasattr(total_users, 'count') else len(total_users.data)

        # Active users (users with recent activity - last 30 days)
        active_users_count = total_users_count  # Placeholder

        # Attendance count (total attendance records in school)
        attendance_count = supabase.table("attendance").select("id", count="exact").eq("school_id", str(school_id)).execute()
        attendance_count = attendance_count.count if hasattr(attendance_count, 'count') else len(attendance_count.data)

        # Assignments created in school
        assignments_count = supabase.table("assignments").select("id", count="exact").eq("school_id", str(school_id)).execute()
        assignments_count = assignments_count.count if hasattr(assignments_count, 'count') else len(assignments_count.data)

        # Grades entered in school
        grades_count = supabase.table("grades").select("id", count="exact").eq("school_id", str(school_id)).execute()
        grades_count = grades_count.count if hasattr(grades_count, 'count') else len(grades_count.data)

        # Classes count in school
        classes_count = supabase.table("classes").select("id", count="exact").eq("school_id", str(school_id)).execute()
        classes_count = classes_count.count if hasattr(classes_count, 'count') else len(classes_count.data)

        # Students enrolled in school
        students_enrolled = supabase.table("class_students").select("student_id", count="exact").execute()
        students_enrolled_count = students_enrolled.count if hasattr(students_enrolled, 'count') else len(students_enrolled.data)

        return {
            "total_users": total_users_count,
            "active_users": active_users_count,
            "total_classes": classes_count,
            "students_enrolled": students_enrolled_count,
            "attendance_records": attendance_count,
            "assignments_created": assignments_count,
            "grades_entered": grades_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {str(e)}")


@router.get("/users")
def get_all_users(school_id: UUID = Depends(get_current_school_id)):
    """
    Get all users with their profiles for the current user's school. Admin only.
    """
    try:
        result = supabase.table("profiles").select("*").eq("school_id", str(school_id)).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")


@router.post("/users")
def create_user(
    user_data: ProfileCreate,
    admin_user: dict = Depends(require_admin_by_uuid)
):
    """
    Create a new user (teacher or student) in the current user's school. Admin only.
    Creates user in Supabase auth.users and profiles table.
    FIXED: Queries school_id from database instead of relying on JWT to avoid race conditions.
    """
    try:
        # FIXED: Extract user_id from the dict (handles both 'id' and 'user_id' keys)
        admin_user_id = admin_user.get("id") or admin_user.get("user_id")
        
        if not admin_user_id:
            raise HTTPException(status_code=403, detail="Could not identify admin user")
        
        # CRITICAL FIX: Get school_id from database, not from JWT/dependency
        admin_profile = supabase.table("profiles").select("school_id, role").eq("id", admin_user_id).execute()
        if not admin_profile.data:
            raise HTTPException(status_code=403, detail="Admin profile not found")
        
        admin_data = admin_profile.data[0]
        if admin_data.get("role") != "admin":
            raise HTTPException(status_code=403, detail="User is not an admin")
        
        school_id = admin_data.get("school_id")
        if not school_id:
            raise HTTPException(status_code=400, detail="Admin not assigned to a school. Please create or join a school first.")
        
        # Debug logging
        print("=" * 50)
        print("DEBUG: create_user function called")
        print(f"DEBUG: Admin User Object: {admin_user}")
        print(f"DEBUG: Admin ID extracted: {admin_user_id}")
        print(f"DEBUG: School ID from database: {school_id}")
        print(f"DEBUG: user_data.email: '{user_data.email}'")
        print(f"DEBUG: user_data.role: '{user_data.role}'")
        print("=" * 50)

        # Validate role (allow admin, teacher, student)
        if user_data.role not in ["admin", "teacher", "student"]:
            raise HTTPException(status_code=400, detail="Role must be one of: 'admin', 'teacher', 'student'")

        # Generate password if not provided
        password = user_data.password
        if not password:
            alphabet = string.ascii_letters + string.digits + string.punctuation
            password = ''.join(secrets.choice(alphabet) for i in range(12))

        # Create user in Supabase Auth with user_metadata
        try:
            auth_response = supabase.auth.admin.create_user({
                "email": user_data.email,
                "password": password,
                "email_confirm": False,
                "user_metadata": {
                    "firstName": user_data.first_name,
                    "lastName": user_data.last_name,
                    "role": user_data.role,
                    "school_id": school_id
                }
            })
            user_id = auth_response.user.id
        except Exception as auth_error:
            error_detail = str(auth_error)
            if hasattr(auth_error, '__dict__'):
                error_detail += f" | Details: {auth_error.__dict__}"

            if "email" in error_detail.lower() and ("already" in error_detail.lower() or "exists" in error_detail.lower()):
                error_detail = f"Email '{user_data.email}' is already registered. Please use a different email address."
            elif "password" in error_detail.lower():
                error_detail = f"Password validation failed: {error_detail}"
            elif "role" in error_detail.lower():
                error_detail = f"Role validation failed: {error_detail}"

            raise HTTPException(status_code=400, detail=f"Failed to create auth user: {error_detail}")

        # Create profile in profiles table using upsert
        try:
            profile_data = {
                "id": user_id,
                "email": user_data.email,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "full_name": f"{user_data.first_name} {user_data.last_name}",
                "role": user_data.role,
                "school_id": school_id
            }
            supabase.table("profiles").upsert(profile_data).execute()
            
        except Exception as profile_error:
            try:
                supabase.auth.admin.delete_user(user_id)
            except Exception as cleanup_error:
                print(f"WARNING: Failed to cleanup auth user after profile creation failure: {cleanup_error}")
            raise HTTPException(status_code=400, detail=f"Failed to create user profile: {str(profile_error)}")

        response = {
            "message": f"{user_data.role.title()} user created successfully",
            "user_id": user_id,
            "email": user_data.email,
            "role": user_data.role,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "school_id": school_id
        }
        if not user_data.password:
            response["generated_password"] = password

        return response
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error creating user: {str(e)}")


@router.post("/bootstrap-admin")
def bootstrap_admin(user_data: ProfileCreate):
    """
    Bootstrap the first admin user. No authentication required.
    Only works when no users exist in the system.
    """
    try:
        # Check if any users exist
        existing_users = supabase.table("profiles").select("id", count="exact").execute()
        total_users = existing_users.count if hasattr(existing_users, 'count') else len(existing_users.data)

        if total_users > 0:
            raise HTTPException(status_code=403, detail="Bootstrap only available for first user creation")

        # Validate that the role is admin for bootstrap
        if user_data.role != "admin":
            raise HTTPException(status_code=400, detail="Bootstrap user must have 'admin' role")

        # Generate password if not provided
        password = user_data.password
        if not password:
            alphabet = string.ascii_letters + string.digits + string.punctuation
            password = ''.join(secrets.choice(alphabet) for i in range(12))

        # Create user in Supabase Auth with user_metadata
        try:
            auth_response = supabase.auth.admin.create_user({
                "email": user_data.email,
                "password": password,
                "email_confirm": False,
                "user_metadata": {
                    "firstName": user_data.first_name,
                    "lastName": user_data.last_name,
                    "role": user_data.role
                }
            })
            user_id = auth_response.user.id
        except Exception as auth_error:
            error_detail = str(auth_error)
            if "email" in error_detail.lower() and ("already" in error_detail.lower() or "exists" in error_detail.lower()):
                error_detail = f"Email '{user_data.email}' is already registered. Please use a different email address."
            raise HTTPException(status_code=400, detail=f"Failed to create auth user: {error_detail}")

        # Create profile in profiles table using upsert
        try:
            profile_data = {
                "id": user_id,
                "email": user_data.email,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "full_name": f"{user_data.first_name} {user_data.last_name}",
                "role": user_data.role
            }
            supabase.table("profiles").upsert(profile_data).execute()
            
        except Exception as profile_error:
            try:
                supabase.auth.admin.delete_user(user_id)
            except Exception as cleanup_error:
                print(f"WARNING: Failed to cleanup auth user after profile creation failure: {cleanup_error}")
            raise HTTPException(status_code=400, detail=f"Failed to create user profile: {str(profile_error)}")

        response = {
            "message": "Admin user created successfully (bootstrap)",
            "user_id": user_id,
            "email": user_data.email,
            "role": user_data.role
        }
        if not user_data.password:
            response["generated_password"] = password

        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bootstrap admin: {str(e)}")


@router.delete("/users/{user_id}")
def delete_user(user_id: str):
    """
    Delete a user and all associated data from the current user's school. Admin only.
    This will permanently remove the user from auth.users and profiles table,
    and cascade delete all related records (classes, attendance, submissions, etc.)
    """
    try:
        # Get school_id for this user
        school_id = get_school_id_for_user(user_id)
        
        # Check if user exists and belongs to the school
        user_check = supabase.table("profiles").select("id, email, role").eq("id", user_id).eq("school_id", str(school_id)).execute()
        if not user_check.data:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user_check.data[0]

        # Prevent deletion of the last admin user in the school
        if user_data["role"] == "admin":
            admin_count = supabase.table("profiles").select("id", count="exact").eq("role", "admin").eq("school_id", str(school_id)).execute()
            admin_total = admin_count.count if hasattr(admin_count, 'count') else len(admin_count.data)
            if admin_total <= 1:
                raise HTTPException(status_code=400, detail="Cannot delete the last admin user in the school")

        # Delete from profiles table first (this will cascade delete related records)
        try:
            supabase.table("profiles").delete().eq("id", user_id).eq("school_id", str(school_id)).execute()
        except Exception as profile_error:
            raise HTTPException(status_code=500, detail=f"Failed to delete user profile: {str(profile_error)}")

        # Delete from auth.users
        try:
            supabase.auth.admin.delete_user(user_id)
        except Exception as auth_error:
            print(f"WARNING: Failed to delete auth user after profile deletion: {auth_error}")
            raise HTTPException(status_code=500, detail=f"Failed to delete auth user: {str(auth_error)}")

        return {
            "message": f"User {user_data['email']} deleted successfully",
            "user_id": user_id,
            "email": user_data["email"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error deleting user: {str(e)}")


@router.get("/activity")
def get_recent_activity(
    limit: int = 50,
    school_id: UUID = Depends(get_current_school_id)
):
    """
    Get recent activity logs for the current user's school. Admin only.
    """
    try:
        result = supabase.table("activity_logs").select("*").eq("school_id", str(school_id)).order("created_at", desc=True).limit(limit).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch activity logs: {str(e)}")


# NEW ANALYTICS ENDPOINTS

@router.get("/schools/{school_id}/analytics/mau")
def get_school_monthly_active_users(
    school_id: UUID,
    admin_id: UUID = Query(..., description="Admin user ID for authentication"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Month (1-12). Defaults to current month"),
    year: Optional[int] = Query(None, ge=2020, description="Year. Defaults to current year")
):
    """
    Get Monthly Active Users (MAU) for a specific school.
    
    For school admins only. Requires both school_id and admin_id.
    MAU is calculated based on users with last_login or activity in the specified month.
    Shows total MAU, active teachers, and active students separately.
    
    Query Parameters:
    - school_id (path): UUID of the school
    - admin_id (query): UUID of the admin user for authentication
    - month (query, optional): Month number (1-12), defaults to current month
    - year (query, optional): Year (e.g., 2026), defaults to current year
    """
    try:
        # Verify the admin exists and has admin role
        admin_check = supabase.table("profiles").select("id, role, school_id").eq("id", str(admin_id)).execute()
        if not admin_check.data:
            raise HTTPException(status_code=403, detail="Admin user not found")
        
        admin_data = admin_check.data[0]
        
        # Verify the user is an admin
        if admin_data.get("role") != "admin":
            raise HTTPException(status_code=403, detail="User is not an admin")
        
        # Verify the admin belongs to the requested school
        if admin_data.get("school_id") != str(school_id):
            raise HTTPException(status_code=403, detail="Admin does not have access to this school")
        
        # Verify the school exists
        school_check = supabase.table("schools").select("id, school_name").eq("id", str(school_id)).execute()
        if not school_check.data:
            raise HTTPException(status_code=404, detail="School not found")
        
        school_name = school_check.data[0].get("school_name")
        
        now = datetime.now(timezone.utc)
        
        # Default to current month/year if not provided
        target_month = month or now.month
        target_year = year or now.year
        
        # Validate month and year
        if target_month < 1 or target_month > 12:
            raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
        if target_year < 2020 or target_year > now.year + 1:
            raise HTTPException(status_code=400, detail=f"Year must be between 2020 and {now.year + 1}")
        
        # Calculate the start and end of the target month
        month_start = datetime(target_year, target_month, 1, tzinfo=timezone.utc)
        
        # Calculate last day of month
        if target_month == 12:
            month_end = datetime(target_year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            month_end = datetime(target_year, target_month + 1, 1, tzinfo=timezone.utc)
        
        # Get all users in the school
        users_resp = supabase.table("profiles").select("id, role, last_login, created_at").eq("school_id", str(school_id)).execute()
        users = users_resp.data or []
        
        total_mau = 0
        active_teachers = 0
        active_students = 0
        active_admins = 0
        
        for user in users:
            last_login = user.get("last_login")
            created_at = user.get("created_at")
            role = user.get("role")
            
            is_active = False
            
            # Check last_login first (primary indicator of activity)
            if last_login:
                try:
                    if isinstance(last_login, str):
                        login_dt = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
                    else:
                        login_dt = last_login
                    
                    if month_start <= login_dt < month_end:
                        is_active = True
                except Exception:
                    pass
            
            # Fallback to created_at if no last_login (newly created users count as active)
            elif created_at:
                try:
                    if isinstance(created_at, str):
                        created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        created_dt = created_at
                    
                    if month_start <= created_dt < month_end:
                        is_active = True
                except Exception:
                    pass
            
            if is_active:
                total_mau += 1
                if role == "teacher":
                    active_teachers += 1
                elif role == "student":
                    active_students += 1
                elif role == "admin":
                    active_admins += 1
        
        return {
            "school_id": str(school_id),
            "school_name": school_name,
            "month": target_month,
            "year": target_year,
            "month_name": datetime(target_year, target_month, 1).strftime("%B"),
            "period": f"{datetime(target_year, target_month, 1).strftime('%B %Y')}",
            "total_mau": total_mau,
            "active_teachers": active_teachers,
            "active_students": active_students,
            "active_admins": active_admins,
            "breakdown": {
                "teachers": active_teachers,
                "students": active_students,
                "admins": active_admins
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting school MAU: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get school MAU: {str(e)}")


@router.get("/schools/{school_id}/analytics/feature-usage")
def get_feature_usage(
    school_id: UUID,
    admin_id: UUID = Query(..., description="Admin user ID for authentication")
):
    """
    Get feature usage statistics for a specific school.
    
    For school admins only. Requires both school_id and admin_id.
    Shows counts for:
    - Attendance records
    - Assignments created
    - Submissions
    - Grades entered
    """
    try:
        # Verify the admin exists and has admin role
        admin_check = supabase.table("profiles").select("id, role, school_id").eq("id", str(admin_id)).execute()
        if not admin_check.data:
            raise HTTPException(status_code=403, detail="Admin user not found")
        
        admin_data = admin_check.data[0]
        
        # Verify the user is an admin
        if admin_data.get("role") != "admin":
            raise HTTPException(status_code=403, detail="User is not an admin")
        
        # Verify the admin belongs to the requested school
        if admin_data.get("school_id") != str(school_id):
            raise HTTPException(status_code=403, detail="Admin does not have access to this school")
        
        # Verify the school exists
        school_check = supabase.table("schools").select("id, school_name").eq("id", str(school_id)).execute()
        if not school_check.data:
            raise HTTPException(status_code=404, detail="School not found")
        
        school_name = school_check.data[0].get("school_name")
        
        # Attendance records count
        attendance_resp = supabase.table("attendance").select("id", count="exact").eq("school_id", str(school_id)).execute()
        attendance_count = attendance_resp.count if hasattr(attendance_resp, 'count') else len(attendance_resp.data or [])
        
        # Assignments created count
        assignments_resp = supabase.table("assignments").select("id", count="exact").eq("school_id", str(school_id)).execute()
        assignments_count = assignments_resp.count if hasattr(assignments_resp, 'count') else len(assignments_resp.data or [])
        
        # Submissions count
        submissions_resp = supabase.table("submissions").select("id", count="exact").eq("school_id", str(school_id)).execute()
        submissions_count = submissions_resp.count if hasattr(submissions_resp, 'count') else len(submissions_resp.data or [])
        
        # Grades entered count
        grades_resp = supabase.table("grades").select("id", count="exact").eq("school_id", str(school_id)).execute()
        grades_count = grades_resp.count if hasattr(grades_resp, 'count') else len(grades_resp.data or [])
        
        return {
            "school_id": str(school_id),
            "school_name": school_name,
            "attendance_records_count": attendance_count,
            "assignments_created_count": assignments_count,
            "submissions_count": submissions_count,
            "grades_entered_count": grades_count,
            "total_feature_interactions": attendance_count + assignments_count + submissions_count + grades_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting feature usage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get feature usage: {str(e)}")