from fastapi import APIRouter, Depends, HTTPException, Query
from app.db.supabase import supabase
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceUpdate,
    AttendanceResponse,
    AttendanceBulkCreate,
)
from app.core.dependencies import get_current_school_id
from datetime import datetime, date as date_type
from typing import List
from uuid import UUID

router = APIRouter(tags=["Attendance"])


@router.post("/", response_model=AttendanceResponse)
def mark_attendance(
    attendance: AttendanceCreate,
    user_id: str = Query(..., description="User ID of the admin or teacher user"),
    school_id: UUID = Depends(get_current_school_id),
):
    """
    Mark attendance for a student. Admin or teacher of the class, scoped to school.
    """
    try:
        # Get current user from user_id
        user_result = supabase.table("profiles").select("id, role").eq("id", user_id).execute()
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        current_user = user_result.data[0]
        
        class_id = str(attendance.class_id)
        student_id = str(attendance.student_id)

        # Check class existence and permission, scoped to school
        class_result = (
            supabase.table("classes")
            .select("id, teacher_id")
            .eq("id", class_id)
            .eq("school_id", str(school_id))
            .execute()
        )
        if not class_result.data:
            raise HTTPException(status_code=404, detail="Class not found")

        if current_user["role"] == "teacher" and class_result.data[0]["teacher_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Check for existing attendance
        existing = (
            supabase.table("attendance")
            .select("id")
            .eq("class_id", class_id)
            .eq("student_id", student_id)
            .eq("date", str(attendance.date))
            .execute()
        )
        if existing.data:
            raise HTTPException(
                status_code=400, detail="Attendance already marked for this date"
            )

        attendance_data = {
            "class_id": class_id,
            "student_id": student_id,
            "date": str(attendance.date),
            "status": attendance.status,
            "marked_by": current_user["id"],
            "school_id": str(school_id),
            "created_at": datetime.utcnow().isoformat(),
        }

        result = supabase.table("attendance").insert(attendance_data).execute()
        return AttendanceResponse(**result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        print(f"Mark attendance error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/bulk", response_model=List[AttendanceResponse])
def mark_bulk_attendance(
    bulk_data: AttendanceBulkCreate,
    user_id: str = Query(..., description="User ID of the admin or teacher user"),
    school_id: UUID = Depends(get_current_school_id),
):
    """
    Mark attendance for multiple students at once, scoped to school.
    """
    try:
        # Get current user from user_id
        user_result = supabase.table("profiles").select("id, role").eq("id", user_id).execute()
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = user_result.data[0]
        
        responses = []
        errors = []

        for attendance in bulk_data.attendances:
            try:
                class_id = str(attendance.class_id)
                student_id = str(attendance.student_id)

                # Check class existence and permission, scoped to school
                class_result = (
                    supabase.table("classes")
                    .select("id, teacher_id")
                    .eq("id", class_id)
                    .eq("school_id", str(school_id))
                    .execute()
                )
                if not class_result.data:
                    errors.append(f"Class {class_id} not found")
                    continue

                if user["role"] == "teacher" and class_result.data[0]["teacher_id"] != user["id"]:
                    errors.append(f"Access denied for class {class_id}")
                    continue

                # Check for existing attendance
                existing = (
                    supabase.table("attendance")
                    .select("id")
                    .eq("class_id", class_id)
                    .eq("student_id", student_id)
                    .eq("date", str(attendance.date))
                    .execute()
                )
                if existing.data:
                    errors.append(f"Attendance already exists for student {student_id} on {attendance.date}")
                    continue

                attendance_data = {
                    "class_id": class_id,
                    "student_id": student_id,
                    "date": str(attendance.date),
                    "status": attendance.status,
                    "marked_by": user["id"],
                    "school_id": str(school_id),
                    "created_at": datetime.utcnow().isoformat(),
                }

                result = supabase.table("attendance").insert(attendance_data).execute()
                responses.append(AttendanceResponse(**result.data[0]))
                
            except Exception as e:
                errors.append(f"Error processing attendance for student {student_id}: {str(e)}")
                continue

        # If no records were processed successfully, raise an error with details
        if not responses and errors:
            raise HTTPException(
                status_code=400, 
                detail={"message": "Failed to process any attendance records", "errors": errors}
            )

        return responses

    except HTTPException:
        raise
    except Exception as e:
        print(f"Bulk attendance error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/class/{class_id}", response_model=List[dict])
def get_class_attendance(
    class_id: UUID,
    user_id: str = Query(..., description="User ID of the admin or teacher user"),
    date: date_type | None = None,
    school_id: UUID = Depends(get_current_school_id),
):
    """
    Get attendance for a class grouped by date, scoped to school.
    Returns attendance records grouped by date with all students for each date.
    """
    try:
        # Get current user from user_id
        user_result = supabase.table("profiles").select("id, role").eq("id", user_id).execute()
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = user_result.data[0]
        
        class_id_str = str(class_id)

        class_result = (
            supabase.table("classes")
            .select("id, teacher_id")
            .eq("id", class_id_str)
            .eq("school_id", str(school_id))
            .execute()
        )
        if not class_result.data:
            raise HTTPException(status_code=404, detail="Class not found")

        if user["role"] == "teacher" and class_result.data[0]["teacher_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        query = supabase.table("attendance").select("*").eq("class_id", class_id_str).eq("school_id", str(school_id))
        if date:
            query = query.eq("date", str(date))

        result = query.execute()
        
        # Group attendance by date
        grouped_by_date = {}
        for record in result.data:
            record_date = record["date"]
            if record_date not in grouped_by_date:
                grouped_by_date[record_date] = {
                    "date": record_date,
                    "class_id": record["class_id"],
                    "students": []
                }
            
            grouped_by_date[record_date]["students"].append({
                "id": record["id"],
                "student_id": record["student_id"],
                "status": record["status"],
                "marked_by": record["marked_by"],
                "created_at": record["created_at"]
            })
        
        # Convert to list and sort by date (most recent first)
        grouped_list = list(grouped_by_date.values())
        grouped_list.sort(key=lambda x: x["date"], reverse=True)
        
        return grouped_list

    except HTTPException:
        raise
    except Exception as e:
        print(f"Get class attendance error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/student/{student_id}", response_model=List[AttendanceResponse])
def get_student_attendance(
    student_id: UUID,
    school_id: UUID = Depends(get_current_school_id),
):
    """
    Get attendance for a student, scoped to school. Public endpoint for student dashboard.
    """
    try:
        student_id_str = str(student_id)

        result = (
            supabase.table("attendance")
            .select("*")
            .eq("student_id", student_id_str)
            .eq("school_id", str(school_id))
            .execute()
        )

        return [AttendanceResponse(**row) for row in result.data]

    except HTTPException:
        raise
    except Exception as e:
        print(f"Get student attendance error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{attendance_id}", response_model=AttendanceResponse)
def update_attendance(
    attendance_id: UUID,
    attendance: AttendanceUpdate,
    user_id: str = Query(..., description="User ID of the admin or teacher user"),
    school_id: UUID = Depends(get_current_school_id),
):
    """
    Update attendance record, scoped to school.
    """
    try:
        # Get current user from user_id
        user_result = supabase.table("profiles").select("id, role").eq("id", user_id).execute()
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = user_result.data[0]
        
        attendance_id_str = str(attendance_id)

        existing = (
            supabase.table("attendance")
            .select("id, class_id, school_id")
            .eq("id", attendance_id_str)
            .eq("school_id", str(school_id))
            .execute()
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Attendance record not found")

        # Verify the class belongs to the user's school and check permissions
        class_result = (
            supabase.table("classes")
            .select("teacher_id")
            .eq("id", existing.data[0]["class_id"])
            .eq("school_id", str(school_id))
            .execute()
        )
        if not class_result.data:
            raise HTTPException(status_code=404, detail="Class not found")

        if user["role"] == "teacher" and class_result.data[0]["teacher_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        result = (
            supabase.table("attendance")
            .update({"status": attendance.status})
            .eq("id", attendance_id_str)
            .eq("school_id", str(school_id))
            .execute()
        )

        return AttendanceResponse(**result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        print(f"Update attendance error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{attendance_id}")
def delete_attendance(
    attendance_id: UUID,
    user_id: str = Query(..., description="User ID of the admin or teacher user"),
    school_id: UUID = Depends(get_current_school_id),
):
    """
    Delete attendance record, scoped to school.
    """
    try:
        # Get current user from user_id
        user_result = supabase.table("profiles").select("id, role").eq("id", user_id).execute()
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = user_result.data[0]
        
        attendance_id_str = str(attendance_id)

        existing = (
            supabase.table("attendance")
            .select("id, class_id, school_id")
            .eq("id", attendance_id_str)
            .eq("school_id", str(school_id))
            .execute()
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Attendance record not found")

        # Verify the class belongs to the user's school and check permissions
        class_result = (
            supabase.table("classes")
            .select("teacher_id")
            .eq("id", existing.data[0]["class_id"])
            .eq("school_id", str(school_id))
            .execute()
        )
        if not class_result.data:
            raise HTTPException(status_code=404, detail="Class not found")

        if user["role"] == "teacher" and class_result.data[0]["teacher_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        supabase.table("attendance").delete().eq("id", attendance_id_str).eq("school_id", str(school_id)).execute()
        return {"message": "Attendance record deleted"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete attendance error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/class/{class_id}/summary")
def get_attendance_summary(
    class_id: UUID,
    user_id: str = Query(..., description="User ID of the admin or teacher user"),
    date: date_type | None = None,
    school_id: UUID = Depends(get_current_school_id),
):
    """
    Get attendance summary for a class, scoped to school.
    """
    try:
        # Get current user from user_id
        user_result = supabase.table("profiles").select("id, role").eq("id", user_id).execute()
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = user_result.data[0]
        
        class_id_str = str(class_id)

        class_result = (
            supabase.table("classes")
            .select("id, teacher_id")
            .eq("id", class_id_str)
            .eq("school_id", str(school_id))
            .execute()
        )
        if not class_result.data:
            raise HTTPException(status_code=404, detail="Class not found")

        if user["role"] == "teacher" and class_result.data[0]["teacher_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        enrollment = (
            supabase.table("class_students")
            .select("student_id", count="exact")
            .eq("class_id", class_id_str)
            .execute()
        )
        total_students = enrollment.count or 0

        if not date:
            date = date_type.today()

        attendance_result = (
            supabase.table("attendance")
            .select("status")
            .eq("class_id", class_id_str)
            .eq("school_id", str(school_id))
            .eq("date", str(date))
            .execute()
        )

        # Count based on boolean status (True = present, False = absent)
        present_count = sum(1 for r in attendance_result.data if r["status"] is True)
        absent_count = sum(1 for r in attendance_result.data if r["status"] is False)
        not_marked = total_students - (present_count + absent_count)
        percentage = (present_count / total_students * 100) if total_students else 0.0

        return {
            "class_id": class_id,
            "date": date,
            "total_students": total_students,
            "present_count": present_count,
            "absent_count": absent_count,
            "not_marked_count": not_marked,
            "attendance_percentage": round(percentage, 2),
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Attendance summary error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")