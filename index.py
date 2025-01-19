from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from typing import Optional
import os
from dotenv import load_dotenv
import logging
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is missing")

# SQLAlchemy setup
try:
    # engine = create_engine(DATABASE_URL)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    logger.info("Database connection established successfully")
except Exception as e:
    logger.error(f"Failed to establish database connection: {e}")
    raise

# Form submission model
class Grandeur(Base):
    __tablename__ = "grandeur"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone_number = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Pydantic model for request validation
class FormData(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    number: str = Field(..., pattern=r"^\d{10}$")

# Initialize FastAPI app
app = FastAPI(
    title="Form Submission API",
    description="API for handling form submissions",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
    finally:
        db.close()

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Failed to create database tables: {e}")
    raise

@app.get("/")
def root():
    return "Hello World!"

@app.post("/submit-form", 
          response_model=dict,
          status_code=201)
async def submit_form(data: FormData, db: Session = Depends(get_db)):
    """
    Submit form data to the database
    """
    try:
        # Create new form submission
        form_entry = Grandeur(
            name=data.name,
            email=data.email,
            phone_number=data.number
        )
        
        db.add(form_entry)
        db.commit()
        db.refresh(form_entry)
        
        logger.info(f"Form submitted successfully. Record ID: {form_entry.id}")
        return {
            "message": "Form submitted successfully!",
            "record_id": form_entry.id
        }

    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database error occurred while submitting the form"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your request"
        )

# Health check endpoint
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Check if the application and database connection are healthy"""
    try:
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable"
        )

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)