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
        return {"privacyLevel": g.user.privacy.level}, 200


api.add_resource(CheckLoginEndpoint, "/loginCheck")


# =====================================================
#                  UPLOAD SECTION
# =====================================================
# Handles file uploads, downloads, and deletions for documents/images.

class UploadEndpoint(Resource):
    @require_admin
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

    @require_admin
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
    @require_admin
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
                "privacy",
                "children"
            ]
        )
        
        children = data["children"]
   
        person = Person.create(
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
            privacy=int(data["privacy"]),
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
        living_birthday_allowed = g.user.hasPrivacyLevel(get_family_privacy())

        if id is None:
            person_list = {"people": []}
            people = Person.select()

            for person in people.iterator():
                if not g.user.hasPrivacyLevel(person.privacy):
                    continue
                person_list["people"].append(
                    serialize_person_summary(person, living_birthday_allowed)
                )

            return person_list, 200

        try:
            person = Person.get(Person.id == id)
        except Person.DoesNotExist:
            abort(404)

        if not g.user.hasPrivacyLevel(person.privacy):
            abort(403)

        content_list = []
        for c in person.content:
            content = c.content
            if not g.user.hasPrivacyLevel(content.privacy):
                continue
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
            "birthDay": (
                str(person.birthDay)
                if person.isDead or living_birthday_allowed
                else "not_allowed"
            ),
            "birthDateUnknowns": person.birthDateUnknowns,
            "deathDay": str(person.deathDay),
            "deathDateUnknowns": person.deathDateUnknowns,
            "maidenName": person.maidenName,
            "birthplace": person.birthplace,
            "isDead": person.isDead,
            "content": content_list,
            "gender": person.gender.id,
            "privacy": person.privacy.id,
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

    @require_admin
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
                "privacy",
                "spouse",
                "children"
            ]
        )
        
        id = int(id)

        try:
            existing_person = Person.get(Person.id == id)
        except Person.DoesNotExist:
            abort(404)

        file_value = parse_optional_int(data["file"], default=existing_person.file)

        Person.update(
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
            privacy=int(data["privacy"]),
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

    @require_admin
    def delete(self, id):
        try:
            person = Person.get(Person.id == id)
        except Person.DoesNotExist:
            abort(404)

        Person_Content.delete().where(Person_Content.person == id).execute()
        person.delete_instance()

        return {"status": "deleted"}, 200


api.add_resource(PersonEndpoint, "/person", "/person/<int:id>")


# =====================================================
#                  CONTENT SECTION
# =====================================================
# CRUD operations for family documents and media content.

class ContentEndpoint(Resource):
    @require_admin
    def post(self):
        data = get_json_or_400(
            required_fields=[
                "user",
                "privacy",
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
            privacy=int(data["privacy"]),
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
            contents = Content.select()

            for content in contents.iterator():
                if not g.user.hasPrivacyLevel(content.privacy):
                    continue
                content_list["content"].append(serialize_content_summary(content))

            return content_list, 200

        try:
            content = Content.get(Content.id == id)
        except Content.DoesNotExist:
            abort(404)

        if not g.user.hasPrivacyLevel(content.privacy):
            abort(403)

        person_list = []
        for p in content.person:
            person = p.person
            if not g.user.hasPrivacyLevel(person.privacy):
                continue
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
            "privacy": content.privacy.id,
        }

        return result, 200

    @require_admin
    def patch(self, id):
        data = get_json_or_400(
            required_fields=[
                "privacy",
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
            privacy=int(data["privacy"]),
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

    @require_admin
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
            "privacyLevel": user.privacy.level,
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

        # Create new user with default privacy level (PUBLIC):
        try:
            public_privacy = Privacy.get(Privacy.level == "PUBLIC")
        except Privacy.DoesNotExist:
            abort(500, description="Default privacy level not found.")

        hashed_password = bcrypt.hashpw(password.encode("utf8"), bcrypt.gensalt()).decode("utf8")
        
        new_user = User.create(
            username=username,
            password=hashed_password,
            privacy=public_privacy
        )

        return {
            "key": signer.sign(str(new_user.id)).decode("utf8"),
            "privacyLevel": new_user.privacy.level,
            "message": "Account created successfully!"
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
    rules_file = os.path.join(APP_DIR, "prolog", "family_rules.pl")

    if os.path.exists(rules_file):
        try:
            # Use absolute path and escape it properly for Prolog:
            escaped_path = rules_file.replace("\\", "\\\\").replace("'", "\\'")
            prolog_engine.consult(escaped_path)
            print(f"DEBUG: Loaded Prolog rules from {rules_file}")
        except Exception as e:
            print(f"WARNING: Failed to load Prolog rules: {e}")
    else:
        print(f"WARNING: Prolog rules file not found at {rules_file}")

# Need to connect the database to the Prolog engine (note that we only want the base facts, rest is inferred):
def load_prolog_facts(prolog_engine):
    """This function loads a person's data from the database in the form of Prolog facts."""
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
        relationship = data["relationship"]

        # Reload facts each time this endpoint is called (can improve by implementing catching!):
        load_prolog_facts(prolog_engine)

        # Build the Prolog query, run it, and handle any surfacing errors:
        try: 
            query = f"{relationship}({person1_id}, {person2_id})"
            result = list(prolog_engine.query(query))

            if result:
                return {"relationship": relationship, "exists": True}, 200
            else:
                return {"relationship": relationship, "exists": False}, 200
        except Exception as e:
            abort(400, description=f"Invalid relationship query: {str(e)}")

# Register the QueryRelationshipEndpoing API endpoint:
api.add_resource(QueryRelationshipEndpoint, "/query/relationship")

# =====================================================
#               FAMILY TREE SECTION
# =====================================================
# Generates family tree visualization data as React Flow nodes and edges.

# Need to build an endpoint that gets family tree data as React Flow nodes and edges, then displays them:
# For AUTHORIZED users only!!!
class FamilyTreeEndpoint(Resource):
    @require_auth
    def get(self, person_id):
        """Get family tree data in the form of React Flow nodes and edges."""
        # Start with our "root" person:
        try:
            root_person = Person.get(Person.id == person_id)
        except Person.DoesNotExist:
            abort(404)

        # Check the person's privacy level (based on utilities.py):
        if not g.user.hasPrivacyLevel(root_person.privacy):
            abort(403)

        # Build tree structure:
        nodes = []
        edges = []
        visited = set()

        # Function that builds the person's tree:
        def build_tree(person, x=0, y=0, level=0):
            """Recursively build tree nodes and edges."""
            if person.id in visited:
                return
            visited.add(person.id)

            # Create node for our root person:
            node = {
                "id": str(person.id),
                "data": {
                    "label": f"{person.firstName} {person.lastName}",
                    "birthDay": str(person.birthDay) if person.birthDay else "Unknown",
                    "gender": person.gender.name,
                },
                "position": {"x": x, "y": y},
                "style": {
                    "background": "#FFB6C1" if person.gender.name == "female" else "#87CEEB",
                    "border": "2px solid #333",
                    "borderRadius": "8px",
                    "padding": "10px",
                }
            }

            # Append the node to the tree:
            nodes.append(node)

            # Add the person's parents as edges if visible:
            # Parents go above the person, one on the left, the other on the right.
            if person.parent1_id:
                if g.user.hasPrivacyLevel(person.parent1_id.privacy):
                    edge = {
                        "id": f"edge-{person.parent1_id.id}-{person.id}",
                        "source": str(person.parent1_id.id),
                        "target": str(person.id),
                        "label": "parent",
                    }
                    edges.append(edge)
                    build_tree(person.parent1_id, x - 150, y - 100, level + 1)
            
            if person.parent2_id:
                if g.user.hasPrivacyLevel(person.parent2_id.privacy):
                    edge = {
                        "id": f"edge-{person.parent2_id.id}-{person.id}",
                        "source": str(person.parent2_id.id),
                        "target": str(person.id),
                        "label": "parent",
                    }
                    edges.append(edge)
                    build_tree(person.parent2_id, x + 150, y - 100, level + 1)

            # Add the person's spouse as an edge if visible:
            # Spouses are to the right of the person.
            if person.spouse_id:
                if g.user.hasPrivacyLevel(person.spouse_id.privacy):
                    edge = {
                        "id": f"edge-{person.id}-{person.spouse_id.id}",
                        "source": str(person.id),
                        "target": str(person.spouse_id.id),
                        "label": "spouse",
                        "style": {"stroke": "#FF69B4", "strokeWidth": 2},
                    }
                    edges.append(edge)
                    build_tree(person.spouse_id, x + 100, y, level)

            # Add the person's children as edges if visible:
            # Children are beneath the person and spread out if there are multiple.
            children_list = Person.select().where(
                (Person.parent1_id == person) | (Person.parent2_id == person)
            )
            for idx, child in enumerate(children_list):
                if not g.user.hasPrivacyLevel(child.privacy):
                    continue
                
                edge = {
                    "id": f"edge-{person.id}-{child.id}",
                    "source": str(person.id),
                    "target": str(child.id),
                    "label": "child",
                }
                edges.append(edge)
                child_x = x + (idx - (len(children_list) - 1) / 2) * 200
                build_tree(child, child_x, y + 150, level - 1)

        # Build the tree:
        build_tree(root_person)

        # Return the tree:
        return {
            "nodes": nodes,
            "edges": edges,
        }, 200

# Add the FamilyTreeEndpoint API endpoint:
api.add_resource(FamilyTreeEndpoint, "/tree/<int:person_id>")

# Initialize Prolog when the application starts:
#initialize_prolog()

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)