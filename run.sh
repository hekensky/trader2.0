#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ "$1" = "bot" ]; then
  python3 -m app.bot
elif [ "$1" = "web" ]; then
  python3 -m app.web_app
else
  echo "Usage: ./run.sh bot|web"
fi
