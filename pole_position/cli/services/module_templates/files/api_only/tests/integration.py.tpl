from fastapi.testclient import TestClient


def test_describe_{{module_name}}(client: TestClient) -> None:
    response = client.get("/api/v1/{{module_name}}/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "{{module_name}}",
        "message": "{{class_name}} API is ready.",
    }


def test_handle_{{module_name}}(client: TestClient) -> None:
    response = client.post("/api/v1/{{module_name}}/", json={"name": "Ada"})

    assert response.status_code == 200
    assert response.json() == {
        "name": "Ada",
        "message": "Ada was handled by {{module_name}}.",
    }
