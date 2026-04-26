from fastapi.testclient import TestClient


def test_create_and_list_races(client: TestClient, race_payload: dict[str, str]) -> None:
    create_response = client.post("/api/v1/races/", json=race_payload)
    assert create_response.status_code == 201

    list_response = client.get("/api/v1/races/")
    assert list_response.status_code == 200

    payload = list_response.json()
    assert len(payload) == 1
    assert payload[0]["name"] == race_payload["name"]
    assert payload[0]["status"] == "scheduled"


def test_update_race_status(client: TestClient, race_payload: dict[str, str]) -> None:
    create_response = client.post("/api/v1/races/", json=race_payload)
    race_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/races/{race_id}/status",
        json={"status": "live"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "live"
