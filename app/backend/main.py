import bcrypt, hashlib, os
from flask import Flask, request, abort, send_from_directory, g
from flask_restful import Resource, Api
from models import *
from dateutil import parser
from itsdangerous import TimestampSigner, SignatureExpired, BadSignature
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, timedelta
from flask_compress import Compress
from pdf2image import convert_from_path
from playhouse.migrate import *
from utilities import *

secretKey = "R]5~iyq'@,ysP1!FuP#ove,h!rY#:dp74QDYh!o1G*1O4ieKGSp7&V'fE<b[MALwp"
s = TimestampSigner(secretKey)
app = Flask(__name__)
Compress(app)
api = Api(app)
API_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = API_DIR + '/upload'
CACHE_FOLDER = UPLOAD_FOLDER + '/cache'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CACHE_FOLDER'] = CACHE_FOLDER

# run database migrators here
@app.before_first_request
def before_first_request():
    db.connect()
    migrator = None
    if type(db) is SqliteDatabase:
        migrator = SqliteMigrator(db)
    if type(db) is MySQLDatabase:
        migrator = MySQLMigrator(db)
    if 'privacy_id' not in [c.name for c in db.get_columns('person')]:
        print("Adding Person.privacy field...")
        pp = Person.privacy
        pp.default = Privacy.get(Privacy.level == 'admin')
        migrate(migrator.add_column('person', 'privacy_id', pp))
    else:
        print("Person.privacy migration already done")
    db.close()


# opens db connection before request
@app.before_request
def beforeRequest():
    criteria = [ request.is_secure, app.debug, request.headers.get('X-Forwarded-Proto', 'http') == 'https' ]
    if not any(criteria):
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=308)
    db.connect()


# closes db connection after request
@app.after_request
def afterRequest(response):
    response.headers.set("Access-Control-Allow-Origin", "*")
    response.headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, PATCH, DELETE")
    response.headers.set("Access-Control-Allow-Headers", "x-api-key, Content-Type, Content-Length")
    response.headers.set("Content-Disposition", "attachment")
    db.close()
    return response


# whatever this is
def requireAuth(func):
    @wraps(func)
    def inner(*args, **kwargs):
        apiKey = request.headers.get("X-api-key").encode("utf8")
        try:
            g.user = User.get(User.id == int(s.unsign(apiKey, max_age=7 * 24 * 3600).decode("utf8")))
        except SignatureExpired:
            abort(401)
        except BadSignature:
            abort(401)
        except User.DoesNotExist:
            abort(401)
        return func(*args, **kwargs)

    return inner


class checkLoginEndpoint(Resource):
    @requireAuth
    def get(self):
        return {'privacyLevel': g.user.privacy.level}


api.add_resource(checkLoginEndpoint, "/loginCheck")


