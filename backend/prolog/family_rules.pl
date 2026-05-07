/*
    Stable family relationship rules.

    Dynamic facts are loaded separately db, ie:

        parent(ParentId, ChildId).
        male(PersonId).
        female(PersonId).
        spouse(PersonId1, PersonId2).
*/

# Tell Prolog that base facts are asserted at runtime rather than defined statically.
# This is because we plan on allowing users to update their family tree as they use the program.
:- dynamic parent/2.
:- dynamic male/1.
:- dynamic female/1.
:- dynamic spouse/2.

/* =========================================================
   Basic parent-child relationships
   ========================================================= */

# Mother:
mother(Mother, Child) :-
    parent(Mother, Child),
    female(Mother).

# Father:
father(Father, Child) :-
    parent(Father, Child),
    male(Father).

# Daughter:
daughter(Daughter, Parent) :-
    parent(Parent, Daughter),
    female(Daughter).

# Son:
son(Son, Parent) :-
    parent(Parent, Son),
    male(Son).


/* =========================================================
   Spouse relationships
   ========================================================= */

# Partner:
partner(X, Y) :-
    spouse(X, Y),
    X \= Y.

# Partner (the other person since you need two different people to create the partner relationship):
partner(X, Y) :-
    spouse(Y, X),
    X \= Y.

# Husband:
husband(Husband, Wife) :-
    partner(Husband, Wife),
    male(Husband).

# Wife:
wife(Wife, Husband) :-
    partner(Wife, Husband),
    female(Wife).


/* =========================================================
   Sibling relationships
   ========================================================= */

# (Blood-related) siblings share at least one parent:
shared_parent(X, Y, Parent) :-
    parent(Parent, X),
    parent(Parent, Y),
    X \= Y.

# General siblings:
sibling(X, Y) :-
    shared_parent(X, Y, _).

# Half-siblings:
half_sibling(X, Y) :-
    # Half siblings share exactly one parent:
    parent(SharedParent, X),
    parent(SharedParent, Y),
    # Their other parent must be different:
    parent(ParentX, X),
    parent(ParentY, Y),
    ParentX \= SharedParent,
    ParentY \= SharedParent,
    ParentX \= ParentY,
    X \= Y.

# Full siblings:
full_sibling(X, Y) :-
    parent(Parent1, X),
    parent(Parent1, Y),
    parent(Parent2, X),
    parent(Parent2, Y),
    Parent1 \= Parent2,
    X \= Y.

brother(Brother, Person) :-
    sibling(Brother, Person),
    male(Brother).

sister(Sister, Person) :-
    sibling(Sister, Person),
    female(Sister).

half_brother(HalfBrother, Person) :-
    half_sibling(HalfBrother, Person),
    male(HalfBrother).

half_sister(HalfSister, Person) :-
    half_sibling(HalfSister, Person),
    female(HalfSister).

full_brother(FullBrother, Person) :-
    full_sibling(FullBrother, Person),
    male(FullBrother).

full_sister(FullSister, Person) :-
    full_sibling(FullSister, Person),
    female(FullSister).


/* =========================================================
   Grandparent relationships
   ========================================================= */

grandparent(Grandparent, Grandchild) :-
    parent(Grandparent, Parent),
    parent(Parent, Grandchild).

grandmother(Grandmother, Grandchild) :-
    grandparent(Grandmother, Grandchild),
    female(Grandmother).

grandfather(Grandfather, Grandchild) :-
    grandparent(Grandfather, Grandchild),
    male(Grandfather).

granddaughter(Granddaughter, Grandparent) :-
    grandparent(Grandparent, Granddaughter),
    female(Granddaughter).

grandson(Grandson, Grandparent) :-
    grandparent(Grandparent, Grandson),
    male(Grandson).


/* =========================================================
   Great-grandparent relationships
   ========================================================= */

great_grandparent(GreatGrandparent, Person) :-
    parent(GreatGrandparent, Grandparent),
    grandparent(Grandparent, Person).

great_grandmother(GreatGrandmother, Person) :-
    great_grandparent(GreatGrandmother, Person),
    female(GreatGrandmother).

