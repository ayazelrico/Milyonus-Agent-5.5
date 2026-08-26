---
name: fastapi
description: FastAPI ile async Python web API'leri kurma
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
    category: gelistirme
    requires_toolsets:
    - terminal
    provenance: official
---

# FastAPI

## Minimal uygulama
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
        raise HTTPException(404, "yok")
    return {"id": item_id}

@app.post("/items")
async def create(item: Item):
    return item
```

## Çalıştır
```bash
uvicorn main:app --reload            # geliştirme
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4   # üretim
```
- Otomatik dokümanlar: `/docs` (Swagger), `/redoc`.

## Desenler
- **Pydantic** modelleri doğrulama + serileştirme sağlar; `response_model=` ile çıktıyı sınırla.
- **Dependency injection:** `def dep(): ...` + `Depends(dep)` — auth, DB oturumu paylaş.
- **Async:** I/O için `async def`; bloklayan işi `run_in_threadpool` ile sar.
- **Router:** büyük app'i `APIRouter` ile böl, `app.include_router(...)`.
- **Middleware / CORS:** `app.add_middleware(CORSMiddleware, ...)`.

## Üretim
- Gunicorn + uvicorn worker; önünde nginx reverse proxy.
- Yapılandırmayı ortam değişkeninden oku (pydantic-settings).
