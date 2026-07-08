#!/bin/zsh
cd /Users/niftez/Coding/Steam-Market-Pulse
source venv/bin/activate
mkdir -p logs
python src/ingestion/collect_snapshots.py >> logs/snapshot_collection.log 2>&1