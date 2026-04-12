from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

# Profile model (extends auth.users)
class Profile(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    role: str  # 'admin', 'teacher', 'student'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Class model
class Class(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    teacher_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Class student relationship
class ClassStudent(BaseModel):
    class_id: str
    student_id: str
    enrolled_at: Optional[datetime] = None

# Attendance model
class Attendance(BaseModel):
    id: Optional[int] = None
    class_id: int
    student_id: str
    date: date
    status: str  # 'present', 'absent', 'late'
    marked_by: str
    created_at: Optional[datetime] = None

# Assignment model
class Assignment(BaseModel):
    id: Optional[int] = None
    class_id: int
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    file_url: Optional[str] = None
    created_by: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Submission model
class Submission(BaseModel):
    id: Optional[int] = None
    assignment_id: int
    student_id: str
    submitted_at: Optional[datetime] = None
    file_url: Optional[str] = None
    notes: Optional[str] = None

# Grade model
class Grade(BaseModel):
    id: Optional[int] = None
    submission_id: int
    grade: str  # 'A', 'B', 'C', 'D', 'F' or numeric
    feedback: Optional[str] = None
    graded_by: str
    graded_at: Optional[datetime] = None

# Activity log model
class ActivityLog(BaseModel):
    id: Optional[int] = None
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[int] = None
    details: Optional[dict] = None
    created_at: Optional[datetime] = None
