#!/bin/bash

# COOL RAG Backend Start Script

echo "🚀 Starting COOL RAG Backend..."

# Ensure we're in the backend directory
cd "$(dirname "$0")"

# Start uvicorn with hot reload
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
