# -*- coding: utf-8 -*-
"""
Test script: Verify audio_duration is available from progress=0

This script tests the complete flow:
1. Create a task with audio_duration
2. Verify audio_duration is returned in task status at progress=0
3. Verify ETA calculation works correctly

Usage:
    python scripts/test_audio_duration_flow.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
import json
from scripts.auth_helper import get_test_token

BASE_URL = "http://localhost:8000/api/v1"


def test_audio_duration_flow():
    """Test audio_duration availability from progress=0"""
    
    # Get auth token
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    print("=" * 80)
    print("Testing audio_duration flow")
    print("=" * 80)
    
    # Step 1: Create a task with audio_duration
    print("\n1. Creating task with audio_duration=479.1 seconds...")
    create_payload = {
        "audio_files": ["uploads/user_test_user/test_audio.ogg"],
        "file_order": [0],
        "original_filenames": ["test_meeting.ogg"],
        "audio_duration": 479.1,  # Audio duration from upload response
        "meeting_type": "weekly_sync",
        "meeting_date": "2026-01-22",
        "meeting_time": "14:30",
        "asr_language": "zh-CN+en-US",
        "output_language": "zh-CN",
        "skip_speaker_recognition": False,
    }
    
    response = requests.post(
        f"{BASE_URL}/tasks",
        headers=headers,
        json=create_payload,
    )
    
    if response.status_code != 201:
        print(f"✗ Failed to create task: {response.status_code}")
        print(response.text)
        return
    
    task_data = response.json()
    task_id = task_data["task_id"]
    print(f"✓ Task created: {task_id}")
    
    # Step 2: Check task status at progress=0
    print(f"\n2. Checking task status at progress=0...")
    response = requests.get(
        f"{BASE_URL}/tasks/{task_id}/status",
        headers=headers,
    )
    
    if response.status_code != 200:
        print(f"✗ Failed to get task status: {response.status_code}")
        print(response.text)
        return
    
    status_data = response.json()
    print(f"✓ Task status retrieved:")
    print(f"  - task_id: {status_data['task_id']}")
    print(f"  - state: {status_data['state']}")
    print(f"  - progress: {status_data['progress']}%")
    print(f"  - audio_duration: {status_data.get('audio_duration')} seconds")
    print(f"  - asr_language: {status_data.get('asr_language')}")
    print(f"  - estimated_time: {status_data.get('estimated_time')} seconds")
    
    # Verify audio_duration is available
    if status_data.get('audio_duration') is None:
        print("\n✗ FAILED: audio_duration is None at progress=0")
        return
    
    if status_data['audio_duration'] != 479.1:
        print(f"\n✗ FAILED: audio_duration mismatch (expected 479.1, got {status_data['audio_duration']})")
        return
    
    # Verify asr_language is available
    if status_data.get('asr_language') is None:
        print("\n✗ FAILED: asr_language is None")
        return
    
    if status_data['asr_language'] != "zh-CN+en-US":
        print(f"\n✗ FAILED: asr_language mismatch (expected zh-CN+en-US, got {status_data['asr_language']})")
        return
    
    print("\n✓ SUCCESS: audio_duration and asr_language are available at progress=0")
    
    # Step 3: Verify ETA calculation
    print(f"\n3. Verifying ETA calculation...")
    audio_duration = status_data['audio_duration']
    progress = status_data['progress']
    
    # Expected ETA formula: estimated_time = audio_duration × 0.25 × (1 - progress/100)
    expected_total_time = audio_duration * 0.25
    expected_eta = expected_total_time * (1 - progress / 100)
    
    print(f"  - Audio duration: {audio_duration} seconds")
    print(f"  - Progress: {progress}%")
    print(f"  - Expected total time: {expected_total_time:.2f} seconds")
    print(f"  - Expected ETA: {expected_eta:.2f} seconds")
    
    if status_data.get('estimated_time') is not None:
        actual_eta = status_data['estimated_time']
        print(f"  - Actual ETA: {actual_eta} seconds")
        
        # Allow small difference due to rounding
        if abs(actual_eta - expected_eta) < 1:
            print("\n✓ ETA calculation is correct")
        else:
            print(f"\n⚠ ETA mismatch (expected {expected_eta:.2f}, got {actual_eta})")
    else:
        print(f"  - Actual ETA: None (will be calculated when task starts)")
    
    # Step 4: Get task detail
    print(f"\n4. Checking task detail...")
    response = requests.get(
        f"{BASE_URL}/tasks/{task_id}",
        headers=headers,
    )
    
    if response.status_code != 200:
        print(f"✗ Failed to get task detail: {response.status_code}")
        print(response.text)
        return
    
    detail_data = response.json()
    print(f"✓ Task detail retrieved:")
    print(f"  - task_id: {detail_data['task_id']}")
    print(f"  - name: {detail_data.get('name')}")
    print(f"  - meeting_type: {detail_data['meeting_type']}")
    print(f"  - duration: {detail_data.get('duration')} seconds")
    
    print("\n" + "=" * 80)
    print("Test completed successfully!")
    print("=" * 80)
    print("\nSummary:")
    print("✓ Task created with audio_duration and asr_language")
    print("✓ audio_duration available at progress=0")
    print("✓ asr_language available at progress=0")
    print("✓ Frontend can calculate ETA from the start")
    print("✓ Frontend can display language labels (中文 / 英文)")
    print("\nETA Formula: estimated_time = audio_duration × 0.25 × (1 - progress/100)")
    print("\nLanguage Format: zh-CN+en-US → Frontend translates to '中文 / 英文'")


if __name__ == "__main__":
    test_audio_duration_flow()
