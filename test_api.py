"""
Test script to verify the complete interview flow.

This script tests the Phase 1 backend by simulating a complete interview.
Make sure the backend is running before executing this script.
"""
import requests
import json
import time
from typing import Optional

BASE_URL = "http://localhost:8000"


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_health_check():
    """Test the health check endpoint."""
    print_section("Testing Health Check")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200, "Health check failed"
    print("✓ Health check passed")
    return True


def test_create_session():
    """Test creating a new interview session."""
    print_section("Creating Interview Session")
    
    payload = {
        "role": "Full Stack Developer",
        "level": "Mid",
        "interview_type": "technical",
        "max_questions": 3,  # Shorter for testing
        "llm_provider": "groq"
    }
    
    print(f"Request payload:\n{json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{BASE_URL}/sessions", json=payload)
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 201, "Session creation failed"
    
    data = response.json()
    session_id = data["session_id"]
    first_question = data["first_question"]
    
    print(f"\n✓ Session created: {session_id}")
    print(f"✓ First question: {first_question}")
    
    return session_id, first_question


def test_submit_answer(session_id: str, question: str, answer: str):
    """Test submitting an answer."""
    print_section(f"Submitting Answer")
    
    print(f"Question: {question}")
    print(f"Answer: {answer}")
    
    payload = {
        "answer_text": answer
    }
    
    response = requests.post(
        f"{BASE_URL}/sessions/{session_id}/answer",
        json=payload
    )
    
    print(f"\nStatus: {response.status_code}")
    
    assert response.status_code == 200, "Answer submission failed"
    
    data = response.json()
    print(f"\n✓ Answer evaluated")
    print(f"Score: {data['evaluation']['score']}/10")
    print(f"Relevance: {data['evaluation']['relevance']}/10")
    print(f"Structure: {data['evaluation']['structure']}/10")
    print(f"Technical Accuracy: {data['evaluation']['technical_accuracy']}/10")
    print(f"Clarity: {data['evaluation']['clarity']}/10")
    
    print(f"\nStrengths:")
    for strength in data['evaluation']['strengths']:
        print(f"  • {strength}")
    
    print(f"\nImprovements:")
    for improvement in data['evaluation']['improvements']:
        print(f"  • {improvement}")
    
    is_complete = data.get("is_complete", False)
    next_question = data.get("next_question")
    
    if not is_complete and next_question:
        print(f"\n✓ Next question: {next_question}")
    elif is_complete:
        print(f"\n✓ Interview complete!")
    
    return is_complete, next_question


def test_get_session(session_id: str):
    """Test getting session details."""
    print_section("Getting Session Details")
    
    response = requests.get(f"{BASE_URL}/sessions/{session_id}")
    print(f"Status: {response.status_code}")
    
    assert response.status_code == 200, "Failed to get session"
    
    data = response.json()
    print(f"\n✓ Session retrieved")
    print(f"Role: {data['session']['role']}")
    print(f"Level: {data['session']['level']}")
    print(f"Interview Type: {data['session']['interview_type']}")
    print(f"Status: {data['session']['status']}")
    print(f"Number of turns: {len(data['turns'])}")
    
    return True


def test_get_report(session_id: str):
    """Test getting the final report."""
    print_section("Generating Final Report")
    
    response = requests.get(f"{BASE_URL}/sessions/{session_id}/report")
    print(f"Status: {response.status_code}")
    
    assert response.status_code == 200, "Failed to get report"
    
    data = response.json()
    print(f"\n✓ Report generated")
    print(f"Overall Score: {data['overall_score']}/10")
    print(f"Questions Answered: {data['turns_count']}")
    print(f"Average Latency: {data['average_latency_ms']:.2f}ms")
    
    print(f"\nKey Strengths:")
    for strength in data['strengths']:
        print(f"  • {strength}")
    
    print(f"\nAreas for Improvement:")
    for weakness in data['weak_areas']:
        print(f"  • {weakness}")
    
    print(f"\nSummary:")
    print(f"  {data['summary']}")
    
    print(f"\nRecommendations:")
    for rec in data['recommendations']:
        print(f"  • {rec}")
    
    return True


def test_list_sessions():
    """Test listing all sessions."""
    print_section("Listing All Sessions")
    
    response = requests.get(f"{BASE_URL}/sessions")
    print(f"Status: {response.status_code}")
    
    assert response.status_code == 200, "Failed to list sessions"
    
    data = response.json()
    print(f"\n✓ Found {data['total']} total session(s)")
    
    for session in data['sessions'][:5]:  # Show first 5
        session_id = session.get('_id') or session.get('id')
        print(f"\nSession: {session_id}")
        print(f"  Role: {session['role']}")
        print(f"  Level: {session['level']}")
        print(f"  Type: {session['interview_type']}")
        print(f"  Status: {session['status']}")
        if session.get('overall_score'):
            print(f"  Score: {session['overall_score']}/10")
    
    return True


def run_complete_interview():
    """Run a complete interview simulation."""
    print_section("AI VOICE INTERVIEW COACH - BACKEND TEST")
    print("This script will test a complete interview flow")
    print("Make sure the backend is running at http://localhost:8000")
    
    input("\nPress Enter to start the test...")
    
    try:
        # 1. Health check
        test_health_check()
        time.sleep(1)
        
        # 2. Create session
        session_id, question = test_create_session()
        time.sleep(1)
        
        # 3. Simulate interview with sample answers
        sample_answers = [
            "React hooks are functions that let you use state and other React features in functional components. The main hooks are useState for managing state, useEffect for side effects, and useContext for consuming context. They enable a more functional approach to building components without classes.",
            "I would implement authentication using JWT tokens. On login, the server generates a signed token containing the user ID and expiration time. The client stores it securely and sends it with each request in the Authorization header. The server validates the signature and checks expiration before processing requests.",
            "For state management in a large application, I'd consider Redux or Zustand. Redux provides a centralized store with predictable state updates through actions and reducers. It works well with complex state logic and has great dev tools. For simpler cases, React Context with useReducer might be sufficient."
        ]
        
        current_question = question
        is_complete = False
        answer_index = 0
        
        while not is_complete and answer_index < len(sample_answers):
            time.sleep(2)  # Simulate thinking time
            
            answer = sample_answers[answer_index]
            is_complete, next_question = test_submit_answer(
                session_id,
                current_question,
                answer
            )
            
            if not is_complete and next_question:
                current_question = next_question
            
            answer_index += 1
        
        time.sleep(1)
        
        # 4. Get session details
        test_get_session(session_id)
        time.sleep(1)
        
        # 5. Get final report
        test_get_report(session_id)
        time.sleep(1)
        
        # 6. List sessions
        test_list_sessions()
        
        print_section("ALL TESTS PASSED ✓")
        print("Backend Phase 1 is working correctly!")
        print(f"\nYou can view the interactive API docs at: {BASE_URL}/docs")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Could not connect to {BASE_URL}")
        print("Make sure the backend is running:")
        print("  python -m uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    run_complete_interview()
