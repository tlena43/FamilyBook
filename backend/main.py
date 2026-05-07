import os
from datetime import datetime
from collections import defaultdict

import bcrypt
import peewee
from dotenv import load_dotenv
from flask import Flask, abort, g, request, send_from_directory
from flask_compress import Compress
from flask_restful import Api, Resource
from flask_cors import CORS
from pdf2image import convert_from_path

from models import *
from utilities import *
from familyTree import *

try:
    from pyswip import Prolog
except Exception:
    Prolog = None
    
"""
Contains all of the setup to run the app
The API endpoints
And any necessary backend logic
"""


# =====================================================
# App setup
# =====================================================

APP_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(APP_DIR, ".env"))

UPLOAD_FOLDER = os.path.join(APP_DIR, "upload")
CACHE_FOLDER = os.path.join(UPLOAD_FOLDER, "cache")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CACHE_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["CACHE_FOLDER"] = CACHE_FOLDER

CORS(
    app,
    origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://192.168.1.173:3000"],
    supports_credentials=True,
    allow_headers=["Content-Type", AUTH_HEADER_NAME],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)

Compress(app)
api = Api(app)

# Do not initialize Prolog at import time. PySwip can hard-crash the backend if
# the local SWI-Prolog/PySwip versions are incompatible.
prolog_engine = None


# =====================================================
# General helpers
# =====================================================

def generate_share_code():
    import secrets
    import string

    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        if not User.get_or_none(User.share_code == code):
            return code


def normalize_share_code(value):
    return (value or "").strip().upper()


def person_summary(person):
    # Current utility signature requires living_birthday_allowed.
    return serialize_person_summary(person)


def serialize_user_account(user):
    return {
        "id": user.id,
        "username": user.username,
        "isOwner": user.id == g.user.id,
    }


def privacy_allows(item):
    # Privacy hierarchy was removed from User. Account/tree access now controls visibility.
    return True


# =====================================================
# Tree / family-group access helpers
# =====================================================

def get_accessible_tree_ids(user):
    """
    Trees visible to user:
    - trees they own
    - trees whose family_group the user belongs to
    - legacy trees with no family_group owned by them
    """
    tree_ids = set()

    if "Tree" not in globals():
        return []

    for tree in Tree.select().where(Tree.owner == user):
        tree_ids.add(tree.id)

    if "FamilyGroupMember" in globals():
        memberships = FamilyGroupMember.select().where(FamilyGroupMember.user == user)
        group_ids = [m.family_group.id for m in memberships]

        if group_ids:
            for tree in Tree.select().where(Tree.family_group.in_(group_ids)):
                tree_ids.add(tree.id)

    return list(tree_ids)


def user_can_view_tree(user, tree):
    if tree is None:
        return False

    if getattr(tree, "owner_id", None) == user.id:
        return True

    if getattr(tree, "family_group_id", None) is None:
        return False

    if "FamilyGroupMember" not in globals():
        return False

    return FamilyGroupMember.select().where(
        (FamilyGroupMember.family_group == tree.family_group) &
        (FamilyGroupMember.user == user)
    ).exists()


def user_can_edit_tree(user, tree):
    if tree is None:
        return False

    if getattr(tree, "owner_id", None) == user.id:
        return True

    if getattr(tree, "family_group_id", None) is None:
        return False

    if "FamilyGroupMember" not in globals():
        return False

    membership = FamilyGroupMember.get_or_none(
        (FamilyGroupMember.family_group == tree.family_group) &
        (FamilyGroupMember.user == user)
    )

    return bool(membership and membership.role in ("owner", "editor"))


def user_can_view_person(user, person):
    return person.user_id == user.id


def user_can_view_content(user, content):
    return content.user_id == user.id


def get_accessible_person_or_404(person_id):
    person = Person.get_or_none(Person.id == person_id)
    if not person:
        abort(404)

    if not user_can_view_person(g.user, person):
        abort(403)

    return person


def get_owned_person_or_404(person_id):
    person = Person.get_or_none((Person.id == person_id) & (Person.user == g.user))
    if not person:
        abort(404)
    return person


def get_accessible_content_or_404(content_id):
    content = Content.get_or_none(Content.id == content_id)
    if not content:
        abort(404)

    if not user_can_view_content(g.user, content):
        abort(403)

    return content


def get_owned_content_or_404(content_id):
    content = Content.get_or_none((Content.id == content_id) & (Content.user == g.user))
    if not content:
        abort(404)
    return content


def get_owned_upload_or_404(filename):
    upload = Upload.get_or_none((Upload.filename == filename) & (Upload.owner == g.user))
    if not upload:
        abort(404)
    return upload


def parse_owned_person_id(value):
    person_id = parse_optional_int(value)
    if not person_id:
        return None

    person = Person.get_or_none((Person.id == person_id) & (Person.user == g.user))
    if not person:
        abort(400, description="Referenced person must belong to your account.")

    return person.id


def parse_owned_upload_id(value):
    upload_id = parse_optional_int(value)
    if not upload_id:
        return None

    upload = Upload.get_or_none((Upload.id == upload_id) & (Upload.owner == g.user))
    if not upload:
        abort(400, description="Referenced upload must belong to your account.")

    return upload.id


def parse_owned_or_editable_tree_id(value, default=None):
    tree_id = parse_optional_int(value, default=default)
    if not tree_id:
        return None

    tree = Tree.get_or_none(Tree.id == tree_id)
    if not tree:
        abort(400, description="Tree not found.")

    if not user_can_edit_tree(g.user, tree):
        abort(403, description="You do not have permission to edit this tree.")

    return tree.id


def get_default_tree_for_user(user):
    if "Tree" not in globals():
        return None

    tree = Tree.select().where(Tree.owner == user).order_by(Tree.id).first()
    return tree


def get_first_owned_tree(user):
    return (
        Tree
        .select()
        .where(Tree.owner == user)
        .order_by(Tree.id)
        .first()
    )

# =====================================================
# Request lifecycle
# =====================================================

@app.before_request
def before_request():
    if db.is_closed():
        db.connect()


@app.teardown_request
def teardown_request(exception=None):
    if not db.is_closed():
        db.close()


# =====================================================
# Auth
# =====================================================

