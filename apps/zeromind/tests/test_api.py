from fastapi.testclient import TestClient

from zeromind.api.main import app


def test_health_reports_read_plane() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "plane": "read"}


def test_read_plane_exposes_no_approve_or_execute_routes() -> None:
    paths = {getattr(route, "path", "") for route in app.routes}
    assert not [p for p in paths if "approve" in p or "execute" in p or "order" in p]
