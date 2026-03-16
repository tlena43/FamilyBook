from pdf2image import convert_from_path
from PIL import Image
import os
from models import Privacy, User
from flask import Flask, abort, request,g
from werkzeug.utils import secure_filename
from functools import wraps
from dateutil import parser
import uuid
from itsdangerous import SignatureExpired, BadSignature, TimestampSigner


def makeCachedUpload(app, filename):
    cFilepath = os.path.join(app.config['CACHE_FOLDER'], filename)
    if not os.path.isfile(cFilepath):
        uFilenameParts = filename.rsplit('.', 1)[0].rsplit('_', 2)
        uFilename = '.'.join(uFilenameParts[0:2])
        uFilepath = os.path.join(app.config['UPLOAD_FOLDER'], uFilename)
        filetype = uFilename.rsplit('.', 1)[-1].lower()
        if filetype == 'pdf':
            pageNum = 1
            if (len(uFilenameParts) > 2):
                pageNum = int(uFilenameParts[2])
            pages = convert_from_path(uFilepath, dpi=150, jpegopt={"progressive": True, "optimize": True})
            pages[pageNum-1].save(cFilepath, quality=35)
        if filetype == 'jpg' or filetype == 'jpeg' or filetype == 'png':
            img = Image.open(uFilepath)
            if filetype == 'png':
                img = img.convert('RGB')
            img.save(cFilepath, "JPEG", quality=35, optimize=True, progressive=True)
            
SECRET_KEY = os.getenv("secretKey")
if not SECRET_KEY:
    raise RuntimeError("secretKey environment variable is not set")

ADMIN_PRIVACY_LEVEL = "admin"
FAMILY_PRIVACY_LEVEL = "family"
AUTH_HEADER_NAME = "X-api-key"
TOKEN_MAX_AGE_SECONDS = 7 * 24 * 3600

ALLOWED_UPLOAD_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "pdf",
    "doc",
    "docx",
    "odt",
    "txt",
}

signer = TimestampSigner(SECRET_KEY)

def get_admin_privacy():
    return Privacy.get(Privacy.level == ADMIN_PRIVACY_LEVEL)


def get_family_privacy():
    return Privacy.get(Privacy.level == FAMILY_PRIVACY_LEVEL)


def is_admin(user):
    return getattr(user.privacy, "level", None) == ADMIN_PRIVACY_LEVEL


def is_blank(value):
    return value in (None, "")


def parse_optional_int(value, default=None):
    if is_blank(value):
        return default
    return int(value)


def parse_optional_str(value):
    if is_blank(value):
        return None
    return str(value).strip() or None


def parse_optional_date(value):
    if is_blank(value):
        return None
    return parser.parse(value)


def require_json_body():
    if not request.is_json:
        abort(400, description="Request must be JSON.")


def require_fields(data, required_fields):
    missing = [field for field in required_fields if field not in data]
    if missing:
        abort(400, description=f"Missing required fields: {', '.join(missing)}")


def get_json_or_400(required_fields=None):
    require_json_body()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, description="Invalid JSON body.")
    if required_fields:
        require_fields(data, required_fields)
    return data


def get_upload_extension(filename):
    if "." not in filename:
        return None
    return filename.rsplit(".", 1)[1].lower()


def build_upload_filename(original_filename):
    safe_name = secure_filename(original_filename.lower())
    extension = get_upload_extension(safe_name)
    if not extension:
        abort(400, description="Invalid filename.")
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        abort(415, description="Unsupported file type.")
    return f"{uuid.uuid4().hex}.{extension}"


def serialize_person_summary(person, living_birthday_allowed):
    return {
        "id": person.id,
        "firstName": person.firstName,
        "middleName": person.middleName,
        "lastName": person.lastName,
        "birthDay": (
            str(person.birthDay)
            if person.isDead or living_birthday_allowed
            else "not_allowed"
        ),
        "birthDateUnknowns": person.birthDateUnknowns,
        "fileName": person.file.filename if person.file else None,
    }


def serialize_content_summary(content):
    return {
        "id": content.id,
        "title": content.title,
        "fileName": content.file.filename if content.file else None,
    }


def require_auth(func):
    @wraps(func)
    def inner(*args, **kwargs):
        api_key = request.headers.get(AUTH_HEADER_NAME)
        if not api_key:
            abort(401)

        try:
            user_id = int(
                signer.unsign(
                    api_key.encode("utf8"),
                    max_age=TOKEN_MAX_AGE_SECONDS,
                ).decode("utf8")
            )
            g.user = User.get(User.id == user_id)
        except (SignatureExpired, BadSignature, User.DoesNotExist, ValueError):
            abort(401)

        return func(*args, **kwargs)

    return inner


def require_admin(func):
    @wraps(func)
    @require_auth
    def inner(*args, **kwargs):
        if not is_admin(g.user):
            abort(403)
        return func(*args, **kwargs)

    return inner