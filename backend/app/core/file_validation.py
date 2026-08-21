from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

ALLOWED_EXTENSIONS: set[str] = {
    "jpg", "jpeg", "png", "gif", "bmp", "svg", "webp",
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "rtf",
    "zip", "rar", "7z", "tar", "gz",
    "mp4", "avi", "mkv", "mov", "webm",
    "mp3", "wav", "ogg", "flac",
    "txt", "csv", "json", "xml", "log", "md",
    "py", "js", "ts", "java", "cpp", "c", "h", "html", "css", "php",
}

MIME_TYPES: dict[str, set[str]] = {
    "jpg": {"image/jpeg"}, "jpeg": {"image/jpeg"}, "png": {"image/png"},
    "gif": {"image/gif"}, "bmp": {"image/bmp", "image/x-ms-bmp"},
    "svg": {"image/svg+xml"}, "webp": {"image/webp"},
    "pdf": {"application/pdf"}, "doc": {"application/msword"},
    "docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    "xls": {"application/vnd.ms-excel"},
    "xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    "ppt": {"application/vnd.ms-powerpoint"},
    "pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    "odt": {"application/vnd.oasis.opendocument.text"}, "rtf": {"application/rtf", "text/rtf"},
    "zip": {"application/zip"}, "rar": {"application/vnd.rar", "application/x-rar"},
    "7z": {"application/x-7z-compressed"}, "tar": {"application/x-tar"},
    "gz": {"application/gzip", "application/x-gzip"},
    "mp4": {"video/mp4"}, "avi": {"video/x-msvideo"}, "mkv": {"video/x-matroska"},
    "mov": {"video/quicktime"}, "webm": {"video/webm"},
    "mp3": {"audio/mpeg"}, "wav": {"audio/wav", "audio/x-wav"},
    "ogg": {"audio/ogg"}, "flac": {"audio/flac", "audio/x-flac"},
    "txt": {"text/plain"}, "csv": {"text/plain", "text/csv"},
    "json": {"application/json", "text/plain"}, "xml": {"application/xml", "text/xml", "text/plain"},
    "log": {"text/plain"}, "md": {"text/markdown", "text/plain"},
    "py": {"text/x-python", "text/plain"}, "js": {"text/javascript", "application/javascript", "text/plain"},
    "ts": {"text/plain", "text/typescript"}, "java": {"text/x-java", "text/plain"},
    "cpp": {"text/x-c++", "text/plain"}, "c": {"text/x-c", "text/plain"},
    "h": {"text/x-c", "text/plain"}, "html": {"text/html", "text/plain"},
    "css": {"text/css", "text/plain"}, "php": {"text/x-php", "text/plain"},
}


def extension_for(filename: str) -> str:
    extension = Path(filename).suffix.lower().lstrip(".")
    if not extension or extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Формат файла не поддерживается")
    return extension


def detect_mime(content: bytes) -> str:
    try:
        import magic
    except ImportError as exc:
        raise RuntimeError("Установите python-magic и libmagic для проверки MIME") from exc
    return magic.from_buffer(content[:1024], mime=True)


def detect_office_mime(extension: str, content: bytes, mime_type: str) -> str:
    office_types = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "odt": "application/vnd.oasis.opendocument.text",
    }
    office_markers = {
        "docx": "wordprocessingml",
        "xlsx": "spreadsheetml",
        "pptx": "presentationml",
        "odt": "opendocument",
    }
    if extension not in office_types or mime_type != "application/zip":
        return mime_type
    try:
        with ZipFile(BytesIO(content)) as archive:
            content_types = archive.read("[Content_Types].xml").decode("utf-8", errors="ignore")
    except (BadZipFile, KeyError, UnicodeDecodeError):
        return mime_type
    return office_types[extension] if office_markers[extension] in content_types else mime_type


def validate_mime(extension: str, mime_type: str, content: bytes = b"") -> str:
    detected_type = detect_office_mime(extension, content, mime_type)
    if detected_type not in MIME_TYPES[extension]:
        raise ValueError("MIME-тип не соответствует расширению")
    return detected_type
