---
name: fastapi
description: Build async Python web APIs with FastAPI
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - python
    - fastapi
    - api
    - web
    category: development
    requires_toolsets:
    - terminal
    provenance: official
---

# FastAPI
## Minimal app
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float

@app.get("/items/{item_id}")
async def read(item_id: int):
    if item_id < 1:
        raise HTTPException(404, "not found")
    return {"id": item_id}

@app.post("/items")
async def create(item: Item):
    return item
```
## Run
```bash
uvicorn main:app --reload            # development
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4   # production
```
- Auto docs: `/docs` (Swagger), `/redoc`.
## Patterns
- **Pydantic** models give validation + serialization; limit output with `response_model=`.
- **Dependency injection:** `def dep(): ...` + `Depends(dep)` — share auth, DB session.
- **Async:** use `async def` for I/O; wrap blocking work with `run_in_threadpool`.
- **Router:** split large apps with `APIRouter`, `app.include_router(...)`.
- **Middleware / CORS:** `app.add_middleware(CORSMiddleware, ...)`.
## Production
- Gunicorn + uvicorn workers; nginx reverse proxy in front.
- Read config from the environment (pydantic-settings).
