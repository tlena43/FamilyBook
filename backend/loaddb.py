from models import *
import bcrypt
import os

"""
Drop existing database and recreate the datavase from scratch
Initialize values for gender and content types
"""

try:
	os.remove("project.db")
except OSError:
	pass

# Create tables (safe=True makes this idempotent):
db.create_tables(
	[Upload, User, Gender, FamilyGroup, FamilyGroupMember, Tree, Person, ContentType],
	safe=True,
)
db.create_tables([Content, Marriage, Person_Marriage, Person_Content], safe=True)

# Seed genders (idempotent):
Gender.get_or_create(name="male")
Gender.get_or_create(name="female")

# Seed admin user (idempotent):

# Seed content types (idempotent):
for ct in [
	"Newspaper",
	"Obituary",
	"Certificate",
	"Photo",
	"Legal Documents",
	"Other",
]:
	ContentType.get_or_create(name=ct)
