from fastapi.testclient import TestClient


def test_health_and_release_version(client: TestClient) -> None:
    live = client.get("/health/live")
    ready = client.get("/health/ready")
    version = client.get("/health/version")

    assert live.status_code == 200 and live.json() == {"status": "ok"}
    assert live.headers["x-request-id"]
    assert live.headers["x-content-type-options"] == "nosniff"
    assert live.headers["x-frame-options"] == "DENY"
    assert live.headers["referrer-policy"] == "no-referrer"
    assert ready.status_code == 200 and ready.json() == {"status": "ready"}
    assert version.status_code == 200
    assert version.json()["version"] == "0.8.4"
    assert version.json()["database_migration_head"] == "0016"
