#!/bin/bash
# Simple script to push changes to GitHub

# Configure git if needed
if [ -z "$(git config --get user.name)" ]; then
  echo "Setting up git configuration..."
  git config --global user.name "Soufian Carson"
  git config --global user.email "your-email@example.com"
fi

# Add all changes
echo "Adding all changes..."
git add .

# Commit changes
echo "Committing changes..."
git commit -m "Integrate Grafana dashboard with SKMA-FON monitoring system"

# Push to GitHub
echo "Pushing to GitHub..."
git push

# Check status
if [ $? -eq 0 ]; then
  echo "✅ Successfully pushed changes to GitHub!"
else
  echo "❌ Failed to push changes."
  echo "You might need to:"
  echo "1. Check your GitHub credentials"
  echo "2. Make sure you have permissions to push to this repository"
  echo "3. Check if you need to pull changes first with 'git pull'"
fi