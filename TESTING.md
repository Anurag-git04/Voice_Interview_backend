# Testing Guide

## Prerequisites

Before testing, ensure you have:

1. **Groq API Key**
   - Sign up at https://console.groq.com
   - Create an API key
   - Free tier includes generous rate limits

2. **MongoDB Atlas Database**
   - Sign up at https://www.mongodb.com/cloud/atlas
   - Create a free cluster
   - Get the connection string
   - Add your IP to network access (or use 0.0.0.0/0 for testing)

3. **Python 3.12+**
   ```powershell
   python --version
   ```

## Setup Steps

### 1. Install Dependencies

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:
```powershell
Copy-Item .env.example .env
```

Edit `.env` with your credentials:
```env
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/interview_coach?retryWrites=true&w=majority
FRONTEND_ORIGIN=http://localhost:3000
MAX_AUDIO_SECONDS=90
MAX_QUESTIONS_PER_SESSION=10
```

### 3. Start the Server

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

## Testing Methods

### Method 1: Automated Test Script (Recommended)

In a new terminal window:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python test_api.py
```

This will:
- ✅ Check health endpoint
- ✅ Create a new interview session
- ✅ Submit 3 sample answers
- ✅ Get evaluations with feedback
- ✅ Generate final report
- ✅ List all sessions

Expected output:
```
============================================================
  AI VOICE INTERVIEW COACH - BACKEND TEST
============================================================

Press Enter to start the test...

============================================================
  Testing Health Check
============================================================

Status: 200
Response: {
  "status": "healthy",
  "message": "API is running",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
✓ Health check passed

...

============================================================
  ALL TESTS PASSED ✓
============================================================
```

### Method 2: Interactive API Docs

1. Open http://localhost:8000/docs in your browser
2. Expand the endpoints
3. Click "Try it out" on any endpoint
4. Fill in the request body
5. Click "Execute"

Example flow:
1. **POST /sessions** - Create a session
   ```json
   {
     "role": "Full Stack Developer",
     "level": "Mid",
     "interview_type": "technical",
     "max_questions": 5,
     "llm_provider": "groq"
   }
   ```
   Copy the `session_id` from the response.

2. **POST /sessions/{session_id}/answer** - Submit answer
   ```json
   {
     "answer_text": "Your answer here..."
   }
   ```

3. **GET /sessions/{session_id}/report** - Get final report

### Method 3: Manual Testing with curl/PowerShell

#### Health Check
```powershell
curl http://localhost:8000/health
```

#### Create Session
```powershell
$body = @{
    role = "Software Engineer"
    level = "Junior"
    interview_type = "technical"
    max_questions = 3
    llm_provider = "groq"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/sessions" -Method Post -Body $body -ContentType "application/json"
$sessionId = $response.session_id
Write-Host "Session ID: $sessionId"
Write-Host "First Question: $($response.first_question)"
```

#### Submit Answer
```powershell
$answer = @{
    answer_text = "React hooks allow functional components to have state and lifecycle methods. The most common are useState for state management and useEffect for side effects."
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/sessions/$sessionId/answer" -Method Post -Body $answer -ContentType "application/json"
Write-Host "Score: $($response.evaluation.score)/10"
Write-Host "Next Question: $($response.next_question)"
```

## Common Issues

### Issue: "Failed to connect to MongoDB"

**Solution:**
- Check your MongoDB connection string in `.env`
- Ensure your IP is whitelisted in MongoDB Atlas Network Access
- Verify the database user has read/write permissions

### Issue: "Groq API error"

**Solution:**
- Verify your API key in `.env`
- Check you haven't exceeded rate limits
- Ensure the model name is correct: `llama-3.1-8b-instant`

### Issue: "ModuleNotFoundError"

**Solution:**
```powershell
pip install -r requirements.txt
```

### Issue: "Port 8000 already in use"

**Solution:**
```powershell
# Find and kill the process using port 8000
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process

# Or use a different port
python -m uvicorn app.main:app --reload --port 8001
```

## Verifying Success

A successful test should show:

1. ✅ Health check returns 200
2. ✅ Session created with a valid ID
3. ✅ First question is generated
4. ✅ Answer submission returns evaluation with:
   - Score (0-10)
   - Relevance, structure, technical_accuracy, clarity scores
   - List of strengths (2-3 items)
   - List of improvements (2-3 items)
   - Sample answer
5. ✅ Next question is generated (if not complete)
6. ✅ Final report includes:
   - Overall score
   - Aggregated strengths and weaknesses
   - Summary paragraph
   - Recommendations

## Performance Metrics

Expected latencies (with Groq):
- Question generation: 500-1500ms
- Answer evaluation: 800-2000ms
- Report generation: 1000-2500ms

These will be logged in the response and can be compared when Gemini is added in Phase 5.

## Database Verification

To verify data is being saved correctly:

1. Log into MongoDB Atlas
2. Navigate to your cluster → Browse Collections
3. Check the `interview_coach` database
4. You should see two collections:
   - `sessions` - One document per interview
   - `turns` - Multiple documents per session (one per question)

## Next Steps After Successful Testing

✅ Phase 1 Complete!

Move on to:
- Phase 2: Add speech-to-text functionality
- Phase 3: Build the Next.js frontend
- Phase 4: Deploy to production

## Getting Help

If you encounter issues:
1. Check the logs in the terminal running uvicorn
2. Look for error messages in the test script output
3. Review the API docs at http://localhost:8000/docs
4. Check environment variables are set correctly
5. Verify MongoDB and Groq credentials are valid
