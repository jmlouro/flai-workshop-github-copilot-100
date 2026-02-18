"""
Tests for the High School Management System API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Reset to original state after test
    for name in activities:
        if name in original_activities:
            activities[name]["participants"] = original_activities[name]["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint"""
    
    def test_get_activities_returns_200(self, client):
        """Test that GET /activities returns 200 status"""
        response = client.get("/activities")
        assert response.status_code == 200
    
    def test_get_activities_returns_dict(self, client):
        """Test that GET /activities returns a dictionary"""
        response = client.get("/activities")
        data = response.json()
        assert isinstance(data, dict)
    
    def test_get_activities_has_expected_keys(self, client):
        """Test that activities have expected structure"""
        response = client.get("/activities")
        data = response.json()
        
        # Check that we have some activities
        assert len(data) > 0
        
        # Check first activity has expected keys
        first_activity = list(data.values())[0]
        assert "description" in first_activity
        assert "schedule" in first_activity
        assert "max_participants" in first_activity
        assert "participants" in first_activity
    
    def test_get_activities_contains_specific_activities(self, client):
        """Test that specific activities exist"""
        response = client.get("/activities")
        data = response.json()
        
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Basketball Team" in data


class TestSignupForActivity:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball Team/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        assert "Signed up test@mergington.edu for Basketball Team" in response.json()["message"]
    
    def test_signup_adds_participant(self, client):
        """Test that signup actually adds participant to activity"""
        email = "newstudent@mergington.edu"
        client.post(f"/activities/Soccer Club/signup?email={email}")
        
        # Verify participant was added
        response = client.get("/activities")
        data = response.json()
        assert email in data["Soccer Club"]["participants"]
    
    def test_signup_for_nonexistent_activity_returns_404(self, client):
        """Test signup for activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_duplicate_returns_400(self, client):
        """Test that signing up twice returns 400 error"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(
            f"/activities/Drama Club/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            f"/activities/Drama Club/signup?email={email}"
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
    
    def test_signup_with_special_characters_in_activity_name(self, client):
        """Test signup with URL-encoded activity names"""
        response = client.post(
            "/activities/Art%20Workshop/signup?email=artist@mergington.edu"
        )
        assert response.status_code == 200


class TestRemoveParticipant:
    """Tests for the DELETE /activities/{activity_name}/participants/{email} endpoint"""
    
    def test_remove_participant_success(self, client):
        """Test successful removal of a participant"""
        # First add a participant
        email = "toremove@mergington.edu"
        client.post(f"/activities/Science Club/signup?email={email}")
        
        # Then remove them
        response = client.delete(
            f"/activities/Science Club/participants/{email}"
        )
        assert response.status_code == 200
        assert f"Removed {email} from Science Club" in response.json()["message"]
    
    def test_remove_participant_actually_removes(self, client):
        """Test that participant is actually removed from activity"""
        email = "willberemoved@mergington.edu"
        
        # Add participant
        client.post(f"/activities/Math Olympiad/signup?email={email}")
        
        # Verify they're added
        response = client.get("/activities")
        assert email in response.json()["Math Olympiad"]["participants"]
        
        # Remove participant
        client.delete(f"/activities/Math Olympiad/participants/{email}")
        
        # Verify they're removed
        response = client.get("/activities")
        assert email not in response.json()["Math Olympiad"]["participants"]
    
    def test_remove_from_nonexistent_activity_returns_404(self, client):
        """Test removing participant from activity that doesn't exist"""
        response = client.delete(
            "/activities/Fake Club/participants/test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_remove_nonexistent_participant_returns_404(self, client):
        """Test removing participant who isn't in the activity"""
        response = client.delete(
            "/activities/Chess Club/participants/notmember@mergington.edu"
        )
        assert response.status_code == 404
        assert "Student not found" in response.json()["detail"]
    
    def test_remove_existing_participant(self, client):
        """Test removing a participant that was already in the activity"""
        # Chess Club has pre-existing participants
        response = client.delete(
            "/activities/Chess Club/participants/michael@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify removal
        activities_response = client.get("/activities")
        assert "michael@mergington.edu" not in activities_response.json()["Chess Club"]["participants"]


class TestIntegration:
    """Integration tests for multiple operations"""
    
    def test_signup_and_remove_workflow(self, client):
        """Test complete workflow of signing up and removing a participant"""
        email = "workflow@mergington.edu"
        activity = "Gym Class"
        
        # Initial state
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity]["participants"])
        
        # Signup
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify added
        after_signup = client.get("/activities")
        assert len(after_signup.json()[activity]["participants"]) == initial_count + 1
        assert email in after_signup.json()[activity]["participants"]
        
        # Remove
        remove_response = client.delete(
            f"/activities/{activity}/participants/{email}"
        )
        assert remove_response.status_code == 200
        
        # Verify removed
        after_remove = client.get("/activities")
        assert len(after_remove.json()[activity]["participants"]) == initial_count
        assert email not in after_remove.json()[activity]["participants"]
    
    def test_multiple_activities_signup(self, client):
        """Test signing up for multiple activities"""
        email = "multitasker@mergington.edu"
        activities_to_join = ["Basketball Team", "Drama Club", "Chess Club"]
        
        for activity in activities_to_join:
            response = client.post(
                f"/activities/{activity}/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify participant is in all activities
        all_activities = client.get("/activities").json()
        for activity in activities_to_join:
            assert email in all_activities[activity]["participants"]
