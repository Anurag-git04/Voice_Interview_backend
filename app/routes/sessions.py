"""API routes for interview sessions."""
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Depends, Request
from datetime import datetime
from bson import ObjectId
from typing import List, Optional
import logging

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.schemas import (
    CreateSessionRequest,
    CreateSessionResponse,
    SubmitAnswerRequest,
    AnswerResponse,
    SessionResponse,
    SessionWithTurnsResponse,
    ReportResponse,
    TurnResponse,
    EvaluationResponse,
    SessionListResponse,
    SessionListItem,
    SessionStatus
)
from app.db import get_sessions_collection, get_turns_collection
from app.interviewer import generate_first_question, generate_next_question
from app.evaluator import evaluate_answer, generate_report
from app.stt import transcribe_audio, validate_audio_file
from app.metrics import calculate_speech_metrics
from app.config import settings
from app.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])
limiter = Limiter(key_func=get_remote_address)


def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable format."""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def serialize_list(docs: List[dict]) -> List[dict]:
    """Convert list of MongoDB documents to JSON-serializable format."""
    return [serialize_doc(doc) for doc in docs]


@router.post("", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/hour")  # Limit session creation to control costs
async def create_session(request: Request, req: CreateSessionRequest, current_user: dict = Depends(get_current_user)):
    """
    Create a new interview session and return the first question.
    """
    try:
        # Generate first question
        first_question, provider_used, model_used, latency_ms = await generate_first_question(
            role=req.role,
            level=req.level.value,
            interview_type=req.interview_type.value,
            max_questions=req.max_questions,
            provider_name=req.llm_provider
        )
        
        # Create session document with user_id
        session_doc = {
            "user_id": str(current_user["_id"]),  # Add user_id
            "role": req.role,
            "level": req.level.value,
            "interview_type": req.interview_type.value,
            "max_questions": req.max_questions,
            "llm_provider": provider_used,
            "llm_model": model_used,
            "status": SessionStatus.active.value,
            "created_at": datetime.utcnow(),
            "completed_at": None,
            "summary": None
        }
        
        # Insert session
        sessions = get_sessions_collection()
        result = await sessions.insert_one(session_doc)
        session_id = str(result.inserted_id)
        
        # Create first turn with the question
        turn_doc = {
            "session_id": session_id,
            "index": 0,
            "question": first_question,
            "answer_text": None,
            "evaluation": None,
            "metrics": None,
            "llm_provider": provider_used,
            "llm_model": model_used,
            "latency_ms": latency_ms,
            "created_at": datetime.utcnow()
        }
        
        turns = get_turns_collection()
        await turns.insert_one(turn_doc)
        
        logger.info(f"Created session {session_id} with first question")
        
        return CreateSessionResponse(
            session_id=session_id,
            first_question=first_question,
            message="Interview session created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        # Sanitized error - don't leak internal details
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session"
        )


@router.post("/{session_id}/answer", response_model=AnswerResponse)
@limiter.limit("60/hour")  # Limit answer submissions to control LLM API costs
async def submit_answer(
    request: Request,
    session_id: str,
    current_user: dict = Depends(get_current_user),
    answer_text: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None)
):
    """
    Submit an answer to the current question and receive evaluation + next question.
    Accepts either text answer OR audio file (not both).
    """
    try:
        # Validate that we have either text or audio
        if not answer_text and not audio_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide either answer_text or audio_file"
            )
        
        if answer_text and audio_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot provide both answer_text and audio_file. Choose one."
            )
        
        # Validate session ID
        if not ObjectId.is_valid(session_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session ID"
            )
        
        # Get session
        sessions = get_sessions_collection()
        session = await sessions.find_one({"_id": ObjectId(session_id)})
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Verify session ownership
        if session.get("user_id") != str(current_user["_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        if session.get("status") == SessionStatus.completed.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session is already completed"
            )
        
        # Get all turns for this session
        turns = get_turns_collection()
        all_turns = await turns.find({"session_id": session_id}).sort("index", 1).to_list(None)
        
        if not all_turns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No question found for this session"
            )
        
        # Get the last turn (current question)
        current_turn = all_turns[-1]
        
        if current_turn.get("answer_text") is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current question already answered. Please wait for the next question."
            )
        
        # Process audio if provided
        metrics_data = None
        if audio_file:
            # Validate audio file
            audio_content = await audio_file.read()
            is_valid, error_msg = validate_audio_file(audio_file.filename, len(audio_content))
            
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
            
            # Transcribe audio
            logger.info(f"Transcribing audio file: {audio_file.filename} ({len(audio_content)} bytes)")
            
            try:
                transcript, duration, word_segments = await transcribe_audio(
                    audio_content,
                    audio_file.filename
                )
            except Exception as trans_error:
                error_str = str(trans_error)
                # Check for specific Groq error about audio being too short
                if "audio_too_short" in error_str or "too short" in error_str.lower():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Audio recording is too short. Please speak for at least 1 second and try again."
                    )
                # Re-raise other transcription errors
                raise
            
            answer_text = transcript
            logger.info(f"Transcription complete: {len(transcript)} characters")
            
            # Calculate speech metrics
            metrics_data = calculate_speech_metrics(
                transcript=transcript,
                duration_seconds=duration,
                word_segments=word_segments
            )
        
        # Evaluate the answer
        current_question = current_turn["question"]
        evaluation_data, eval_provider, eval_model, eval_latency = await evaluate_answer(
            question=current_question,
            answer=answer_text,
            provider_name=session["llm_provider"]
        )
        
        # Update the current turn with answer, evaluation, and metrics
        # Use conditional update to prevent double-submit
        update_data = {
            "answer_text": answer_text,
            "evaluation": evaluation_data,
            "llm_provider": eval_provider,
            "llm_model": eval_model,
            "latency_ms": eval_latency
        }
        
        if metrics_data:
            update_data["metrics"] = metrics_data
        
        # Conditional update: only update if answer_text is still None
        result = await turns.update_one(
            {
                "_id": current_turn["_id"],
                "answer_text": None  # Only update if not already answered
            },
            {"$set": update_data}
        )
        
        # Check if update succeeded
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This question has already been answered"
            )
        
        logger.info(f"Evaluated answer for session {session_id}, turn {current_turn['index']}")
        
        # Get updated turns list for generating next question
        all_turns = await turns.find({"session_id": session_id}).sort("index", 1).to_list(None)
        
        logger.info(f"=== BEFORE GENERATE_NEXT_QUESTION ===")
        logger.info(f"Session {session_id}: max_questions={session['max_questions']}")
        logger.info(f"Total turns in DB: {len(all_turns)}")
        logger.info(f"Turn indexes: {[t['index'] for t in all_turns]}")
        
        # Generate next question
        next_question, next_provider, next_model, next_latency, is_complete = await generate_next_question(
            session=session,
            turns=all_turns,
            provider_name=session["llm_provider"]
        )
        
        # If interview is complete
        if is_complete:
            # Mark session as completed
            await sessions.update_one(
                {"_id": ObjectId(session_id)},
                {
                    "$set": {
                        "status": SessionStatus.completed.value,
                        "completed_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"Interview completed for session {session_id}")
            
            return AnswerResponse(
                evaluation=EvaluationResponse(**evaluation_data),
                next_question=None,
                is_complete=True,
                message="Interview completed! You can now view your report."
            )
        
        # Create new turn with next question
        new_turn_doc = {
            "session_id": session_id,
            "index": len(all_turns),
            "question": next_question,
            "answer_text": None,
            "evaluation": None,
            "metrics": None,
            "llm_provider": next_provider,
            "llm_model": next_model,
            "latency_ms": next_latency,
            "created_at": datetime.utcnow()
        }
        
        await turns.insert_one(new_turn_doc)
        
        logger.info(f"Generated next question for session {session_id}")
        
        return AnswerResponse(
            evaluation=EvaluationResponse(**evaluation_data),
            next_question=next_question,
            is_complete=False,
            message="Answer evaluated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting answer: {e}")
        # Sanitized error - don't leak internal details
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit answer"
        )


@router.get("/{session_id}", response_model=SessionWithTurnsResponse)
async def get_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get session details with all turns.
    """
    try:
        if not ObjectId.is_valid(session_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session ID"
            )
        
        # Get session
        sessions = get_sessions_collection()
        session = await sessions.find_one({"_id": ObjectId(session_id)})
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Verify session ownership
        if session.get("user_id") != str(current_user["_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get all turns
        turns = get_turns_collection()
        all_turns = await turns.find({"session_id": session_id}).sort("index", 1).to_list(None)
        
        # Serialize
        session = serialize_doc(session)
        all_turns = serialize_list(all_turns)
        
        return SessionWithTurnsResponse(
            session=SessionResponse(**session),
            turns=[TurnResponse(**turn) for turn in all_turns]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        # Sanitized error - don't leak internal details
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session"
        )


@router.get("/{session_id}/report", response_model=ReportResponse)
@limiter.limit("30/hour")  # Limit report generation to control LLM API costs
async def get_report(request: Request, session_id: str, current_user: dict = Depends(get_current_user)):
    """
    Generate and return the final interview report.
    """
    try:
        if not ObjectId.is_valid(session_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session ID"
            )
        
        # Get session
        sessions = get_sessions_collection()
        session = await sessions.find_one({"_id": ObjectId(session_id)})
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Verify session ownership
        if session.get("user_id") != str(current_user["_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get all turns with answers
        turns = get_turns_collection()
        all_turns = await turns.find({
            "session_id": session_id,
            "answer_text": {"$ne": None}
        }).sort("index", 1).to_list(None)
        
        if not all_turns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No answered questions found"
            )
        
        # Check if report already exists
        if session.get("summary"):
            summary = session["summary"]
        else:
            # Generate report
            turns_data = serialize_list(all_turns)
            summary, report_provider, report_model, report_latency = await generate_report(
                turns_data=turns_data,
                provider_name=session["llm_provider"]
            )
            
            # Save report to session
            await sessions.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"summary": summary}}
            )
            
            logger.info(f"Generated report for session {session_id}")
        
        # Calculate average latency
        latencies = [turn.get("latency_ms", 0) for turn in all_turns]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        return ReportResponse(
            session_id=session_id,
            overall_score=summary.get("overall_score", 0),
            strengths=summary.get("strengths", []),
            weak_areas=summary.get("weak_areas", []),
            summary=summary.get("summary", ""),
            recommendations=summary.get("recommendations", []),
            turns_count=len(all_turns),
            average_latency_ms=round(avg_latency, 2)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        # Sanitized error - don't leak internal details
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )


@router.get("", response_model=SessionListResponse)
async def list_sessions(limit: int = 20, skip: int = 0, current_user: dict = Depends(get_current_user)):
    """
    List all interview sessions for the authenticated user.
    """
    try:
        sessions = get_sessions_collection()
        
        # Filter sessions by user_id
        user_id = str(current_user["_id"])
        query = {"user_id": user_id}
        
        # Get sessions with pagination
        all_sessions = await sessions.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(None)
        total = await sessions.count_documents(query)
        
        # Add overall score from summary if available
        session_items = []
        for session in all_sessions:
            session = serialize_doc(session)
            overall_score = None
            if session.get("summary"):
                overall_score = session["summary"].get("overall_score")
            
            session_items.append(SessionListItem(
                **session,
                overall_score=overall_score
            ))
        
        return SessionListResponse(
            sessions=session_items,
            total=total
        )
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        # Sanitized error - don't leak internal details
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list sessions"
        )
