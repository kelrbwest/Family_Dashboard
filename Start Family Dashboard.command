#!/bin/bash
# Family Age Dashboard — macOS launcher
# Double-click this file to start the dashboard.

# Go to the folder this script lives in
cd "$(dirname "$0")"

echo ""
echo "========================================="
echo "   West Family Dashboard"
echo "========================================="
echo ""

# Check Python is available
if ! command -v python3 &>/dev/null; then
  echo "ERROR: Python 3 is not installed."
  echo ""
  echo "Please install it from https://www.python.org/downloads/"
  echo "Then double-click this file again."
  echo ""
  read -p "Press Enter to close..."
  exit 1
fi

echo "Checking dependencies..."
python3 -m pip install -r requirements.txt -q

echo "Starting the dashboard..."
echo ""
echo "Opening http://localhost:5000 in your browser."
echo "Close this window to stop the dashboard."
echo ""

# Open browser after a short pause for Flask to start
(sleep 2 && open "http://localhost:8080") &

# Start Flask
python3 app.py
