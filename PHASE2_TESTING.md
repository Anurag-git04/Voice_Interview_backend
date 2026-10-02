# Phase 2 Testing Guide - Audio Upload

## Prerequisites

1. **Backend running** on http://localhost:8000
2. **Audio file** to test with (any of these formats):
   - MP3, WAV, WebM, M4A, OGG, FLAC
   - Maximum size: 25MB
   - Recommended: 10-60 seconds of speech

## Getting an Audio File

### Option 1: Record on Your Phone
1. Open Voice Recorder app
2. Record yourself answering an interview question
3. Transfer the file to your computer
4. Save it in the `backend/` folder

### Option 2: Windows Voice Recorder
1. Press **Windows + S**, search for "Voice Recorder"
2. Click record, answer a question
3. Save the recording
4. File is usually in: `%USERPROFILE%\Documents\Sound recordings\`

### Option 3: Use Existing Audio
Any audio/video file works: a podcast clip, YouTube download (mp3), etc.

## Testing Steps

### Step 1: Start the Backend

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 2: Create a Session

Go to http://localhost:8000/docs and:

1. Expand **POST /sessions**
2. Click "Try it out"
3. Use this payload:
   ```json
   {
     "role": "Full Stack Developer",
     "level": "Mid",
     "interview_type": "technical",
     "max_questions": 3,
     "llm_provider": "groq"
   }
   ```
4. Click "Execute"
5. **Copy the `session_id`** from the response

### Step 3: Test Audio Upload

#### Method A: Using Swagger UI (Recommended)

1. Go to http://localhost:8000/docs
2. Expand **POST /sessions/{session_id}/answer**
3. Click "Try it out"
4. Enter your `session_id`
5. Click "Choose File" under `audio_file`
6. Select your audio file
7. Leave `answer_text` empty
8. Click "Execute"

You should see:
- ✅ Transcript of your audio
- ✅ Evaluation with scores
- ✅ Speech metrics (words, WPM, filler words, pauses)
- ✅ Next question

#### Method B: Using Test Script

```powershell
python test_audio_api.py <session_id> <audio_file.mp3>
```

Example:
```powershell
python test_audio_api.py 6abeb0759b95db557b6be014 my_answer.mp3
```

### Step 4: View Speech Metrics

1. Go to http://localhost:8000/docs
2. Expand **GET /sessions/{session_id}**
3. Enter your `session_id`
4. Click "Execute"

Look for the `metrics` field in the response:
```json
{
  "metrics": {
    "words": 120,
    "wpm": 145.5,
    "duration_seconds": 49.5,
    "pace_assessment": "normal",
    "filler_count": 8,
    "filler_ratio": 6.67,
    "filler_details": {
      "um": 3,
      "uh": 2,
      "like": 3
    },
    "long_pauses": 2,
    "pause_details": [
      {"start": 15.2, "end": 17.8, "duration": 2.6},
      {"start": 35.1, "end": 37.5, "duration": 2.4}
    ]
  }
}
```

## What Gets Analyzed

### Transcription (Groq Whisper)
- Converts your audio to text
- Extracts word-level timestamps
- Measures audio duration

### Speech Metrics
- **Word Count**: Total words spoken
- **WPM**: Words per minute (typical range: 120-180)
- **Filler Words**: um, uh, like, you know, etc.
- **Filler Ratio**: Percentage of filler words
- **Long Pauses**: Gaps > 2 seconds
- **Pace Assessment**: slow / normal / fast / very fast

### Interview Evaluation
- Same 4-dimension rubric as Phase 1
- Evaluation is based on the transcript
- Feedback on content quality

## Troubleshooting

### Error: "Unsupported file format"
- Use mp3, wav, webm, m4a, ogg, or flac
- Check file extension is correct

### Error: "File too large"
- Maximum size is 25MB
- Compress the audio or trim it shorter

### Error: "Must provide either answer_text or audio_file"
- You need to upload EITHER audio OR text, not both
- Don't fill in `answer_text` when uploading audio

### Transcription takes a long time
- Normal for larger files (30s audio ≈ 2-5s to transcribe)
- Whisper-large-v3-turbo is fast but not instant

### No metrics in response
- Check that you uploaded audio (not text)
- Verify the audio has actual speech content
- Check logs for transcription errors

## Expected Performance

- **Transcription speed**: 2-10 seconds per minute of audio
- **Small file (10s)**: ~1-2 seconds total
- **Medium file (30s)**: ~3-5 seconds total
- **Large file (60s)**: ~5-10 seconds total

## Next Steps After Testing

Once audio upload works:
- ✅ Phase 2 is complete!
- 📱 Move to Phase 3: Build the Next.js frontend
- 🎤 Add push-to-talk interface
- 🚀 Deploy to production (Phase 4)

## Support

If you encounter issues:
1. Check server logs in the terminal
2. Verify your `.env` has `GROQ_API_KEY`
3. Ensure Whisper model is accessible (`whisper-large-v3-turbo`)
4. Test with a small, clear audio file first
