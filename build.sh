#!/bin/bash
echo "Building Frontend..."
cd frontend
npm install
npm run build
cd ..

echo "Installing Backend dependencies..."
pip install -r requirements.txt
