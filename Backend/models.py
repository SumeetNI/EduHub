from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Any
from datetime import datetime
from bson import ObjectId

# Simple approach: Don't use custom PyObjectId, just use strings
class UserModel(BaseModel):
    """User model for MongoDB"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[str] = Field(default=None, alias="_id")
    email: EmailStr
    username: str
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SubjectModel(BaseModel):
    """Subject model for MongoDB"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    code: str
    description: Optional[str] = None
    icon: str = "📚"

class MaterialModel(BaseModel):
    """Material model for MongoDB"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[str] = Field(default=None, alias="_id")
    subject_id: str
    title: str
    content: Optional[str] = None
    file_url: Optional[str] = None
    uploaded_by: str  # User ID as string
    created_at: datetime = Field(default_factory=datetime.utcnow)
