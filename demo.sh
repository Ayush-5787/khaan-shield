#!/usr/bin/env bash
set -e
python -m pytest tests/ -v
python -m src.main