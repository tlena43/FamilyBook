# Hardcoded sample family for testing purposes ONLY.
# In production, this file SHOULD NOT BE USED!!!
male(john).
male(paul).
male(tom).

female(lisa).
female(anna).
female(mary).


spouse(john,mary).
spouse(mary,john).

spouse(paul,lisa).
spouse(lisa,paul).


/* John and Mary have two children */
parent(john,paul).
parent(mary,paul).

parent(john,lisa).
parent(mary,lisa).

/* Their children have kids */
parent(paul,anna).
parent(lisa,tom).