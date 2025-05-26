# -*- coding: utf-8 -*-
import json
import time
from app.api import routes as api_routes # Import the routes module to access analysis_status

def reset_analysis_status():
    """Helper function to reset the global analysis_status for test isolation."""
    api_routes.analysis_status = {
        "running": False,
        "progress": 0,
        "message": "尚未開始",
        "last_run_time": None,
        "last_run_success": True,
        "error_message": "",
        "output_files": []
    }

def test_index_page(client):
    reset_analysis_status() # Ensure clean state
    """Test the index page loads correctly."""
    response = client.get('/')
    assert response.status_code == 200
    assert "Starlink 台北衛星覆蓋分析中心" in response.data.decode('utf-8')

def test_analysis_status_api(client):
    reset_analysis_status() # Ensure clean state
    """Test the /analysis_status API endpoint."""
    response = client.get('/analysis_status')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "running" in data
    assert "progress" in data
    assert "message" in data
    assert not data["running"] # Initially, no analysis should be running

def test_start_analysis_api_valid(client):
    reset_analysis_status() # Ensure clean state
    """Test starting an analysis with valid duration."""
    response = client.post('/start_analysis', json={'duration': 10})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert data["message"] == "分析已啟動"

    # Check status - should be running now
    time.sleep(0.1) # Give a moment for the thread to potentially start
    status_response = client.get('/analysis_status')
    status_data = json.loads(status_response.data)
    assert status_data["running"] == True
    assert isinstance(status_data["message"], str)
    # It's hard to reliably test the full completion in an automated integration test
    # without extensive mocking or very long test durations.
    # For now, we confirm it started. The analysis thread itself uses subprocess.

def test_start_analysis_api_invalid_duration_type(client):
    reset_analysis_status() # Ensure clean state
    """Test starting an analysis with invalid duration type."""
    response = client.post('/start_analysis', json={'duration': 'not-a-number'})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert data["message"] == "無效的分析時間"

def test_start_analysis_api_invalid_duration_range_too_low(client):
    reset_analysis_status() # Ensure clean state
    """Test starting an analysis with duration too low."""
    response = client.post('/start_analysis', json={'duration': 1})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert data["message"] == "分析時間需介於5到240分鐘之間"

def test_start_analysis_api_invalid_duration_range_too_high(client):
    reset_analysis_status() # Ensure clean state
    """Test starting an analysis with duration too high."""
    response = client.post('/start_analysis', json={'duration': 300})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert data["message"] == "分析時間需介於5到240分鐘之間"

def test_start_analysis_api_already_running(client):
    reset_analysis_status() # Ensure clean state
    """Test starting an analysis when one is already running."""
    # Start one analysis
    client.post('/start_analysis', json={'duration': 5}) 
    time.sleep(0.1) # Give it a moment to register as running

    # Try to start another one
    response = client.post('/start_analysis', json={'duration': 5})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert data["message"] == "分析已在進行中"
    
    # Clean up: wait for the dummy analysis to finish to not affect other tests.
    # This is tricky because the analysis runs in a separate thread using subprocess.
    # For true isolation, tests involving `run_analysis_thread` might need mocking `subprocess.Popen`.
    # For now, let's assume a short duration might finish or be in a state where subsequent tests are not impacted.
    # A better approach for CI would be to mock out the actual analysis script call.
    # Let's check the status until it's no longer running, with a timeout.
    timeout_seconds = 15 # Max wait time for the 5-min (simulated) analysis to clear
    start_wait_time = time.time()
    while True:
        status_response = client.get('/analysis_status')
        status_data = json.loads(status_response.data)
        if not status_data["running"]:
            break
        if time.time() - start_wait_time > timeout_seconds:
            print("Warning: Analysis did not complete in cleanup phase of test_start_analysis_api_already_running.")
            # Force reset status if timeout occurs to prevent test leakage
            reset_analysis_status()
            break
        time.sleep(0.5)
    reset_analysis_status() # Final reset after loop

# More tests can be added for other routes or specific behaviors. 