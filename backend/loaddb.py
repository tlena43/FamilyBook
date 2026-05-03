from models import *
import bcrypt
import os

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
def ensure_user(username: str, raw_password: str) -> User:
	user = User.get_or_none(User.username == username)
	if user:
		return user
	salt = bcrypt.gensalt()
	pw_hash = bcrypt.hashpw(raw_password.encode("utf8"), salt)
	return User.create(username=username, password=pw_hash)

admin_user = ensure_user("Admin", "k1$ch00k")

# Seed a default family group and default tree to demonstrate the model:
default_group, _ = FamilyGroup.get_or_create(name="Default Family", owner=admin_user)

# Ensure group membership:
FamilyGroupMember.get_or_create(family_group=default_group, user=admin_user, defaults={"role": "owner"})

# Default tree owned by admin, visible to group members:
default_tree, _ = Tree.get_or_create(name="Default Tree", owner=admin_user, family_group=default_group)

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
