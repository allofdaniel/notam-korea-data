#!/usr/bin/env python3
"""
List available Gemini models
"""
import google.generativeai as genai

GEMINI_API_KEY = 'AIzaSyA7zE8nqLkNcSXjHPX9AVOZues3BsNczbA'
genai.configure(api_key=GEMINI_API_KEY)

print("Available Gemini models:")
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"  - {model.name}")
        print(f"    Display name: {model.display_name}")
        print(f"    Supported: {model.supported_generation_methods}")
        print()