class CheckLoginEndpoint(Resource):
    @require_auth
    def get(self):
        return {"userName": g.user.username, "userId": g.user.id}, 200


api.add_resource(CheckLoginEndpoint, "/loginCheck")


class LoginEndpoint(Resource):
    def post(self):
        data = get_json_or_400(required_fields=["username", "password"])
        user = User.get_or_none(User.username == data["username"])

        if not user:
            abort(401)

        if not bcrypt.checkpw(data["password"].encode("utf8"), user.password.encode("utf8")):
            abort(401)

        return {
            "key": signer.sign(str(user.id)).decode("utf8"),
            "username": user.username,
            "userId": user.id,
        }, 200


api.add_resource(LoginEndpoint, "/login")


class SignupEndpoint(Resource):
    def post(self):
        data = get_json_or_400(required_fields=["username", "password", "passwordConfirm"])

        username = data["username"].strip()
        password = data["password"]
        password_confirm = data["passwordConfirm"]

        if not username or len(username) < 3:
            abort(400, description="Username must be at least 3 characters long.")
        if not password or len(password) < 6:
            abort(400, description="Password must be at least 6 characters long.")
        if password != password_confirm:
            abort(400, description="Passwords do not match.")
        if User.get_or_none(User.username == username):
            abort(400, description="Username already exists.")

        hashed_password = bcrypt.hashpw(password.encode("utf8"), bcrypt.gensalt()).decode("utf8")

        with db.atomic():
            new_user = User.create(
                username=username,
                password=hashed_password,
                share_code=generate_share_code(),
            )

            # Create family-group/tree structure for new accounts if models exist.
            if "FamilyGroup" in globals() and "FamilyGroupMember" in globals() and "Tree" in globals():
                group = FamilyGroup.create(name=f"{username}'s Family", owner=new_user)
                FamilyGroupMember.create(family_group=group, user=new_user, role="owner")
                Tree.create(name=f"{username}'s Tree", owner=new_user, family_group=group)

        return {
            "key": signer.sign(str(new_user.id)).decode("utf8"),
            "username": new_user.username,
            "userId": new_user.id,
            "message": "Account created successfully!",
        }, 201


api.add_resource(SignupEndpoint, "/signup")


# =====================================================
# Share code / legacy viewer access
# =====================================================

class MyShareCodeEndpoint(Resource):
    @require_auth
    def get(self):
        if not getattr(g.user, "share_code", None):
            g.user.share_code = generate_share_code()
            g.user.save()
        return {"shareCode": g.user.share_code}, 200

    @require_auth
    def post(self):
        g.user.share_code = generate_share_code()
        g.user.save()
        return {"shareCode": g.user.share_code}, 200


api.add_resource(MyShareCodeEndpoint, "/share-code")


class RedeemShareCodeEndpoint(Resource):
    @require_auth
    def post(self):
        data = get_json_or_400(required_fields=["shareCode"])
        code = normalize_share_code(data["shareCode"])

        if not code:
            abort(400, description="Share code is required.")

        owner = User.get_or_none(User.share_code == code)
        if not owner:
            abort(404, description="Invalid share code.")

        if owner.id == g.user.id:
            abort(400, description="You cannot redeem your own share code.")

        # Add user to ALL of owner's family groups as viewer
        groups = FamilyGroup.select().where(FamilyGroup.owner == owner)

        added_groups = []

        for group in groups:
            _, created = FamilyGroupMember.get_or_create(
                family_group=group,
                user=g.user,
                defaults={"role": "viewer"},
            )
            added_groups.append(group.id)

        return {
            "status": "access_granted",
            "owner": serialize_user_account(owner),
            "groupsJoined": added_groups,
        }, 201


api.add_resource(RedeemShareCodeEndpoint, "/share-code/redeem")


class SharedUsersEndpoint(Resource):
    @require_auth
    def get(self):
        users = {}

        memberships = (
            FamilyGroupMember
            .select(FamilyGroupMember, FamilyGroup, User)
            .join(FamilyGroup)
            .switch(FamilyGroupMember)
            .join(User)
            .where(FamilyGroupMember.user == g.user)
        )

        for m in memberships:
            owner = m.family_group.owner
            if owner.id != g.user.id:
                users[owner.id] = serialize_user_account(owner)

        return {"users": list(users.values())}, 200


api.add_resource(SharedUsersEndpoint, "/shared-users")


class MyViewersEndpoint(Resource):
    @require_auth
    def get(self):
        viewers = {}

        groups = FamilyGroup.select().where(FamilyGroup.owner == g.user)

        for group in groups:
            members = FamilyGroupMember.select().where(FamilyGroupMember.family_group == group)

            for m in members:
                if m.user.id != g.user.id:
                    viewers[m.user.id] = {
                        **serialize_user_account(m.user),
                        "role": m.role,
                        "groupId": group.id,
                        "groupName": group.name,
                    }

        return {"viewers": list(viewers.values())}, 200


api.add_resource(MyViewersEndpoint, "/my-viewers")


class RevokeViewerEndpoint(Resource):
    @require_auth
    def delete(self, viewer_id):
        groups = FamilyGroup.select().where(FamilyGroup.owner == g.user)

        deleted = 0

        for group in groups:
            deleted += FamilyGroupMember.delete().where(
                (FamilyGroupMember.family_group == group) &
                (FamilyGroupMember.user == int(viewer_id))
            ).execute()

        if not deleted:
            abort(404)

        return {"status": "access_revoked"}, 200


api.add_resource(RevokeViewerEndpoint, "/my-viewers/<int:viewer_id>")


# =====================================================
# Uploads
# =====================================================

