from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import timedelta
import os
from dotenv import load_dotenv
from bson import ObjectId

from database import (
    init_db, 
    close_db,
    users_collection,
    subjects_collection,
    materials_collection
)
from auth import (
    get_password_hash, 
    authenticate_user, 
    create_access_token, 
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from utils import validate_email, validate_password, format_response

load_dotenv()

app = FastAPI(title="EduHub API", version="1.0.0")

# CORS configuration
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class UserSignup(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    created_at: str

class SubjectResponse(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str]
    icon: str

class MaterialCreate(BaseModel):
    subject_id: str
    title: str
    content: Optional[str]
    file_url: Optional[str]

class MaterialResponse(BaseModel):
    id: str
    subject_id: str
    title: str
    content: Optional[str]
    file_url: Optional[str]
    uploaded_by: str
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    await init_db()
    print("🚀 EduHub API is running with MongoDB!")

@app.on_event("shutdown")
async def shutdown_event():
    await close_db()

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return format_response(True, "EduHub API is healthy", {"status": "running", "database": "MongoDB"})

# Authentication endpoints
@app.post("/api/auth/signup", response_model=TokenResponse)
async def signup(user_data: UserSignup):
    """Register a new user"""
    # Validate email
    if not validate_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    
    # Validate password
    is_valid, error_msg = validate_password(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Check if user already exists
    existing_user = await users_collection.find_one({
        "$or": [
            {"email": user_data.email},
            {"username": user_data.username}
        ]
    })
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )
    
    # Create new user
    from datetime import datetime
    hashed_password = get_password_hash(user_data.password)
    new_user = {
        "email": user_data.email,
        "username": user_data.username,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow()
    }
    
    result = await users_collection.insert_one(new_user)
    new_user["_id"] = str(result.inserted_id)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": new_user["email"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    user_response = UserResponse(
        id=new_user["_id"],
        email=new_user["email"],
        username=new_user["username"],
        created_at=new_user["created_at"].isoformat()
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """Login user and return JWT token"""
    user = await authenticate_user(user_data.email, user_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user["email"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    user_response = UserResponse(
        id=user["_id"],
        email=user["email"],
        username=user["username"],
        created_at=user["created_at"].isoformat()
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user information"""
    return UserResponse(
        id=current_user["_id"],
        email=current_user["email"],
        username=current_user["username"],
        created_at=current_user["created_at"].isoformat()
    )

# Subject endpoints
@app.get("/api/subjects", response_model=List[SubjectResponse])
async def get_subjects():
    """Get all subjects"""
    subjects = await subjects_collection.find().to_list(length=100)
    return [
        SubjectResponse(
            id=str(subject["_id"]),
            name=subject["name"],
            code=subject["code"],
            description=subject.get("description"),
            icon=subject.get("icon", "📚")
        )
        for subject in subjects
    ]

@app.get("/api/subjects/{subject_id}", response_model=SubjectResponse)
async def get_subject(subject_id: str):
    """Get a specific subject by ID"""
    if not ObjectId.is_valid(subject_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subject ID"
        )
    
    subject = await subjects_collection.find_one({"_id": ObjectId(subject_id)})
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found"
        )
    
    return SubjectResponse(
        id=str(subject["_id"]),
        name=subject["name"],
        code=subject["code"],
        description=subject.get("description"),
        icon=subject.get("icon", "📚")
    )

# Material endpoints
@app.get("/api/subjects/{subject_id}/materials", response_model=List[MaterialResponse])
async def get_subject_materials(subject_id: str):
    """Get all materials for a specific subject"""
    materials = await materials_collection.find({"subject_id": subject_id}).to_list(length=100)
    return [
        MaterialResponse(
            id=str(material["_id"]),
            subject_id=material["subject_id"],
            title=material["title"],
            content=material.get("content"),
            file_url=material.get("file_url"),
            uploaded_by=material["uploaded_by"],
            created_at=material["created_at"].isoformat()
        )
        for material in materials
    ]

@app.post("/api/materials", response_model=MaterialResponse)
async def create_material(
    material_data: MaterialCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new study material (requires authentication)"""
    # Verify subject exists
    if ObjectId.is_valid(material_data.subject_id):
        subject = await subjects_collection.find_one({"_id": ObjectId(material_data.subject_id)})
    else:
        subject = None
    
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found"
        )
    
    # Create new material
    from datetime import datetime
    new_material = {
        "subject_id": material_data.subject_id,
        "title": material_data.title,
        "content": material_data.content,
        "file_url": material_data.file_url,
        "uploaded_by": current_user["_id"],
        "created_at": datetime.utcnow()
    }
    
    result = await materials_collection.insert_one(new_material)
    new_material["_id"] = str(result.inserted_id)
    
    return MaterialResponse(
        id=new_material["_id"],
        subject_id=new_material["subject_id"],
        title=new_material["title"],
        content=new_material.get("content"),
        file_url=new_material.get("file_url"),
        uploaded_by=new_material["uploaded_by"],
        created_at=new_material["created_at"].isoformat()
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to EduHub API",
        "version": "1.0.0",
        "database": "MongoDB",
        "docs": "/docs"
    }