great_grandfather(GreatGrandfather, Person) :-
    great_grandparent(GreatGrandfather, Person),
    male(GreatGrandfather).

great_great_grandparent(GreatGreatGrandparent, Person) :-
    parent(GreatGreatGrandparent, Ancestor),
    great_grandparent(Ancestor, Person).

great_great_grandmother(GreatGreatGrandmother, Person) :-
    great_great_grandparent(GreatGreatGrandmother, Person),
    female(GreatGreatGrandmother).

great_great_grandfather(GreatGreatGrandfather, Person) :-
    great_great_grandparent(GreatGreatGrandfather, Person),
    male(GreatGreatGrandfather).


great_great_great_grandparent(GreatGreatGreatGrandparent, Person) :-
    parent(GreatGreatGreatGrandparent, Ancestor),
    great_great_grandparent(Ancestor, Person).


/* =========================================================
   Ancestor-descendant relationships
   ========================================================= */

ancestor(Ancestor, Descendant) :-
    parent(Ancestor, Descendant).

ancestor(Ancestor, Descendant) :-
    parent(Ancestor, Intermediate),
    ancestor(Intermediate, Descendant).

descendant(Descendant, Ancestor) :-
    ancestor(Ancestor, Descendant).


/* =========================================================
   nibling-pibling relationships
   ========================================================= */

pibling(Pibling, Person) :-
    parent(Parent, Person),
    sibling(Pibling, Parent).

aunt(Aunt, Person) :-
    pibling(Aunt, Person),
    female(Aunt).

uncle(Uncle, Person) :-
    pibling(Uncle, Person),
    male(Uncle).

niece(Niece, Person) :-
    pibling(Person, Niece),
    female(Niece).

nephew(Nephew, Person) :-
    pibling(Person, Nephew),
    male(Nephew).

/* =========================================================
   Extended nibling-pibling relationships
   ========================================================= */
grand_pibling(GrandPibling, Person) :-
    grandparent(Grandparent, Person),
    sibling(GrandPibling, Grandparent).

grand_aunt(GrandAunt, Person) :-
    grand_pibling(GrandAunt, Person),
    female(GrandAunt).

grand_uncle(GrandUncle, Person) :-
    grand_pibling(GrandUncle, Person),
    male(GrandUncle).

great_grand_pibling(GreatGrandPibling, Person) :-
    great_grandparent(GreatGrandparent, Person),
    sibling(GreatGrandPibling, GreatGrandparent).

great_grand_aunt(GreatGrandAunt, Person) :-
    great_grand_pibling(GreatGrandAunt, Person),
    female(GreatGrandAunt).

great_grand_uncle(GreatGrandUncle, Person) :-
    great_grand_pibling(GreatGrandUncle, Person),
    male(GreatGrandUncle).

grand_niece(GrandNiece, Person) :-
    niece(Niece, Person),
    parent(Niece, GrandNiece),
    female(GrandNiece).

grand_nephew(GrandNephew, Person) :-
    nephew(Nephew, Person),
    parent(Nephew, GrandNephew),
    male(GrandNephew).


/* =========================================================
   Cousin relationships
   ========================================================= */

/* =========================================================
   Cousin relationships
   ========================================================= */

% First cousins: children of siblings.
first_cousin(X, Y) :-
    parent(Parent1, X),
    parent(Parent2, Y),
    sibling(Parent1, Parent2),
    X \= Y.

cousin(X, Y) :-
    first_cousin(X, Y).

first_cousin_once_removed(X, Y) :-
    (
        parent(Parent, X),
        first_cousin(Parent, Y)
    ;
        parent(Parent, Y),
        first_cousin(X, Parent)
    ),
    X \= Y.

first_cousin_twice_removed(X, Y) :-
    (
        parent(Parent, X),
        first_cousin_once_removed(Parent, Y)
    ;
        parent(Parent, Y),
        first_cousin_once_removed(X, Parent)
    ),
    X \= Y.