class UploadEndpoint(Resource):
    @require_auth
    def post(self):
        upload = request.files.get("upload")
        if not upload or not upload.filename:
            abort(400, description="No upload provided.")

        unique_filename = build_upload_filename(upload.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
        upload.save(filepath)

        saved_upload = Upload.create(
            filename=unique_filename,
            timestamp=datetime.utcnow(),
            owner=g.user,
        )

        return {"filename": unique_filename, "fileid": saved_upload.id}, 201

    # Public so <img src="/upload/file.jpg"> works without custom auth headers.
    def get(self, filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @require_auth
    def delete(self, filename):
        upload = get_owned_upload_or_404(filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        try:
            upload.delete_instance()
            if os.path.isfile(filepath):
                os.remove(filepath)
        except peewee.IntegrityError:
            abort(409)

        return {"status": "deleted"}, 200


api.add_resource(UploadEndpoint, "/upload", "/upload/<string:filename>")


class CacheEndpoint(Resource):
    def get(self, filename):
        makeCachedUpload(app, filename)
        return send_from_directory(app.config["CACHE_FOLDER"], filename)


api.add_resource(CacheEndpoint, "/upload/cache/<string:filename>")


class PdfNumPagesEndpoint(Resource):
    @require_auth
    def get(self, filename):
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        if not os.path.isfile(filepath):
            abort(404)

        try:
            pages = convert_from_path(filepath)
        except Exception:
            abort(400, description="Could not process PDF.")

        return {"num_pages": len(pages)}, 200


api.add_resource(PdfNumPagesEndpoint, "/upload/num_pages/<string:filename>")


# =====================================================
# People
# =====================================================

class PersonEndpoint(Resource):
    @require_auth
    def post(self):
        data = get_json_or_400(required_fields=[
            "birthDay", "birthDateUnknowns", "deathDateUnknowns", "deathDay",
            "file", "birthplace", "parent1", "parent2", "spouse", "firstName",
            "lastName", "gender", "isDead", "middleName", "maidenName", "children"
        ])

        tree_id = parse_owned_or_editable_tree_id(data.get("tree"), default=None)
        if tree_id is None:
            default_tree = get_default_tree_for_user(g.user)
            tree_id = default_tree.id if default_tree else None

        person = Person.create(
            user=g.user,
            tree=tree_id,
            birthDay=parse_optional_date(data["birthDay"]),
            birthDateUnknowns=data["birthDateUnknowns"],
            deathDateUnknowns=data["deathDateUnknowns"],
            deathDay=parse_optional_date(data["deathDay"]),
            file=parse_owned_upload_id(data["file"]),
            birthplace=parse_optional_str(data["birthplace"]),
            parent1_id=parse_owned_person_id(data["parent1"]),
            parent2_id=parse_owned_person_id(data["parent2"]),
            spouse_id=parse_owned_person_id(data["spouse"]),
            firstName=data["firstName"],
            lastName=data["lastName"],
            gender=int(data["gender"]),
            isDead=data["isDead"],
            middleName=parse_optional_str(data["middleName"]),
            maidenName=parse_optional_str(data["maidenName"]),
        )

        spouse_id = parse_optional_int(data.get("spouse"))
        if spouse_id and spouse_id != person.id:
            spouse_person = Person.get_or_none((Person.id == spouse_id) & (Person.user == g.user))
            if spouse_person:
                spouse_person.spouse_id = person.id
                spouse_person.save()

        for child_id in data.get("children") or []:
            try:
                child_id = int(child_id)
            except (TypeError, ValueError):
                continue

            if child_id == person.id:
                continue

            child = Person.get_or_none((Person.id == child_id) & (Person.user == g.user))
            if not child:
                continue

            if not child.parent1_id:
                child.parent1_id = person.id
            elif not child.parent2_id:
                child.parent2_id = person.id
            else:
                continue

            child.save()

        return {"id": person.id}, 201

    @require_auth
    def get(self, id=None):
        if id is None:

            query = Person.select().where(
                (Person.user == g.user) 
            )

            return {
                "people": [person_summary(person) for person in query.iterator()]
            }, 200

        person = get_accessible_person_or_404(id)

        content_list = []
        for c in person.content:
            content = c.content
            if user_can_view_content(g.user, content):
                content_list.append({"id": content.id, "title": content.title})

        result = {
            "id": person.id,
            "ownerId": person.user.id,
            "ownerUsername": person.user.username,
            "canEdit": person.user.id == g.user.id,
            "firstName": person.firstName,
            "middleName": person.middleName,
            "lastName": person.lastName,
            "birthDay": str(person.birthDay),
            "birthDateUnknowns": person.birthDateUnknowns,
            "deathDay": str(person.deathDay),
            "deathDateUnknowns": person.deathDateUnknowns,
            "maidenName": person.maidenName,
            "birthplace": person.birthplace,
            "isDead": person.isDead,
            "content": content_list,
            "tree": person.tree_id,
            "gender": person.gender.id,
            "fileName": person.file.filename if person.file else None,
            "parent1": person_summary(person.parent1_id) if person.parent1_id and user_can_view_person(g.user, person.parent1_id) else None,
            "parent2": person_summary(person.parent2_id) if person.parent2_id and user_can_view_person(g.user, person.parent2_id) else None,
            "spouse": person_summary(person.spouse_id) if person.spouse_id and user_can_view_person(g.user, person.spouse_id) else None,
            "children": [
                person_summary(child)
                for child in Person.select().where(
                    (Person.tree == person.tree) &
                    ((Person.parent1_id == person) | (Person.parent2_id == person))
                )
                if user_can_view_person(g.user, child)
            ],
        }

        return result, 200

    @require_auth
    def patch(self, id):
        data = get_json_or_400(required_fields=[
            "birthDay", "birthDateUnknowns", "deathDateUnknowns", "deathDay",
            "file", "birthplace", "parent1", "parent2", "firstName", "lastName",
            "gender", "isDead", "middleName", "maidenName", "spouse", "children"
        ])

        id = int(id)
        existing_person = get_owned_person_or_404(id)

        file_value = parse_owned_upload_id(data["file"])
        if file_value is None:
            file_value = existing_person.file.id if existing_person.file else None

        tree_value = parse_owned_or_editable_tree_id(data.get("tree"), default=existing_person.tree_id)

        Person.update(
            tree=tree_value,
            birthDay=parse_optional_date(data["birthDay"]),
            birthDateUnknowns=data["birthDateUnknowns"],
            deathDateUnknowns=data["deathDateUnknowns"],
            deathDay=parse_optional_date(data["deathDay"]),
            file=file_value,
            birthplace=parse_optional_str(data["birthplace"]),
            parent1_id=parse_owned_person_id(data["parent1"]),
            parent2_id=parse_owned_person_id(data["parent2"]),
            firstName=data["firstName"],
            lastName=data["lastName"],
            gender=int(data["gender"]),
            isDead=data["isDead"],
            middleName=parse_optional_str(data["middleName"]),
            maidenName=parse_optional_str(data["maidenName"]),
            spouse_id=parse_owned_person_id(data["spouse"]),
        ).where((Person.id == id) & (Person.user == g.user)).execute()

        spouse_id = parse_optional_int(data.get("spouse"))
        if spouse_id and spouse_id != id:
            spouse_person = Person.get_or_none((Person.id == spouse_id) & (Person.user == g.user))
            if spouse_person:
                spouse_person.spouse_id = id
                spouse_person.save()

        for child_id in data.get("children") or []:
            try:
                child_id = int(child_id)
            except (TypeError, ValueError):
                continue

            if child_id == id:
                continue

            child = Person.get_or_none((Person.id == child_id) & (Person.user == g.user))
            if not child:
                continue

            if not child.parent1_id:
                child.parent1_id = id
            elif not child.parent2_id:
                child.parent2_id = id

            child.save()

        return {"id": id}, 200

    @require_auth
    def delete(self, id):
        person = get_owned_person_or_404(id)

        with db.atomic():
            Person_Content.delete().where(Person_Content.person == person).execute()
            Person.update(parent1_id=None).where(Person.parent1_id == person).execute()
            Person.update(parent2_id=None).where(Person.parent2_id == person).execute()
            Person.update(spouse_id=None).where(Person.spouse_id == person).execute()
            person.delete_instance()

        return {"status": "deleted"}, 200


api.add_resource(PersonEndpoint, "/person", "/person/<int:id>")


# =====================================================
# Content
# =====================================================

class ContentEndpoint(Resource):
    @require_auth
    def post(self):
        data = get_json_or_400(required_fields=[
            "type", "date", "notes", "title", "file", "location", "dateUnknowns", "people"
        ])

        file_id = parse_owned_upload_id(data["file"])
        if not file_id:
            abort(400, description="A file is required.")

        tree_id = parse_owned_or_editable_tree_id(data.get("tree"), default=None)
        if tree_id is None:
            default_tree = get_default_tree_for_user(g.user)
            tree_id = default_tree.id if default_tree else None

        content = Content.create(
            user=g.user,
            tree=tree_id,
            type=int(data["type"]) if data["type"] != 0 else None,
            date=parse_optional_date(data["date"]),
            notes=parse_optional_str(data["notes"]),
            title=data["title"],
            file=file_id,
            location=parse_optional_str(data["location"]),
            dateUnknowns=data["dateUnknowns"],
        )

        for item in data["people"]:
            person = Person.get_or_none((Person.id == item) & (Person.user == g.user))
            if not person:
                abort(400, description="Content can only be attached to people in your account.")
            Person_Content.create(content=content, person=person)

        return {"id": content.id}, 201

    @require_auth
    def get(self, id=None):
        if id is None:
            tree_ids = get_accessible_tree_ids(g.user)
            contents = Content.select().where(
                (Content.user == g.user) 
            )
            return {"content": [serialize_content_summary(c) for c in contents.iterator()]}, 200

        content = get_accessible_content_or_404(id)

        person_list = []
        for p in content.person:
            person = p.person
            if user_can_view_person(g.user, person):
                person_list.append(person_summary(person))

        return {
            "id": content.id,
            "ownerId": content.user.id,
            "ownerUsername": content.user.username,
            "canEdit": content.user.id == g.user.id,
            "title": content.title,
            "fileName": content.file.filename if content.file else None,
            "type": content.type.name if content.type is not None else None,
            "date": str(content.date),
            "dateUnknowns": content.dateUnknowns,
            "notes": content.notes,
            "location": content.location,
            "people": person_list,
            "tree": content.tree_id,
        }, 200

    @require_auth
    def patch(self, id):
        data = get_json_or_400(required_fields=[
            "type", "date", "notes", "title", "location", "dateUnknowns", "people"
        ])

        content = get_owned_content_or_404(id)
        tree_value = parse_owned_or_editable_tree_id(data.get("tree"), default=content.tree_id)

        Content.update(
            tree=tree_value,
            type=int(data["type"]) if data["type"] != 0 else None,
            date=parse_optional_date(data["date"]),
            notes=parse_optional_str(data["notes"]),
            title=data["title"],
            location=parse_optional_str(data["location"]),
            dateUnknowns=data["dateUnknowns"],
        ).where((Content.id == id) & (Content.user == g.user)).execute()

        Person_Content.delete().where(Person_Content.content == content).execute()
        for item in data["people"]:
            person = Person.get_or_none((Person.id == item) & (Person.user == g.user))
            if not person:
                abort(400, description="Content can only be attached to people in your account.")
            Person_Content.create(content=content, person=person)

        return {"id": id}, 200

    @require_auth
    def delete(self, id):
        content = get_owned_content_or_404(id)
        Person_Content.delete().where(Person_Content.content == content).execute()
        content.delete_instance()
        return {"status": "deleted"}, 200


api.add_resource(ContentEndpoint, "/content", "/content/<int:id>")


# =====================================================
# Gender
# =====================================================

class GenderEndpoint(Resource):
    def get(self):
        return {
            "genders": [
                {"id": gender.id, "name": gender.name}
                for gender in Gender.select().iterator()
            ]
        }, 200


api.add_resource(GenderEndpoint, "/gender")


# =====================================================
# Relationship / Prolog
# =====================================================

ALLOWED_RELATIONSHIPS = [
    "parent", "mother", "father", "child", "son", "daughter",
    "spouse", "partner", "husband", "wife", "sibling", "full_sibling", "half_sibling",
    "brother", "sister", "full_brother", "half_brother", "full_sister", "half_sister",
    "grandparent", "grandfather", "grandmother", "grandchild", "grandson", "granddaughter",
    "great_grandparent", "great_grandmother", "great_grandfather",
    "ancestor", "descendant", "pibling", "aunt", "uncle", "niece", "nephew",
    "cousin", "first_cousin", "second_cousin", "third_cousin",
    "parent_in_law", "mother_in_law", "father_in_law",
    "child_in_law", "son_in_law", "daughter_in_law",
    "sibling_in_law", "brother_in_law", "sister_in_law",
    "step_parent", "step_mother", "step_father", "step_child", "step_sibling",
]


def initialize_prolog():
    global prolog_engine

    if Prolog is None:
        prolog_engine = None
        print("WARNING: PySwip is not available. Relationship endpoints disabled.")
        return

    rules_file = os.path.abspath(os.path.join(APP_DIR, "prolog", "family_rules.pl"))

    if not os.path.exists(rules_file):
        prolog_engine = None
        print(f"WARNING: Prolog rules file not found at {rules_file}")
        return

    try:
        engine = Prolog()

        rules_file = rules_file.replace("\\", "/")  # normalize path

        list(engine.query(f"consult('{rules_file}')"))
        list(engine.query("true"))

        prolog_engine = engine
        print(f"DEBUG: Successfully loaded Prolog rules from {rules_file}")

    except Exception as e:
        prolog_engine = None
        print("WARNING: Prolog failed to initialize. Relationship endpoints disabled.")
        print(f"WARNING: Error: {e}")


def ensure_prolog_available():
    if prolog_engine is None:
        abort(503, description="Prolog engine is not available.")


def load_prolog_facts(owner_tree):
    ensure_prolog_available()

    try:
        list(prolog_engine.query("retractall(parent(_,_))"))
        list(prolog_engine.query("retractall(male(_))"))
        list(prolog_engine.query("retractall(female(_))"))
        list(prolog_engine.query("retractall(spouse(_,_))"))
    except Exception:
        pass

    for person in Person.select().where(Person.tree == owner_tree):
        if person.gender.name == "male":
            prolog_engine.assertz(f"male({person.id})")
        else:
            prolog_engine.assertz(f"female({person.id})")

        if person.parent1_id and person.parent1_id.tree_id == owner_tree.id:
            prolog_engine.assertz(f"parent({person.parent1_id.id}, {person.id})")
        if person.parent2_id and person.parent2_id.tree_id == owner_tree.id:
            prolog_engine.assertz(f"parent({person.parent2_id.id}, {person.id})")
        if person.spouse_id and person.spouse_id.tree_id == owner_tree.id:
            prolog_engine.assertz(f"spouse({person.id}, {person.spouse_id.id})")


class QueryRelationshipEndpoint(Resource):
    @require_auth
    def post(self):
        ensure_prolog_available()

        data = get_json_or_400(required_fields=["person1_id", "person2_id", "relationship"])
        person1_id = int(data["person1_id"])
        person2_id = int(data["person2_id"])
        relationship = (data["relationship"] or "").strip()

        person1 = get_accessible_person_or_404(person1_id)
        person2 = get_accessible_person_or_404(person2_id)

        if person1.tree_id is None or person1.tree_id != person2.tree_id:
            abort(400, description="Relationship queries must stay inside one tree.")

        if relationship != "all" and relationship not in set(ALLOWED_RELATIONSHIPS):
            abort(400, description="Unknown or unsupported relationship predicate.")

        load_prolog_facts(person1.tree)

        def is_undefined_predicate_error(exc):
            return "existence_error(procedure" in str(exc)

        try:
            if relationship == "all":
                true_relationships = []
                skipped_relationships = []

                for rel in ALLOWED_RELATIONSHIPS:
                    query = f"{rel}({person1_id}, {person2_id})"
                    try:
                        result = list(prolog_engine.query(query))
                    except Exception as e:
                        if is_undefined_predicate_error(e):
                            skipped_relationships.append(rel)
                            continue
                        raise
                    if result:
                        true_relationships.append(rel)

                return {
                    "person1_id": person1_id,
                    "person2_id": person2_id,
                    "true_relationships": true_relationships,
                    "skipped_relationships": skipped_relationships,
                }, 200

            query = f"{relationship}({person1_id}, {person2_id})"
            result = list(prolog_engine.query(query))
            return {"relationship": relationship, "exists": bool(result)}, 200

        except Exception as e:
            abort(400, description=f"Invalid relationship query: {str(e)}")


api.add_resource(QueryRelationshipEndpoint, "/query/relationship")


class SearchRelationshipEndpoint(Resource):
    @require_auth
    def post(self):
        ensure_prolog_available()

        data = get_json_or_400(required_fields=["person_id", "relationship"])
        person_id = int(data["person_id"])
        relationship = (data["relationship"] or "").strip()

        if relationship not in set(ALLOWED_RELATIONSHIPS):
            abort(400, description="Unknown or unsupported relationship predicate.")

        person = get_accessible_person_or_404(person_id)
        if person.tree_id is None:
            abort(400, description="Person is not assigned to a tree.")

        load_prolog_facts(person.tree)

        try:
            solutions = list(prolog_engine.query(f"{relationship}(X, {person_id})"))
        except Exception as e:
            abort(400, description=f"Invalid relationship query: {str(e)}")

        match_ids = []
        for s in solutions:
            try:
                match_ids.append(int(str(s["X"])))
            except (KeyError, ValueError):
                pass

        people = Person.select().where((Person.id.in_(match_ids)) & (Person.tree == person.tree))
        return {
            "person_id": person_id,
            "relationship": relationship,
            "results": [person_summary(p) for p in people.iterator()],
        }, 200


api.add_resource(SearchRelationshipEndpoint, "/query/relationship/search")


# =====================================================
# Family tree rendering
# =====================================================

def build_tree_graph(root_person, tree):
    people, parent_edges, spouse_edges = collect_family(root_person)

    people = {
        pid: person
        for pid, person in people.items()
        if getattr(person, "tree_id", None) == tree.id
    }

    allowed_ids = set(people.keys())
    parent_edges = [(a, b) for (a, b) in parent_edges if a in allowed_ids and b in allowed_ids]
    spouse_edges = [(a, b) for (a, b) in spouse_edges if a in allowed_ids and b in allowed_ids]

    NODE_WIDTH = 160
    V_SPACING = 180
    SPOUSE_GAP = 40
    NODE_HEIGHT = 60
    FAMILY_COLORS = ["#6C8AE4", "#8B2908", "#07572B", "#6E165B", "#628103", "#0A8488", "#805C08"]

    generation = assign_generations(root_person.id, people, parent_edges, spouse_edges)
    two_parent_families, single_parent_families = build_family_groups(people, parent_edges)

    positions = layout_full_tree(
        people,
        generation,
        two_parent_families,
        single_parent_families,
        node_width=NODE_WIDTH,
        spouse_gap=SPOUSE_GAP,
        level_gap=V_SPACING,
        root_gap=40,
        sibling_gap=40,
    )

    snap_spouse_only_people(positions, people, two_parent_families, single_parent_families, node_width=NODE_WIDTH, spouse_gap=SPOUSE_GAP)
    center_top_families_over_immediate_children(positions, generation, two_parent_families, single_parent_families, node_width=NODE_WIDTH, spouse_gap=SPOUSE_GAP)
    spread_top_family_blocks(positions, generation, two_parent_families, single_parent_families, node_width=NODE_WIDTH, spouse_gap=SPOUSE_GAP, family_gap=80)

    family_row_offsets = {}
    families_by_generation = defaultdict(list)
    family_colors = {}
    gen_family_index = {}
    single_family_colors = {}

    for (p1_id, p2_id), child_ids in two_parent_families.items():
        if p1_id not in generation:
            continue
        gen = generation[p1_id]
        gen_family_index.setdefault(gen, 0)
        color_idx = gen_family_index[gen] % len(FAMILY_COLORS)
        gen_family_index[gen] += 1
        family_colors[(p1_id, p2_id)] = FAMILY_COLORS[color_idx]

    for parent_id, child_ids in single_parent_families.items():
        if parent_id not in generation:
            continue
        gen = generation[parent_id]
        gen_family_index.setdefault(gen, 0)
        color_idx = gen_family_index[gen] % len(FAMILY_COLORS)
        gen_family_index[gen] += 1
        single_family_colors[parent_id] = FAMILY_COLORS[color_idx]

    for (p1_id, p2_id), child_ids in two_parent_families.items():
        if p1_id in generation:
            families_by_generation[generation[p1_id]].append(("two", p1_id, p2_id))

    for parent_id, child_ids in single_parent_families.items():
        if parent_id in generation:
            families_by_generation[generation[parent_id]].append(("one", parent_id))

    for gen, fams in families_by_generation.items():
        fams.sort()
        for idx, fam in enumerate(fams):
            family_row_offsets[fam] = idx % 3

    nodes = []
    edges = []
    added_nodes = set()
    added_edges = set()

    for pid, person in people.items():
        gender_name = (person.gender.name or "").lower()
        nodes.append({
            "id": str(pid),
            "type": "person",
            "data": {
                "label": f"{person.firstName} {person.lastName}",
                "years": format_years(person),
                "personId": pid,
                "ownerId": person.user.id,
                "canEdit": person.user.id == g.user.id,
            },
            "position": positions[pid],
            "style": {
                "background": "#FFB6C1" if gender_name == "female" else "#87CEEB",
                "border": "2px solid #333",
                "borderRadius": "8px",
                "padding": "10px",
                "width": NODE_WIDTH,
            },
        })
        added_nodes.add(str(pid))

    for a, b in set(spouse_edges):
        if a not in positions or b not in positions:
            continue
        source_id, target_id = (a, b) if positions[a]["x"] <= positions[b]["x"] else (b, a)
        add_edge_once(edges, added_edges, {
            "id": f"spouse-{source_id}-{target_id}",
            "source": str(source_id),
            "target": str(target_id),
            "sourceHandle": "spouse-right",
            "targetHandle": "spouse-left",
            "type": "straight",
            "style": {"stroke": "#FF69B4", "strokeWidth": 2},
        })

    for (p1_id, p2_id), child_ids in two_parent_families.items():
        if p1_id not in positions or p2_id not in positions:
            continue

        visible_children = [cid for cid in child_ids if cid in positions]
        if not visible_children:
            continue

        p1_center = positions[p1_id]["x"] + NODE_WIDTH / 2
        p2_center = positions[p2_id]["x"] + NODE_WIDTH / 2
        mid_x = (p1_center + p2_center) / 2
        attach_y = positions[p1_id]["y"] + NODE_HEIGHT / 2
        offset_band = family_row_offsets.get(("two", p1_id, p2_id), 0)
        route_y = positions[p1_id]["y"] + NODE_HEIGHT + 25 + (offset_band * 24)
        attach_id = f"attach-{p1_id}-{p2_id}"
        route_id = f"route-{p1_id}-{p2_id}"
        color = family_colors.get((p1_id, p2_id), "#777777")

        add_junction_node(nodes, added_nodes, attach_id, mid_x, attach_y, "#FF69B4")
        add_junction_node(nodes, added_nodes, route_id, mid_x, route_y, color)

        for n in nodes:
            if n["id"] == route_id:
                n["data"]["familyType"] = "two"
                n["data"]["parentIds"] = [p1_id, p2_id]
                break

        add_edge_once(edges, added_edges, {
            "id": f"{attach_id}-{route_id}",
            "source": attach_id,
            "target": route_id,
            "sourceHandle": "bottom",
            "targetHandle": "top",
            "type": "straight",
            "style": {"stroke": color, "strokeWidth": 2},
        })

        for child_id in visible_children:
            add_edge_once(edges, added_edges, {
                "id": f"{route_id}-{child_id}",
                "source": route_id,
                "target": str(child_id),
                "sourceHandle": "bottom",
                "targetHandle": "top",
                "type": "step",
                "style": {"stroke": color, "strokeWidth": 2},
            })

        for parent_id in [p1_id, p2_id]:
            add_edge_once(edges, added_edges, {
                "id": f"hidden-{parent_id}-{attach_id}",
                "source": str(parent_id),
                "target": attach_id,
                "sourceHandle": "bottom",
                "targetHandle": "top",
                "type": "straight",
                "style": {"stroke": "rgba(0,0,0,0)", "strokeWidth": 0},
                "selectable": False,
                "focusable": False,
            })

    for parent_id, child_ids in single_parent_families.items():
        if parent_id not in positions:
            continue

        visible_children = [cid for cid in child_ids if cid in positions]
        if not visible_children:
            continue

        parent_center = positions[parent_id]["x"] + NODE_WIDTH / 2
        attach_y = positions[parent_id]["y"] + NODE_HEIGHT / 2
        offset_band = family_row_offsets.get(("one", parent_id), 0)
        route_y = positions[parent_id]["y"] + NODE_HEIGHT + 25 + (offset_band * 24)
        attach_id = f"single-attach-{parent_id}"
        route_id = f"single-route-{parent_id}"
        color = single_family_colors.get(parent_id, "#777777")

        add_junction_node(nodes, added_nodes, attach_id, parent_center, attach_y, "rgba(0,0,0,0)")
        add_junction_node(nodes, added_nodes, route_id, parent_center, route_y, color)

        for n in nodes:
            if n["id"] == route_id:
                n["data"]["familyType"] = "one"
                n["data"]["parentIds"] = [parent_id]
                break

        add_edge_once(edges, added_edges, {
            "id": f"{attach_id}-{route_id}",
            "source": attach_id,
            "target": route_id,
            "sourceHandle": "bottom",
            "targetHandle": "top",
            "type": "straight",
            "style": {"stroke": color, "strokeWidth": 2},
        })

        for child_id in visible_children:
            add_edge_once(edges, added_edges, {
                "id": f"{route_id}-{child_id}",
                "source": route_id,
                "target": str(child_id),
                "sourceHandle": "bottom",
                "targetHandle": "top",
                "type": "step",
                "style": {"stroke": color, "strokeWidth": 2},
            })

        add_edge_once(edges, added_edges, {
            "id": f"hidden-{parent_id}-{attach_id}",
            "source": str(parent_id),
            "target": attach_id,
            "sourceHandle": "bottom",
            "targetHandle": "top",
            "type": "straight",
            "style": {"stroke": "rgba(0,0,0,0)", "strokeWidth": 0},
            "selectable": False,
            "focusable": False,
        })

    return {"nodes": nodes, "edges": edges, "treeId": tree.id, "rootPersonId": root_person.id}


class FamilyTreeEndpoint(Resource):
    @require_auth
    def get(self, person_id):
        root_person = get_accessible_person_or_404(person_id)

        if root_person.tree_id is None:
            abort(400, description="Person is not assigned to a tree.")

        if not user_can_view_tree(g.user, root_person.tree):
            abort(403)

        return build_tree_graph(root_person, root_person.tree), 200


api.add_resource(FamilyTreeEndpoint, "/tree/<int:person_id>")


class TreeByIdEndpoint(Resource):
    @require_auth
    def get(self, tree_id):
        tree = Tree.get_or_none(Tree.id == int(tree_id))
        if not tree:
            abort(404)

        if not user_can_view_tree(g.user, tree):
            abort(403)

        root_person = (
            Person.select()
            .where(
                (Person.tree == tree) &
                (Person.parent1_id.is_null(True)) &
                (Person.parent2_id.is_null(True))
            )
            .order_by(Person.id)
            .first()
        )

        if root_person is None:
            root_person = Person.select().where(Person.tree == tree).order_by(Person.id).first()

        if root_person is None:
            return {
                "nodes": [],
                "edges": [],
                "treeId": tree.id,
                "message": "This tree has no people yet. Add a person to begin building your tree.",
            }, 200

        return build_tree_graph(root_person, tree), 200


api.add_resource(TreeByIdEndpoint, "/trees/<int:tree_id>/view")


# =====================================================
# Family group membership
# =====================================================

def _get_group_or_404(group_id):
    group = FamilyGroup.get_or_none(FamilyGroup.id == int(group_id))
    if not group:
        abort(404)
    return group


def _require_group_member(group):
    membership = FamilyGroupMember.get_or_none(
        (FamilyGroupMember.family_group == group) &
        (FamilyGroupMember.user == g.user)
    )
    if not membership:
        abort(403)
    return membership


def _role_rank(role):
    return {"viewer": 1, "editor": 2, "owner": 3}.get(role, 0)


def _require_group_role_at_least(group, required_role):
    membership = _require_group_member(group)
    if _role_rank(membership.role) < _role_rank(required_role):
        abort(403)
    return membership


class FamilyGroupMembersEndpoint(Resource):
    @require_auth
    def get(self, group_id):
        group = _get_group_or_404(group_id)
        _require_group_member(group)

        query = (
            FamilyGroupMember.select(FamilyGroupMember, User)
            .join(User)
            .where(FamilyGroupMember.family_group == group)
            .order_by(User.username)
        )

        return {
            "familyGroup": {"id": group.id, "name": group.name, "ownerUserId": group.owner_id},
            "members": [
                {"userId": m.user.id, "username": m.user.username, "role": m.role}
                for m in query
            ],
        }, 200

    @require_auth
    def post(self, group_id):
        group = _get_group_or_404(group_id)
        _require_group_role_at_least(group, "editor")

        data = get_json_or_400(required_fields=["username"])
        username = (data.get("username") or "").strip()
        role = (data.get("role") or "viewer").strip().lower()

        if not username:
            abort(400, description="username is required")
        if role not in ("viewer", "editor", "owner"):
            abort(400, description="Invalid role")
        if role == "owner":
            _require_group_role_at_least(group, "owner")

        user_to_add = User.get_or_none(User.username == username)
        if not user_to_add:
            abort(404, description="User not found")

        existing = FamilyGroupMember.get_or_none(
            (FamilyGroupMember.family_group == group) &
            (FamilyGroupMember.user == user_to_add)
        )
        if existing:
            return {"status": "already_member"}, 200

        FamilyGroupMember.create(family_group=group, user=user_to_add, role=role)

        return {
            "status": "added",
            "userId": user_to_add.id,
            "username": user_to_add.username,
            "role": role,
        }, 201


api.add_resource(FamilyGroupMembersEndpoint, "/family-groups/<int:group_id>/members")


class FamilyGroupMemberDetailEndpoint(Resource):
    @require_auth
    def patch(self, group_id, user_id):
        group = _get_group_or_404(group_id)
        _require_group_role_at_least(group, "owner")

        data = get_json_or_400(required_fields=["role"])
        new_role = (data.get("role") or "").strip().lower()
        if new_role not in ("viewer", "editor", "owner"):
            abort(400, description="Invalid role")

        membership = FamilyGroupMember.get_or_none(
            (FamilyGroupMember.family_group == group) &
            (FamilyGroupMember.user == int(user_id))
        )
        if not membership:
            abort(404)

        if membership.user_id == group.owner_id and new_role != "owner":
            abort(409, description="Cannot downgrade the family group owner")

        membership.role = new_role
        membership.save()

        return {"status": "updated", "userId": membership.user_id, "role": membership.role}, 200

    @require_auth
    def delete(self, group_id, user_id):
        group = _get_group_or_404(group_id)
        _require_group_role_at_least(group, "owner")

        membership = FamilyGroupMember.get_or_none(
            (FamilyGroupMember.family_group == group) &
            (FamilyGroupMember.user == int(user_id))
        )
        if not membership:
            abort(404)

        if membership.user_id == group.owner_id:
            abort(409, description="Cannot remove the family group owner")

        membership.delete_instance()
        return {"status": "removed", "userId": int(user_id)}, 200


api.add_resource(
    FamilyGroupMemberDetailEndpoint,
    "/family-groups/<int:group_id>/members/<int:user_id>",
)


class MyFamilyGroupsEndpoint(Resource):
    @require_auth
    def get(self):
        query = (
            FamilyGroupMember.select(FamilyGroupMember, FamilyGroup)
            .join(FamilyGroup)
            .where(FamilyGroupMember.user == g.user)
            .order_by(FamilyGroup.name)
        )

        return {
            "familyGroups": [
                {
                    "id": m.family_group.id,
                    "name": m.family_group.name,
                    "ownerUserId": m.family_group.owner_id,
                    "myRole": m.role,
                }
                for m in query
            ]
        }, 200


api.add_resource(MyFamilyGroupsEndpoint, "/family-groups")

class GroupAccessSummaryEndpoint(Resource):
    @require_auth
    def get(self):
        owned_groups = []

        for group in FamilyGroup.select().where(FamilyGroup.owner == g.user):
            members = (
                FamilyGroupMember
                .select(FamilyGroupMember, User)
                .join(User)
                .where(FamilyGroupMember.family_group == group)
                .order_by(User.username)
            )

            owned_groups.append({
                "id": group.id,
                "name": group.name,
                "shareCode": g.user.share_code,
                "members": [
                    {
                        "userId": member.user.id,
                        "username": member.user.username,
                        "role": member.role,
                        "isOwner": member.user.id == group.owner_id,
                    }
                    for member in members
                ],
            })

        accessible_groups = []

        memberships = (
            FamilyGroupMember
            .select(FamilyGroupMember, FamilyGroup, User)
            .join(FamilyGroup)
            .switch(FamilyGroupMember)
            .join(User)
            .where(FamilyGroupMember.user == g.user)
            .order_by(FamilyGroup.name)
        )

        for membership in memberships:
            group = membership.family_group

            if group.owner_id == g.user.id:
                continue

            accessible_groups.append({
                "id": group.id,
                "name": group.name,
                "ownerUserId": group.owner_id,
                "ownerUsername": group.owner.username,
                "myRole": membership.role,
                "isOwnedByMe": False,
            })
        return {
            "ownedGroups": owned_groups,
            "accessibleGroups": accessible_groups,
        }, 200

api.add_resource(GroupAccessSummaryEndpoint, "/group-access-summary")

class LeaveFamilyGroupEndpoint(Resource):
    @require_auth
    def delete(self, group_id):
        membership = FamilyGroupMember.get_or_none(
            (FamilyGroupMember.family_group_id == int(group_id)) &
            (FamilyGroupMember.user_id == g.user.id)
        )

        if not membership:
            abort(404)

        group = membership.family_group

        if group.owner_id == g.user.id:
            abort(400, description="Owners cannot leave their own group.")

        membership.delete_instance()
        return {"status": "left_group"}, 200


api.add_resource(LeaveFamilyGroupEndpoint, "/family-groups/<int:group_id>/leave")

# =====================================================
# Trees
# =====================================================

class MyTreesEndpoint(Resource):
    @require_auth
    def get(self):
        trees = []
        seen = set()

        for tree_id in get_accessible_tree_ids(g.user):
            tree = Tree.get_or_none(Tree.id == tree_id)
            if not tree or tree.id in seen:
                continue
            seen.add(tree.id)
            trees.append({
                "id": tree.id,
                "name": tree.name,
                "ownerUserId": tree.owner_id,
                "familyGroupId": tree.family_group_id,
                "familyGroupName": tree.family_group.name if tree.family_group_id else None,
            })

        return {"trees": trees}, 200
    
class FirstOwnedTreeEndpoint(Resource):
    @require_auth
    def get(self):
        tree = get_first_owned_tree(g.user)

        if not tree:
            return {"tree": None}, 200

        return {
            "tree": {
                "id": tree.id,
                "name": tree.name,
                "ownerUserId": tree.owner_id,
                "familyGroupId": tree.family_group_id,
                "familyGroupName": tree.family_group.name if tree.family_group_id else None,
            }
        }, 200

api.add_resource(FirstOwnedTreeEndpoint, "/trees/first")


class FamilyGroupTreesEndpoint(Resource):
    @require_auth
    def get(self, group_id):
        group = _get_group_or_404(group_id)
        _require_group_member(group)

        trees = [
            {
                "id": tree.id,
                "name": tree.name,
                "ownerUserId": tree.owner_id,
                "familyGroupId": group.id,
                "familyGroupName": group.name,
            }
            for tree in Tree.select().where(Tree.family_group == group).order_by(Tree.name)
        ]

        return {"familyGroup": {"id": group.id, "name": group.name}, "trees": trees}, 200

    @require_auth
    def post(self, group_id):
        group = _get_group_or_404(group_id)
        _require_group_role_at_least(group, "editor")

        data = get_json_or_400(required_fields=["name"])
        name = (data.get("name") or "").strip()
        if not name:
            abort(400, description="name is required")

        tree = Tree.create(name=name, owner=g.user, family_group=group)

        return {
            "id": tree.id,
            "name": tree.name,
            "ownerUserId": tree.owner_id,
            "familyGroupId": group.id,
        }, 201


api.add_resource(MyTreesEndpoint, "/trees")
api.add_resource(FamilyGroupTreesEndpoint, "/family-groups/<int:group_id>/trees")


if __name__ == "__main__":
    initialize_prolog()
    app.run(host="127.0.0.1", port=5000, debug=False)
