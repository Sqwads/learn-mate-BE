from pydantic import BaseModel
from typing import Optional

class UserResponse(BaseModel):
    user_id: str
    email: Optional[str] = None
    role: str
    full_name: Optional[str] = None
    school_id: Optional[str] = None
    school_name: Optional[str] = None

class UserIdRequest(BaseModel):
    user_id: str

class LoginResponse(BaseModel):
    user_id: str
    token: Optional[str] = None