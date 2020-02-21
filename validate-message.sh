#!/bin/bash

set -eo pipefail

BASE="origin/master"
MAGIC="Changes were validated by"

LOG_OUTPUT=$(git log '--format=format:%b' "$BASE"..HEAD)

if [[ -z "$LOG_OUTPUT" ]]
then
  exit 0
else
  if (echo "$LOG_OUTPUT" | grep "$MAGIC")
  then
    exit 0
  else
    echo "No commit message found in this PR matching commit template."
    echo "To add a commit message, please run:"
    echo ""
    echo "  git commit --allow-empty --squash HEAD -t .gitmessage"
    echo ""
    exit 1
  fi
fi
