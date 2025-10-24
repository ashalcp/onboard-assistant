#!/bin/bash

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Get port from Azure environment variable or use default
PORT=${WEBSITES_PORT:-8000}
echo "Starting Streamlit on port $PORT..."

# Run Streamlit
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true