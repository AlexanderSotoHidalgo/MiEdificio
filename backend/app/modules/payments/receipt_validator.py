from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from fastapi import HTTPException, UploadFile

SIGNATURES = {
    "application/pdf": (b"%PDF-", ".pdf"),
    "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
    "image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
}


@dataclass(frozen=True)
class ValidatedReceipt:
    content: bytes
    content_type: str
    extension: str
    size: int
    sha256: str
    original_filename: str


def detect_content_type(content: bytes) -> tuple[str, str] | None:
    for content_type, (signature, extension) in SIGNATURES.items():
        if content.startswith(signature):
            return content_type, extension
    if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


async def validate_receipt(upload: UploadFile, max_mb: int) -> ValidatedReceipt:
    content = await upload.read(max_mb * 1024 * 1024 + 1)
    await upload.close()
    if not content:
        raise HTTPException(status_code=422, detail="El comprobante está vacío")
    if len(content) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"El comprobante supera {max_mb} MB")
    detected = detect_content_type(content)
    if detected is None:
        raise HTTPException(status_code=415, detail="Use un archivo PDF, JPG, PNG o WEBP válido")
    content_type, extension = detected
    return ValidatedReceipt(
        content=content,
        content_type=content_type,
        extension=extension,
        size=len(content),
        sha256=sha256(content).hexdigest(),
        original_filename=Path(upload.filename or f"comprobante{extension}").name[:255],
    )
