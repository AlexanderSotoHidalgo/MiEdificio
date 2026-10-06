import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.models import PaymentAllocation, PaymentReport, PaymentStatus, Receipt

PDF = b"%PDF-1.4\n% valid test\n%%EOF"


def report(client, headers, fee_id: int, amount: str = "40.00", key: str = "payment-test-key"):
    return client.post(
        "/api/v1/payments/report",
        headers={**headers, "Idempotency-Key": key},
        data={
            "amount": amount,
            "payment_date": date.today().isoformat(),
            "operation_number": key,
            "allocations": json.dumps([{"fee_id": fee_id, "amount": amount}]),
        },
        files={"receipt": (f"{key}.pdf", PDF + key.encode(), "application/pdf")},
    )


def test_partial_payment_and_idempotency(
    client, resident_headers, admin_headers, sample_data
) -> None:
    first = report(client, resident_headers, sample_data["fee"])
    second = report(client, resident_headers, sample_data["fee"])
    assert first.status_code == 201, first.text
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    approved = client.post(
        f"/api/v1/payments/{first.json()['id']}/review",
        json={"action": "approve"},
        headers=admin_headers,
    )
    assert approved.status_code == 200, approved.text
    account = client.get("/api/v1/fees/my-account", headers=resident_headers).json()
    fee = next(item for item in account if item["id"] == sample_data["fee"])
    assert Decimal(fee["paid_amount"]) == Decimal("40.00")
    assert Decimal(fee["balance"]) == Decimal("60.00")


def test_receipt_idor(client, resident_headers, other_headers, sample_data) -> None:
    created = report(client, resident_headers, sample_data["fee"], key="idor-payment-key")
    assert created.status_code == 201
    forbidden = client.get(
        f"/api/v1/payments/{created.json()['id']}/receipt", headers=other_headers
    )
    assert forbidden.status_code == 403


def test_concurrent_approval_applies_once(
    client, resident_headers, admin_headers, sample_data, db_session_factory
) -> None:
    created = report(
        client, resident_headers, sample_data["fee"], amount="100.00", key="concurrent-key"
    )
    payment_id = created.json()["id"]

    def approve():
        return client.post(
            f"/api/v1/payments/{payment_id}/review",
            json={"action": "approve"},
            headers=admin_headers,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: approve(), range(2)))
    assert [response.status_code for response in responses] == [200, 200]
    assert sum(bool(response.json()["idempotent"]) for response in responses) == 1
    with db_session_factory() as db:
        assert (
            db.scalar(select(func.count(Receipt.id)).where(Receipt.payment_report_id == payment_id))
            == 1
        )
        report_row = db.get(PaymentReport, payment_id)
        assert report_row.status == PaymentStatus.APPROVED
        assert db.scalar(
            select(func.sum(PaymentAllocation.amount)).where(
                PaymentAllocation.payment_report_id == payment_id
            )
        ) == Decimal("100.00")
