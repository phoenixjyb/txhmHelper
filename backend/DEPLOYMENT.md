# GTO Server Deployment Guide

Target host/port: `192.168.100.100:10102`

## 1) Prerequisites
- Python 3.10+ on the server (GPU box with 4090 recommended)
- Git access to this repo
- (Optional) Docker if you want a containerized deployment

## 2) Venv deployment (recommended for quick bring-up)
```bash
ssh user@192.168.100.100
cd /path/to/txhmHelper/backend/server
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 10102
```
Run uvicorn under a process manager (systemd/supervisor) for persistence.

Proxy bypass (if local proxies interfere): use the provided script which clears proxy env vars:
```
./start.sh
```

Systemd sample (`/etc/systemd/system/txhm-gto.service`):
```
[Unit]
Description=TXHM GTO API
After=network.target

[Service]
User=YOURUSER
WorkingDirectory=/path/to/txhmHelper/backend/server
ExecStart=/path/to/txhmHelper/backend/server/start.sh
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```
Then:
```
sudo systemctl daemon-reload
sudo systemctl enable --now txhm-gto
sudo systemctl status txhm-gto
```

## 3) Docker deployment (optional)
```bash
cd backend/server
docker build -t txhm-gto:latest .
docker run --rm -p 10102:8000 txhm-gto:latest \
  uvicorn main:app --host 0.0.0.0 --port 8000
```
Adjust port mapping or uvicorn args as needed.

## 4) API
- Health: `GET /health` -> `{ "status": "ok" }`
- Solve: `POST /solve`
  - Body: `{ "stage": "flop|turn|river|preflop", "hole": ["As","Kd"], "board": ["Jh","Td","2c"], "pot": 10.0, "effective_stack": 100.0, "bet_sizing": [0.33, 0.5, 1.0] }`
  - Returns: `{ "strategy": { "check": 0.42, "bet": 0.58 }, "note": "Strategy from simplified CFR solver (single bet size, no raises)." }`

## 5) Solver notes
- `solver_cfr.py` runs Monte Carlo CFR across streets with a single bet size and no raises. It samples villain hands and runouts to the river. This is a simplified solver, not full-scale GTO; extend the bet tree/abstractions for richer play.
- Tune iterations/sampling in `solve_cfr` for speed vs. quality (defaults: ~3000 iterations, ~4000 villain samples).
- Consider adding hand/board bucketing and multiple bet sizes for stronger strategies, leveraging the 4090.

## 6) Client config
- Android app base URL is `http://192.168.100.100:10102/` via BuildConfig. Ensure the server is reachable from the device (same network or proper routing).
