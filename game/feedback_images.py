"""Decode bounded feedback screenshots and strip untrusted image metadata.

Bytes are stored in PostgreSQL by player_feedback, never in a release directory.
Only reencoded, single-frame raster images are served to the player/operator.
"""
from __future__ import annotations

import base64
import binascii
import io
import threading
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGES = 3
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_IMAGE_PIXELS = 12_600_000  # Includes 4032x3024 phone photos and 4K screenshots.
MAX_IMAGE_SIDE = 10_000
MAX_BASE64 = 4 * ((MAX_IMAGE_BYTES + 2) // 3)
MAX_BODY = MAX_IMAGES * (MAX_BASE64 + 64) + 64 * 1024
FORMATS = {'image/png': 'PNG', 'image/jpeg': 'JPEG', 'image/webp': 'WEBP'}
_DECODE_GATE = threading.BoundedSemaphore(1)  # Each worker decodes one submission; never queue large bodies.


class ImageUploadError(ValueError):
    def __init__(self, message: str, code: str = 'bad_images', status: int = 400):
        super().__init__(message)
        self.code, self.status = code, status


def decode_images(values) -> list[dict]:
    if not isinstance(values, list) or len(values) > MAX_IMAGES:
        raise ImageUploadError('Mỗi góp ý được gửi tối đa 3 ảnh.')
    if not values:
        return []
    if not _DECODE_GATE.acquire(blocking=False):
        raise ImageUploadError('Máy chủ đang xử lý ảnh. Góp ý vẫn còn, bạn thử gửi lại sau một lát nhé.', 'image_busy', 503)
    try:
        return [_decode(value) for value in values]
    finally:
        _DECODE_GATE.release()


def _decode(value) -> dict:
    invalid = 'Ảnh không hợp lệ. Chọn ảnh PNG, JPG hoặc WebP tĩnh.'
    too_large = 'Mỗi ảnh tối đa 2 MB, 12,6 triệu điểm ảnh và 10.000 điểm mỗi chiều.'
    if not isinstance(value, str) or len(value) > MAX_BASE64 + 32:
        raise ImageUploadError(too_large if isinstance(value, str) else invalid)
    header, sep, encoded = value.partition(',')
    mime = next((mime for mime in FORMATS if header == 'data:' + mime + ';base64'), None)
    if not mime or not sep or not encoded or len(encoded) > MAX_BASE64:
        raise ImageUploadError(invalid)
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise ImageUploadError(invalid) from None
    if len(raw) > MAX_IMAGE_BYTES:
        raise ImageUploadError(too_large)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw), formats=list(FORMATS.values())) as source:
                if source.format != FORMATS[mime] or getattr(source, 'n_frames', 1) != 1:
                    raise ImageUploadError(invalid)
                width, height = source.size
                if not (0 < width <= MAX_IMAGE_SIDE and 0 < height <= MAX_IMAGE_SIDE) or width * height > MAX_IMAGE_PIXELS:
                    raise ImageUploadError(too_large)
                source.verify()
            with Image.open(io.BytesIO(raw), formats=list(FORMATS.values())) as source:
                source.load()
                # In-place orientation avoids an unconditional full-image copy.
                ImageOps.exif_transpose(source, in_place=True)
                mode = 'RGBA' if mime != 'image/jpeg' and ('A' in source.getbands() or 'transparency' in source.info) else 'RGB'
                clean = source if source.mode == mode else source.convert(mode)
                # Save only decoded pixels. No EXIF, text chunks, profiles or trailing bytes.
                clean.info.clear()
                output = io.BytesIO()
                options = {'quality': 90} if mime != 'image/png' else {}
                clean.save(output, FORMATS[mime], **options)
                binary = output.getvalue()
                width, height = clean.size
                if clean is not source:
                    clean.close()
    except ImageUploadError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ImageUploadError(invalid) from None
    if len(binary) > MAX_IMAGE_BYTES:
        raise ImageUploadError('Ảnh sau khi xử lý vượt 2 MB. Hãy chọn ảnh nhỏ hơn.')
    return dict(data=binary, mime=mime, width=width, height=height, size=len(binary))
