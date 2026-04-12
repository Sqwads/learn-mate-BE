from pydantic import BaseModel
from typing import List
from datetime import date, datetime
from uuid import UUID


class AttendanceCreate(BaseModel):
    class_id: UUID
    student_id: UUID
    date: date
    status: bool


class AttendanceUpdate(BaseModel):
    status: bool


class AttendanceResponse(BaseModel):
    id: UUID
    class_id: UUID
    student_id: UUID
    date: date
    status: bool
    marked_by: UUID
    school_id: UUID
    created_at: datetime


class AttendanceBulkCreate(BaseModel):
    attendances: List[AttendanceCreate]
