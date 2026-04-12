from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import date, datetime
from uuid import UUID

class AssignmentCreate(BaseModel):
    class_id: UUID                          # Changed from str to UUID
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    file_url: Optional[str] = None
    total_points: Optional[str] = None
    isMCQ: Optional[bool] = False
    mcq_questions: Optional[List[Any]] = None

class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    file_url: Optional[str] = None
    total_points: Optional[str] = None
    isMCQ: Optional[bool] = None
    mcq_questions: Optional[List[Any]] = None

class AssignmentResponse(BaseModel):
    id: str
    class_id: UUID                          # Changed from str to UUID
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    file_url: Optional[str] = None
    total_points: Optional[str] = None
    isMCQ: Optional[bool] = False
    mcq_questions: Optional[List[Any]] = None
    created_by: str
    school_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True