"""Read-plane FastAPI app (dashboard API). No approve/execute endpoints (ADR-0001/0002)."""

from fastapi import FastAPI

app = FastAPI(title="ZeroMind (read plane)")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "plane": "read"}
