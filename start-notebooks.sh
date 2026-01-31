#!/bin/bash
# Start both Marimo notebooks on different ports

# Start first notebook in background using python -m to avoid shebang issues
python -m marimo run notebooks/01_template_vs_ib_analysis.py \
    --host 127.0.0.1 \
    --port 2719 \
    --no-token &

# Start second notebook in background
python -m marimo run notebooks/02_country_compliance_analysis.py \
    --host 127.0.0.1 \
    --port 2720 \
    --no-token &

# Wait for both processes
wait
