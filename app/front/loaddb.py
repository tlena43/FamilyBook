from models import *
import bcrypt
import os

try:
	os.remove("project.db")
except OSError:
	pass

db.create_tables([Upload, Privacy, User, Gender, Person, ContentType], safe=True)
db.create_tables([Content, Marriage, Person_Marriage, Person_Content], safe=True)

Gender.create(name="male")
Gender.create(name="female")

admin = Privacy.create(level="admin")
family = Privacy.create(level="family", parent=admin)
extended = Privacy.create(level="extended", parent=family)

adminPass = "k1$ch00k"
adminSalt = bcrypt.gensalt()
adminPassB = bcrypt.hashpw(adminPass.encode("utf8"), adminSalt)
User.create(privacy=admin, username="Admin", password=adminPassB)

familyPass = "familyPass"
familySalt = bcrypt.gensalt()
familyPassB = bcrypt.hashpw(familyPass.encode("utf8"), familySalt)
User.create(privacy=family, username="Family", password=familyPassB)

extendedPass = "extendedPass"
extendedSalt = bcrypt.gensalt()
extendedPassB = bcrypt.hashpw(extendedPass.encode("utf8"), extendedSalt)
User.create(privacy=extended, username="ExtendedFamily", password=extendedPassB)

ContentType.create(name="Newspaper")
ContentType.create(name="Obituary")
ContentType.create(name="Certificate")
ContentType.create(name="Photo")
ContentType.create(name="Legal Documents")
ContentType.create(name="Other")
