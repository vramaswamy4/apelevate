from pathlib import Path

from django.core.exceptions import ValidationError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024

# Extension -> the bytes a genuine file of that type starts with. Checking the content as well as
# the name stops a renamed .html or .exe from being accepted as a "PDF".
SIGNATURES = {
    ".pdf": b"%PDF-",
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
}


def validate_document(upload):
    ext = Path(upload.name).suffix.lower()
    if ext not in SIGNATURES:
        raise ValidationError("Upload a PDF, PNG or JPEG file.", code="file_type")
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError("Files must be 5 MB or smaller.", code="file_size")
    head = upload.read(len(SIGNATURES[ext]))
    upload.seek(0)
    if not head.startswith(SIGNATURES[ext]):
        raise ValidationError(
            "That file's contents don't match its extension.", code="file_content"
        )
