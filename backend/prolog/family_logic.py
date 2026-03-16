from pyswip import Prolog

prolog = Prolog()

prolog = Prolog()

prolog.consult("family_rules.pl")
prolog.consult("family_facts.pl")

results = list(prolog.query("ancestor(X, tom)"))

print(results)