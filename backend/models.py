from peewee import *
import os
from dotenv import load_dotenv

load_dotenv()

# Always store/read the SQLite DB next to this file (backend/project.db):
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "project.db")
db = SqliteDatabase(DB_PATH)
#db = MySQLDatabase("project", user=os.getenv("user"), password=os.getenv("pass"), host=os.getenv("host"), port=os.getenv("port"))


class BaseModel(Model):
    class Meta:
        database = db


class Upload(BaseModel):
    filename = CharField(unique=True)
    owner = DeferredForeignKey('User', related_name='uploads')
    timestamp = DateTimeField()


class Privacy(BaseModel):
    level = CharField(unique=True)
    parent = ForeignKeyField("self", null=True, backref="children")


class User(BaseModel):
    username = CharField(unique=True)
    password = CharField()
    share_code = CharField(unique=True, null=True)

class User_Access(BaseModel):
    owner = ForeignKeyField(User, backref="owns")
    viewer = ForeignKeyField(User, backref="can_view")
    


class Gender(BaseModel):
    name = CharField(unique=True)


class Person(BaseModel):
    user = ForeignKeyField(User, backref="people")
    birthDay = DateField(null=True)
    privacy = ForeignKeyField(Privacy, backref="people")
    birthDateUnknowns = IntegerField()
    deathDay = DateField(null=True)
    deathDateUnknowns = IntegerField()
    birthplace = CharField(null=True)
    parent1_id = ForeignKeyField("self", null=True, backref="children")
    parent2_id = ForeignKeyField("self", null=True, backref="children")
    spouse_id = ForeignKeyField("self", null=True, backref="spouse_of")
    firstName = CharField()
    middleName = CharField(null=True)
    lastName = CharField()
    gender = ForeignKeyField(Gender, backref="people")
    isDead = BooleanField()
    maidenName = CharField(null=True)
    file = ForeignKeyField(Upload, null=True)


class ContentType(BaseModel):
    name = CharField(unique=True)


class Content(BaseModel):
    user = ForeignKeyField(User, backref="content")
    privacy = ForeignKeyField(Privacy, backref="content")
    type = ForeignKeyField(ContentType, backref="content", null=True)
    date = DateField(null=True)
    dateUnknowns = IntegerField()
    notes = CharField(null=True)
    title = CharField()
    file = ForeignKeyField(Upload)
    location = CharField(null=True)

class Person_Content(BaseModel):
    person = ForeignKeyField(Person, backref="content")
    content = ForeignKeyField(Content, backref="person")

class Marriage(BaseModel):
    marriage_date = DateField(null=True)
    separation_date = DateField(null=True)


class Person_Marriage(BaseModel):
    person = ForeignKeyField(User, backref="marriage")
    marriage = ForeignKeyField(Marriage, null=True, backref="person")
