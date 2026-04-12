from fastapi import APIRouter, Depends, HTTPException
from app.db.supabase import supabase
from app.schemas.submissions import SubmissionCreate, SubmissionUpdate, SubmissionResponse
from app.core.dependencies import require_admin_or_teacher, get_current_school_id
from app.core.security import get_current_user
from datetime import datetime
from uuid import UUID
import json

router = APIRouter(tags=["Submissions"])

@router.post("/", response_model=SubmissionResponse)
def submit_assignment(
    submission: SubmissionCreate,
    school_id: UUID = Depends(get_current_school_id),
    user: dict = Depends(get_current_user)
):
    """
    Submit an assignment, scoped to school. Only students can submit.
    Supports both regular file submissions and MCQ answer submissions.
    """
    try:
        if user["role"] != "student":
            raise HTTPException(status_code=403, detail="Only students can submit assignments")

        # Check if assignment exists, scoped to school
        assignment_result = supabase.table("assignments").select("*, classes(teacher_id)").eq("id", str(submission.assignment_id)).eq("school_id", str(school_id)).execute()
        if not assignment_result.data:
            raise HTTPException(status_code=404, detail="Assignment not found")

        assignment = assignment_result.data[0]
        class_id = assignment["class_id"]
        
        # Verify the provided class_id matches the assignment's class_id
        if str(submission.class_id) != class_id:
            raise HTTPException(status_code=400, detail="Class ID does not match assignment's class")

        # Check if student is enrolled in the class
        enrollment = supabase.table("class_students").select("*").eq("class_id", class_id).eq("student_id", user["id"]).execute()
        if not enrollment.data:
            raise HTTPException(status_code=403, detail="Not enrolled in this class")

        # Check if submission already exists
        existing = supabase.table("submissions").select("*").eq("assignment_id", str(submission.assignment_id)).eq("student_id", user["id"]).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Submission already exists")

        submission_data = {
            "assignment_id": str(submission.assignment_id),
            "class_id": str(submission.class_id),
            "student_id": user["id"],
            "submitted_at": datetime.utcnow().isoformat(),
            "file_url": submission.file_url,
            "notes": submission.notes,
            "isMCQ": submission.isMCQ or False,
            "mcq_answers": json.dumps(submission.mcq_answers) if submission.mcq_answers else None,
            "school_id": str(school_id)
        }

        result = supabase.table("submissions").insert(submission_data).execute()
        return SubmissionResponse(**result.data[0])
    except HTTPException:
        raise
    except Exception as e:
        print(f"Submit assignment error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/assignment/{assignment_id}", response_model=list[SubmissionResponse])
def get_assignment_submissions(
    assignment_id: str,
    school_id: UUID = Depends(get_current_school_id),
    user: dict = Depends(require_admin_or_teacher)
):
    """
    Get all submissions for an assignment, scoped to school. Admin or teacher of the class.
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

        result = supabase.table("submissions").select("*").eq("assignment_id", assignment_id).eq("school_id", str(school_id)).execute()
        return [SubmissionResponse(**submission) for submission in result.data]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get assignment submissions error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/my", response_model=list[SubmissionResponse])
def get_my_submissions(
    school_id: UUID = Depends(get_current_school_id),
    user: dict = Depends(get_current_user)
):
    """
    Get current user's submissions, scoped to school. Only for students.
    """
    try:
        if user["role"] != "student":
            raise HTTPException(status_code=403, detail="Only students can view their submissions")

        result = supabase.table("submissions").select("*").eq("student_id", user["id"]).eq("school_id", str(school_id)).execute()
        return [SubmissionResponse(**submission) for submission in result.data]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get my submissions error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{submission_id}", response_model=SubmissionResponse)
def get_submission(
    submission_id: str,
    school_id: UUID = Depends(get_current_school_id),
    user: dict = Depends(get_current_user)
):
    """
    Get specific submission by ID, scoped to school.
    """
    try:
        # Get submission with assignment and class info, scoped to school
        result = supabase.table("submissions").select("*, assignments(class_id, classes(teacher_id))").eq("id", submission_id).eq("school_id", str(school_id)).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Submission not found")

        submission = result.data[0]
        teacher_id = submission["assignments"]["classes"]["teacher_id"]

        # Check permissions
        if user["role"] == "student" and submission["student_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        elif user["role"] == "teacher" and teacher_id != user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Remove nested data before returning
        submission.pop("assignments", None)
        return SubmissionResponse(**submission)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get submission error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{submission_id}", response_model=SubmissionResponse)
def update_submission(
    submission_id: str,
    submission: SubmissionUpdate,
    school_id: UUID = Depends(get_current_school_id),
    user: dict = Depends(get_current_user)
):
    """
    Update submission, scoped to school. Only the student who submitted can update.
    """
    try:
        if user["role"] != "student":
            raise HTTPException(status_code=403, detail="Only students can update their submissions")

        # Check if submission exists and belongs to user, scoped to school
        existing = supabase.table("submissions").select("*").eq("id", submission_id).eq("student_id", user["id"]).eq("school_id", str(school_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Submission not found")

        update_data = {}
        if submission.file_url is not None:
            update_data["file_url"] = submission.file_url
        if submission.notes is not None:
            update_data["notes"] = submission.notes
        if submission.isMCQ is not None:
            update_data["isMCQ"] = submission.isMCQ
        if submission.mcq_answers is not None:
            update_data["mcq_answers"] = json.dumps(submission.mcq_answers)

        if update_data:
            result = supabase.table("submissions").update(update_data).eq("id", submission_id).eq("school_id", str(school_id)).execute()
            return SubmissionResponse(**result.data[0])
        else:
            return SubmissionResponse(**existing.data[0])
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update submission error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{submission_id}")
def delete_submission(
    submission_id: str,
    school_id: UUID = Depends(get_current_school_id),
    user: dict = Depends(require_admin_or_teacher)
):
    """
    Delete submission, scoped to school. Admin or teacher of the class.
    """
    try:
        # Get submission with assignment and class info, scoped to school
        submission_result = supabase.table("submissions").select("*, assignments(class_id, classes(teacher_id))").eq("id", submission_id).eq("school_id", str(school_id)).execute()
        if not submission_result.data:
            raise HTTPException(status_code=404, detail="Submission not found")

        submission = submission_result.data[0]
        teacher_id = submission["assignments"]["classes"]["teacher_id"]

        if user["role"] == "teacher" and teacher_id != user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        result = supabase.table("submissions").delete().eq("id", submission_id).eq("school_id", str(school_id)).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Submission not found")
        return {"message": "Submission deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete submission error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")