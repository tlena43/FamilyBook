import os
from datetime import datetime
import bcrypt
import peewee
from dotenv import load_dotenv
from flask import Flask, abort, g, redirect, request, send_from_directory
from flask_compress import Compress
from flask_restful import Api, Resource
from pdf2image import convert_from_path
from models import *
from utilities import *
from pyswip import Prolog

load_dotenv()

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


##endpoints
class CheckLoginEndpoint(Resource):
    @require_auth
    def get(self):
        return {"privacyLevel": g.user.privacy.level}, 200


api.add_resource(CheckLoginEndpoint, "/loginCheck")


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


class CacheEndpoint(Resource):
    def get(self, filename):
        makeCachedUpload(app, filename)
        return send_from_directory(app.config["CACHE_FOLDER"], filename)


api.add_resource(CacheEndpoint, "/upload/cache/<string:filename>")


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
                "firstName",
                "lastName",
                "gender",
                "isDead",
                "middleName",
                "maidenName",
                "privacy",
            ]
        )

        person = Person.create(
            birthDay=parse_optional_date(data["birthDay"]),
            birthDateUnknowns=data["birthDateUnknowns"],
            deathDateUnknowns=data["deathDateUnknowns"],
            deathDay=parse_optional_date(data["deathDay"]),
            file=parse_optional_int(data["file"]),
            birthplace=parse_optional_str(data["birthplace"]),
            parent1=parse_optional_int(data["parent1"]),
            parent2=parse_optional_int(data["parent2"]),
            firstName=data["firstName"],
            lastName=data["lastName"],
            gender=int(data["gender"]),
            isDead=data["isDead"],
            middleName=parse_optional_str(data["middleName"]),
            maidenName=parse_optional_str(data["maidenName"]),
            privacy=int(data["privacy"]),
        )

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
            ]
        )

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
            parent1=parse_optional_int(data["parent1"]),
            parent2=parse_optional_int(data["parent2"]),
            firstName=data["firstName"],
            lastName=data["lastName"],
            gender=int(data["gender"]),
            isDead=data["isDead"],
            middleName=parse_optional_str(data["middleName"]),
            maidenName=parse_optional_str(data["maidenName"]),
            privacy=int(data["privacy"]),
        ).where(Person.id == id).execute()

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)