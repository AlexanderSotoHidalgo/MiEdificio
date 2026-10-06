from datetime import date, timedelta
from decimal import Decimal

from app.models import FeeStatus
from app.modules.fees.service import calculate_fee_status


def test_calculate_all_fee_states() -> None:
    today = date.today()
    assert (
        calculate_fee_status(
            FeeStatus.PENDING, today, Decimal("100"), Decimal("100"), Decimal("0"), today
        )
        == "Pagada"
    )
    assert (
        calculate_fee_status(
            FeeStatus.PENDING, today, Decimal("100"), Decimal("0"), Decimal("20"), today
        )
        == "Pago en revisión"
    )
    assert (
        calculate_fee_status(
            FeeStatus.PENDING,
            today - timedelta(days=1),
            Decimal("100"),
            Decimal("0"),
            Decimal("0"),
            today,
        )
        == "Vencida"
    )
    assert (
        calculate_fee_status(
            FeeStatus.PENDING,
            today + timedelta(days=1),
            Decimal("100"),
            Decimal("0"),
            Decimal("0"),
            today,
        )
        == "Pendiente"
    )
    assert (
        calculate_fee_status(
            FeeStatus.CANCELLED, today, Decimal("100"), Decimal("0"), Decimal("0"), today
        )
        == "Anulada"
    )
