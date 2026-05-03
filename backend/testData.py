from datetime import date
import bcrypt
# Adjust this import to match your project structure
from models import Person, Privacy, Gender, User


def get_default_privacy():
    privacy = Privacy.select().first()
    if not privacy:
        raise Exception("No Privacy record found. Create one before running this seed file.")
    return privacy

def get_gender():
    gender = Gender.select().first()
    if not gender:
        raise Exception("No Gender record found. Create one before running this seed file.")
    return gender

def create_user():
    adminPass = "k1$ch00k"
    adminSalt = bcrypt.gensalt()
    adminPassB = bcrypt.hashpw(adminPass.encode("utf8"), adminSalt)
    return User.create(username="Admin", password=adminPassB, share_code = "1234")

def create_person(
    user,
    people,
    key,
    first_name,
    last_name,
    birth_date=None,
    death_date=None,
    birth_place=None,
    maiden_name=None,
):
    privacy = get_default_privacy()
    gender = get_gender()

    person = Person.create(
        user = user,
        birthDay=birth_date,
        privacy=privacy,
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

    # -------------------------
    # Generation 1 (great-grandparents / oldest branch)
    # -------------------------
    create_person( user,
        people, "arthur_sr", "Arthur", "Bennett",
        birth_date=date(1932, 4, 11), birth_place="Boston"
    )
    create_person( user,
        people, "evelyn_sr", "Evelyn", "Bennett",
        birth_date=date(1934, 9, 2), birth_place="Boston", maiden_name="Carter"
    )
    set_spouses(people["arthur_sr"], people["evelyn_sr"])

    create_person( user,
        people, "frank_sr", "Frank", "Morrison", 
        birth_date=date(1930, 1, 18), death_date=date(2001, 6, 9), birth_place="Chicago"
    )
    create_person( user,
        people, "helen_sr", "Helen", "Morrison", 
        birth_date=date(1933, 12, 25), birth_place="Chicago", maiden_name="Reed"
    )
    set_spouses(people["frank_sr"], people["helen_sr"])

    create_person( user,
        people, "walter_sr", "Walter", "Hayes", 
        birth_date=date(1931, 7, 8), death_date=date(1998, 2, 1), birth_place="Denver"
    )
    create_person( user,
        people, "dorothy_sr", "Dorothy", "Hayes", 
        birth_date=date(1935, 5, 14), birth_place="Denver", maiden_name="Parker"
    )
    set_spouses(people["walter_sr"], people["dorothy_sr"])

    # -------------------------
    # Generation 2
    # -------------------------
    create_person( user,
        people, "robert", "Robert", "Bennett", 
        birth_date=date(1958, 2, 20), birth_place="Boston"
    )
    create_person( user,
        people, "linda", "Linda", "Bennett", 
        birth_date=date(1960, 6, 3), birth_place="Boston", maiden_name="Morrison"
    )
    set_spouses(people["robert"], people["linda"])
    set_parents(people["robert"], people["arthur_sr"], people["evelyn_sr"])
    set_parents(people["linda"], people["frank_sr"], people["helen_sr"])

    create_person( user,
        people, "michael", "Michael", "Bennett", 
        birth_date=date(1962, 8, 12), birth_place="Boston"
    )
    set_parents(people["michael"], people["arthur_sr"], people["evelyn_sr"])

    create_person( user,
        people, "susan", "Susan", "Hayes", 
        birth_date=date(1965, 10, 19), birth_place="Denver", maiden_name="Hayes"
    )
    set_spouses(people["michael"], people["susan"])
    set_parents(people["susan"], people["walter_sr"], people["dorothy_sr"])

    create_person( user,
        people, "patricia", "Patricia", "Morrison", 
        birth_date=date(1964, 11, 30), birth_place="Chicago", maiden_name="Morrison"
    )
    set_parents(people["patricia"], people["frank_sr"], people["helen_sr"])

    create_person( user,
        people, "george", "George", "Clark", 
        birth_date=date(1961, 4, 7), birth_place="Milwaukee"
    )
    set_spouses(people["george"], people["patricia"])

    # -------------------------
    # Generation 3
    # Robert + Linda children
    # -------------------------
    create_person( user,
        people, "daniel", "Daniel", "Bennett", 
        birth_date=date(1984, 1, 15), birth_place="Seattle"
    )
    create_person( user,
        people, "emma", "Emma", "Bennett", 
        birth_date=date(1987, 9, 4), birth_place="Seattle"
    )
    create_person( user,
        people, "noah", "Noah", "Bennett", 
        birth_date=date(1990, 7, 22), birth_place="Seattle"
    )
    set_parents(people["daniel"], people["robert"], people["linda"])
    set_parents(people["emma"], people["robert"], people["linda"])
    set_parents(people["noah"], people["robert"], people["linda"])

    # Michael + Susan children
    create_person( user,
        people, "olivia", "Olivia", "Bennett",
        birth_date=date(1988, 3, 10), birth_place="Portland"
    )
    create_person( user,
        people, "ethan", "Ethan", "Bennett",
        birth_date=date(1992, 12, 1), birth_place="Portland"
    )
    set_parents(people["olivia"], people["michael"], people["susan"])
    set_parents(people["ethan"], people["michael"], people["susan"])

    # George + Patricia children
    create_person( user,
        people, "grace", "Grace", "Clark",
        birth_date=date(1989, 5, 25), birth_place="Chicago"
    )
    create_person( user,
        people, "henry", "Henry", "Clark", 
        birth_date=date(1993, 6, 18), birth_place="Chicago"
    )
    set_parents(people["grace"], people["george"], people["patricia"])
    set_parents(people["henry"], people["george"], people["patricia"])

    # -------------------------
    # Spouses for Generation 3
    # -------------------------
    create_person( user,
        people, "lauren", "Lauren", "Bennett", 
        birth_date=date(1985, 8, 8), birth_place="Tacoma", maiden_name="Foster"
    )
    set_spouses(people["daniel"], people["lauren"])

    create_person( user,
        people, "james", "James", "Turner", 
        birth_date=date(1986, 2, 14), birth_place="Salem"
    )
    set_spouses(people["emma"], people["james"])

    create_person( user,
        people, "sophia", "Sophia", "Bennett", 
        birth_date=date(1991, 11, 21), birth_place="Spokane", maiden_name="Reyes"
    )
    set_spouses(people["noah"], people["sophia"])

    create_person( user,
        people, "liam", "Liam", "Cole", 
        birth_date=date(1987, 4, 2), birth_place="Portland"
    )
    set_spouses(people["olivia"], people["liam"])

    create_person( user,
        people, "ava", "Ava", "Bennett", 
        birth_date=date(1994, 7, 13), birth_place="Eugene", maiden_name="Brooks"
    )
    set_spouses(people["ethan"], people["ava"])

    create_person( user,
        people, "lucas", "Lucas", "Miller", 
        birth_date=date(1988, 10, 9), birth_place="Chicago"
    )
    set_spouses(people["grace"], people["lucas"])

    create_person( user,
        people, "zoe", "Zoe", "Clark", 
        birth_date=date(1994, 1, 27), birth_place="Chicago", maiden_name="Nguyen"
    )
    set_spouses(people["henry"], people["zoe"])

    # -------------------------
    # Generation 4
    # -------------------------
    create_person( user,
        people, "charlotte", "Charlotte", "Bennett", 
        birth_date=date(2010, 6, 1), birth_place="Seattle"
    )
    create_person( user,
        people, "jack", "Jack", "Bennett", 
        birth_date=date(2013, 2, 9), birth_place="Seattle"
    )
    set_parents(people["charlotte"], people["daniel"], people["lauren"])
    set_parents(people["jack"], people["daniel"], people["lauren"])

    create_person( user,
        people, "ella", "Ella", "Turner", 
        birth_date=date(2012, 9, 15), birth_place="Salem"
    )
    create_person( user,
        people, "logan", "Logan", "Turner", 
        birth_date=date(2015, 12, 30), birth_place="Salem"
    )
    set_parents(people["ella"], people["james"], people["emma"])
    set_parents(people["logan"], people["james"], people["emma"])

    create_person( user,
        people, "mason", "Mason", "Bennett", 
        birth_date=date(2016, 4, 5), birth_place="Spokane"
    )
    set_parents(people["mason"], people["noah"], people["sophia"])

    create_person( user,
        people, "amelia", "Amelia", "Cole",
        birth_date=date(2011, 7, 7), birth_place="Portland"
    )
    create_person( user,
        people, "harper", "Harper", "Cole", 
        birth_date=date(2014, 8, 19), birth_place="Portland"
    )
    set_parents(people["amelia"], people["liam"], people["olivia"])
    set_parents(people["harper"], people["liam"], people["olivia"])

    create_person( user,
        people, "benjamin", "Benjamin", "Bennett", 
        birth_date=date(2018, 3, 11), birth_place="Eugene"
    )
    set_parents(people["benjamin"], people["ethan"], people["ava"])

    create_person( user,
        people, "nora", "Nora", "Miller", 
        birth_date=date(2017, 5, 24), birth_place="Chicago"
    )
    set_parents(people["nora"], people["lucas"], people["grace"])

    create_person( user,
        people, "leo", "Leo", "Clark",
        birth_date=date(2020, 11, 4), birth_place="Chicago"
    )
    set_parents(people["leo"], people["henry"], people["zoe"])

    # -------------------------
    # Add a second marriage + half-sibling branch
    # -------------------------
    # Daniel's first spouse Lauren dies; Daniel remarries.
    #people["lauren"].deathDay = date(2018, 1, 12)
    #people["lauren"].deathDateUnknowns = 0
    #people["lauren"].isDead = True
    #people["lauren"].save()

    #people["daniel"].spouse_id = None
    #people["daniel"].save()
    #people["lauren"].spouse_id = None
    #people["lauren"].save()

    #create_person(
    #    people, "rachel", "Rachel", "Bennett", 
    #    birth_date=date(1989, 9, 29), birth_place="Boise", maiden_name="Adams"
    #)
    #set_spouses(people["daniel"], people["rachel"])

    #create_person(
    #    people, "ivy", "Ivy", "Bennett", 
    #    birth_date=date(2021, 6, 17), birth_place="Boise"
    #)
    #set_parents(people["ivy"], people["daniel"], people["rachel"])

    # -------------------------
    # Add another divorce/remarriage branch
    # -------------------------
    # Patricia and George separate; Henry remains their child.
    #people["george"].spouse_id = None
    #people["george"].save()
    #people["patricia"].spouse_id = None
    #people["patricia"].save()

    #create_person(
    #    people, "steven", "Steven", "Hall", 
    #    birth_date=date(1960, 3, 2), birth_place="Detroit"
    #)
    #set_spouses(people["patricia"], people["steven"])

    #create_person(
    #    people, "hannah", "Hannah", "Hall", 
    #    birth_date=date(1998, 2, 8), birth_place="Chicago"
    #)
    #set_parents(people["hannah"], people["steven"], people["patricia"])

    print(f"Seeded {len(people)} people successfully.")


if __name__ == "__main__":
    seed_family_tree()