from pydantic import BaseModel, validator, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class SchoolCreate(BaseModel):
    school_name: str
    admin_user_id: UUID

    @validator('school_name')
    def school_name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('School name cannot be empty')
        return v.strip()

class SchoolResponse(BaseModel):
    id: UUID
    school_name: str
    admin_user_id: UUID = Field(..., alias="admin_id")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True  # Allow both admin_id and admin_user_id

class SchoolDelete(BaseModel):
    admin_id: UUID
    school_id: UUID