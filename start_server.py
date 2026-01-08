#!/usr/bin/env python
"""
Start script for FAIX Chatbot
Handles virtual environment activation, Ollama check, and Django server startup
"""
import os
import sys
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path

def check_ollama_running():
    """Check if Ollama is running on localhost:11434"""
    try:
        req = urllib.request.Request('http://localhost:11434/api/tags')
        urllib.request.urlopen(req, timeout=2)
        return True
    except (urllib.error.URLError, OSError):
        return False

def start_ollama():
    """Start Ollama server in background"""
    print("[2/3] Starting Ollama server...")
    try:
        if sys.platform == 'win32':
            subprocess.Popen(['ollama', 'serve'], 
                          creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(['ollama', 'serve'], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
        
        # Wait for Ollama to start
        max_wait = 30
        waited = 0
        while not check_ollama_running() and waited < max_wait:
            time.sleep(2)
            waited += 2
            print(".", end="", flush=True)
        print()
        
        if check_ollama_running():
            print("✓ Ollama is running")
            return True
        else:
            print("⚠ Warning: Ollama may not have started")
            return False
    except FileNotFoundError:
        print("⚠ ERROR: Ollama not found in PATH")
        print("   Please install Ollama from https://ollama.ai")
        return False

def main():
    print("=" * 50)
    print("FAIX Chatbot - Starting Server")
    print("=" * 50)
    print()
    
    # Check virtual environment
    venv_python = Path('venv') / 'Scripts' / 'python.exe' if sys.platform == 'win32' else Path('venv') / 'bin' / 'python'
    if not venv_python.exists():
        print("ERROR: Virtual environment not found!")
        print("Please create it first: python -m venv venv")
        sys.exit(1)
    
    print("[1/3] Virtual environment found")
    
    # Check Ollama
    print("[2/3] Checking Ollama service...")
    if not check_ollama_running():
        if not start_ollama():
            print("⚠ Continuing without Ollama (LLM features will be disabled)")
    else:
        print("✓ Ollama is already running")
    
    # Start Django server
    print("[3/3] Starting Django development server...")
    print()
    print("=" * 50)
    print("Server starting at http://0.0.0.0:8000")
    print("Access from this device: http://localhost:8000 or http://127.0.0.1:8000")
    print("Access from other devices: http://<your-ip-address>:8000")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    print()
    
    # Run Django server using venv Python (bind to 0.0.0.0 for network access)
    try:
        subprocess.run([str(venv_python), 'manage.py', 'runserver', '0.0.0.0:8000'], check=True)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        sys.exit(0)

if __name__ == '__main__':
    main()