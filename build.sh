#!/usr/bin/env bash
# Render build script
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Seed the database on first deploy (SQLite is created in instance/)
python seed_data.py
