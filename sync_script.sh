#!/bin/bash

# Usage: ./sync_script.sh "Commit message"

if [ -z "$1" ]; then
    echo "Please provide a commit message."
    exit 1
fi

COMMIT_MESSAGE="$1"

# Repositories to synchronize
GITHUB_REMOTE="origin"
CODEBERG_REMOTE="codeberg"

# Commit changes

git add .
git commit -m "$COMMIT_MESSAGE"

echo "✅ Commit created with message: $COMMIT_MESSAGE"

# Push to GitHub

echo "🚀 Pushing to GitHub..."
git push $GITHUB_REMOTE main

echo "✅ Push to GitHub completed."

# Push to Codeberg

echo "🚀 Pushing to Codeberg..."
git push $CODEBERG_REMOTE main

echo "✅ Push to Codeberg completed."

# Push to Radicle

echo "🚀 Pushing to Radicle..."
rad push

echo "✅ Push to Radicle completed."

echo "🎉 Synchronization complete!"
