from fastapi import APIRouter, HTTPException, Query, Depends
from app.db.supabase import supabase
from app.schemas.classes import (
    ClassCreate,
    ClassUpdate,
    ClassResponse,
    ClassStudentAdd,
    ClassStudentResponse,
)
from app.core.dependencies import (
    require_admin_by_uuid,
    require_teacher_by_uuid,
    require_admin_or_teacher_by_uuid,
    get_current_school_id,
    get_school_id_for_user,
)
from datetime import datetime
import uuid
from uuid import UUID

router = APIRouter(tags=["Classes"])


# -------------------------
# HELPER: ATTACH STUDENTS
# -------------------------
def attach_students_to_class(class_obj: dict) -> dict:
    enrollments = (
        supabase
        .table("class_students")
        .select("student_id")
        .eq("class_id", class_obj["id"])
        .execute()
    )

    student_ids = [row["student_id"] for row in enrollments.data]

    if not student_ids:
        class_obj["students"] = []
        return class_obj

    students = (
        supabase
        .table("profiles")
        .select("id, full_name, email")
        .in_("id", student_ids)
        .execute()
    )

    class_obj["students"] = students.data
    return class_obj


# -------------------------
# CREATE CLASS (ADMIN UID)
# -------------------------
@router.post("/", response_model=ClassResponse)
def create_class(
    class_data: ClassCreate,
    school_id: UUID = Depends(get_current_school_id),
):
    """
    Create a new class. Automatically scoped to current user's school.
    """
    class_dict = {
        "id": str(uuid.uuid4()),
        "name": class_data.name,
        "description": class_data.description,
        "teacher_id": class_data.teacher_id,
        "school_id": str(school_id),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    result = supabase.table("classes").insert(class_dict).execute()
    return ClassResponse(**result.data[0])


# -------------------------
# GET CLASSES (SCHOOL SCOPED)
# -------------------------
@router.get("/", response_model=list[dict])
def get_classes(
    school_id: UUID = Depends(get_current_school_id),
):
    """
    Get all classes for the current user's school.
    """
    result = supabase.table("classes").select("*").eq("school_id", str(school_id)).execute()
    return [attach_students_to_class(cls) for cls in result.data]


# -------------------------
# GET STUDENT'S ENROLLED CLASSES
# -------------------------
@router.get("/student", response_model=list[dict])
def get_student_classes(
    user_id: str = Query(..., description="User ID for authentication"),
    school_id: UUID = Depends(get_current_school_id),
):
    """
    Get all classes the authenticated student is enrolled in within the current user's school.
    """
    # Get all class enrollments for the student (user_id is the student_id)
    enrollments = (
        supabase
        .table("class_students")
        .select("class_id")
        .eq("student_id", user_id)
        .execute()
    )

    class_ids = [row["class_id"] for row in enrollments.data]

    if not class_ids:
        return []

    # Get all classes the student is enrolled in, filtered by school
    classes = (
        supabase
        .table("classes")
        .select("*")
        .in_("id", class_ids)
        .eq("school_id", str(school_id))
        .execute()
    )

    return [attach_students_to_class(cls) for cls in classes.data]


# -------------------------
# GET SINGLE CLASS
# -------------------------
@router.get("/{class_id}", response_model=dict)
def get_class(
    class_id: str,
    school_id: UUID = Depends(get_current_school_id),
):
    """
    Get a single class by ID, scoped to current user's school.
    """
    result = supabase.table("classes").select("*").eq("id", class_id).eq("school_id", str(school_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Class not found")

    return attach_students_to_class(result.data[0])


# -------------------------
# UPDATE CLASS
# -------------------------
@router.put("/{class_id}", response_model=ClassResponse)
def update_class(
    class_id: str,
    class_data: ClassUpdate,
    school_id: UUID = Depends(get_current_school_id),
):
    """
    Update a class, scoped to current user's school.
    """
    update_data = {"updated_at": datetime.utcnow().isoformat()}

    if class_data.name is not None:
        update_data["name"] = class_data.name
    if class_data.description is not None:
        update_data["description"] = class_data.description
    if class_data.teacher_id is not None:
        update_data["teacher_id"] = class_data.teacher_id

    result = (
        supabase
        .table("classes")
        .update(update_data)
        .eq("id", class_id)
        .eq("school_id", str(school_id))
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Class not found")

    return ClassResponse(**result.data[0])


# -------------------------
# DELETE CLASS
# -------------------------
@router.delete("/{class_id}")
def delete_class(
    class_id: str,
    school_id: UUID = Depends(get_current_school_id),
):
    """
    Delete a class, scoped to current user's school.
    """
    result = supabase.table("classes").delete().eq("id", class_id).eq("school_id", str(school_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Class not found")

    return {"message": "Class deleted successfully"}


# -------------------------
# ADD STUDENT TO CLASS
# -------------------------
@router.post("/{class_id}/students", response_model=ClassStudentResponse)
def add_student_to_class(
    class_id: str,
    student_data: ClassStudentAdd,
    school_id: UUID = Depends(get_current_school_id),
):
    """
    Add a student to a class, scoped to current user's school.
    """
    class_result = supabase.table("classes").select("*").eq("id", class_id).eq("school_id", str(school_id)).execute()
    if not class_result.data:
        raise HTTPException(status_code=404, detail="Class not found")

    existing = (
        supabase
        .table("class_students")
        .select("*")
        .eq("class_id", class_id)
        .eq("student_id", student_data.student_id)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=400, detail="Student already enrolled")

    enrollment_data = {
        "class_id": class_id,
        "student_id": student_data.student_id,
        "enrolled_at": datetime.utcnow().isoformat(),
    }

    result = supabase.table("class_students").insert(enrollment_data).execute()
    return ClassStudentResponse(**result.data[0])


# -------------------------
# REMOVE STUDENT FROM CLASS
# -------------------------
@router.delete("/{class_id}/students/{student_id}")
def remove_student_from_class(
    class_id: str,
    student_id: str,
    school_id: UUID = Depends(get_current_school_id),
):
    """
    Remove a student from a class, scoped to current user's school.
    """
    class_result = supabase.table("classes").select("*").eq("id", class_id).eq("school_id", str(school_id)).execute()
    if not class_result.data:
        raise HTTPException(status_code=404, detail="Class not found")

    result = (
        supabase
        .table("class_students")
        .delete()
        .eq("class_id", class_id)
        .eq("student_id", student_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    return {"message": "Student removed from class"}