#!/usr/bin/env bash
# Render build script
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Safe idempotent seed: only populates data if database is empty
python seed_data.py
