"""
Test script for audio upload functionality (Phase 2).

This script tests the audio upload and transcription features.
Make sure the backend is running before executing this script.

You'll need an audio file to test with. You can:
1. Record audio on your phone and transfer it
2. Use any existing audio/video file (mp3, wav, webm, m4a, etc.)
3. Record using Windows Voice Recorder
"""
import requests
import json
from pathlib import Path


BASE_URL = "http://localhost:8000"


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_audio_answer(session_id: str, audio_file_path: str):
    """
    Test submitting an audio answer.
    
    Args:
        session_id: The session ID from create_session
        audio_file_path: Path to audio file to upload
    """
    print_section("Testing Audio Upload")
    
    audio_path = Path(audio_file_path)
    
    if not audio_path.exists():
        print(f"❌ Error: Audio file not found: {audio_file_path}")
        print("\nTo test audio upload:")
        print("1. Record audio on your phone or using Windows Voice Recorder")
        print("2. Save it somewhere (e.g., test_audio.mp3)")
        print("3. Run: python test_audio_api.py <session_id> <audio_file_path>")
        return False
    
    print(f"Audio file: {audio_path.name}")
    print(f"File size: {audio_path.stat().st_size / 1024:.2f} KB")
    
    # Open and upload the audio file
    with open(audio_path, 'rb') as audio_file:
        files = {
            'audio_file': (audio_path.name, audio_file, 'audio/mpeg')
        }
        
        print(f"\nUploading to: {BASE_URL}/sessions/{session_id}/answer")
        
        response = requests.post(
            f"{BASE_URL}/sessions/{session_id}/answer",
            files=files
        )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Error: {response.text}")
        return False
    
    data = response.json()
    
    print("\n✅ Audio uploaded and transcribed successfully!")
    
    # Show evaluation
    print(f"\n📊 Evaluation:")
    print(f"  Score: {data['evaluation']['score']}/10")
    print(f"  Relevance: {data['evaluation']['relevance']}/10")
    print(f"  Structure: {data['evaluation']['structure']}/10")
    print(f"  Technical Accuracy: {data['evaluation']['technical_accuracy']}/10")
    print(f"  Clarity: {data['evaluation']['clarity']}/10")
    
    print(f"\n💪 Strengths:")
    for strength in data['evaluation']['strengths']:
        print(f"  • {strength}")
    
    print(f"\n📈 Improvements:")
    for improvement in data['evaluation']['improvements']:
        print(f"  • {improvement}")
    
    # Show next question or completion
    if data.get('is_complete'):
        print(f"\n✅ {data.get('message', 'Interview complete!')}")
    elif data.get('next_question'):
        print(f"\n❓ Next question:")
        print(f"  {data['next_question']}")
    
    return True


def test_get_session_with_metrics(session_id: str):
    """Get session details to see the speech metrics."""
    print_section("Getting Session with Speech Metrics")
    
    response = requests.get(f"{BASE_URL}/sessions/{session_id}")
    
    if response.status_code != 200:
        print(f"❌ Error: {response.text}")
        return False
    
    data = response.json()
    
    print("✅ Session retrieved")
    
    # Find turns with metrics
    for turn in data['turns']:
        if turn.get('metrics'):
            print(f"\n📊 Speech Metrics for Turn {turn['index']}:")
            metrics = turn['metrics']
            
            print(f"  Words: {metrics.get('words', 'N/A')}")
            print(f"  WPM: {metrics.get('wpm', 'N/A')}")
            print(f"  Duration: {metrics.get('duration_seconds', 'N/A')}s")
            print(f"  Pace: {metrics.get('pace_assessment', 'N/A')}")
            print(f"  Filler words: {metrics.get('filler_count', 0)} ({metrics.get('filler_ratio', 0)}%)")
            print(f"  Long pauses: {metrics.get('long_pauses', 0)}")
            
            if metrics.get('filler_details'):
                print(f"\n  Filler breakdown:")
                for filler, count in metrics['filler_details'].items():
                    print(f"    - '{filler}': {count}")
    
    return True


def main():
    """Main test function."""
    import sys
    
    print_section("AI Voice Interview Coach - Audio Upload Test")
    
    if len(sys.argv) < 2:
        print("Usage: python test_audio_api.py [session_id] [audio_file_path]")
        print("\nOption 1: Test with existing session")
        print("  python test_audio_api.py <session_id> <audio_file.mp3>")
        print("\nOption 2: Create new session first")
        print("  1. Go to http://localhost:8000/docs")
        print("  2. Create a session with POST /sessions")
        print("  3. Run this script with the session_id")
        print("\nExample:")
        print("  python test_audio_api.py 6abeb0759b95db557b6be014 test_audio.mp3")
        return
    
    session_id = sys.argv[1]
    
    if len(sys.argv) >= 3:
        audio_file_path = sys.argv[2]
        
        # Test audio upload
        success = test_audio_answer(session_id, audio_file_path)
        
        if success:
            # Show the metrics
            input("\nPress Enter to view speech metrics...")
            test_get_session_with_metrics(session_id)
        
    else:
        # Just show metrics for existing session
        test_get_session_with_metrics(session_id)
    
    print("\n" + "="*60)
    print("  Test Complete!")
    print("="*60)


if __name__ == "__main__":
    main()
