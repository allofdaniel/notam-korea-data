#!/usr/bin/env python3
"""
Test Gemini NOTAM Interpretation API
"""
import requests
import json

API_URL = "http://3.27.240.67:8000/api/translate"

# Sample NOTAM text from the database
test_notam = {
    "text": "RWY 14R/32L CLSD DUE TO MAINTENANCE WORK.\nAD AVBL ON RWY 14L/32R ONLY.",
    "context": {
        "airport": "RKSS",
        "notam_number": "A0002/25"
    }
}

print("Testing Gemini NOTAM Interpretation...")
print(f"NOTAM: {test_notam['text']}")
print("\nCalling API...")

response = requests.post(API_URL, json=test_notam, timeout=60)

print(f"\nStatus Code: {response.status_code}")
print("\nResponse:")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
