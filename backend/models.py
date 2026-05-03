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


class User(BaseModel):
    username = CharField(unique=True)
    password = CharField()


# Family groups + trees (multi-tree per user; access via family group membership):

class FamilyGroup(BaseModel):
    name = CharField()
    owner = ForeignKeyField(User, backref="owned_family_groups")


class FamilyGroupMember(BaseModel):
    ROLE_CHOICES = (("owner", "owner"), ("editor", "editor"), ("viewer", "viewer"))

    family_group = ForeignKeyField(FamilyGroup, backref="members")
    user = ForeignKeyField(User, backref="family_memberships")
    role = CharField(default="viewer", choices=ROLE_CHOICES)

    class Meta:
        indexes = ((('family_group', 'user'), True),)


class Tree(BaseModel):
    name = CharField()
    owner = ForeignKeyField(User, backref="owned_trees")
    family_group = ForeignKeyField(FamilyGroup, null=True, backref="trees")


class Gender(BaseModel):
    name = CharField(unique=True)


class Person(BaseModel):
    # A person belongs to a tree (tree visibility is based on family group membership):
    tree = ForeignKeyField(Tree, backref="people", null=True)

    birthDay = DateField(null=True)
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
    # Content can be scoped to a tree (and thus a family group) for access.
    tree = ForeignKeyField(Tree, null=True, backref="content")

    user = ForeignKeyField(User, backref="content")
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
