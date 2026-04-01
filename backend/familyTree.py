from collections import deque, defaultdict
from flask import g
from models import Person

def collect_family(root_person):
    people = {}
    parent_edges = []
    spouse_edges = []
    visited = set()
    queue = deque([root_person])

    while queue:
        person = queue.popleft()
        if person.id in visited:
            continue
        visited.add(person.id)
        people[person.id] = person

        # parents
        for parent in [person.parent1_id, person.parent2_id]:
            if parent and g.user.hasPrivacyLevel(parent.privacy):
                parent_edges.append((parent.id, person.id))
                if parent.id not in visited:
                    queue.append(parent)

        # spouse
        if person.spouse_id and g.user.hasPrivacyLevel(person.spouse_id.privacy):
            a, b = sorted([person.id, person.spouse_id.id])
            spouse_edges.append((a, b))
            if person.spouse_id.id not in visited:
                queue.append(person.spouse_id)

        # children
        children = Person.select().where(
            (Person.parent1_id == person) | (Person.parent2_id == person)
        )
        for child in children:
            if not g.user.hasPrivacyLevel(child.privacy):
                continue
            parent_edges.append((person.id, child.id))
            if child.id not in visited:
                queue.append(child)

    parent_edges = list(set(parent_edges))
    spouse_edges = list(set(spouse_edges))
    return people, parent_edges, spouse_edges

def assign_generations(root_id, people, parent_edges, spouse_edges):
    generation = {root_id: 0}
    queue = deque([root_id])

    parents_of = defaultdict(list)
    children_of = defaultdict(list)
    spouses_of = defaultdict(list)

    for p, c in parent_edges:
        children_of[p].append(c)
        parents_of[c].append(p)

    for a, b in spouse_edges:
        spouses_of[a].append(b)
        spouses_of[b].append(a)

    while queue:
        pid = queue.popleft()
        g0 = generation[pid]

        for parent_id in parents_of[pid]:
            if parent_id not in generation:
                generation[parent_id] = g0 - 1
                queue.append(parent_id)

        for child_id in children_of[pid]:
            if child_id not in generation:
                generation[child_id] = g0 + 1
                queue.append(child_id)

        for spouse_id in spouses_of[pid]:
            if spouse_id not in generation:
                generation[spouse_id] = g0
                queue.append(spouse_id)

    # In case some nodes are disconnected by privacy weirdness,
    # give them fallback generation 0
    for pid in people:
        generation.setdefault(pid, 0)

    return generation

def group_by_generation(generation):
    rows = defaultdict(list)
    for pid, gen in generation.items():
        rows[gen].append(pid)
    return rows

def initial_row_order(rows, people):
    for gen in rows:
        rows[gen].sort(key=lambda pid: (
            people[pid].lastName or "",
            people[pid].firstName or ""
        ))
    return rows

def assign_positions(rows, generation, h_spacing=240, v_spacing=180):
    positions = {}
    for gen in sorted(rows.keys()):
        row = rows[gen]
        start_x = -((len(row) - 1) * h_spacing) / 2
        y = gen * v_spacing
        for i, pid in enumerate(row):
            positions[pid] = {
                "x": start_x + i * h_spacing,
                "y": y
            }
    return positions

def keep_spouses_adjacent(rows, spouse_edges):
    spouse_map = {}
    for a, b in spouse_edges:
        spouse_map.setdefault(a, set()).add(b)
        spouse_map.setdefault(b, set()).add(a)

    for gen, row in rows.items():
        i = 0
        while i < len(row) - 1:
            pid = row[i]
            spouses = spouse_map.get(pid, set())

            spouse_index = None
            for j in range(i + 1, len(row)):
                if row[j] in spouses:
                    spouse_index = j
                    break

            if spouse_index is not None and spouse_index != i + 1:
                spouse_id = row.pop(spouse_index)
                row.insert(i + 1, spouse_id)

            i += 1

    return rows

def build_family_units(people):
    families = defaultdict(list)

    for child in people.values():
        p1 = child.parent1_id.id if child.parent1_id and child.parent1_id.id in people else None
        p2 = child.parent2_id.id if child.parent2_id and child.parent2_id.id in people else None

        key = tuple(sorted([x for x in [p1, p2] if x is not None]))
        if key:
            families[key].append(child.id)

    return families