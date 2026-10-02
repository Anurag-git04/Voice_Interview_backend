"""
Test script to verify the authentication API.

This script tests user registration, login, profile access, and protected routes.
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


def print_response(response: requests.Response):
    """Print formatted response."""
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")


def test_health_check():
    """Test the health check endpoint."""
    print_section("1. Testing Health Check")
    
    response = requests.get(f"{BASE_URL}/health")
    print_response(response)
    
    assert response.status_code == 200, "Health check failed"
    print("✓ Health check passed")
    return True


def test_register_user(email: str, password: str, full_name: str):
    """Test user registration."""
    print_section(f"2. Registering User: {email}")
    
    payload = {
        "email": email,
        "password": password,
        "full_name": full_name
    }
    
    print(f"Request payload:\n{json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{BASE_URL}/auth/register", json=payload)
    print_response(response)
    
    if response.status_code == 201:
        print(f"✓ User registered successfully")
        data = response.json()
        return data.get("user_id"), data.get("token")
    elif response.status_code == 400 and "already registered" in response.json().get("detail", ""):
        print("⚠ User already exists, will try to login")
        return None, None
    else:
        print(f"✗ Registration failed")
        return None, None


def test_login_user(email: str, password: str):
    """Test user login."""
    print_section(f"3. Logging In: {email}")
    
    payload = {
        "email": email,
        "password": password
    }
    
    print(f"Request payload:\n{json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{BASE_URL}/auth/login", json=payload)
    print_response(response)
    
    assert response.status_code == 200, f"Login failed: {response.text}"
    print(f"✓ Login successful")
    
    data = response.json()
    return data.get("token")


def test_get_profile(token: str):
    """Test getting user profile with authentication."""
    print_section("4. Getting User Profile (Protected Route)")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    print(f"Request headers:\n{json.dumps(headers, indent=2)}")
    
    response = requests.get(f"{BASE_URL}/auth/profile", headers=headers)
    print_response(response)
    
    assert response.status_code == 200, f"Get profile failed: {response.text}"
    print(f"✓ Profile retrieved successfully")
    
    return response.json()


def test_create_session_with_auth(token: str):
    """Test creating a session with authentication."""
    print_section("5. Creating Session (Protected Route)")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "role": "Full Stack Developer",
        "level": "Mid",
        "interview_type": "technical",
        "max_questions": 3,
        "llm_provider": "groq"
    }
    
    print(f"Request headers:\n{json.dumps(headers, indent=2)}")
    print(f"Request payload:\n{json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{BASE_URL}/sessions", json=payload, headers=headers)
    print_response(response)
    
    if response.status_code == 201:
        print(f"✓ Session created successfully")
        data = response.json()
        return data.get("session_id")
    else:
        print(f"✗ Session creation failed")
        return None


def test_get_sessions_with_auth(token: str):
    """Test getting user's sessions (should be filtered by user_id)."""
    print_section("6. Getting User Sessions (Protected Route)")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    print(f"Request headers:\n{json.dumps(headers, indent=2)}")
    
    response = requests.get(f"{BASE_URL}/sessions", headers=headers)
    print_response(response)
    
    if response.status_code == 200:
        print(f"✓ Sessions retrieved successfully")
        data = response.json()
        sessions = data.get("sessions", [])
        print(f"Total sessions for this user: {len(sessions)}")
        return sessions
    else:
        print(f"✗ Get sessions failed")
        return []


def test_unauthorized_access():
    """Test accessing protected routes without authentication."""
    print_section("7. Testing Unauthorized Access (No Token)")
    
    # Try to get profile without token
    print("Attempting to access /auth/profile without token...")
    response = requests.get(f"{BASE_URL}/auth/profile")
    print_response(response)
    
    assert response.status_code == 401, "Should return 401 Unauthorized"
    print("✓ Correctly rejected unauthorized request")
    
    # Try to create session without token
    print("\nAttempting to create session without token...")
    payload = {
        "role": "Developer",
        "level": "Mid",
        "interview_type": "technical",
        "max_questions": 3,
        "llm_provider": "groq"
    }
    response = requests.post(f"{BASE_URL}/sessions", json=payload)
    print_response(response)
    
    assert response.status_code == 401, "Should return 401 Unauthorized"
    print("✓ Correctly rejected unauthorized request")


def test_invalid_token():
    """Test accessing protected routes with invalid token."""
    print_section("8. Testing Invalid Token")
    
    headers = {
        "Authorization": "Bearer invalid_token_here"
    }
    
    print(f"Request headers:\n{json.dumps(headers, indent=2)}")
    
    response = requests.get(f"{BASE_URL}/auth/profile", headers=headers)
    print_response(response)
    
    assert response.status_code == 401, "Should return 401 Unauthorized for invalid token"
    print("✓ Correctly rejected invalid token")


def test_wrong_password(email: str):
    """Test login with wrong password."""
    print_section("9. Testing Wrong Password")
    
    payload = {
        "email": email,
        "password": "wrong_password_123"
    }
    
    print(f"Request payload:\n{json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{BASE_URL}/auth/login", json=payload)
    print_response(response)
    
    assert response.status_code == 401, "Should return 401 Unauthorized for wrong password"
    print("✓ Correctly rejected wrong password")


def test_duplicate_registration(email: str, password: str, full_name: str):
    """Test registering with an email that already exists."""
    print_section("10. Testing Duplicate Registration")
    
    payload = {
        "email": email,
        "password": password,
        "full_name": full_name
    }
    
    print(f"Request payload:\n{json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{BASE_URL}/auth/register", json=payload)
    print_response(response)
    
    assert response.status_code == 400, "Should return 400 Bad Request for duplicate email"
    assert "already registered" in response.json().get("detail", "").lower()
    print("✓ Correctly rejected duplicate registration")


def run_all_tests():
    """Run all authentication tests."""
    print("\n" + "="*60)
    print("  AUTHENTICATION API TEST SUITE")
    print("="*60)
    print(f"Testing API at: {BASE_URL}")
    
    # Test user credentials
    test_email = "test_user@example.com"
    test_password = "SecurePass123!"
    test_full_name = "Test User"
    
    try:
        # Test 1: Health check
        test_health_check()
        
        # Test 2: Register user
        user_id, token = test_register_user(test_email, test_password, test_full_name)
        
        # If registration failed due to existing user, login instead
        if not token:
            token = test_login_user(test_email, test_password)
        
        # Test 3: Get profile
        profile = test_get_profile(token)
        
        # Test 4: Create session with auth
        session_id = test_create_session_with_auth(token)
        
        # Test 5: Get user sessions
        sessions = test_get_sessions_with_auth(token)
        
        # Test 6: Unauthorized access
        test_unauthorized_access()
        
        # Test 7: Invalid token
        test_invalid_token()
        
        # Test 8: Wrong password
        test_wrong_password(test_email)
        
        # Test 9: Duplicate registration
        test_duplicate_registration(test_email, test_password, test_full_name)
        
        # Summary
        print_section("TEST SUMMARY")
        print("✓ All authentication tests passed!")
        print(f"✓ User Email: {test_email}")
        print(f"✓ Token received and validated")
        print(f"✓ Protected routes working correctly")
        print(f"✓ Authorization checks working")
        
        return True
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {str(e)}")
        return False
    except requests.exceptions.ConnectionError:
        print(f"\n✗ Connection failed. Is the backend running at {BASE_URL}?")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
