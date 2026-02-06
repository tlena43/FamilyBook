from peewee import *

db = SqliteDatabase("project.db")
# db = MySQLDatabase('kischook', host='localhost', user='kischook', password='YAN_>&Z^:#|k/op[N_2[#)<_p,>Nw:8eK6BqGMx{vSKn6!J_/Imewe<y#6*')

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
    privacy = ForeignKeyField(Privacy, backref="users")
    username = CharField(unique=True)
    password = CharField()

    def hasPrivacyLevel(self, privacy):
        while privacy is not None:
            if self.privacy == privacy:
                return True
            privacy = privacy.parent
        return False



class Gender(BaseModel):
    name = CharField(unique=True)


class Person(BaseModel):
    birthDay = DateField(null=True)
    privacy = ForeignKeyField(Privacy, backref="people")
    birthDateUnknowns = IntegerField()
    deathDay = DateField(null=True)
    deathDateUnknowns = IntegerField()
    birthplace = CharField(null=True)
    parent1 = ForeignKeyField("self", null=True, backref="children")
    parent2 = ForeignKeyField("self", null=True, backref="children")
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
