from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class SubmissionCreate(BaseModel):
    assignment_id: UUID
    class_id: UUID
    file_url: Optional[str] = None
    notes: Optional[str] = None
    isMCQ: Optional[bool] = False
    mcq_answers: Optional[List[str]] = None

class SubmissionUpdate(BaseModel):
    file_url: Optional[str] = None
    notes: Optional[str] = None
    isMCQ: Optional[bool] = None
    mcq_answers: Optional[List[str]] = None

class SubmissionResponse(BaseModel):
    id: UUID                                     # Changed from str to UUID
    assignment_id: UUID
    class_id: UUID
    student_id: UUID                             # Changed from str to UUID
    submitted_at: datetime
    file_url: Optional[str] = None
    notes: Optional[str] = None
    isMCQ: Optional[bool] = False
    mcq_answers: Optional[List[str]] = None
    school_id: UUID

    class Config:
        populate_by_name = True