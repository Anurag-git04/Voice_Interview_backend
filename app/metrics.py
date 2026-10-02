"""Speech metrics calculation for interview analysis."""
import re
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


# Common filler words and phrases in English
FILLER_WORDS = {
    'um', 'uh', 'er', 'ah', 'like', 'you know', 'i mean', 
    'sort of', 'kind of', 'basically', 'actually', 'literally',
    'so', 'well', 'right', 'okay', 'yeah', 'hmm', 'uh-huh',
    'you see', 'you know what i mean', 'at the end of the day'
}


def calculate_word_count(text: str) -> int:
    """
    Calculate the number of words in the transcript.
    
    Args:
        text: Transcript text
        
    Returns:
        Number of words
    """
    if not text:
        return 0
    
    # Split by whitespace and count non-empty tokens
    words = text.split()
    return len(words)


def calculate_wpm(word_count: int, duration_seconds: float) -> float:
    """
    Calculate words per minute.
    
    Args:
        word_count: Total number of words
        duration_seconds: Audio duration in seconds
        
    Returns:
        Words per minute (WPM)
    """
    if duration_seconds <= 0:
        return 0.0
    
    minutes = duration_seconds / 60.0
    wpm = word_count / minutes
    
    return round(wpm, 2)


def count_filler_words(text: str) -> Dict[str, int]:
    """
    Count occurrences of filler words in the transcript.
    
    Args:
        text: Transcript text
        
    Returns:
        Dictionary with total count and breakdown by filler word
    """
    if not text:
        return {"total": 0, "details": {}}
    
    text_lower = text.lower()
    
    filler_counts = {}
    total_count = 0
    
    # Check for multi-word phrases first (to avoid double-counting)
    multi_word_fillers = [f for f in FILLER_WORDS if ' ' in f]
    for filler in sorted(multi_word_fillers, key=len, reverse=True):
        count = len(re.findall(r'\b' + re.escape(filler) + r'\b', text_lower))
        if count > 0:
            filler_counts[filler] = count
            total_count += count
            # Remove found phrases to avoid double-counting with single words
            text_lower = re.sub(r'\b' + re.escape(filler) + r'\b', '', text_lower)
    
    # Check single-word fillers
    single_word_fillers = [f for f in FILLER_WORDS if ' ' not in f]
    for filler in single_word_fillers:
        count = len(re.findall(r'\b' + re.escape(filler) + r'\b', text_lower))
        if count > 0:
            filler_counts[filler] = count
            total_count += count
    
    return {
        "total": total_count,
        "details": filler_counts
    }


def detect_long_pauses(
    word_segments: Optional[List[Dict]], 
    threshold_seconds: float = 2.0
) -> List[Dict]:
    """
    Detect long pauses between words.
    
    Args:
        word_segments: List of word segments with timing info
            [{"word": "hello", "start": 0.0, "end": 0.5}, ...]
        threshold_seconds: Minimum pause duration to count (default: 2.0s)
        
    Returns:
        List of pause events [{"start": 1.5, "end": 3.5, "duration": 2.0}, ...]
    """
    if not word_segments or len(word_segments) < 2:
        return []
    
    pauses = []
    
    for i in range(len(word_segments) - 1):
        current_end = word_segments[i].get('end')
        next_start = word_segments[i + 1].get('start')
        
        if current_end is not None and next_start is not None:
            gap = next_start - current_end
            
            if gap >= threshold_seconds:
                pauses.append({
                    "start": current_end,
                    "end": next_start,
                    "duration": round(gap, 2)
                })
    
    return pauses


def calculate_speech_metrics(
    transcript: str,
    duration_seconds: Optional[float] = None,
    word_segments: Optional[List[Dict]] = None
) -> Dict:
    """
    Calculate comprehensive speech metrics.
    
    Args:
        transcript: Transcribed text
        duration_seconds: Audio duration in seconds
        word_segments: Word-level timing information
        
    Returns:
        Dictionary of metrics
    """
    metrics = {}
    
    # Word count
    word_count = calculate_word_count(transcript)
    metrics['words'] = word_count
    
    # Words per minute
    if duration_seconds and duration_seconds > 0:
        metrics['wpm'] = calculate_wpm(word_count, duration_seconds)
        metrics['duration_seconds'] = round(duration_seconds, 2)
    else:
        metrics['wpm'] = None
        metrics['duration_seconds'] = None
    
    # Filler words
    filler_analysis = count_filler_words(transcript)
    metrics['filler_count'] = filler_analysis['total']
    metrics['filler_details'] = filler_analysis['details']
    
    # Filler word ratio (percentage)
    if word_count > 0:
        metrics['filler_ratio'] = round((filler_analysis['total'] / word_count) * 100, 2)
    else:
        metrics['filler_ratio'] = 0.0
    
    # Long pauses
    if word_segments:
        pauses = detect_long_pauses(word_segments)
        metrics['long_pauses'] = len(pauses)
        metrics['pause_details'] = pauses
    else:
        metrics['long_pauses'] = 0
        metrics['pause_details'] = []
    
    # Speech pace assessment
    if metrics['wpm'] is not None:
        if metrics['wpm'] < 120:
            pace = "slow"
        elif metrics['wpm'] < 160:
            pace = "normal"
        elif metrics['wpm'] < 200:
            pace = "fast"
        else:
            pace = "very fast"
        metrics['pace_assessment'] = pace
    else:
        metrics['pace_assessment'] = None
    
    logger.info(
        f"Calculated metrics: {word_count} words, "
        f"{metrics['wpm']} WPM, "
        f"{metrics['filler_count']} fillers, "
        f"{metrics['long_pauses']} pauses"
    )
    
    return metrics


def get_metrics_summary(metrics: Dict) -> str:
    """
    Generate a human-readable summary of speech metrics.
    
    Args:
        metrics: Metrics dictionary from calculate_speech_metrics
        
    Returns:
        Summary string
    """
    summary_parts = []
    
    # Word count
    summary_parts.append(f"Spoke {metrics['words']} words")
    
    # WPM
    if metrics['wpm']:
        summary_parts.append(f"at {metrics['wpm']} words per minute ({metrics['pace_assessment']} pace)")
    
    # Fillers
    if metrics['filler_count'] > 0:
        summary_parts.append(
            f"with {metrics['filler_count']} filler words ({metrics['filler_ratio']}% of speech)"
        )
    else:
        summary_parts.append("with no filler words")
    
    # Pauses
    if metrics['long_pauses'] > 0:
        summary_parts.append(f"and {metrics['long_pauses']} long pause(s)")
    
    return ", ".join(summary_parts) + "."
