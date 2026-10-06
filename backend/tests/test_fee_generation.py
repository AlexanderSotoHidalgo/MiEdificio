from datetime import date, timedelta


def test_batch_generation_is_idempotent(client, admin_headers) -> None:
    period = (date.today().replace(day=1) - timedelta(days=2)).replace(day=1)
    payload = {
        "period": period.isoformat(),
        "due_date": (period + timedelta(days=14)).isoformat(),
        "concept_code": "ORDINARIA",
        "calculation": "fixed",
        "amount": "120.00",
    }
    first = client.post("/api/v1/fees/batch", json=payload, headers=admin_headers)
    second = client.post("/api/v1/fees/batch", json=payload, headers=admin_headers)
    assert first.status_code == 201, first.text
    assert first.json()["created"] == 2
    assert second.status_code == 201
    assert second.json()["created"] == 0
    assert len(second.json()["skipped"]) == 2
