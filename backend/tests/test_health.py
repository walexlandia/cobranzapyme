from fastapi.testclient import TestClient


def test_health_and_release_version(client: TestClient) -> None:
    live = client.get("/health/live")
    ready = client.get("/health/ready")
    version = client.get("/health/version")

    assert live.status_code == 200 and live.json() == {"status": "ok"}
    assert ready.status_code == 200 and ready.json() == {"status": "ready"}
    assert version.status_code == 200
    assert version.json()["version"] == "0.8.4"
    assert version.json()["database_migration_head"] == "0015"
