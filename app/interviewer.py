"""Interview question generation and conversation management."""
import logging
from typing import Dict, Any, Optional, List

from app.llm import generate
from app.prompts import get_interviewer_prompt

logger = logging.getLogger(__name__)


def build_conversation_history(turns: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Build conversation history from turns for LLM context.
    
    Args:
        turns: List of turn documents from database
        
    Returns:
        List of message dictionaries for LLM
    """
    history = []
    
    for turn in turns:
        # Add question (assistant message)
        if 'question' in turn:
            history.append({
                "role": "assistant",
                "content": turn['question']
            })
        
        # Add answer (user message)
        if 'answer_text' in turn:
            history.append({
                "role": "user",
                "content": turn['answer_text']
            })
    
    return history


def is_interview_complete(question: str, current_count: int, max_questions: int) -> bool:
    """
    Check if the interview should end.
    
    Args:
        question: The latest question from the interviewer
        current_count: Current number of main questions asked (including this one)
        max_questions: Maximum questions allowed
        
    Returns:
        True if interview is complete
    """
    # Check for completion marker
    if "[INTERVIEW_COMPLETE]" in question:
        return True
    
    # Check if we've exceeded the max (not reached - we want exactly max_questions)
    if current_count > max_questions:
        return True
    
    return False


def count_main_questions(turns: List[Dict[str, Any]]) -> int:
    """
    Count the number of main questions (not follow-ups).
    
    Each turn represents one Q&A pair, so the number of turns
    equals the number of questions asked.
    
    Args:
        turns: List of turn documents (each turn = 1 question)
        
    Returns:
        Number of main questions
    """
    # Each turn document represents one question
    # (turns are only created when a new question is asked)
    return len(turns)


async def generate_next_question(
    session: Dict[str, Any],
    turns: List[Dict[str, Any]],
    provider_name: str = "groq"
) -> tuple[str, str, str, float, bool]:
    """
    Generate the next interview question based on session and conversation history.
    
    Args:
        session: Session document from database
        turns: List of turn documents for this session
        provider_name: LLM provider to use
        
    Returns:
        Tuple of (question, provider_used, model_used, latency_ms, is_complete)
    """
    # Get session parameters
    role = session.get('role', 'Software Developer')
    level = session.get('level', 'Mid')
    interview_type = session.get('interview_type', 'technical')
    max_questions = session.get('max_questions', 5)
    
    # Build conversation history
    history = build_conversation_history(turns)
    
    # Count questions asked so far
    question_count = count_main_questions(turns)
    
    # Log for debugging
    logger.info(f"=== GENERATE_NEXT_QUESTION DEBUG ===")
    logger.info(f"Total turns in DB: {len(turns)}")
    logger.info(f"Question count: {question_count}")
    logger.info(f"Max questions: {max_questions}")
    logger.info(f"Should generate question #{question_count + 1}")
    
    # Check if we should end (we want to generate up to max_questions)
    # After answering question 5 (in 5-question interview), question_count will be 5
    # So we should NOT generate another question
    if question_count >= max_questions:
        logger.info(f"Interview complete: {question_count} questions asked (max: {max_questions})")
        return (
            "[INTERVIEW_COMPLETE]",
            provider_name,
            session.get('llm_model', 'unknown'),
            0.0,
            True
        )
    
    # Get system prompt
    system_prompt = get_interviewer_prompt(
        role=role,
        level=level,
        interview_type=interview_type,
        max_questions=max_questions
    )
    
    # If this is the first question
    if not history:
        history.append({
            "role": "user",
            "content": "Please ask the first interview question."
        })
    else:
        # Ask for the next question
        history.append({
            "role": "user",
            "content": "Please ask the next question."
        })
    
    try:
        # Generate question
        question, provider_used, model_used, latency_ms = await generate(
            system=system_prompt,
            history=history,
            provider_name=provider_name,
            fallback=False
        )
        
        # Clean up the question
        question = question.strip()
        
        # Check if interview is complete
        is_complete = is_interview_complete(question, question_count + 1, max_questions)
        
        # Remove the marker from the question if present
        question = question.replace("[INTERVIEW_COMPLETE]", "").strip()
        
        logger.info(f"Generated question {question_count + 1}/{max_questions}")
        
        return question, provider_used, model_used, latency_ms, is_complete
        
    except Exception as e:
        logger.error(f"Error generating question: {e}")
        raise


async def generate_first_question(
    role: str,
    level: str,
    interview_type: str,
    max_questions: int,
    provider_name: str = "groq"
) -> tuple[str, str, str, float]:
    """
    Generate the first question for a new interview session.
    
    Args:
        role: Job role
        level: Experience level
        interview_type: Type of interview
        max_questions: Maximum number of questions
        provider_name: LLM provider to use
        
    Returns:
        Tuple of (question, provider_used, model_used, latency_ms)
    """
    system_prompt = get_interviewer_prompt(
        role=role,
        level=level,
        interview_type=interview_type,
        max_questions=max_questions
    )
    
    history = [
        {
            "role": "user",
            "content": "Please ask the first interview question."
        }
    ]
    
    try:
        question, provider_used, model_used, latency_ms = await generate(
            system=system_prompt,
            history=history,
            provider_name=provider_name,
            fallback=False
        )
        
        question = question.strip()
        logger.info("Generated first question")
        
        return question, provider_used, model_used, latency_ms
        
    except Exception as e:
        logger.error(f"Error generating first question: {e}")
        raise
