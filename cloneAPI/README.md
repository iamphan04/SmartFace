## SmartFace Fraud Engine

This optional API forwards profile and face checks to the main SmartFace API.

### Install

```bash
pip install -r requirements.txt
```

### Run Locally

```bash
set SMARTFACE_API_URL=http://127.0.0.1:8001
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8002
```

`SMARTFACE_API_URL` should point to the main `database_pdt/main.py` service.

### Endpoints

- `GET /health`
- `POST /verify`
- `POST /register`

### Architecture

```text
Frontend
  -> SmartFace API
  -> optional Fraud Engine
  -> System.db
```
