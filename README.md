# AI Voice Interview Coach - Backend

FastAPI backend for the AI Voice Interview Coach system.

## Setup

### 1. Create Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```powershell
Copy-Item .env.example .env
```

Required environment variables:

- `GROQ_API_KEY`: Your Groq API key from https://console.groq.com
- `MONGODB_URI`: MongoDB Atlas connection string
- `FRONTEND_ORIGIN`: Frontend URL (default: http://localhost:3000)

### 4. Run the Server

```powershell
# Development mode with auto-reload
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using the main module directly
python app/main.py
```

The API will be available at:

- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## API Endpoints

### Sessions

- `POST /sessions` - Create a new interview session
- `POST /sessions/{id}/answer` - Submit an answer to the current question
- `GET /sessions/{id}` - Get session details with all turns
- `GET /sessions/{id}/report` - Get the final interview report
- `GET /sessions` - List all sessions

### Health

- `GET /health` - Health check endpoint

## Testing

You can test the API using:

1. FastAPI interactive docs at http://localhost:8000/docs
2. Postman or any HTTP client
3. The test script: `python test_api.py` (after creating one)

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app entry point
│   ├── config.py         # Environment configuration
│   ├── db.py             # MongoDB connection
│   ├── llm.py            # LLM provider layer
│   ├── prompts.py        # System prompts
│   ├── interviewer.py    # Question generation
│   ├── evaluator.py      # Answer evaluation
│   ├── schemas.py        # Pydantic models
│   └── routes/
│       └── sessions.py   # API routes
├── requirements.txt
├── .env.example
└── README.md
```

## Phase 1 Features ✅

- ✅ Text-only interview flow
- ✅ Groq LLM integration
- ✅ MongoDB session storage
- ✅ Rubric-based evaluation (relevance, structure, technical accuracy, clarity)
- ✅ Adaptive questioning based on role, level, and interview type
- ✅ Final report generation with strengths and improvement areas

## Phase 2 Features ✅

- ✅ Speech-to-text with Groq Whisper (`whisper-large-v3-turbo`)
- ✅ Audio file upload support (mp3, wav, webm, m4a, ogg, flac, up to 25MB)
- ✅ Speech metrics: word count, WPM, filler words, pauses, pace
- ✅ Automatic transcription with word-level timestamps

## Coming in Future Phases

- Phase 3: Frontend with Next.js
- Phase 4: Deployment to Render + Vercel
- Phase 5: Gemini provider integration
- Phase 6: Resume-based questions with vector search
