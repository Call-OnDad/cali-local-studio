#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/runtime${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
exec .venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8780 --no-access-log
