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
        try:
            root_person = Person.get(Person.id == person_id)
        except Person.DoesNotExist:
            abort(404)

        if not g.user.hasPrivacyLevel(root_person.privacy):
            abort(403)

        people, parent_edges, spouse_edges = collect_family(root_person)

        NODE_WIDTH = 160
        H_SPACING = 220
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
        rows = build_rows(generation)
        spouse_map = build_spouse_map(spouse_edges)
        rows = order_rows(rows, spouse_map)
        positions = assign_positions(rows, spouse_edges,H_SPACING, V_SPACING, NODE_WIDTH, SPOUSE_GAP)
        

        two_parent_families, single_parent_families = build_family_groups(people)
        
        align_last_generation_under_parents(
            positions,
            generation,
            two_parent_families,
            single_parent_families,
            node_width=NODE_WIDTH,
            child_spacing=200,
        )
        
        maxGen = max(generation.values()) - 1

        for gen in range(1, maxGen):
            center_generation_over_children(
                positions,
                generation,
                two_parent_families,
                single_parent_families,
                target_generation=gen,
                node_width=NODE_WIDTH,
                spouse_gap=40,
            )

        
        family_row_offsets = {}
        families_by_generation = defaultdict(list)
        
        family_colors = {}
        gen_family_index = {}

        for (p1_id, p2_id), child_ids in two_parent_families.items():
            if p1_id not in generation:
                continue

            gen = generation[p1_id]

            if gen not in gen_family_index:
                gen_family_index[gen] = 0

            color_idx = gen_family_index[gen] % len(FAMILY_COLORS)
            gen_family_index[gen] += 1

            family_colors[(p1_id, p2_id)] = FAMILY_COLORS[color_idx]

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

        for pid, person in people.items():
            gender_name = (person.gender.name or "").lower()

            nodes.append({
                "id": str(pid),
                "type": "person",
                "data": {
                    "label": f"{person.firstName} {person.lastName}",
                    "years": format_years(person),
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

        # spouse lines
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
                "sourceHandle": "right",
                "targetHandle": "left",
                "type": "straight",
                "style": {
                    "stroke": "#FF69B4",
                    "strokeWidth": 2,
                },
            })

        # two-parent children: one shared drop only
        for (p1_id, p2_id), child_ids in two_parent_families.items():
            if p1_id not in positions or p2_id not in positions:
                continue

            visible_children = [cid for cid in child_ids if cid in positions]
            if not visible_children:
                continue

            p1_center = positions[p1_id]["x"] + NODE_WIDTH / 2
            p2_center = positions[p2_id]["x"] + NODE_WIDTH / 2
            mid_x = (p1_center + p2_center) / 2

            # This is the y-position of the spouse line / node midpoint
            attach_y = positions[p1_id]["y"] + NODE_HEIGHT / 2

            # This is your staggered routing height
            offset_band = family_row_offsets.get(("two", p1_id, p2_id), 0)
            route_y = positions[p1_id]["y"] + NODE_HEIGHT + 25 + (offset_band * 24)

            attach_id = f"attach-{p1_id}-{p2_id}"
            route_id = f"route-{p1_id}-{p2_id}"

            add_junction_node(nodes, added_nodes, attach_id, mid_x, attach_y)
            add_junction_node(nodes, added_nodes, route_id, mid_x, route_y)

            color = family_colors.get((p1_id, p2_id), "#777777")

            # short vertical from spouse line down to routed level
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

        # single-parent children: direct line
        for parent_id, child_ids in single_parent_families.items():
            if parent_id not in positions:
                continue

            for child_id in child_ids:
                if child_id not in positions:
                    continue

                add_edge_once(edges, added_edges, {
                    "id": f"{parent_id}-{child_id}",
                    "source": str(parent_id),
                    "target": str(child_id),
                    "sourceHandle": "bottom",
                    "targetHandle": "top",
                    "type": "step",
                    "style": {"strokeWidth": 1.5},
                })

        return {"nodes": nodes, "edges": edges}, 200

# Add the FamilyTreeEndpoint API endpoint:
api.add_resource(FamilyTreeEndpoint, "/tree/<int:person_id>")

# Initialize Prolog when the application starts:
#initialize_prolog()

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)