"""
Test script to check if multiple downloads happen at backend level
"""
import requests
import json
import time

# Test data
test_request = {
    "youtube_url": "https://www.youtube.com/watch?v=Uqb0PD9srbA",
    "segments": [
        {
            "start_time": "00:02:55",
            "end_time": "00:03:10"
        }
    ],
    "project_name": "Debug Test",
    "resolution": "720p"
}

print("=" * 80)
print("🧪 Testing Backend - Checking for Multiple Downloads")
print("=" * 80)

# Send request
print("\n📤 Sending request to backend...")
response = requests.post("http://localhost:8000/api/process", json=test_request)

if response.status_code == 200:
    data = response.json()
    project_id = data['project_id']
    print(f"✅ Request accepted! Project ID: {project_id}")
    
    # Poll status
    print("\n📊 Polling status...")
    while True:
        status_response = requests.get(f"http://localhost:8000/api/status/{project_id}")
        status_data = status_response.json()
        
        status = status_data['status']
        message = status_data.get('message', '')
        
        print(f"   Status: {status} - {message}")
        
        if status in ['completed', 'error']:
            break
        
        time.sleep(2)
    
    print("\n" + "=" * 80)
    if status == 'completed':
        print("✅ Test COMPLETED!")
        print(f"Output files: {status_data.get('output', [])}")
    else:
        print(f"❌ Test FAILED: {message}")
    print("=" * 80)
    
else:
    print(f"❌ Request failed: {response.status_code}")
    print(response.text)

print("\n💡 Check the backend terminal logs above.")
print("   Count how many times you see '[download]' lines.")
print("   Should only see 1 download session!")