second_cousin(X, Y) :-
    parent(Parent1, X),
    parent(Parent2, Y),
    first_cousin(Parent1, Parent2),
    X \= Y.

second_cousin_once_removed(X, Y) :-
    (
        parent(Parent, X),
        second_cousin(Parent, Y)
    ;
        parent(Parent, Y),
        second_cousin(X, Parent)
    ),
    X \= Y.

second_cousin_twice_removed(X, Y) :-
    (
        parent(Parent, X),
        second_cousin_once_removed(Parent, Y)
    ;
        parent(Parent, Y),
        second_cousin_once_removed(X, Parent)
    ),
    X \= Y.

third_cousin(X, Y) :-
    parent(Parent1, X),
    parent(Parent2, Y),
    second_cousin(Parent1, Parent2),
    X \= Y.

third_cousin_once_removed(X, Y) :-
    (
        parent(Parent, X),
        third_cousin(Parent, Y)
    ;
        parent(Parent, Y),
        third_cousin(X, Parent)
    ),
    X \= Y.

third_cousin_twice_removed(X, Y) :-
    (
        parent(Parent, X),
        third_cousin_once_removed(Parent, Y)
    ;
        parent(Parent, Y),
        third_cousin_once_removed(X, Parent)
    ),
    X \= Y.


/* =========================================================
   In-law relationships
   ========================================================= */

parent_in_law(ParentInLaw, Person) :-
    partner(Person, Spouse),
    parent(ParentInLaw, Spouse).

mother_in_law(MotherInLaw, Person) :-
    parent_in_law(MotherInLaw, Person),
    female(MotherInLaw).

father_in_law(FatherInLaw, Person) :-
    parent_in_law(FatherInLaw, Person),
    male(FatherInLaw).

child_in_law(ChildInLaw, Person) :-
    parent(Person, Child),
    partner(Child, ChildInLaw).

son_in_law(SonInLaw, Person) :-
    child_in_law(SonInLaw, Person),
    male(SonInLaw).

daughter_in_law(DaughterInLaw, Person) :-
    child_in_law(DaughterInLaw, Person),
    female(DaughterInLaw).

sibling_in_law(SiblingInLaw, Person) :-
    (
        partner(Person, Spouse),
        sibling(SiblingInLaw, Spouse)
    ;
        sibling(Sibling, Person),
        partner(Sibling, SiblingInLaw)
    ),
    SiblingInLaw \= Person.

brother_in_law(BrotherInLaw, Person) :-
    sibling_in_law(BrotherInLaw, Person),
    male(BrotherInLaw).

sister_in_law(SisterInLaw, Person) :-
    sibling_in_law(SisterInLaw, Person),
    female(SisterInLaw).


/* =========================================================
   Step relationships: only applies if step parent not listed as parent
   ========================================================= */

step_parent(StepParent, Child) :-
    partner(StepParent, Parent),
    parent(Parent, Child),
    \+ parent(StepParent, Child).

step_mother(StepMother, Child) :-
    step_parent(StepMother, Child),
    female(StepMother).

step_father(StepFather, Child) :-
    step_parent(StepFather, Child),
    male(StepFather).

step_child(StepChild, Person) :-
    step_parent(Person, StepChild).

step_sibling(X, Y) :-
    parent(P1, X),
    parent(P2, Y),
    partner(P1, P2),
    \+ sibling(X, Y),
    X \= Y.

step_brother(StepBrother, Person) :-
    step_sibling(StepBrother, Person),
    male(StepBrother).

step_sister(StepSister, Person) :-
    step_sibling(StepSister, Person),
    female(StepSister).


/* =========================================================
   Convenience inverses / aliases (to match API predicate names)
   ========================================================= */

% child(Child, Parent) is the inverse of parent(Parent, Child).
child(Child, Parent) :-
    parent(Parent, Child).

% NOTE: spouse/2 facts are asserted dynamically from the DB at runtime.
% Do NOT define spouse/2 rules here, or SWI-Prolog will treat it as a static
% predicate and PySwip will fail with permission_error(modify, static_procedure,...).
% Use partner/2 (defined above) for symmetric spouse queries.