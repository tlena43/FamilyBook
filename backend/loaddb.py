from models import *
import bcrypt
import os

try:
	os.remove("project.db")
except OSError:
	pass

db.create_tables([Upload, Privacy, User, User_Access, Gender, Person, ContentType], safe=True)
db.create_tables([Content, Marriage, Person_Marriage, Person_Content], safe=True)

Gender.create(name="male")
Gender.create(name="female")

owner = Privacy.create(level="owner")
#editor = Privacy.create(level="editor", parent=owner)
viewer = Privacy.create(level="viewer", parent=owner)

ContentType.create(name="Newspaper")
ContentType.create(name="Obituary")
ContentType.create(name="Certificate")
ContentType.create(name="Photo")
ContentType.create(name="Legal Documents")
ContentType.create(name="Other")
