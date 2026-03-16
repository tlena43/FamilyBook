/*
    Stable family relationship rules.

    Dynamic facts are loaded separately db, ie:

        parent(ParentId, ChildId).
        male(PersonId).
        female(PersonId).
        spouse(PersonId1, PersonId2).
*/


/* =========================================================
   Basic parent-child relationships
   ========================================================= */

mother(Mother, Child) :-
    parent(Mother, Child),
    female(Mother).

father(Father, Child) :-
    parent(Father, Child),
    male(Father).

daughter(Daughter, Parent) :-
    parent(Parent, Daughter),
    female(Daughter).

son(Son, Parent) :-
    parent(Parent, Son),
    male(Son).


/* =========================================================
   Spouse relationships
   ========================================================= */

partner(X, Y) :-
    spouse(X, Y),
    X \= Y.

partner(X, Y) :-
    spouse(Y, X),
    X \= Y.

husband(Husband, Wife) :-
    partner(Husband, Wife),
    male(Husband).

wife(Wife, Husband) :-
    partner(Wife, Husband),
    female(Wife).


/* =========================================================
   Sibling relationships
   ========================================================= */

shared_parent(X, Y, Parent) :-
    parent(Parent, X),
    parent(Parent, Y),
    X \= Y.

sibling(X, Y) :-
    shared_parent(X, Y, _).

half_sibling(X, Y) :-
    parent(SharedParent, X),
    parent(SharedParent, Y),
    parent(ParentX, X),
    parent(ParentY, Y),
    ParentX \= SharedParent,
    ParentY \= SharedParent,
    ParentX \= ParentY,
    X \= Y.

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
   Cousin relationships
   ========================================================= */

cousin(X, Y) :-
    parent(Parent1, X),
    parent(Parent2, Y),
    sibling(Parent1, Parent2),
    X \= Y.

first_cousin(X, Y) :-
    cousin(X, Y).

cousin_once_removed(X, Y) :-
    (
        parent(Parent, X),
        cousin(Parent, Y)
    ;
        parent(Parent, Y),
        cousin(X, Parent)
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