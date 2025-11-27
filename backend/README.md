# GTO Backend (FastAPI)

Local venv setup:
```
cd backend/server
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 10102
```

Target server:
- Host: `192.168.100.100`
- Port: `10102`

Docker alternative (if you want to containerize after swapping in a real solver):
```
cd backend/server
docker build -t txhm-gto:latest .
docker run --rm -p 10102:8000 txhm-gto:latest  # adjust CMD/port if you change uvicorn args
```

Notes:
- `solver_cfr.py` implements a simplified CFR solver for all streets using a single bet size and no raises. It samples villain hands and runouts each iteration. Extend the bet tree/abstractions as needed for richer GTO coverage.
- Update the Android app base URL to point to `http://192.168.100.100:10102`.
