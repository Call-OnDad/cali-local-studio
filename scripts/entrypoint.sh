#!/bin/sh
set -eu
if [ "${STUDIO_DOWNLOAD_MODELS:-1}" = 1 ]; then
 python scripts/setup_assets.py models
fi
exec python -m uvicorn app:app --host 0.0.0.0 --port 8780 --no-access-log
