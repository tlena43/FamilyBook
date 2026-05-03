"""
Run this after loaddb.py to add 3 fake test users to the database.

Usage:
    cd backend
    python loaddb.py   # initialize tables first (delete project.db if upgrading)
    python seed.py     # add test users
"""

from models import db, User, FamilyGroup, FamilyGroupMember, Tree
import bcrypt

TEST_USERS = [
    {"username": "alice",  "password": "AlicePass1",  "role": "owner"},
    {"username": "bob",    "password": "BobPass1",    "role": "editor"},
    {"username": "carol",  "password": "CarolPass1",  "role": "viewer"},
]

db.connect(reuse_if_open=True)

def make_user(username: str, password: str) -> User:
    existing = User.get_or_none(User.username == username)
    if existing:
        return existing
    pw_hash = bcrypt.hashpw(password.encode("utf8"), bcrypt.gensalt())
    return User.create(username=username, password=pw_hash)

with db.atomic():
    users = []
    for u in TEST_USERS:
        users.append((make_user(u["username"], u["password"]), u["role"]))

    owner_user = users[0][0]
    group, _ = FamilyGroup.get_or_create(name="Test Family Group", owner=owner_user)
    Tree.get_or_create(name="Test Tree", owner=owner_user, family_group=group)

    for user, role in users:
        FamilyGroupMember.get_or_create(
            family_group=group,
            user=user,
            defaults={"role": role},
        )

db.close()

print("Seed complete. Test accounts:")
print()
for u in TEST_USERS:
    print(f"  Username: {u['username']:<10}  Password: {u['password']:<14}  Role: {u['role']}")
print()
print("All three share 'Test Family Group' with a 'Test Tree' inside.")
