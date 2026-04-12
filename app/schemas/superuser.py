from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime


class SchoolListItem(BaseModel):
    id: str
    school_name: str
    status: Optional[str]
    created_at: Optional[datetime]
    admin_id: Optional[str]
    admin_name: Optional[str]
    admin_email: Optional[str]


class SchoolListResponse(BaseModel):
    total_schools: int
    schools: List[SchoolListItem]


class SchoolAnalytics(BaseModel):
    school_id: str
    school_name: Optional[str]
    total_users: int
    active_users: int
    users_by_role: Dict[str, int]
    total_classes: int
    active_classes: int
    total_attendance_records: int
    attendance_rate: Optional[float] = None  # Changed to Optional
    recent_attendance_activity: int
    generated_at: datetime


class PlatformAnalytics(BaseModel):
    total_schools: int
    active_schools: int
    total_users: int
    active_users: int
    users_by_role: Dict[str, int]
    total_classes: int
    active_classes: int
    total_attendance_records: int
    overall_attendance_rate: Optional[float] = None  # Changed to Optional
    recent_attendance_activity: int
    top_schools_by_users: List[Dict]
    top_schools_by_attendance: List[Dict]
    generated_at: datetime