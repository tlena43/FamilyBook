from datetime import date
import bcrypt

from models import (
    Person,
    Gender,
    User,
    FamilyGroup,
    Tree,
    FamilyGroupMember,
    db,
)


def get_gender(name="male"):
    gender = Gender.get_or_none(Gender.name == name)
    if gender:
        return gender

    gender = Gender.select().first()
    if not gender:
        raise Exception("No Gender record found. Create one before running this seed file.")

    return gender


def create_user():
    admin_pass = "k1$ch00k"
    password_hash = bcrypt.hashpw(
        admin_pass.encode("utf8"),
        bcrypt.gensalt()
    ).decode("utf8")

    user, created = User.get_or_create(
        username="Admin",
        defaults={
            "password": password_hash,
            "share_code": "1234",
        }
    )

    if not created and not user.share_code:
        user.share_code = "1234"
        user.save()

    return user


def get_or_create_default_tree(user):
    default_group, _ = FamilyGroup.get_or_create(
        name="Default Family",
        owner=user,
    )

    FamilyGroupMember.get_or_create(
        family_group=default_group,
        user=user,
        defaults={"role": "owner"},
    )

    default_tree, _ = Tree.get_or_create(
        name="Default Tree",
        owner=user,
        family_group=default_group,
    )

    return default_tree


def create_person(
    user,
    tree,
    people,
    key,
    first_name,
    last_name,
    birth_date=None,
    death_date=None,
    birth_place=None,
    maiden_name=None,
    gender_name="male",
):
    gender = get_gender(gender_name)

    person = Person.create(
        user=user,
        tree=tree,
        birthDay=birth_date,
        birthDateUnknowns=0 if birth_date else 1,
        deathDay=death_date,
        deathDateUnknowns=0 if death_date else 1,
        birthplace=birth_place,
        parent1_id=None,
        parent2_id=None,
        spouse_id=None,
        firstName=first_name,
        middleName=None,
        lastName=last_name,
        gender=gender,
        isDead=(death_date is not None),
        maidenName=maiden_name,
        file=None,
    )

    people[key] = person
    return person


def set_spouses(a, b):
    a.spouse_id = b
    a.save()

    b.spouse_id = a
    b.save()


def set_parents(child, parent1=None, parent2=None):
    child.parent1_id = parent1
    child.parent2_id = parent2
    child.save()


