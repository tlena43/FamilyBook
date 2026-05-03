import os
from dotenv import load_dotenv

# Load .env from the current directory:
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

# DEBUG: Check if secretKey was loaded...
#secret_key = os.getenv('secretKey')
#print(f"DEBUG: env_path = {env_path}")
#print(f"DEBUG: secretKey = {secret_key}")
#print(f"DEBUG: .env exists? {os.path.exists(env_path)}")

from datetime import datetime
import bcrypt
import peewee
from flask import Flask, abort, g, redirect, request, send_from_directory
from flask_compress import Compress
from flask_restful import Api, Resource
from pdf2image import convert_from_path
from models import *
from utilities import *
from pyswip import Prolog
from familyTree import *
from collections import defaultdict

# Prolog engine initialization (rest of the code is down below):
prolog_engine = Prolog()

APP_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_DIR, "upload")
CACHE_FOLDER = os.path.join(UPLOAD_FOLDER, "cache")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CACHE_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["CACHE_FOLDER"] = CACHE_FOLDER

Compress(app)
api = Api(app)

@app.before_request
def before_request():
    criteria = [
        request.is_secure,
        app.debug,
        request.headers.get("X-Forwarded-Proto", "http") == "https",
    ]
    if not any(criteria):
        url = request.url.replace("http://", "https://", 1)
        return redirect(url, code=308)

    if db.is_closed():
        db.connect()


@app.teardown_request
def teardown_request(exception=None):
    if not db.is_closed():
        db.close()


