#!/usr/bin/env bash
# Run uvicorn with proxy disabled to ensure LAN access is not intercepted.
export http_proxy=
export https_proxy=
export HTTP_PROXY=
export HTTPS_PROXY=

source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 10102
