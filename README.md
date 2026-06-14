# SmartFace

SmartFace now uses one FastAPI server and one SQLite database:

- `frontend`: React/Vite interface
- `database_pdt/main.py`: unified API and static frontend server
- `database_pdt/System.db`: primary database
- `cloneAPI/fraud_engine.py`: fraud score and risk decision logic

## Run

For the first installation, run:

```powershell
.\install-python.bat
```

This creates `.venv-smartface312` with the pinned Python dependencies used
by MediaPipe, OpenCV, pyzbar, and FastAPI.

Double-click `start.bat`, or run:

```powershell
npm run build
npm start
```

Open `http://localhost:8000`.

## Development

Run the backend:

```powershell
npm run dev:backend
```

Run Vite in a second terminal:

```powershell
npm run dev:frontend
```

Vite proxies `/api` to `http://127.0.0.1:8000`.

API documentation is available at `http://localhost:8000/docs`.

## Camera API

- `GET /health`: FastAPI, database, frontend, and camera status
- `GET /api/camera/stream`: MJPEG stream used by the React frontend
- `POST /api/camera/start` and `/api/camera/stop`: camera lifecycle
- `POST /api/face/start/{student_id}?purpose=register|verify`: run `pdt_face.py`
- `GET /api/face/status`: face capture progress
- `POST /api/face/verify/{student_id}`: verify the server-captured face
- `POST /api/qr/start`: run `pdt_QR.py`
- `GET /api/qr/status`: QR scan status and result
- `POST /api/qr/verify/{student_id}`: compare QR value with the selected student
