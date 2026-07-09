from fastapi.testclient import TestClient


def test_create_and_list_{{module_name}}(client: TestClient) -> None:
    create_response = client.post("/api/v1/{{module_name}}/", json={"name": "Main {{class_name}}"})
    assert create_response.status_code == 201

    list_response = client.get("/api/v1/{{module_name}}/")
    assert list_response.status_code == 200

    payload = list_response.json()
    assert len(payload) == 1
    assert payload[0]["name"] == "Main {{class_name}}"
