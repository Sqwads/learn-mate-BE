from fastapi import APIRouter, Depends, HTTPException
from app.db.supabase import supabase
from app.schemas.grades import GradeCreate, GradeUpdate, GradeResponse
from app.core.dependencies import require_admin_or_teacher, get_current_school_id
from app.core.security import get_current_user
from datetime import datetime, timezone
from uuid import UUID

router = APIRouter(tags=["Grades"])

@router.post("/", response_model=GradeResponse)
def grade_submission(
    grade: GradeCreate,
    school_id: UUID = Depends(get_current_school_id),
    user: dict = Depends(get_current_user)  # Changed from require_admin_or_teacher
):
    """
    Grade a submission, scoped to school.
    - Admin or teacher can grade any submission
    - Students can only grade their own MCQ submissions (auto-grading)
    """
    try:
        # Get submission with assignment and class info, scoped to school
        submission_result = supabase.table("submissions").select("*, assignments(class_id, isMCQ, classes(teacher_id))").eq("id", str(grade.submission_id)).eq("school_id", str(school_id)).execute()
        if not submission_result.data:
            raise HTTPException(status_code=404, detail="Submission not found")

        submission = submission_result.data[0]
        teacher_id = submission["assignments"]["classes"]["teacher_id"]
        student_id = submission.get("student_id")
        is_mcq = submission["assignments"].get("isMCQ", False)

        # Permission check
        if user["role"] == "student":
            # Students can only grade their own MCQ submissions
            if student_id != user["id"]:
                raise HTTPException(status_code=403, detail="You can only grade your own submissions")
            if not is_mcq:
                raise HTTPException(status_code=403, detail="Students can only grade MCQ submissions")
        elif user["role"] == "teacher":
            # Teachers can only grade submissions for their classes
            if teacher_id != user["id"]:
                raise HTTPException(status_code=403, detail="Access denied")
        # Admins can grade any submission (no additional check needed)

        # Check if grade already exists
        existing = supabase.table("grades").select("*").eq("submission_id", str(grade.submission_id)).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Grade already exists for this submission")

        grade_data = {
            "submission_id": str(grade.submission_id),
            "grade": grade.grade,
            "feedback": grade.feedback,
            "graded_by": user["id"],
            "school_id": str(school_id),
            "graded_at": datetime.now(timezone.utc).isoformat()
        }

        result = supabase.table("grades").insert(grade_data).execute()
        return GradeResponse(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Grade submission error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/submission/{submission_id}", response_model=GradeResponse)
def get_submission_grade(
    submission_id: str,
    school_id: UUID = Depends(get_current_school_id),
    user: dict = Depends(get_current_user)
):
    """
    Get grade for a submission, scoped to school. Student can view their own grades, teachers can view grades they gave.
    """
    try:
        # Get grade with submission and assignment info, scoped to school
        result = supabase.table("grades").select("*, submissions(student_id, assignments(class_id, classes(teacher_id)))").eq("submission_id", submission_id).eq("school_id", str(school_id)).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Grade not found")

        grade = result.data[0]
        student_id = grade["submissions"]["student_id"]
        teacher_id = grade["submissions"]["assignments"]["classes"]["teacher_id"]

        # Check permissions
        if user["role"] == "student" and student_id != user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        elif user["role"] == "teacher" and teacher_id != user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Remove nested data before returning
        grade.pop("submissions", None)
        return GradeResponse(**grade)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get submission grade error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/my", response_model=list[GradeResponse])
def get_my_grades(
    school_id: UUID = Depends(get_current_school_id),
    user: dict = Depends(get_current_user)
):
    """
    Get current user's grades, scoped to school. Only for students.
    """
    try:
        if user["role"] != "student":
            raise HTTPException(status_code=403, detail="Only students can view their grades")

        # First, get all submissions by this student
        submissions = supabase.table("submissions").select("id").eq("student_id", user["id"]).eq("school_id", str(school_id)).execute()
        
        if not submissions.data:
            # No submissions yet, return empty array
            return []
        
        # Extract submission IDs
        submission_ids = [sub["id"] for sub in submissions.data]
        
        # Get all grades for these submissions
        result = supabase.table("grades").select("*").in_("submission_id", submission_ids).eq("school_id", str(school_id)).execute()
        
        return [GradeResponse(**grade) for grade in result.data]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get my grades error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/assignment/{assignment_id}", response_model=list[GradeResponse])
def get_assignment_grades(
    assignment_id: str,
    school_id: UUID = Depends(get_current_school_id),
    user: dict = Depends(require_admin_or_teacher)
):
    """
    Get all grades for an assignment, scoped to school. Admin or teacher of the class.
    """
    try:
        # Get assignment with class info, scoped to school
        assignment_result = supabase.table("assignments").select("*, classes(teacher_id)").eq("id", assignment_id).eq("school_id", str(school_id)).execute()
        if not assignment_result.data:
            raise HTTPException(status_code=404, detail="Assignment not found")

        assignment = assignment_result.data[0]
        teacher_id = assignment["classes"]["teacher_id"]

        if user["role"] == "teacher" and teacher_id != user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # First, get all submissions for this assignment
        submissions = supabase.table("submissions").select("id").eq("assignment_id", assignment_id).eq("school_id", str(school_id)).execute()
        
        if not submissions.data:
            # No submissions yet, return empty array
            return []
        
        # Extract submission IDs
        submission_ids = [sub["id"] for sub in submissions.data]
        
        # Get all grades for these submissions
        result = supabase.table("grades").select("*").in_("submission_id", submission_ids).eq("school_id", str(school_id)).execute()
        
        return [GradeResponse(**grade) for grade in result.data]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get assignment grades error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{grade_id}", response_model=GradeResponse)
def update_grade(
    grade_id: str,
    grade: GradeUpdate,
    school_id: UUID = Depends(get_current_school_id),
    user: dict = Depends(require_admin_or_teacher)
):
    """
    Update grade, scoped to school. Admin or teacher who graded it.
    """
    try:
        # Get grade with submission and class info, scoped to school
        existing = supabase.table("grades").select("*, submissions(assignments(class_id, classes(teacher_id)))").eq("id", grade_id).eq("school_id", str(school_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Grade not found")

        record = existing.data[0]
        teacher_id = record["submissions"]["assignments"]["classes"]["teacher_id"]
        graded_by = record["graded_by"]

        if user["role"] == "teacher" and (teacher_id != user["id"] or graded_by != user["id"]):
            raise HTTPException(status_code=403, detail="Access denied")

        # Note: grade parameter is missing from function signature
        # This endpoint needs GradeUpdate parameter added
        update_data = {}
        # This section needs to be fixed - no grade parameter available
        
        if update_data:
            result = supabase.table("grades").update(update_data).eq("id", grade_id).eq("school_id", str(school_id)).execute()
            return GradeResponse(**result.data[0])
        else:
            record.pop("submissions", None)
            return GradeResponse(**record)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update grade error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{grade_id}")
def delete_grade(
    grade_id: str,
    school_id: UUID = Depends(get_current_school_id),
    user: dict = Depends(require_admin_or_teacher)
):
    """
    Delete grade, scoped to school. Admin or teacher who graded it.
    """
    try:
        # Get grade with submission and class info, scoped to school
        existing = supabase.table("grades").select("*, submissions(assignments(class_id, classes(teacher_id)))").eq("id", grade_id).eq("school_id", str(school_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Grade not found")

        record = existing.data[0]
        teacher_id = record["submissions"]["assignments"]["classes"]["teacher_id"]
        graded_by = record["graded_by"]

        if user["role"] == "teacher" and (teacher_id != user["id"] or graded_by != user["id"]):
            raise HTTPException(status_code=403, detail="Access denied")

        result = supabase.table("grades").delete().eq("id", grade_id).eq("school_id", str(school_id)).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Grade not found")
        return {"message": "Grade deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete grade error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")