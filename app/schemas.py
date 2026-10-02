"""Pydantic schemas for API requests and responses."""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class InterviewType(str, Enum):
    """Types of interviews."""
    technical = "technical"
    behavioral = "behavioral"
    system_design = "system_design"


class ExperienceLevel(str, Enum):
    """Experience levels."""
    junior = "Junior"
    mid = "Mid"
    senior = "Senior"


class SessionStatus(str, Enum):
    """Session status."""
    active = "active"
    completed = "completed"


# Authentication Schemas

class RegisterRequest(BaseModel):
    """Request to register a new user."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (minimum 8 characters)")
    full_name: str = Field(..., min_length=1, max_length=100, description="User full name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securePassword123",
                "full_name": "John Doe"
            }
        }


class RegisterResponse(BaseModel):
    """Response after successful registration."""
    user_id: str
    email: str
    full_name: str
    token: str


class LoginRequest(BaseModel):
    """Request to login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securePassword123"
            }
        }


class LoginResponse(BaseModel):
    """Response after successful login."""
    token: str
    email: str
    full_name: str


class ProfileResponse(BaseModel):
    """User profile response."""
    user_id: str
    email: str
    full_name: str
    created_at: datetime


# Request Schemas

class CreateSessionRequest(BaseModel):
    """Request to create a new interview session."""
    role: str = Field(..., min_length=2, max_length=100, description="Job role")
    level: ExperienceLevel = Field(..., description="Experience level")
    interview_type: InterviewType = Field(..., description="Interview type")
    max_questions: int = Field(5, ge=1, le=10, description="Maximum number of questions")
    llm_provider: str = Field("groq", description="LLM provider to use")
    
    class Config:
        json_schema_extra = {
            "example": {
                "role": "Full Stack Developer",
                "level": "Mid",
                "interview_type": "technical",
                "max_questions": 5,
                "llm_provider": "groq"
            }
        }


class SubmitAnswerRequest(BaseModel):
    """Request to submit an answer (text or audio)."""
    answer_text: Optional[str] = Field(None, min_length=1, description="Text answer from candidate (if not using audio)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer_text": "React hooks are functions that let you use state and lifecycle features in functional components..."
            }
        }


# Note: Audio file uploads are handled via multipart/form-data, not JSON
# The route will accept either answer_text OR an audio file


# Response Schemas

class EvaluationResponse(BaseModel):
    """Evaluation data for an answer."""
    score: Optional[float] = None
    relevance: Optional[float] = None
    structure: Optional[float] = None
    technical_accuracy: Optional[float] = None
    clarity: Optional[float] = None
    strengths: List[str] = []
    improvements: List[str] = []
    sample_answer: str = ""
    evaluation_failed: Optional[bool] = None


class MetricsResponse(BaseModel):
    """Speech metrics from audio analysis."""
    words: Optional[int] = None
    wpm: Optional[float] = None
    filler_count: Optional[int] = None
    filler_ratio: Optional[float] = None
    filler_details: Optional[Dict] = None
    long_pauses: Optional[int] = None
    pause_details: Optional[List[Dict]] = None
    duration_seconds: Optional[float] = None
    pace_assessment: Optional[str] = None  # "slow", "normal", "fast", "very fast"


class TurnResponse(BaseModel):
    """Response for a single interview turn."""
    id: str = Field(..., alias="_id")
    session_id: str
    index: int
    question: str
    answer_text: Optional[str] = None
    evaluation: Optional[EvaluationResponse] = None
    metrics: Optional[MetricsResponse] = None
    llm_provider: str
    llm_model: str
    latency_ms: float
    created_at: datetime
    
    class Config:
        populate_by_name = True


class AnswerResponse(BaseModel):
    """Response after submitting an answer."""
    evaluation: EvaluationResponse
    next_question: Optional[str] = None
    is_complete: bool = Field(..., description="Whether the interview is complete")
    message: Optional[str] = None


class SessionResponse(BaseModel):
    """Response for session details."""
    id: str = Field(..., alias="_id")
    role: str
    level: str
    interview_type: str
    max_questions: int
    llm_provider: str
    llm_model: str
    status: SessionStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    summary: Optional[dict] = None
    
    class Config:
        populate_by_name = True


class SessionWithTurnsResponse(BaseModel):
    """Session with all turns."""
    session: SessionResponse
    turns: List[TurnResponse]


class CreateSessionResponse(BaseModel):
    """Response after creating a session."""
    session_id: str
    first_question: str
    message: str


class ReportStrengthsWeaknesses(BaseModel):
    """Strengths and weaknesses in the report."""
    strengths: List[str]
    weak_areas: List[str]


class ReportResponse(BaseModel):
    """Final interview report."""
    session_id: str
    overall_score: float
    strengths: List[str]
    weak_areas: List[str]
    summary: str
    recommendations: List[str]
    turns_count: int
    average_latency_ms: float


class SessionListItem(BaseModel):
    """Abbreviated session info for listing."""
    id: str = Field(..., alias="_id")
    role: str
    level: str
    interview_type: str
    status: SessionStatus
    created_at: datetime
    overall_score: Optional[float] = None
    
    class Config:
        populate_by_name = True


class SessionListResponse(BaseModel):
    """List of sessions."""
    sessions: List[SessionListItem]
    total: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    message: str
    timestamp: datetime
