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

The repository includes a ready-to-install unit for the current server at
`backend/server/txhm-gto.service`. It runs as `converge` from
`/home/converge/data/yanbo/txhmHelper`. Install it with:
```
sudo install -m 644 backend/server/txhm-gto.service /etc/systemd/system/txhm-gto.service
```

For another host, update the user and paths in the unit. The equivalent unit is:
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
  - Returns: `{ "strategy": { "check": 0.42, "bet_33": 0.18, "bet_50": 0.40 }, "note": "Strategy from chance-sampled CFR in a heads-up, one-street abstraction (no raises)." }`

### v1 queued heads-up postflop solve

`POST /v1/solve` starts a bounded CFR+ job and returns `202 Accepted`. Poll
`GET /v1/solve/{job_id}` until `status` is `complete` or `failed`. Identical
requests reuse the in-memory cached job result.

Example payload:
```json
{
  "stage": "flop",
  "hole": ["As", "Kd"],
  "board": ["Jh", "Td", "2c"],
  "pot": 10.0,
  "effective_stack": 100.0,
  "hero_position": "oop",
  "action_history": [],
  "villain_range": [{ "cards": ["Qs", "Qd"], "weight": 1.0 }],
  "bet_sizing": [0.33, 0.5, 1.0],
  "raise_sizing": [0.75, 1.5],
  "raise_cap": 1,
  "rake_pct": 0.05,
  "rake_cap": 3.0,
  "iterations": 5000
}
```

The Hero must be the next player to act. `hero_position: "ip"` is therefore
valid only after the out-of-position opponent has acted (for example,
`action_history: ["check"]`).

## 5) Solver notes
- The compatibility endpoint (`/solve`) runs the original chance-sampled one-street CFR game.
- `/v1/solve` runs CFR+ in a stronger, still-bounded heads-up postflop game: weighted villain range, IP/OOP, action history, multiple bet sizes, one capped raise, and rake inputs. Unknown runouts are sampled to river; subsequent-street decisions are not yet modeled.
- The server is CPU-only today. Its health response reports `gpu_accelerated: false`; do not label it GPU accelerated until a CUDA evaluator and benchmarks are deployed.
- Run `python -m unittest -v test_solver_cfr.py test_solver_v2.py test_api_v1.py` before deployment. Benchmark the iteration count on the 4090 server before exposing longer solves to the app.

## 6) Client config
- Android app base URL is `http://192.168.100.100:10102/` via BuildConfig. Ensure the server is reachable from the device (same network or proper routing).
