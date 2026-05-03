from pdf2image import convert_from_path
from PIL import Image
import os
from models import User
from flask import Flask, abort, request,g
from werkzeug.utils import secure_filename
from functools import wraps
from dateutil import parser
import uuid
from itsdangerous import SignatureExpired, BadSignature, TimestampSigner
from models import FamilyGroupMember, Tree, FamilyGroup


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


def user_can_access_tree(user, tree: Tree) -> bool:
    """
    Tree access is granted via the tree's family group's membership.
    If a tree has no family_group (legacy / personal), only the owner can access it.
    """
    if tree is None:
        return False

    if tree.family_group_id is None:
        return tree.owner_id == user.id

    return (
        FamilyGroupMember.select()
        .where(
            (FamilyGroupMember.family_group == tree.family_group)
            & (FamilyGroupMember.user == user)
        )
        .exists()
    )


def get_accessible_tree_ids(user) -> set:
    """Return the set of tree IDs the user can access (via group membership or direct ownership)."""
    member_group_ids = [
        m.family_group_id
        for m in FamilyGroupMember.select().where(FamilyGroupMember.user == user)
    ]
    group_tree_ids = [
        t.id for t in Tree.select().where(Tree.family_group.in_(member_group_ids))
    ] if member_group_ids else []
    owned_tree_ids = [
        t.id for t in Tree.select().where((Tree.owner == user) & Tree.family_group.is_null())
    ]
    return set(group_tree_ids + owned_tree_ids)


def require_tree_access(tree_id_param: str = "tree_id"):
    """Decorator factory: loads Tree from URL kwarg and checks membership."""

    def decorator(func):
        @wraps(func)
        @require_auth
        def inner(*args, **kwargs):
            tree_id = kwargs.get(tree_id_param)
            try:
                tree = Tree.get(Tree.id == int(tree_id))
            except Exception:
                abort(404)

            if not user_can_access_tree(g.user, tree):
                abort(403)

            g.tree = tree
            return func(*args, **kwargs)

        return inner

    return decorator


FAMILY_GROUP_ROLE_ORDER = {
    "viewer": 1,
    "editor": 2,
    "owner": 3,
}


def get_family_group_membership(user, family_group: FamilyGroup):
    return FamilyGroupMember.get_or_none(
        (FamilyGroupMember.family_group == family_group) & (FamilyGroupMember.user == user)
    )


def user_family_group_role(user, family_group: FamilyGroup):
    membership = get_family_group_membership(user, family_group)
    return membership.role if membership else None


def user_has_family_group_role_at_least(user, family_group: FamilyGroup, required_role: str) -> bool:
    role = user_family_group_role(user, family_group)
    if not role:
        return False
    return FAMILY_GROUP_ROLE_ORDER.get(role, 0) >= FAMILY_GROUP_ROLE_ORDER.get(required_role, 999)