@app.after_request
def after_request(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, PATCH, DELETE"
    response.headers["Access-Control-Allow-Headers"] = f"{AUTH_HEADER_NAME}, Content-Type, Content-Length"
    return response


# =====================================================
#                  CHECK LOGIN SECTION
# =====================================================
# Verifies that the user is authenticated and returns their privacy level.

##endpoints
class CheckLoginEndpoint(Resource):
    @require_auth
    def get(self):
        return {"username": g.user.username}, 200


api.add_resource(CheckLoginEndpoint, "/loginCheck")


# =====================================================
#                  ADMIN USERS SECTION
# =====================================================
# Admin-only endpoint to list user accounts (no passwords returned).

class AdminUsersEndpoint(Resource):
    @require_auth
    def get(self):
        users = []
        for u in User.select().order_by(User.id):
            users.append(
                {
                    "id": u.id,
                    "username": u.username,
                }
            )

        return {"users": users}, 200


api.add_resource(AdminUsersEndpoint, "/admin/users")


# =====================================================
#                  UPLOAD SECTION
# =====================================================
# Handles file uploads, downloads, and deletions for documents/images.

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

        return {
            "filename": unique_filename,
            "fileid": saved_upload.id,
        }, 201

    def get(self, filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @require_auth
    def delete(self, filename):
        try:
            upload = Upload.get(Upload.filename == filename)
        except Upload.DoesNotExist:
            abort(404)

        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        try:
            upload.delete_instance()
            if os.path.isfile(filepath):
                os.remove(filepath)
        except peewee.IntegrityError:
            abort(409)

        return {"status": "deleted"}, 200


api.add_resource(UploadEndpoint, "/upload", "/upload/<string:filename>")


# =====================================================
#                   CACHE SECTION
# =====================================================
# Generates and serves cached versions of PDFs (e.g., as images).

class CacheEndpoint(Resource):
    def get(self, filename):
        makeCachedUpload(app, filename)
        return send_from_directory(app.config["CACHE_FOLDER"], filename)


api.add_resource(CacheEndpoint, "/upload/cache/<string:filename>")


# =====================================================
#                PDF PAGES SECTION
# =====================================================
# Returns the number of pages in a PDF file.

class PdfNumPagesEndpoint(Resource):
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
#                   PERSON SECTION
# =====================================================
# CRUD operations for family members (create, read, update, delete).

class PersonEndpoint(Resource):
    @require_auth
    def post(self):
        data = get_json_or_400(
            required_fields=[
                "birthDay",
                "birthDateUnknowns",
                "deathDateUnknowns",
                "deathDay",
                "file",
                "birthplace",
                "parent1",
                "parent2",
                "spouse",
                "firstName",
                "lastName",
                "gender",
                "isDead",
                "middleName",
                "maidenName",
                "children"
            ]
        )

        children = data["children"]

        person = Person.create(
            tree=parse_optional_int(data.get("tree")),
            birthDay=parse_optional_date(data["birthDay"]),
            birthDateUnknowns=data["birthDateUnknowns"],
            deathDateUnknowns=data["deathDateUnknowns"],
            deathDay=parse_optional_date(data["deathDay"]),
            file=parse_optional_int(data["file"]),
            birthplace=parse_optional_str(data["birthplace"]),
            parent1_id=parse_optional_int(data["parent1"]),
            parent2_id=parse_optional_int(data["parent2"]),
            spouse_id=parse_optional_int(data["spouse"]),
            firstName=data["firstName"],
            lastName=data["lastName"],
            gender=int(data["gender"]),
            isDead=data["isDead"],
            middleName=parse_optional_str(data["middleName"]),
            maidenName=parse_optional_str(data["maidenName"]),
        )
        
        spouse_id = parse_optional_int(data.get("spouse"))

        if spouse_id and spouse_id != person.id:
            spouse_person = Person.get_or_none(Person.id == spouse_id)
            if spouse_person:
                spouse_person.spouse_id = person.id
                spouse_person.save()
                
        children_ids = data.get("children") or []

        for child_id in children_ids:
            try:
                child_id = int(child_id)
            except (TypeError, ValueError):
                continue

            if child_id == person.id:
                continue  # prevent self-parenting

            child = Person.get_or_none(Person.id == child_id)
            if not child:
                continue

            # Fill first available parent slot
            if not child.parent1_id:
                child.parent1_id = person.id
            elif not child.parent2_id:
                child.parent2_id = person.id
            else:
                # already has two parents
                continue

            child.save()
                

        return {"id": person.id}, 201

    @require_auth
    def get(self, id=None):
        if id is None:
            person_list = {"people": []}
            tree_ids = get_accessible_tree_ids(g.user)
            if tree_ids:
                people = Person.select().where(
                    Person.tree.in_(tree_ids) | Person.tree.is_null()
                )
            else:
                people = Person.select().where(Person.tree.is_null())

            for person in people:
                person_list["people"].append(
                    serialize_person_summary(person, True)
                )

            return person_list, 200

        try:
            person = Person.get(Person.id == id)
        except Person.DoesNotExist:
            abort(404)

        content_list = []
        for c in person.content:
            content = c.content
            content_list.append(
                {
                    "id": content.id,
                    "title": content.title,
                }
            )

        result = {
            "id": person.id,
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
            "parent1" : {
                "id": person.parent1_id.id,
                "firstName": person.parent1_id.firstName,
                "lastName": person.parent1_id.lastName,
                "middleName": person.parent1_id.middleName,
                "birthDay": str(person.parent1_id.birthDay),
                "birthDateUnknowns": person.parent1_id.birthDateUnknowns,
                } if person.parent1_id else None,
            "parent2" : {
                "id": person.parent2_id.id,
                "firstName": person.parent2_id.firstName,
                "lastName": person.parent2_id.lastName,
                "middleName": person.parent2_id.middleName,
                "birthDay": str(person.parent2_id.birthDay),
                "birthDateUnknowns": person.parent2_id.birthDateUnknowns,
                } if person.parent2_id else None,
            "spouse" : {
                "id": person.spouse_id.id,
                "firstName": person.spouse_id.firstName,
                "lastName": person.spouse_id.lastName,
                "middleName": person.spouse_id.middleName,
                "birthDay": str(person.spouse_id.birthDay),
                "birthDateUnknowns": person.spouse_id.birthDateUnknowns,
                } if person.spouse_id else None,
            "children": [
                {
                    "id": child.id,
                    "firstName": child.firstName,
                    "lastName": child.lastName,
                    "middleName": child.middleName,
                }
                for child in Person.select().where(
                    (Person.parent1_id == person) | (Person.parent2_id == person)
                )
            ],
        }

        return result, 200

    @require_auth
    def patch(self, id):
        data = get_json_or_400(
            required_fields=[
                "birthDay",
                "birthDateUnknowns",
                "deathDateUnknowns",
                "deathDay",
                "file",
                "birthplace",
                "parent1",
                "parent2",
                "firstName",
                "lastName",
                "gender",
                "isDead",
                "middleName",
                "maidenName",
                "spouse",
                "children"
            ]
        )

        id = int(id)

        try:
            existing_person = Person.get(Person.id == id)
        except Person.DoesNotExist:
            abort(404)

        if existing_person.tree_id is not None:
            if not user_can_access_tree(g.user, existing_person.tree):
                abort(403)

        file_value = parse_optional_int(data["file"], default=existing_person.file)

        tree_value = parse_optional_int(data.get("tree"), default=existing_person.tree_id)

        Person.update(
            tree=tree_value,
            birthDay=parse_optional_date(data["birthDay"]),
            birthDateUnknowns=data["birthDateUnknowns"],
            deathDateUnknowns=data["deathDateUnknowns"],
            deathDay=parse_optional_date(data["deathDay"]),
            file=file_value,
            birthplace=parse_optional_str(data["birthplace"]),
            parent1_id=parse_optional_int(data["parent1"]),
            parent2_id=parse_optional_int(data["parent2"]),
            firstName=data["firstName"],
            lastName=data["lastName"],
            gender=int(data["gender"]),
            isDead=data["isDead"],
            middleName=parse_optional_str(data["middleName"]),
            maidenName=parse_optional_str(data["maidenName"]),
            spouse_id=parse_optional_int(data["spouse"]),
        ).where(Person.id == id).execute()
        
        spouse_id = parse_optional_int(data.get("spouse"))

        if spouse_id and spouse_id != id:
            spouse_person = Person.get_or_none(Person.id == spouse_id)
            if spouse_person:
                spouse_person.spouse_id = id
                spouse_person.save()
                
        children_ids = data.get("children") or []

        for child_id in children_ids:
            try:
                child_id = int(child_id)
            except (TypeError, ValueError):
                continue

            if child_id == id:
                continue  # prevent self-parenting

            child = Person.get_or_none(Person.id == child_id)
            if not child:
                continue

            # Fill first available parent slot
            if not child.parent1_id:
                child.parent1_id = id
            elif not child.parent2_id:
                child.parent2_id = id
            else:
                # already has two parents
                continue

            child.save()

        return {"id": id}, 200

    @require_auth
    def delete(self, id):
        try:
            person = Person.get(Person.id == id)
        except Person.DoesNotExist:
            abort(404)

        if person.tree_id is not None:
            if not user_can_access_tree(g.user, person.tree):
                abort(403)

        with db.atomic():
            Person_Content.delete().where(Person_Content.person == id).execute()
            Person.update(parent1_id=None).where(Person.parent1_id == id).execute()
            Person.update(parent2_id=None).where(Person.parent2_id == id).execute()
            Person.update(spouse_id=None).where(Person.spouse_id == id).execute()
            person.delete_instance()

        return {"status": "deleted"}, 200


api.add_resource(PersonEndpoint, "/person", "/person/<int:id>")


# =====================================================
#                  CONTENT SECTION
# =====================================================
# CRUD operations for family documents and media content.

class ContentEndpoint(Resource):
    @require_auth
    def post(self):
        data = get_json_or_400(
            required_fields=[
                "user",
                "type",
                "date",
                "notes",
                "title",
                "file",
                "location",
                "dateUnknowns",
                "people",
            ]
        )

        content = Content.create(
            user=int(data["user"]),
            type=int(data["type"]) if data["type"] != 0 else None,
            date=parse_optional_date(data["date"]),
            notes=parse_optional_str(data["notes"]),
            title=data["title"],
            file=int(data["file"]),
            location=parse_optional_str(data["location"]),
            dateUnknowns=data["dateUnknowns"],
        )

        for item in data["people"]:
            Person_Content.create(content=content.id, person=item)

        return {"id": content.id}, 201

    @require_auth
    def get(self, id=None):
        if id is None:
            content_list = {"content": []}
            tree_ids = get_accessible_tree_ids(g.user)
            if tree_ids:
                contents = Content.select().where(
                    Content.tree.in_(tree_ids) | Content.tree.is_null()
                )
            else:
                contents = Content.select().where(Content.tree.is_null())

            for content in contents:
                content_list["content"].append(serialize_content_summary(content))

            return content_list, 200

        try:
            content = Content.get(Content.id == id)
        except Content.DoesNotExist:
            abort(404)

        person_list = []
        for p in content.person:
            person = p.person
            person_list.append(
                {
                    "id": person.id,
                    "firstName": person.firstName,
                    "middleName": person.middleName,
                    "lastName": person.lastName,
                    "birthDay": str(person.birthDay),
                    "birthDateUnknowns": person.birthDateUnknowns,
                }
            )

        result = {
            "title": content.title,
            "fileName": content.file.filename if content.file else None,
            "type": content.type.name if content.type is not None else None,
            "date": str(content.date),
            "dateUnknowns": content.dateUnknowns,
            "notes": content.notes,
            "location": content.location,
            "people": person_list,
        }

        return result, 200

    @require_auth
    def patch(self, id):
        data = get_json_or_400(
            required_fields=[
                "type",
                "date",
                "notes",
                "title",
                "location",
                "dateUnknowns",
                "people",
            ]
        )

        try:
            Content.get(Content.id == id)
        except Content.DoesNotExist:
            abort(404)

        Content.update(
            type=int(data["type"]) if data["type"] != 0 else None,
            date=parse_optional_date(data["date"]),
            notes=parse_optional_str(data["notes"]),
            title=data["title"],
            location=parse_optional_str(data["location"]),
            dateUnknowns=data["dateUnknowns"],
        ).where(Content.id == id).execute()

        Person_Content.delete().where(Person_Content.content == id).execute()

        for item in data["people"]:
            Person_Content.create(content=id, person=item)

        return {"id": id}, 200

    @require_auth
    def delete(self, id):
        try:
            content = Content.get(Content.id == id)
        except Content.DoesNotExist:
            abort(404)

        Person_Content.delete().where(Person_Content.content == id).execute()
        content.delete_instance()

        return {"status": "deleted"}, 200


api.add_resource(ContentEndpoint, "/content", "/content/<int:id>")


# =====================================================
#                   GENDER SECTION
# =====================================================
# Returns list of available genders for person creation/editing.

class GenderEndpoint(Resource):
    def get(self):
        gender_list = {"genders": []}
        genders = Gender.select()

        for gender in genders.iterator():
            gender_list["genders"].append(
                {
                    "id": gender.id,
                    "name": gender.name,
                }
            )

        return gender_list, 200


api.add_resource(GenderEndpoint, "/gender")

# =====================================================
#                    LOGIN SECTION
# =====================================================
# Authenticates users and returns auth token and privacy level.

class LoginEndpoint(Resource):
    def post(self):
        data = get_json_or_400(required_fields=["username", "password"])

        username = data["username"]
        password_input = data["password"]

        try:
            user = User.get(User.username == username)
        except User.DoesNotExist:
            abort(401)

        if not bcrypt.checkpw(
            password_input.encode("utf8"),
            user.password.encode("utf8"),
        ):
            abort(401)

        return {
            "key": signer.sign(str(user.id)).decode("utf8"),
        }, 200


api.add_resource(LoginEndpoint, "/login")

# =====================================================
#                    SIGNUP SECTION
# =====================================================
# Registers new users with username, password validation, and auto-login.

class SignupEndpoint(Resource):
    def post(self):
        data = get_json_or_400(required_fields=["username", "password", "passwordConfirm"])

        username = data["username"].strip()
        password = data["password"]
        password_confirm = data["passwordConfirm"]

        # Validate inputs:
        if not username or len(username) < 3:
            abort(400, description="Username must be at least 3 characters long.")

        if not password or len(password) < 6:
            abort(400, description="Password must be at least 6 characters long.")

        if password != password_confirm:
            abort(400, description="Passwords do not match.")

        # Check if user already exists:
        try:
            User.get(User.username == username)
            abort(400, description="Username already exists.")
        except User.DoesNotExist:
            pass

        hashed_password = bcrypt.hashpw(password.encode("utf8"), bcrypt.gensalt()).decode("utf8")

        # Use a transaction so we don't create partial accounts.
        with db.atomic():
            new_user = User.create(
                username=username,
                password=hashed_password,
            )

            # Every user gets their own personal FamilyGroup (owned by them).
            personal_group_name = f"{username}'s Family"
            personal_group = FamilyGroup.create(name=personal_group_name, owner=new_user)
            FamilyGroupMember.create(
                family_group=personal_group,
                user=new_user,
                role="owner",
            )

        return {
            "key": signer.sign(str(new_user.id)).decode("utf8"),
            "message": "Account created successfully!",
        }, 201


api.add_resource(SignupEndpoint, "/signup")

# =====================================================
#                    PROLOG SECTION
# =====================================================
# Prolog logic engine for inferring complex family relationships (sibling, cousin, etc.).

# Load family_rules.pl from file:
def initialize_prolog():
    """Initialize the Prolog engine with our family rules."""
    global prolog_engine
    prolog_engine = Prolog()

    rules_file = os.path.abspath(os.path.join(APP_DIR, "prolog", "family_rules.pl"))

    if not os.path.exists(rules_file):
        print(f"WARNING: Prolog rules file not found at {rules_file}")
        return

    try:
        # Direct consult is clearer and works when PySwip is healthy.
        prolog_engine.consult(rules_file)

        # Sanity check that the engine can execute queries.
        list(prolog_engine.query("true"))

        print(f"DEBUG: Successfully loaded Prolog rules from {rules_file}")
    except Exception as e:
        print(f"WARNING: Failed to load Prolog rules from {rules_file}")
        print(f"WARNING: Error: {e}")


# Need to connect the database to the Prolog engine (note that we only want the base facts, rest is inferred):
def load_prolog_facts(prolog_engine):
    """This function loads a person's data from the database in the form of Prolog facts."""

    # Clear previously asserted dynamic facts to prevent duplicates across requests.
    try:
        list(prolog_engine.query("retractall(parent(_,_))"))
        list(prolog_engine.query("retractall(male(_))"))
        list(prolog_engine.query("retractall(female(_))"))
        list(prolog_engine.query("retractall(spouse(_,_))"))
    except Exception:
        # If retractall fails (e.g., predicates not yet exist), ignore.
        pass

    for person in Person.select():
        # Male or female:
        if person.gender.name == "male":
            prolog_engine.assertz(f"male({person.id})")
        else:
            prolog_engine.assertz(f"female({person.id})")

        # Parent or spouse:
        # Parent follows parent(parent, person).
        # Spouse follows spouse(person, spouse).
        if person.parent1_id:
            prolog_engine.assertz(f"parent({person.parent1_id.id}, {person.id})")
        if person.parent2_id:
            prolog_engine.assertz(f"parent({person.parent2_id.id}, {person.id})")
        if person.spouse_id:
            prolog_engine.assertz(f"spouse({person.id}, {person.spouse_id.id})")

ALLOWED_RELATIONSHIPS = [
    # Core
    "parent", "mother", "father",
    "child", "son", "daughter",
    "spouse", "partner", "husband", "wife",
    # Siblings
    "sibling", "full_sibling", "half_sibling",
    "brother", "sister", "full_brother", "half_brother", "full_sister", "half_sister",
    # Grandparents/children
    "grandparent", "grandfather", "grandmother",
    "grandchild", "grandson", "granddaughter",
    # Great-grandparents
    "great_grandparent", "great_grandmother", "great_grandfather",
    "great_great_grandparent", "great_great_grandmother", "great_great_grandfather",
    "great_great_great_grandparent",
    # Ancestors/descendants
    "ancestor", "descendant",
    # Aunts/uncles/niblings
    "pibling", "aunt", "uncle",
    "grand_pibling", "grand_aunt", "grand_uncle",
    "great_grand_pibling", "great_grand_aunt", "great_grand_uncle",
    "niece", "nephew", "grand_niece", "grand_nephew",
    # Cousins
    "cousin", "first_cousin",
    "first_cousin_once_removed", "first_cousin_twice_removed",
    "second_cousin", "second_cousin_once_removed", "second_cousin_twice_removed",
    "third_cousin", "third_cousin_once_removed", "third_cousin_twice_removed",
    # In-laws
    "parent_in_law", "mother_in_law", "father_in_law",
    "child_in_law", "son_in_law", "daughter_in_law",
    "sibling_in_law", "brother_in_law", "sister_in_law",
    # Step relations
    "step_parent", "step_mother", "step_father",
    "step_child", "step_sibling", "step_brother", "step_sister",
]

# Need a function that allows us to determine the relationship between two people (inference):
# This should only be available to AUTHENTICATED users!!!
class QueryRelationshipEndpoint(Resource):
    @require_auth
    def post(self):
        """Query the relationship(s) between two people using Prolog."""
        data = get_json_or_400(required_fields=["person1_id", "person2_id", "relationship"])

        # Split data by person + relationship:
        person1_id = int(data["person1_id"])
        person2_id = int(data["person2_id"])
        relationship = (data["relationship"] or "").strip()

        allowed_relationships = ALLOWED_RELATIONSHIPS

        # Support a more intuitive 'infer all' mode.
        # Client can send relationship='all' to get a list of all true relationships.
        if relationship != "all" and relationship not in set(allowed_relationships):
            abort(400, description="Unknown or unsupported relationship predicate.")

        # Reload facts each time this endpoint is called (can improve by implementing caching):
        load_prolog_facts(prolog_engine)

        def _is_undefined_predicate_error(exc: Exception) -> bool:
            msg = str(exc)
            return "existence_error(procedure" in msg

        try:
            if relationship == "all":
                true_relationships = []
                skipped_relationships = []

                for rel in allowed_relationships:
                    query = f"{rel}({person1_id}, {person2_id})"
                    try:
                        result = list(prolog_engine.query(query))
                    except Exception as e:
                        # If a predicate isn't defined in the currently loaded rules,
                        # skip it so inference still works.
                        if _is_undefined_predicate_error(e):
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

            # Backwards-compatible single relationship mode
            query = f"{relationship}({person1_id}, {person2_id})"
            try:
                result = list(prolog_engine.query(query))
            except Exception as e:
                if _is_undefined_predicate_error(e):
                    abort(400, description="Relationship predicate is not defined in Prolog rules.")
                raise

            if result:
                return {"relationship": relationship, "exists": True}, 200
            else:
                return {"relationship": relationship, "exists": False}, 200
        except Exception as e:
            abort(400, description=f"Invalid relationship query: {str(e)}")

# Register the QueryRelationshipEndpoing API endpoint:
api.add_resource(QueryRelationshipEndpoint, "/query/relationship")


class SearchRelationshipEndpoint(Resource):
    @require_auth
    def post(self):
        """Find all people who have a given relationship with a specified person."""
        data = get_json_or_400(required_fields=["person_id", "relationship"])
        person_id = int(data["person_id"])
        relationship = (data["relationship"] or "").strip()

        if relationship not in set(ALLOWED_RELATIONSHIPS):
            abort(400, description="Unknown or unsupported relationship predicate.")

        load_prolog_facts(prolog_engine)

        def _is_undefined_predicate_error(exc: Exception) -> bool:
            return "existence_error(procedure" in str(exc)

        try:
            solutions = list(prolog_engine.query(f"{relationship}({person_id}, X)"))
        except Exception as e:
            if _is_undefined_predicate_error(e):
                abort(400, description="Relationship predicate is not defined in Prolog rules.")
            abort(400, description=f"Invalid relationship query: {str(e)}")

        match_ids = []
        for s in solutions:
            try:
                match_ids.append(int(str(s["X"])))
            except (KeyError, ValueError):
                pass

        tree_ids = get_accessible_tree_ids(g.user)
        if tree_ids:
            people = Person.select().where(
                Person.id.in_(match_ids) & Person.tree.in_(tree_ids)
            )
        else:
            people = []

        results = [
            {
                "id": p.id,
                "firstName": p.firstName,
                "middleName": p.middleName,
                "lastName": p.lastName,
            }
            for p in people
        ]
        return {"person_id": person_id, "relationship": relationship, "results": results}, 200


api.add_resource(SearchRelationshipEndpoint, "/query/relationship/search")

# =====================================================
#               FAMILY TREE SECTION
# =====================================================
# Generates family tree visualization data as React Flow nodes and edges.

# Need to build an endpoint that gets family tree data as React Flow nodes and edges, then displays them:
# For AUTHORIZED users only!!!
class FamilyTreeEndpoint(Resource):
    @require_auth
    def get(self, person_id):
        try:
            root_person = Person.get(Person.id == person_id)
        except Person.DoesNotExist:
            abort(404)

        # Tree access via family group membership:
        if getattr(root_person, "tree_id", None) is None:
            abort(400, description="Person is not assigned to a tree.")

        root_tree = root_person.tree

        from utilities import user_can_access_tree

        if not user_can_access_tree(g.user, root_tree):
            abort(403)

        # Collect family as before, but restrict results to the same tree.
        people, parent_edges, spouse_edges = collect_family(root_person)

        # Filter to same-tree people only (prevents accidental cross-tree merges)
        people = {pid: p for pid, p in people.items() if getattr(p, "tree_id", None) == root_tree.id}

        # Filter edges so they only include nodes we kept
        allowed_ids = set(people.keys())
        parent_edges = [(a, b) for (a, b) in parent_edges if a in allowed_ids and b in allowed_ids]
        spouse_edges = [(a, b) for (a, b) in spouse_edges if a in allowed_ids and b in allowed_ids]

        NODE_WIDTH = 160
        V_SPACING = 180
        SPOUSE_GAP = 40
        NODE_HEIGHT = 60

        FAMILY_COLORS = [
            "#6C8AE4",
            "#8B2908",
            "#07572B",
            "#6E165B",
            "#628103",
            "#0A8488",
            "#805C08",
        ]

        generation = assign_generations(root_person.id, people, parent_edges, spouse_edges)
        two_parent_families, single_parent_families = build_family_groups(people, parent_edges)
        spouse_map = build_spouse_map(spouse_edges)

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

        snap_spouse_only_people(
            positions,
            people,
            two_parent_families,
            single_parent_families,
            node_width=NODE_WIDTH,
            spouse_gap=SPOUSE_GAP,
        )

        center_top_families_over_immediate_children(
            positions,
            generation,
            two_parent_families,
            single_parent_families,
            node_width=NODE_WIDTH,
            spouse_gap=SPOUSE_GAP,
        )

        spread_top_family_blocks(
            positions,
            generation,
            two_parent_families,
            single_parent_families,
            node_width=NODE_WIDTH,
            spouse_gap=SPOUSE_GAP,
            family_gap=80,
        )

        family_row_offsets = {}
        families_by_generation = defaultdict(list)

        family_colors = {}
        gen_family_index = {}
        single_family_colors = {}

        for (p1_id, p2_id), child_ids in two_parent_families.items():
            if p1_id not in generation:
                continue

            gen = generation[p1_id]
            if gen not in gen_family_index:
                gen_family_index[gen] = 0

            color_idx = gen_family_index[gen] % len(FAMILY_COLORS)
            gen_family_index[gen] += 1
            family_colors[(p1_id, p2_id)] = FAMILY_COLORS[color_idx]

        for parent_id, child_ids in single_parent_families.items():
            if parent_id not in generation:
                continue

            gen = generation[parent_id]
            if gen not in gen_family_index:
                gen_family_index[gen] = 0

            color_idx = gen_family_index[gen] % len(FAMILY_COLORS)
            gen_family_index[gen] += 1
            single_family_colors[parent_id] = FAMILY_COLORS[color_idx]

        for (p1_id, p2_id), child_ids in two_parent_families.items():
            if p1_id in generation:
                gen = generation[p1_id]
                families_by_generation[gen].append(("two", p1_id, p2_id))

        for parent_id, child_ids in single_parent_families.items():
            if parent_id in generation:
                gen = generation[parent_id]
                families_by_generation[gen].append(("one", parent_id))

        for gen, fams in families_by_generation.items():
            fams.sort()
            for idx, fam in enumerate(fams):
                family_row_offsets[fam] = idx % 3

        nodes = []
        edges = []
        added_nodes = set()
        added_edges = set()

        # Person nodes
        for pid, person in people.items():
            gender_name = (person.gender.name or "").lower()

            nodes.append({
                "id": str(pid),
                "type": "person",
                "data": {
                    "label": f"{person.firstName} {person.lastName}",
                    "years": format_years(person),
                    "personId": pid,
                },
                "position": positions[pid],
                "style": {
                    "background": "#FFB6C1" if gender_name == "female" else "#87CEEB",
                    "border": "2px solid #333",
                    "borderRadius": "8px",
                    "padding": "10px",
                    "width": NODE_WIDTH,
                }
            })
            added_nodes.add(str(pid))

        # Spouse edges (keep these for visual spouse links)
        for a, b in set(spouse_edges):
            if a not in positions or b not in positions:
                continue

            if positions[a]["x"] <= positions[b]["x"]:
                source_id, target_id = a, b
            else:
                source_id, target_id = b, a

            add_edge_once(edges, added_edges, {
                "id": f"spouse-{source_id}-{target_id}",
                "source": str(source_id),
                "target": str(target_id),
                "sourceHandle": "spouse-right",
                "targetHandle": "spouse-left",
                "type": "straight",
                "style": {
                    "stroke": "#FF69B4",
                    "strokeWidth": 2,
                },
            })

        # Two-parent families
        # Keep the original clean visual shape:
        # spouse line is visible, attach->route is visible, route->child is visible.
        # Add hidden parent->attach edges only so BFS can traverse the graph.
        for (p1_id, p2_id), child_ids in two_parent_families.items():
            if p1_id not in positions or p2_id not in positions:
                continue

            visible_children = [cid for cid in child_ids if cid in positions]
            if not visible_children:
                continue

            p1_center = positions[p1_id]["x"] + NODE_WIDTH / 2
            p2_center = positions[p2_id]["x"] + NODE_WIDTH / 2
            mid_x = (p1_center + p2_center) / 2

            # midpoint of spouse row
            attach_y = positions[p1_id]["y"] + NODE_HEIGHT / 2
            offset_band = family_row_offsets.get(("two", p1_id, p2_id), 0)
            route_y = positions[p1_id]["y"] + NODE_HEIGHT + 25 + (offset_band * 24)

            attach_id = f"attach-{p1_id}-{p2_id}"
            route_id = f"route-{p1_id}-{p2_id}"
            color = family_colors.get((p1_id, p2_id), "#777777")

            add_junction_node(nodes, added_nodes, attach_id, mid_x, attach_y, "#FF69B4")
            add_junction_node(nodes, added_nodes, route_id, mid_x, route_y, color)

            # add metadata so frontend can highlight the top parent people too
            for n in nodes:
                if n["id"] == route_id:
                    n["data"]["familyType"] = "two"
                    n["data"]["parentIds"] = [p1_id, p2_id]
                    break

            # VISIBLE: midpoint drops down into the child route
            add_edge_once(edges, added_edges, {
                "id": f"{attach_id}-{route_id}",
                "source": attach_id,
                "target": route_id,
                "sourceHandle": "bottom",
                "targetHandle": "top",
                "type": "straight",
                "style": {
                    "stroke": color,
                    "strokeWidth": 2,
                },
            })

            # VISIBLE: route fans out to children
            for child_id in visible_children:
                add_edge_once(edges, added_edges, {
                    "id": f"{route_id}-{child_id}",
                    "source": route_id,
                    "target": str(child_id),
                    "sourceHandle": "bottom",
                    "targetHandle": "top",
                    "type": "step",
                    "style": {
                        "stroke": color,
                        "strokeWidth": 2,
                    },
                })

            # HIDDEN: connect parents into the graph for traversal only
            add_edge_once(edges, added_edges, {
                "id": f"hidden-{p1_id}-{attach_id}",
                "source": str(p1_id),
                "target": attach_id,
                "sourceHandle": "bottom",
                "targetHandle": "top",
                "type": "straight",
                "style": {
                    "stroke": "rgba(0,0,0,0)",
                    "strokeWidth": 0,
                },
                "selectable": False,
                "focusable": False,
            })

            add_edge_once(edges, added_edges, {
                "id": f"hidden-{p2_id}-{attach_id}",
                "source": str(p2_id),
                "target": attach_id,
                "sourceHandle": "bottom",
                "targetHandle": "top",
                "type": "straight",
                "style": {
                    "stroke": "rgba(0,0,0,0)",
                    "strokeWidth": 0,
                },
                "selectable": False,
                "focusable": False,
            })

        # Single-parent families
        # Keep the original clean visual shape and add one hidden connector edge.
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

            # VISIBLE
            add_edge_once(edges, added_edges, {
                "id": f"{attach_id}-{route_id}",
                "source": attach_id,
                "target": route_id,
                "sourceHandle": "bottom",
                "targetHandle": "top",
                "type": "straight",
                "style": {
                    "stroke": color,
                    "strokeWidth": 2,
                },
            })

            for child_id in visible_children:
                add_edge_once(edges, added_edges, {
                    "id": f"{route_id}-{child_id}",
                    "source": route_id,
                    "target": str(child_id),
                    "sourceHandle": "bottom",
                    "targetHandle": "top",
                    "type": "step",
                    "style": {
                        "stroke": color,
                        "strokeWidth": 2,
                    },
                })

            # HIDDEN
            add_edge_once(edges, added_edges, {
                "id": f"hidden-{parent_id}-{attach_id}",
                "source": str(parent_id),
                "target": attach_id,
                "sourceHandle": "bottom",
                "targetHandle": "top",
                "type": "straight",
                "style": {
                    "stroke": "rgba(0,0,0,0)",
                    "strokeWidth": 0,
                },
                "selectable": False,
                "focusable": False,
            })

        return {"nodes": nodes, "edges": edges}, 200

# Add the FamilyTreeEndpoint API endpoint:
api.add_resource(FamilyTreeEndpoint, "/tree/<int:person_id>")

# =====================================================
#             FAMILY GROUP MEMBERSHIP SECTION
# =====================================================
# Access to trees is granted via FamilyGroup membership.


def _get_group_or_404(group_id: int) -> FamilyGroup:
    try:
        return FamilyGroup.get(FamilyGroup.id == int(group_id))
    except Exception:
        abort(404)


def _require_group_member(group: FamilyGroup):
    membership = FamilyGroupMember.get_or_none(
        (FamilyGroupMember.family_group == group) & (FamilyGroupMember.user == g.user)
    )
    if not membership:
        abort(403)
    return membership


def _require_group_role_at_least(group: FamilyGroup, required_role: str):
    from utilities import user_has_family_group_role_at_least

    if not user_has_family_group_role_at_least(g.user, group, required_role):
        abort(403)


class FamilyGroupMembersEndpoint(Resource):
    """List members (any member) and add a member (owner/editor)."""

    @require_auth
    def get(self, group_id):
        group = _get_group_or_404(group_id)
        _require_group_member(group)

        members = []
        query = (
            FamilyGroupMember.select(FamilyGroupMember, User)
            .join(User)
            .where(FamilyGroupMember.family_group == group)
            .order_by(User.username)
        )

        for m in query:
            members.append(
                {
                    "userId": m.user.id,
                    "username": m.user.username,
                    "role": m.role,
                }
            )

        return {
            "familyGroup": {"id": group.id, "name": group.name, "ownerUserId": group.owner_id},
            "members": members,
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

        try:
            user_to_add = User.get(User.username == username)
        except User.DoesNotExist:
            abort(404, description="User not found")

        if FamilyGroupMember.select().where(
            (FamilyGroupMember.family_group == group) & (FamilyGroupMember.user == user_to_add)
        ).exists():
            return {"status": "already_member"}, 200

        # Only an owner can add another owner.
        if role == "owner":
            _require_group_role_at_least(group, "owner")

        FamilyGroupMember.create(family_group=group, user=user_to_add, role=role)

        return {
            "status": "added",
            "userId": user_to_add.id,
            "username": user_to_add.username,
            "role": role,
        }, 201


api.add_resource(FamilyGroupMembersEndpoint, "/family-groups/<int:group_id>/members")


class FamilyGroupMemberDetailEndpoint(Resource):
    """Update role (owner only) or remove a member (owner only)."""

    @require_auth
    def patch(self, group_id, user_id):
        group = _get_group_or_404(group_id)
        _require_group_role_at_least(group, "owner")

        data = get_json_or_400(required_fields=["role"])
        new_role = (data.get("role") or "").strip().lower()
        if new_role not in ("viewer", "editor", "owner"):
            abort(400, description="Invalid role")

        membership = FamilyGroupMember.get_or_none(
            (FamilyGroupMember.family_group == group) & (FamilyGroupMember.user == int(user_id))
        )
        if not membership:
            abort(404)

        # Prevent downgrading the group's owner without an explicit ownership-transfer flow.
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
            (FamilyGroupMember.family_group == group) & (FamilyGroupMember.user == int(user_id))
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
    """List family groups the current user belongs to."""

    @require_auth
    def get(self):
        groups = []

        query = (
            FamilyGroupMember.select(FamilyGroupMember, FamilyGroup)
            .join(FamilyGroup)
            .where(FamilyGroupMember.user == g.user)
            .order_by(FamilyGroup.name)
        )

        for m in query:
            groups.append(
                {
                    "id": m.family_group.id,
                    "name": m.family_group.name,
                    "ownerUserId": m.family_group.owner_id,
                    "myRole": m.role,
                }
            )

        return {"familyGroups": groups}, 200


api.add_resource(MyFamilyGroupsEndpoint, "/family-groups")

# =====================================================
#                    TREE SECTION
# =====================================================
# Discovery and management of family trees (via family group membership).

class MyTreesEndpoint(Resource):
    """List trees the current user can access via family group membership."""

    @require_auth
    def get(self):
        # Trees are accessible if the user is a member of the tree's family group.
        # (Legacy personal trees without a family_group are only accessible by owner.)
        trees = []

        # Trees with a family group: join through FamilyGroupMember
        q1 = (
            Tree.select(Tree, FamilyGroup)
            .join(FamilyGroup, JOIN.LEFT_OUTER)
            .switch(Tree)
            .join(FamilyGroupMember, JOIN.LEFT_OUTER, on=(Tree.family_group == FamilyGroupMember.family_group))
            .where(
                (Tree.family_group.is_null(False))
                & (FamilyGroupMember.user == g.user)
            )
            .order_by(Tree.name)
        )

        for t in q1:
            trees.append(
                {
                    "id": t.id,
                    "name": t.name,
                    "ownerUserId": t.owner_id,
                    "familyGroupId": t.family_group_id,
                    "familyGroupName": t.family_group.name if t.family_group_id else None,
                }
            )

        # Legacy / personal trees (no family group) - owner only
        q2 = Tree.select().where((Tree.family_group.is_null(True)) & (Tree.owner == g.user)).order_by(Tree.name)
        for t in q2:
            trees.append(
                {
                    "id": t.id,
                    "name": t.name,
                    "ownerUserId": t.owner_id,
                    "familyGroupId": None,
                    "familyGroupName": None,
                }
            )

        # De-dupe by id in case of joins
        deduped = {t["id"]: t for t in trees}
        return {"trees": list(deduped.values())}, 200


class FamilyGroupTreesEndpoint(Resource):
    """List trees in a family group (member-only) and create a tree (editor+)."""

    @require_auth
    def get(self, group_id):
        group = _get_group_or_404(group_id)
        _require_group_member(group)

        trees = []
        for t in Tree.select().where(Tree.family_group == group).order_by(Tree.name):
            trees.append(
                {
                    "id": t.id,
                    "name": t.name,
                    "ownerUserId": t.owner_id,
                    "familyGroupId": group.id,
                    "familyGroupName": group.name,
                }
            )

        return {"familyGroup": {"id": group.id, "name": group.name}, "trees": trees}, 200

    @require_auth
    def post(self, group_id):
        group = _get_group_or_404(group_id)
        _require_group_role_at_least(group, "editor")

        data = get_json_or_400(required_fields=["name"])
        name = (data.get("name") or "").strip()
        if not name:
            abort(400, description="name is required")

        # Create a new tree in this family group. Owner is the creator.
        tree = Tree.create(name=name, owner=g.user, family_group=group)

        return {
            "id": tree.id,
            "name": tree.name,
            "ownerUserId": tree.owner_id,
            "familyGroupId": group.id,
        }, 201


api.add_resource(MyTreesEndpoint, "/trees")
api.add_resource(FamilyGroupTreesEndpoint, "/family-groups/<int:group_id>/trees")

# =====================================================
#                    NEW TREE VIEW SECTION
# =====================================================
# View a family tree by tree_id (not by picking a root person id in the URL).

class TreeByIdEndpoint(Resource):
    """View a tree by tree_id (not by picking a root person id in the URL).

    This returns the same React Flow graph format as FamilyTreeEndpoint.
    """

    @require_auth
    def get(self, tree_id):
        try:
            tree = Tree.get(Tree.id == int(tree_id))
        except Exception:
            abort(404)

        from utilities import user_can_access_tree

        if not user_can_access_tree(g.user, tree):
            abort(403)

        # Pick a root person for rendering.
        # Prefer someone with no parents, otherwise fall back to the lowest id in the tree.
        root_person = (
            Person.select()
            .where(
                (Person.tree == tree)
                & (Person.parent1_id.is_null(True))
                & (Person.parent2_id.is_null(True))
            )
            .order_by(Person.id)
            .first()
        )
        if root_person is None:
            root_person = Person.select().where(Person.tree == tree).order_by(Person.id).first()

        if root_person is None:
            return {"nodes": [], "edges": [], "treeId": tree.id, "message": "This tree has no people yet. Add a person to begin building your tree."}, 200

        # Build graph and scope it to the tree
        people, parent_edges, spouse_edges = collect_family(root_person)
        people = {pid: p for pid, p in people.items() if getattr(p, "tree_id", None) == tree.id}

        allowed_ids = set(people.keys())
        parent_edges = [(a, b) for (a, b) in parent_edges if a in allowed_ids and b in allowed_ids]
        spouse_edges = [(a, b) for (a, b) in spouse_edges if a in allowed_ids and b in allowed_ids]

        # Reuse the existing layout code by delegating to FamilyTreeEndpoint logic.
        # (We inline the minimal shared constants here; rest of code below remains unchanged.)
        NODE_WIDTH = 160
        V_SPACING = 180
        SPOUSE_GAP = 40
        NODE_HEIGHT = 60

        FAMILY_COLORS = [
            "#6C8AE4",
            "#8B2908",
            "#07572B",
            "#6E165B",
            "#628103",
            "#0A8488",
            "#805C08",
        ]

        generation = assign_generations(root_person.id, people, parent_edges, spouse_edges)
        two_parent_families, single_parent_families = build_family_groups(people, parent_edges)
        spouse_map = build_spouse_map(spouse_edges)

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

        snap_spouse_only_people(
            positions,
            people,
            two_parent_families,
            single_parent_families,
            node_width=NODE_WIDTH,
            spouse_gap=SPOUSE_GAP,
        )

        center_top_families_over_immediate_children(
            positions,
            generation,
            two_parent_families,
            single_parent_families,
            node_width=NODE_WIDTH,
            spouse_gap=SPOUSE_GAP,
        )

        spread_top_family_blocks(
            positions,
            generation,
            two_parent_families,
            single_parent_families,
            node_width=NODE_WIDTH,
            spouse_gap=SPOUSE_GAP,
            family_gap=80,
        )

        family_row_offsets = {}
        families_by_generation = defaultdict(list)

        family_colors = {}
        gen_family_index = {}
        single_family_colors = {}

        for (p1_id, p2_id), child_ids in two_parent_families.items():
            if p1_id not in generation:
                continue

            gen = generation[p1_id]
            if gen not in gen_family_index:
                gen_family_index[gen] = 0

            color_idx = gen_family_index[gen] % len(FAMILY_COLORS)
            gen_family_index[gen] += 1
            family_colors[(p1_id, p2_id)] = FAMILY_COLORS[color_idx]

        for parent_id, child_ids in single_parent_families.items():
            if parent_id not in generation:
                continue

            gen = generation[parent_id]
            if gen not in gen_family_index:
                gen_family_index[gen] = 0

            color_idx = gen_family_index[gen] % len(FAMILY_COLORS)
            gen_family_index[gen] += 1
            single_family_colors[parent_id] = FAMILY_COLORS[color_idx]

        for (p1_id, p2_id), child_ids in two_parent_families.items():
            if p1_id in generation:
                gen = generation[p1_id]
                families_by_generation[gen].append(("two", p1_id, p2_id))

        for parent_id, child_ids in single_parent_families.items():
            if parent_id in generation:
                gen = generation[parent_id]
                families_by_generation[gen].append(("one", parent_id))

        for gen, fams in families_by_generation.items():
            fams.sort()
            for idx, fam in enumerate(fams):
                family_row_offsets[fam] = idx % 3

        nodes = []
        edges = []
        added_nodes = set()
        added_edges = set()

        # Person nodes
        for pid, person in people.items():
            gender_name = (person.gender.name or "").lower()

            nodes.append({
                "id": str(pid),
                "type": "person",
                "data": {
                    "label": f"{person.firstName} {person.lastName}",
                    "years": format_years(person),
                    "personId": pid,
                },
                "position": positions[pid],
                "style": {
                    "background": "#FFB6C1" if gender_name == "female" else "#87CEEB",
                    "border": "2px solid #333",
                    "borderRadius": "8px",
                    "padding": "10px",
                    "width": NODE_WIDTH,
                }
            })
            added_nodes.add(str(pid))

        # Spouse edges
        for a, b in set(spouse_edges):
            if a not in positions or b not in positions:
                continue

            if positions[a]["x"] <= positions[b]["x"]:
                source_id, target_id = a, b
            else:
                source_id, target_id = b, a

            add_edge_once(edges, added_edges, {
                "id": f"spouse-{source_id}-{target_id}",
                "source": str(source_id),
                "target": str(target_id),
                "sourceHandle": "spouse-right",
                "targetHandle": "spouse-left",
                "type": "straight",
                "style": {
                    "stroke": "#FF69B4",
                    "strokeWidth": 2,
                },
            })

        # Two-parent families
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
                "style": {
                    "stroke": color,
                    "strokeWidth": 2,
                },
            })

            for child_id in visible_children:
                add_edge_once(edges, added_edges, {
                    "id": f"{route_id}-{child_id}",
                    "source": route_id,
                    "target": str(child_id),
                    "sourceHandle": "bottom",
                    "targetHandle": "top",
                    "type": "step",
                    "style": {
                        "stroke": color,
                        "strokeWidth": 2,
                    },
                })

            add_edge_once(edges, added_edges, {
                "id": f"hidden-{p1_id}-{attach_id}",
                "source": str(p1_id),
                "target": attach_id,
                "sourceHandle": "bottom",
                "targetHandle": "top",
                "type": "straight",
                "style": {
                    "stroke": "rgba(0,0,0,0)",
                    "strokeWidth": 0,
                },
                "selectable": False,
                "focusable": False,
            })

            add_edge_once(edges, added_edges, {
                "id": f"hidden-{p2_id}-{attach_id}",
                "source": str(p2_id),
                "target": attach_id,
                "sourceHandle": "bottom",
                "targetHandle": "top",
                "type": "straight",
                "style": {
                    "stroke": "rgba(0,0,0,0)",
                    "strokeWidth": 0,
                },
                "selectable": False,
                "focusable": False,
            })

        # Single-parent families
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
                "style": {
                    "stroke": color,
                    "strokeWidth": 2,
                },
            })

            for child_id in visible_children:
                add_edge_once(edges, added_edges, {
                    "id": f"{route_id}-{child_id}",
                    "source": route_id,
                    "target": str(child_id),
                    "sourceHandle": "bottom",
                    "targetHandle": "top",
                    "type": "step",
                    "style": {
                        "stroke": color,
                        "strokeWidth": 2,
                    },
                })

            add_edge_once(edges, added_edges, {
                "id": f"hidden-{parent_id}-{attach_id}",
                "source": str(parent_id),
                "target": attach_id,
                "sourceHandle": "bottom",
                "targetHandle": "top",
                "type": "straight",
                "style": {
                    "stroke": "rgba(0,0,0,0)",
                    "strokeWidth": 0,
                },
                "selectable": False,
                "focusable": False,
            })

        return {"nodes": nodes, "edges": edges, "treeId": tree.id, "rootPersonId": root_person.id}, 200


api.add_resource(TreeByIdEndpoint, "/trees/<int:tree_id>/view")


if __name__ == "__main__":
    # Local dev entrypoint. Keep HTTP so the SPA can call the API at http://127.0.0.1:5000.
    # (The before_request HTTPS redirect is bypassed when app.debug is True.)
    app.run(host="127.0.0.1", port=5000, debug=True)