import pytest
from fastapi import HTTPException, UploadFile

from app.modules.payments.receipt_validator import validate_receipt


@pytest.mark.anyio
async def test_rejects_spoofed_file() -> None:
    from io import BytesIO

    upload = UploadFile(
        filename="fraude.pdf",
        file=BytesIO(b"not a pdf"),
        headers={"content-type": "application/pdf"},
    )
    with pytest.raises(HTTPException) as error:
        await validate_receipt(upload, 5)
    assert error.value.status_code == 415
