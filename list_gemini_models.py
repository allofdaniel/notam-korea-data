#!/usr/bin/env python3
"""
List available Gemini models
"""
import google.generativeai as genai

# API 키는 환경 변수에서 가져오세요
# export GEMINI_API_KEY=your_key_here
import os
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다")
genai.configure(api_key=GEMINI_API_KEY)

print("Available Gemini models:")
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"  - {model.name}")
        print(f"    Display name: {model.display_name}")
        print(f"    Supported: {model.supported_generation_methods}")
        print()