def seed_family_tree():
    people = {}
    user = create_user()
    default_tree = get_or_create_default_tree(user)

    def add_person(*args, **kwargs):
        return create_person(user, default_tree, *args, **kwargs)

    # Generation 1
    add_person(
        people, "arthur_sr", "Arthur", "Bennett",
        birth_date=date(1932, 4, 11),
        birth_place="Boston",
        gender_name="male",
    )
    add_person(
        people, "evelyn_sr", "Evelyn", "Bennett",
        birth_date=date(1934, 9, 2),
        birth_place="Boston",
        maiden_name="Carter",
        gender_name="female",
    )
    set_spouses(people["arthur_sr"], people["evelyn_sr"])

    add_person(
        people, "frank_sr", "Frank", "Morrison",
        birth_date=date(1930, 1, 18),
        death_date=date(2001, 6, 9),
        birth_place="Chicago",
        gender_name="male",
    )
    add_person(
        people, "helen_sr", "Helen", "Morrison",
        birth_date=date(1933, 12, 25),
        birth_place="Chicago",
        maiden_name="Reed",
        gender_name="female",
    )
    set_spouses(people["frank_sr"], people["helen_sr"])

    add_person(
        people, "walter_sr", "Walter", "Hayes",
        birth_date=date(1931, 7, 8),
        death_date=date(1998, 2, 1),
        birth_place="Denver",
        gender_name="male",
    )
    add_person(
        people, "dorothy_sr", "Dorothy", "Hayes",
        birth_date=date(1935, 5, 14),
        birth_place="Denver",
        maiden_name="Parker",
        gender_name="female",
    )
    set_spouses(people["walter_sr"], people["dorothy_sr"])

    # Generation 2
    add_person(
        people, "robert", "Robert", "Bennett",
        birth_date=date(1958, 2, 20),
        birth_place="Boston",
        gender_name="male",
    )
    add_person(
        people, "linda", "Linda", "Bennett",
        birth_date=date(1960, 6, 3),
        birth_place="Boston",
        maiden_name="Morrison",
        gender_name="female",
    )
    set_spouses(people["robert"], people["linda"])
    set_parents(people["robert"], people["arthur_sr"], people["evelyn_sr"])
    set_parents(people["linda"], people["frank_sr"], people["helen_sr"])

    add_person(
        people, "michael", "Michael", "Bennett",
        birth_date=date(1962, 8, 12),
        birth_place="Boston",
        gender_name="male",
    )
    set_parents(people["michael"], people["arthur_sr"], people["evelyn_sr"])

    add_person(
        people, "susan", "Susan", "Hayes",
        birth_date=date(1965, 10, 19),
        birth_place="Denver",
        maiden_name="Hayes",
        gender_name="female",
    )
    set_spouses(people["michael"], people["susan"])
    set_parents(people["susan"], people["walter_sr"], people["dorothy_sr"])

    add_person(
        people, "patricia", "Patricia", "Morrison",
        birth_date=date(1964, 11, 30),
        birth_place="Chicago",
        maiden_name="Morrison",
        gender_name="female",
    )
    set_parents(people["patricia"], people["frank_sr"], people["helen_sr"])

    add_person(
        people, "george", "George", "Clark",
        birth_date=date(1961, 4, 7),
        birth_place="Milwaukee",
        gender_name="male",
    )
    set_spouses(people["george"], people["patricia"])

    # Generation 3
    add_person(
        people, "daniel", "Daniel", "Bennett",
        birth_date=date(1984, 1, 15),
        birth_place="Seattle",
        gender_name="male",
    )
    add_person(
        people, "emma", "Emma", "Bennett",
        birth_date=date(1987, 9, 4),
        birth_place="Seattle",
        gender_name="female",
    )
    add_person(
        people, "noah", "Noah", "Bennett",
        birth_date=date(1990, 7, 22),
        birth_place="Seattle",
        gender_name="male",
    )
    set_parents(people["daniel"], people["robert"], people["linda"])
    set_parents(people["emma"], people["robert"], people["linda"])
    set_parents(people["noah"], people["robert"], people["linda"])

    add_person(
        people, "olivia", "Olivia", "Bennett",
        birth_date=date(1988, 3, 10),
        birth_place="Portland",
        gender_name="female",
    )
    add_person(
        people, "ethan", "Ethan", "Bennett",
        birth_date=date(1992, 12, 1),
        birth_place="Portland",
        gender_name="male",
    )
    set_parents(people["olivia"], people["michael"], people["susan"])
    set_parents(people["ethan"], people["michael"], people["susan"])

    add_person(
        people, "grace", "Grace", "Clark",
        birth_date=date(1989, 5, 25),
        birth_place="Chicago",
        gender_name="female",
    )
    add_person(
        people, "henry", "Henry", "Clark",
        birth_date=date(1993, 6, 18),
        birth_place="Chicago",
        gender_name="male",
    )
    set_parents(people["grace"], people["george"], people["patricia"])
    set_parents(people["henry"], people["george"], people["patricia"])

    # Spouses for Generation 3
    add_person(
        people, "lauren", "Lauren", "Bennett",
        birth_date=date(1985, 8, 8),
        birth_place="Tacoma",
        maiden_name="Foster",
        gender_name="female",
    )
    set_spouses(people["daniel"], people["lauren"])

    add_person(
        people, "james", "James", "Turner",
        birth_date=date(1986, 2, 14),
        birth_place="Salem",
        gender_name="male",
    )
    set_spouses(people["emma"], people["james"])

    add_person(
        people, "sophia", "Sophia", "Bennett",
        birth_date=date(1991, 11, 21),
        birth_place="Spokane",
        maiden_name="Reyes",
        gender_name="female",
    )
    set_spouses(people["noah"], people["sophia"])

    add_person(
        people, "liam", "Liam", "Cole",
        birth_date=date(1987, 4, 2),
        birth_place="Portland",
        gender_name="male",
    )
    set_spouses(people["olivia"], people["liam"])

    add_person(
        people, "ava", "Ava", "Bennett",
        birth_date=date(1994, 7, 13),
        birth_place="Eugene",
        maiden_name="Brooks",
        gender_name="female",
    )
    set_spouses(people["ethan"], people["ava"])

    add_person(
        people, "lucas", "Lucas", "Miller",
        birth_date=date(1988, 10, 9),
        birth_place="Chicago",
        gender_name="male",
    )
    set_spouses(people["grace"], people["lucas"])

    add_person(
        people, "zoe", "Zoe", "Clark",
        birth_date=date(1994, 1, 27),
        birth_place="Chicago",
        maiden_name="Nguyen",
        gender_name="female",
    )
    set_spouses(people["henry"], people["zoe"])

    # Generation 4
    add_person(
        people, "charlotte", "Charlotte", "Bennett",
        birth_date=date(2010, 6, 1),
        birth_place="Seattle",
        gender_name="female",
    )
    add_person(
        people, "jack", "Jack", "Bennett",
        birth_date=date(2013, 2, 9),
        birth_place="Seattle",
        gender_name="male",
    )
    set_parents(people["charlotte"], people["daniel"], people["lauren"])
    set_parents(people["jack"], people["daniel"], people["lauren"])

    add_person(
        people, "ella", "Ella", "Turner",
        birth_date=date(2012, 9, 15),
        birth_place="Salem",
        gender_name="female",
    )
    add_person(
        people, "logan", "Logan", "Turner",
        birth_date=date(2015, 12, 30),
        birth_place="Salem",
        gender_name="male",
    )
    set_parents(people["ella"], people["james"], people["emma"])
    set_parents(people["logan"], people["james"], people["emma"])

    add_person(
        people, "mason", "Mason", "Bennett",
        birth_date=date(2016, 4, 5),
        birth_place="Spokane",
        gender_name="male",
    )
    set_parents(people["mason"], people["noah"], people["sophia"])

    add_person(
        people, "amelia", "Amelia", "Cole",
        birth_date=date(2011, 7, 7),
        birth_place="Portland",
        gender_name="female",
    )
    add_person(
        people, "harper", "Harper", "Cole",
        birth_date=date(2014, 8, 19),
        birth_place="Portland",
        gender_name="female",
    )
    set_parents(people["amelia"], people["liam"], people["olivia"])
    set_parents(people["harper"], people["liam"], people["olivia"])

    add_person(
        people, "benjamin", "Benjamin", "Bennett",
        birth_date=date(2018, 3, 11),
        birth_place="Eugene",
        gender_name="male",
    )
    set_parents(people["benjamin"], people["ethan"], people["ava"])

    add_person(
        people, "nora", "Nora", "Miller",
        birth_date=date(2017, 5, 24),
        birth_place="Chicago",
        gender_name="female",
    )
    set_parents(people["nora"], people["lucas"], people["grace"])

    add_person(
        people, "leo", "Leo", "Clark",
        birth_date=date(2020, 11, 4),
        birth_place="Chicago",
        gender_name="male",
    )
    set_parents(people["leo"], people["henry"], people["zoe"])

    print(f"Seeded {len(people)} people successfully.")
    print(f"User: {user.username}")
    print("Password: k1$ch00k")
    print(f"Share code: {user.share_code}")
    print(f"Family group: {default_tree.family_group.name}")
    print(f"Tree: {default_tree.name}")


if __name__ == "__main__":
    if db.is_closed():
        db.connect()

    seed_family_tree()

    if not db.is_closed():
        db.close()