class UploadEndpoint(Resource):
    '''Upload an image and returns a unique filename. Retrieve image from filename.'''

    @requireAuth
    def post(self):
        if g.user.privacy != Privacy.get(Privacy.level == "admin"):
            abort(401)
        uFile = request.files['upload']
        if uFile and '.' in uFile.filename:
            uFilenameParts = secure_filename(uFile.filename.lower()).rsplit('.', 1)
            if uFilenameParts[1] in {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'odt', 'txt'}:
                isUnique = False
                while not isUnique:
                    uFilename = '%s.%s' % (
                        hashlib.md5((uFilenameParts[0] + datetime.utcnow().isoformat()).encode("utf8")).hexdigest(),
                        uFilenameParts[1])
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], uFilename)
                    isUnique = not os.path.isfile(filepath)
                uFile.save(filepath)
                u = Upload.create(filename=uFilename, timestamp=datetime.utcnow(), owner=g.user)
                return {'filename': uFilename, 'fileid': u.id}, 201
            abort(415)
        abort(400)


    def get(self, filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    def delete(self, filename):
        try:
            file = Upload.get(Upload.filename == filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.delete_instance()
            if os.path.isfile(filepath):
                os.remove(filepath)
        except peewee.IntegrityError:
            abort(409)


api.add_resource(UploadEndpoint, "/upload", "/upload/<string:filename>")


class CacheEndpoint(Resource):
    '''Get cached image preview of uploads. Format example:
        filename.png -> filename_png.jpg
        filename.jpg -> filename_jpg.jpg
        filename.pdf -> filename_pdf.jpg
        filename.pdf -> filename_pdf_<pagenum>.jpg (specific page)'''

    def get(self, filename):
        makeCachedUpload(app, filename)
        return send_from_directory(app.config['CACHE_FOLDER'], filename)


api.add_resource(CacheEndpoint, "/upload/cache/<string:filename>")


class PdfNumPagesEndpoint(Resource):

    def get(self, filename):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        pages = convert_from_path(filepath)
        return {'num_pages': len(pages)}, 200


api.add_resource(PdfNumPagesEndpoint, "/upload/num_pages/<string:filename>")


# endpoint for persons
class PersonEndpoint(Resource):
    @requireAuth
    def post(self):
        if g.user.privacy != Privacy.get(Privacy.level == "admin"):
            abort(401)

        birthDate = None
        deathDate = None
        if request.json["birthDay"] is not None:
            birthDate = parser.parse(request.json["birthDay"])

        if request.json["deathDay"] is not None:
            deathDate = parser.parse(request.json["deathDay"])

        person = Person.create(birthDay=birthDate,
                               birthDateUnknowns=request.json["birthDateUnknowns"],
                               deathDateUnknowns=request.json["deathDateUnknowns"],
                               deathDay=deathDate,
                               file=int(request.json["file"]) if request.json["file"] != "" else None,
                               birthplace=request.json["birthplace"] if request.json["birthplace"] != "" else None,
                               parent1=int(request.json["parent1"]) if request.json["parent1"] != "" else None,
                               parent2=int(request.json["parent2"]) if request.json["parent2"] != "" else None,
                               firstName=request.json["firstName"],
                               lastName=request.json["lastName"], gender=int(request.json["gender"]),
                               isDead=request.json["isDead"],
                               middleName=request.json["middleName"] if request.json["middleName"] != "" else None,
                               maidenName=request.json["maidenName"] if request.json["maidenName"] != "" else None,
                               privacy=int(request.json["privacy"]))
        return {"id": person.id}, 201

    @requireAuth
    def get(self, id=None):
        livingBirthdayAllowed = g.user.hasPrivacyLevel(Privacy.get(Privacy.level == "family"))
        if id == None:
            personList = {"people": []}
            people = Person.select()

            for person in people.iterator():
                if not g.user.hasPrivacyLevel(person.privacy):
                    continue
                fileName = person.file
                if fileName is not None:
                    fileName = fileName.filename
                curPerson = {"firstName": person.firstName, "id": person.id, "lastName": person.lastName,
                             "middleName": person.middleName, "birthDay": str(person.birthDay) if person.isDead or livingBirthdayAllowed else "not_allowed",
                             "fileName": fileName, "birthDateUnknowns": person.birthDateUnknowns}
                personList["people"].append(curPerson)

            return personList



        else:
            try:
                person = Person.select().where(Person.id == id).get()
                if not g.user.hasPrivacyLevel(person.privacy):
                    abort(401)
                fileName = person.file
                if fileName is not None:
                    fileName = fileName.filename

                contentList = []
                for c in person.content:
                    content = c.content
                    if not g.user.hasPrivacyLevel(content.privacy):
                        continue
                    contentJSON = {"id": content.id, "title": content.title}
                    contentList.append(contentJSON)

                res = {"firstName": person.firstName, "id": person.id, "lastName": person.lastName,
                       "middleName": person.middleName, "birthDay": str(person.birthDay) if person.isDead or livingBirthdayAllowed else "not_allowed",
                       "fileName": fileName, "birthDateUnknowns": person.birthDateUnknowns,
                       "deathDay": str(person.deathDay), "deathDateUnknowns": person.deathDateUnknowns,
                       "maidenName": person.maidenName, "birthplace": person.birthplace,
                       "isDead": person.isDead, "content": contentList, "gender": person.gender.id,
                       "privacy": person.privacy.id}

            except Person.DoesNotExist:
                ##handle this later
                abort(404)

        return res

    @requireAuth
    def patch(self, id):
        if g.user.privacy != Privacy.get(Privacy.level == "admin"):
            abort(401)

        birthDate = None
        deathDate = None
        if request.json["birthDay"] is not None:
            birthDate = parser.parse(request.json["birthDay"])

        if request.json["deathDay"] is not None:
            deathDate = parser.parse(request.json["deathDay"])

        Person.update(birthDay=birthDate,
                      birthDateUnknowns=request.json["birthDateUnknowns"],
                      deathDateUnknowns=request.json["deathDateUnknowns"],
                      deathDay=deathDate,
                      file=int(request.json["file"]) if request.json["file"] != "" else Person.get(Person.id == id).file,
                      birthplace=request.json["birthplace"] if request.json["birthplace"] != "" else None,
                      parent1=int(request.json["parent1"]) if request.json["parent1"] != "" else None,
                      parent2=int(request.json["parent2"]) if request.json["parent2"] != "" else None,
                      firstName=request.json["firstName"],
                      lastName=request.json["lastName"], gender=int(request.json["gender"]),
                      isDead=request.json["isDead"],
                      middleName=request.json["middleName"] if request.json["middleName"] != "" else None,
                      maidenName=request.json["maidenName"] if request.json["maidenName"] != "" else None,
                      privacy=int(request.json["privacy"])) \
            .where(Person.id == id).execute()
        return {"id": id}, 200

    @requireAuth
    def delete(self, id):
        if g.user.privacy != Privacy.get(Privacy.level == "admin"):
            abort(401)

        person = Person.get(Person.id == id)
        personContent = Person_Content.delete().where(Person_Content.person == id)
        personContent.execute()
        person.delete_instance()
        return 200


api.add_resource(PersonEndpoint, '/person', "/person/<int:id>")


# endpoint for content
class ContentEndpoint(Resource):
    @requireAuth
    def post(self):
        if g.user.privacy != Privacy.get(Privacy.level == "admin"):
            abort(401)

        date = None
        if request.json["date"] is not None:
            date = parser.parse(request.json["date"])

        content = Content.create(user=int(request.json["user"]), privacy=int(request.json["privacy"]),
                                 type=(int(request.json["type"])) if request.json["type"] != 0 else None,
                                 date=date,
                                 notes=(request.json["notes"]) if request.json["notes"] != "" else None,
                                 title=request.json["title"],
                                 file=int(request.json["file"]),
                                 location=(request.json["location"]) if request.json["location"] != "" else None,
                                 dateUnknowns=request.json["dateUnknowns"])
        if request.json["people"] != []:
            for item in request.json["people"]:
                Person_Content.create(content=content.id, person=item)
        return {"id": content.id}, 201

    @requireAuth
    def get(self, id=None):
        if id == None:
            contentList = {"content": []}
            contents = Content.select()

            for content in contents.iterator():
                if not g.user.hasPrivacyLevel(content.privacy):
                    continue
                curContent = {"title": content.title, "fileName": content.file.filename, "id": content.id}
                contentList["content"].append(curContent)

            return contentList
        else:
            try:
                content = Content.select().where(Content.id == id).get()
                if not g.user.hasPrivacyLevel(content.privacy):
                    abort(401)
                personList = []
                for p in content.person:
                    person = p.person
                    if not g.user.hasPrivacyLevel(person.privacy):
                        continue
                    personJSON = {"id": person.id, "firstName": person.firstName,
                                  "middleName": person.middleName, "lastName": person.lastName,
                                  "birthDay": str(person.birthDay), "birthDateUnknowns": person.birthDateUnknowns}
                    personList.append(personJSON)

                res = {"title": content.title, "fileName": content.file.filename,
                       "type": content.type.name if content.type is not None else None,
                       "date": str(content.date), "dateUnknowns": content.dateUnknowns, "notes": content.notes,
                       "location": content.location, "people": personList, "privacy": content.privacy.id}

            except Content.DoesNotExist:
                ##handle this later
                abort(404)

        return res

    @requireAuth
    def patch(self, id):
        if g.user.privacy != Privacy.get(Privacy.level == "admin"):
            abort(401)

        date = None
        if request.json["date"] is not None:
            date = parser.parse(request.json["date"])

        Content.update(privacy=int(request.json["privacy"]),
                       type=(int(request.json["type"])) if request.json["type"] != 0 else None,
                       date=date,
                       notes=(request.json["notes"]) if request.json["notes"] != "" else None,
                       title=request.json["title"],
                       location=(request.json["location"]) if request.json["location"] != "" else None,
                       dateUnknowns=request.json["dateUnknowns"]).where(Content.id == id).execute()

        Person_Content.delete().where(Person_Content.content == id).execute()

        if request.json["people"] != []:
            for item in request.json["people"]:
                Person_Content.create(content=id, person=item)

        return {"id": id}, 200

    @requireAuth
    def delete(self, id):
        if g.user.privacy != Privacy.get(Privacy.level == "admin"):
            abort(401)

        content = Content.get(Content.id == id)
        personContent = Person_Content.delete().where(Person_Content.content == id)
        personContent.execute()
        content.delete_instance()
        return 200


api.add_resource(ContentEndpoint, '/content', '/content/<int:id>')


# endpoint for gender
class GenderEndpoint(Resource):
    def get(self):
        genderList = {"genders": []}
        genders = Gender.select()

        for gender in genders.iterator():
            curGender = {"name": gender.name, "id": gender.id}
            genderList["genders"].append(curGender)

        return genderList


api.add_resource(GenderEndpoint, '/gender')


class LoginEndpoint(Resource):
    def post(self):
        passwordInput = request.json["password"]
        username = request.json["username"]
        user = User.get(User.username == username)

        if bcrypt.checkpw(passwordInput.encode("utf8"), user.password.encode("utf8")):
            # match
            return {"key": s.sign(str(user.id)).decode("utf8"), 'privacyLevel': user.privacy.level}
        else:
            # pass wrong
            print("no match")


api.add_resource(LoginEndpoint, "/login")

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
