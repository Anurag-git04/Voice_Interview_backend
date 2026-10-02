"""Answer evaluation with JSON validation and rubric scoring."""
import json
import re
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError

from app.llm import generate
from app.prompts import get_evaluator_prompt

logger = logging.getLogger(__name__)


class Evaluation(BaseModel):
    """Pydantic model for evaluation response."""
    score: float = Field(ge=0, le=10, description="Overall score")
    relevance: float = Field(ge=0, le=10, description="Relevance score")
    structure: float = Field(ge=0, le=10, description="Structure score")
    technical_accuracy: float = Field(ge=0, le=10, description="Technical accuracy score")
    clarity: float = Field(ge=0, le=10, description="Clarity score")
    strengths: list[str] = Field(default_factory=list, description="List of strengths (may be empty for weak answers)")
    improvements: list[str] = Field(default_factory=list, description="List of improvements (may be empty)")
    sample_answer: str = Field(default="", description="Sample answer (required even for weak answers)")


def strip_code_fences(text: str) -> str:
    """
    Remove markdown code fences and extra text around JSON.
    
    Args:
        text: Raw LLM response
        
    Returns:
        Cleaned JSON string
    """
    # Remove code fences
    text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
    text = text.strip()
    
    # Try to extract JSON object if there's extra text
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    
    return text


def get_safe_default_evaluation(question: str, answer: str) -> Dict[str, Any]:
    """
    Return a safe default evaluation when JSON parsing fails.
    Marks evaluation as failed with null scores.
    
    Args:
        question: The interview question
        answer: The candidate's answer
        
    Returns:
        Default evaluation dictionary with evaluation_failed flag
    """
    return {
        "score": None,
        "relevance": None,
        "structure": None,
        "technical_accuracy": None,
        "clarity": None,
        "strengths": [],
        "improvements": ["Could not automatically score this answer - evaluation failed"],
        "sample_answer": "",
        "evaluation_failed": True
    }


async def evaluate_answer(
    question: str,
    answer: str,
    provider_name: str = "groq",
    max_retries: int = 1
) -> tuple[Dict[str, Any], str, str, float]:
    """
    Evaluate a candidate's answer using the LLM.
    
    Args:
        question: The interview question
        answer: The candidate's answer
        provider_name: LLM provider to use
        max_retries: Number of retries on JSON parse failure
        
    Returns:
        Tuple of (evaluation_dict, provider_used, model_used, latency_ms)
    """
    system_prompt = get_evaluator_prompt()
    
    history = [
        {
            "role": "user",
            "content": f"Question: {question}\n\nCandidate's Answer: {answer}\n\nProvide your evaluation in JSON format."
        }
    ]
    
    attempts = 0
    last_error = None
    
    while attempts <= max_retries:
        try:
            # Get LLM response
            response_text, provider_used, model_used, latency_ms = await generate(
                system=system_prompt,
                history=history,
                provider_name=provider_name,
                fallback=False
            )
            
            # Clean the response
            cleaned_json = strip_code_fences(response_text)
            
            # Parse JSON
            evaluation_data = json.loads(cleaned_json)
            
            # Validate with Pydantic
            evaluation = Evaluation(**evaluation_data)
            
            logger.info(f"Successfully evaluated answer (attempt {attempts + 1})")
            return evaluation.model_dump(), provider_used, model_used, latency_ms
            
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            logger.warning(f"JSON validation failed (attempt {attempts + 1}): {e}")
            
            if attempts < max_retries:
                # Retry with a more explicit instruction
                history.append({
                    "role": "assistant",
                    "content": response_text
                })
                history.append({
                    "role": "user",
                    "content": "That was not valid JSON. Please respond with ONLY valid JSON, no code fences or additional text."
                })
            
            attempts += 1
        
        except Exception as e:
            logger.error(f"Evaluation error: {e}")
            last_error = e
            break
    
    # If all retries failed, return safe default
    logger.error(f"All evaluation attempts failed. Last error: {last_error}")
    return (
        get_safe_default_evaluation(question, answer),
        provider_name,
        "unknown",
        0.0
    )


async def generate_report(
    turns_data: list[Dict[str, Any]],
    provider_name: str = "groq"
) -> tuple[Dict[str, Any], str, str, float]:
    """
    Generate a final interview report based on all turns.
    
    Args:
        turns_data: List of turn dictionaries with questions, answers, and evaluations
        provider_name: LLM provider to use
        
    Returns:
        Tuple of (report_dict, provider_used, model_used, latency_ms)
    """
    from app.prompts import get_report_prompt
    
    # Filter out failed evaluations for scoring
    valid_turns = [
        turn for turn in turns_data
        if turn.get('evaluation') and not turn['evaluation'].get('evaluation_failed')
    ]
    
    system_prompt = get_report_prompt(turns_data)
    
    # Build summary of all turns (including failed ones for context)
    turns_summary = ""
    for i, turn in enumerate(turns_data, 1):
        turns_summary += f"\n--- Question {i} ---\n"
        turns_summary += f"Q: {turn.get('question', 'N/A')}\n"
        turns_summary += f"A: {turn.get('answer_text', 'N/A')}\n"
        if 'evaluation' in turn:
            eval_data = turn['evaluation']
            if eval_data.get('evaluation_failed'):
                turns_summary += "Score: [Evaluation Failed]\n"
            else:
                turns_summary += f"Score: {eval_data.get('score', 'N/A')}\n"
                turns_summary += f"Strengths: {', '.join(eval_data.get('strengths', []))}\n"
                turns_summary += f"Improvements: {', '.join(eval_data.get('improvements', []))}\n"
    
    history = [
        {
            "role": "user",
            "content": f"Here is the complete interview data:\n{turns_summary}\n\nProvide the final report in JSON format."
        }
    ]
    
    try:
        # Get LLM response
        response_text, provider_used, model_used, latency_ms = await generate(
            system=system_prompt,
            history=history,
            provider_name=provider_name,
            fallback=False
        )
        
        # Clean and parse
        cleaned_json = strip_code_fences(response_text)
        report_data = json.loads(cleaned_json)
        
        logger.info("Successfully generated report")
        return report_data, provider_used, model_used, latency_ms
        
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        
        # Calculate average score from VALID turns only
        if valid_turns:
            scores = [t['evaluation']['score'] for t in valid_turns]
            avg_score = sum(scores) / len(scores) if scores else None
        else:
            avg_score = None  # No valid scores
        
        failed_count = len(turns_data) - len(valid_turns)
        note = f" ({failed_count} answers could not be scored)" if failed_count > 0 else ""
        
        return {
            "overall_score": round(avg_score, 1) if avg_score else None,
            "strengths": ["Completed the interview"],
            "weak_areas": ["Unable to generate detailed report"],
            "summary": f"Interview completed{note}. Please review individual question feedback.",
            "recommendations": ["Practice more interviews"]
        }, provider_name, "unknown", 0.0
