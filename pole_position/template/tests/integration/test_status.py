from fastapi.testclient import TestClient


def test_status(client: TestClient) -> None:
    response = client.get("/api/v1/status")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "{{project_name}}"
    assert payload["environment"] == "test"
    assert isinstance(payload["uptime_seconds"], int)
