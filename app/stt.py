"""Speech-to-Text using Groq Whisper."""
import logging
import asyncio
from typing import Tuple, Optional, List, Dict
from pathlib import Path
import tempfile

from groq import AsyncGroq
from app.config import settings

logger = logging.getLogger(__name__)


async def transcribe_audio(
    audio_file_content: bytes,
    filename: str,
    model: str = "whisper-large-v3-turbo"
) -> Tuple[str, Optional[float], Optional[List[Dict]]]:
    """
    Transcribe audio file using Groq Whisper.
    
    Args:
        audio_file_content: Audio file bytes
        filename: Original filename (for extension detection)
        model: Whisper model to use (default: whisper-large-v3-turbo)
        
    Returns:
        Tuple of (transcript_text, duration_seconds, word_segments)
        word_segments contains timing info if available: [{"word": "hello", "start": 0.0, "end": 0.5}, ...]
    """
    client = AsyncGroq(api_key=settings.groq_api_key)
    
    try:
        # Create a temporary file to save the audio
        # Groq API requires a file object, not just bytes
        suffix = Path(filename).suffix or ".webm"
        
        # Write file in thread pool to avoid blocking
        temp_path = await asyncio.to_thread(_write_temp_file, audio_file_content, suffix)
        
        try:
            # Read and transcribe in thread pool
            file_content = await asyncio.to_thread(_read_file, temp_path, filename)
            
            # Request transcription with timestamps (async)
            transcription = await client.audio.transcriptions.create(
                file=file_content,
                model=model,
                response_format="verbose_json",  # Get detailed response with timestamps
                timestamp_granularities=["segment"],  # Request segment timestamps
                temperature=0.0,  # Deterministic transcription
                language="en",  # English language
                prompt="Umm, let me think, like... you know, I mean, basically, uh, yes."  # Help preserve filler words
            )
            
            # Extract transcript
            transcript_text = transcription.text
            
            # Extract duration if available
            duration = getattr(transcription, 'duration', None)
            
            # Extract segment-level timestamps for pause detection
            # Segments are typically sentence-level breaks
            word_segments = None
            if hasattr(transcription, 'segments') and transcription.segments:
                word_segments = []
                for segment in transcription.segments:
                    word_segments.append({
                        "text": segment.text if hasattr(segment, 'text') else "",
                        "start": segment.start if hasattr(segment, 'start') else 0.0,
                        "end": segment.end if hasattr(segment, 'end') else 0.0
                    })
            
            logger.info(
                f"Transcribed audio: {len(transcript_text)} chars, "
                f"duration: {duration}s, "
                f"segments: {len(word_segments) if word_segments else 0}"
            )
            
            return transcript_text, duration, word_segments
            
        finally:
            # Clean up temp file in thread pool
            await asyncio.to_thread(_cleanup_file, temp_path)
    
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise


def _write_temp_file(content: bytes, suffix: str) -> str:
    """Write content to temp file (blocking, run in thread pool)."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(content)
        temp_file.flush()
        return temp_file.name


def _read_file(temp_path: str, filename: str) -> tuple:
    """Read file content (blocking, run in thread pool)."""
    with open(temp_path, "rb") as audio_file:
        return (filename, audio_file.read())


def _cleanup_file(temp_path: str):
    """Delete temp file (blocking, run in thread pool)."""
    try:
        Path(temp_path).unlink()
    except Exception as e:
        logger.warning(f"Failed to delete temp file: {e}")
    
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise


def validate_audio_file(filename: str, file_size: int) -> Tuple[bool, Optional[str]]:
    """
    Validate audio file before transcription.
    
    Args:
        filename: Name of the file
        file_size: Size of the file in bytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file size (limit to 25MB)
    max_size = 25 * 1024 * 1024  # 25MB
    if file_size > max_size:
        return False, f"File too large. Maximum size is {max_size / (1024*1024):.0f}MB"
    
    # Check file extension
    allowed_extensions = {
        '.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', 
        '.wav', '.webm', '.ogg', '.flac'
    }
    
    file_ext = Path(filename).suffix.lower()
    if file_ext not in allowed_extensions:
        return False, f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
    
    return True, None


def estimate_duration_from_size(file_size: int, format: str = "webm") -> float:
    """
    Estimate audio duration from file size (rough approximation).
    
    Args:
        file_size: File size in bytes
        format: Audio format
        
    Returns:
        Estimated duration in seconds
    """
    # Rough estimates (bitrate in kbps)
    bitrates = {
        "webm": 48,  # WebM opus typical bitrate
        "mp3": 128,
        "m4a": 128,
        "wav": 1411,  # 16-bit, 44.1kHz stereo
        "flac": 700,
    }
    
    bitrate = bitrates.get(format.lower(), 128)
    # Convert file size to kilobits and divide by bitrate
    duration = (file_size * 8) / (bitrate * 1000)
    
    return duration
