from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "eduhub")

# Async MongoDB client for FastAPI
client = AsyncIOMotorClient(MONGODB_URL)
database = client[DATABASE_NAME]

# Collections
users_collection = database.get_collection("users")
subjects_collection = database.get_collection("subjects")
materials_collection = database.get_collection("materials")

async def init_db():
    """Initialize database and create indexes"""
    try:
        # Create indexes for users
        await users_collection.create_index("email", unique=True)
        await users_collection.create_index("username", unique=True)
        
        # Create indexes for subjects
        await subjects_collection.create_index("code", unique=True)
        
        # Create indexes for materials
        await materials_collection.create_index("subject_id")
        await materials_collection.create_index("uploaded_by")
        
        # Check if subjects already exist
        existing_subjects = await subjects_collection.count_documents({})
        if existing_subjects == 0:
            default_subjects = [
                {"name": "Internet of Things", "code": "IOT", "description": "IOT", "icon": "🌐"},
                {"name": "IOT Lab", "code": "IOT_LAB", "description": "Practical Sessions", "icon": "🔧"},
                {"name": "Pervasive Computing", "code": "PC", "description": "PC", "icon": "☁️"},
                {"name": "PC Lab", "code": "PC_LAB", "description": "Hands-on Practice", "icon": "⚙️"},
                {"name": "Big Data Analytics", "code": "BDA", "description": "BDA", "icon": "📊"},
                {"name": "Cryptography & Network Security", "code": "CNS", "description": "CNS", "icon": "🔐"},
                {"name": "Internet & Mobile Tech", "code": "INTM", "description": "INTM", "icon": "🧠"},
            ]
            await subjects_collection.insert_many(default_subjects)
            print("✅ Default subjects added to MongoDB")
        
        print("✅ MongoDB initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing MongoDB: {e}")

async def close_db():
    """Close database connection"""
    client.close()
