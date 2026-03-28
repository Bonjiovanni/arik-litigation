#!/bin/bash
cd "/c/Users/arika/OneDrive/CLaude Cowork/audio_pipeline"
echo "Running format_utils tests..."
"C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/test_format_utils.py -v
echo ""
echo "Running full test suite..."
"C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe" -m pytest -v
