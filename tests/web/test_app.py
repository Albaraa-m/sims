from fastapi.testclient import TestClient

from web.app import create_app


class HealthTests:
    def test_health_returns_ok(self):
        response = TestClient(create_app()).get("/api/health")

        assert response.json() == {"status": "ok"}
