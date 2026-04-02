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



def format_years(person):
    birth = str(person.birthDay.year) if person.birthDay else "?"
    death = str(person.deathDay.year) if person.deathDay else ""
    return f"{birth}–{death}" if death else f"{birth}–"

def align_last_generation_under_parents(
    positions,
    generation,
    two_parent_families,
    single_parent_families,
    node_width=160,
    child_spacing=120,
):
    if not generation:
        return

    last_gen = max(generation.values())

    # Two-parent families
    for (p1_id, p2_id), child_ids in two_parent_families.items():
        last_gen_children = [cid for cid in child_ids if generation.get(cid) == last_gen and cid in positions]
        if not last_gen_children:
            continue

        if p1_id not in positions or p2_id not in positions:
            continue

        p1_center = positions[p1_id]["x"] + node_width / 2
        p2_center = positions[p2_id]["x"] + node_width / 2
        family_center = (p1_center + p2_center) / 2

        start_x = family_center - ((len(last_gen_children) - 1) * child_spacing) / 2 - node_width / 2

        # stable left-to-right order
        last_gen_children = sorted(last_gen_children)

        for i, child_id in enumerate(last_gen_children):
            positions[child_id]["x"] = start_x + i * child_spacing

    # Single-parent families
    for parent_id, child_ids in single_parent_families.items():
        last_gen_children = [cid for cid in child_ids if generation.get(cid) == last_gen and cid in positions]
        if not last_gen_children:
            continue

        if parent_id not in positions:
            continue

        parent_center = positions[parent_id]["x"] + node_width / 2
        start_x = parent_center - ((len(last_gen_children) - 1) * child_spacing) / 2 - node_width / 2

        last_gen_children = sorted(last_gen_children)

        for i, child_id in enumerate(last_gen_children):
            positions[child_id]["x"] = start_x + i * child_spacing
            
def center_generation_over_children(
    positions,
    generation,
    two_parent_families,
    single_parent_families,
    target_generation,
    node_width=160,
    spouse_gap=40,
):
    """
    Reposition one generation so each parent pair is centered over its children.
    target_generation is the parent row to move.
    """

    # Two-parent families
    for (p1_id, p2_id), child_ids in two_parent_families.items():
        if generation.get(p1_id) != target_generation:
            continue

        if p1_id not in positions or p2_id not in positions:
            continue

        visible_children = [cid for cid in child_ids if cid in positions]
        if not visible_children:
            continue

        child_centers = [positions[cid]["x"] + node_width / 2 for cid in visible_children]
        family_center = sum(child_centers) / len(child_centers)

        total_width = (2 * node_width) + spouse_gap
        left_x = family_center - (total_width / 2)

        positions[p1_id]["x"] = left_x
        positions[p2_id]["x"] = left_x + node_width + spouse_gap

    # Single-parent families
    for parent_id, child_ids in single_parent_families.items():
        if generation.get(parent_id) != target_generation:
            continue

        if parent_id not in positions:
            continue

        visible_children = [cid for cid in child_ids if cid in positions]
        if not visible_children:
            continue

        child_centers = [positions[cid]["x"] + node_width / 2 for cid in visible_children]
        family_center = sum(child_centers) / len(child_centers)

        positions[parent_id]["x"] = family_center - node_width / 2
        
def add_edge_once(edge_list, added, edge):
    key = (
        edge["source"],
        edge["target"],
        edge.get("sourceHandle"),
        edge.get("targetHandle"),
        edge.get("type"),
    )
    if key in added:
        return
    added.add(key)
    edge_list.append(edge)

def add_junction_node(node_list, added, node_id, x, y):
    if node_id in added:
        return
    node_list.append({
        "id": node_id,
        "type": "familyJunction",
        "data": {"label": ""},
        "position": {"x": x, "y": y},
        "draggable": False,
        "selectable": False,
    })
    added.add(node_id)

def build_rows(generation):
    rows = {}
    for pid, gen in generation.items():
        rows.setdefault(gen, []).append(pid)
    return rows

def build_spouse_map(spouse_edges):
    spouse_map = {}
    for a, b in spouse_edges:
        spouse_map.setdefault(a, set()).add(b)
        spouse_map.setdefault(b, set()).add(a)
    return spouse_map

def order_rows(rows, spouse_map):
    ordered = {}
    for gen in sorted(rows.keys()):
        row = sorted(rows[gen])
        used = set()
        out = []

        for pid in row:
            if pid in used:
                continue

            spouses = [s for s in spouse_map.get(pid, set()) if s in row and s not in used]
            if spouses:
                sid = sorted(spouses)[0]
                pair = sorted([pid, sid])
                out.extend(pair)
                used.add(pid)
                used.add(sid)
            else:
                out.append(pid)
                used.add(pid)

        ordered[gen] = out
    return ordered

def assign_positions(rows, spouse_edges, H_SPACING=200, V_SPACING=150, NODE_WIDTH=160, SPOUSE_GAP=40):
    positions = {}
    for gen in sorted(rows.keys()):
        row = rows[gen]
        start_x = -((len(row) - 1) * H_SPACING) / 2
        y = gen * V_SPACING

        i = 0
        while i < len(row):
            pid = row[i]

            # keep spouses tighter together if adjacent spouse pair
            if i + 1 < len(row):
                next_id = row[i + 1]
                if tuple(sorted((pid, next_id))) in set(tuple(sorted(x)) for x in spouse_edges):
                    pair_x = start_x + i * H_SPACING
                    positions[pid] = {"x": pair_x, "y": y}
                    positions[next_id] = {"x": pair_x + NODE_WIDTH + SPOUSE_GAP, "y": y}
                    i += 2
                    continue

            positions[pid] = {"x": start_x + i * H_SPACING, "y": y}
            i += 1

    return positions

def build_family_groups(people):
    two_parent = {}
    single_parent = {}

    for person in people.values():
        parents = []

        if person.parent1_id and person.parent1_id.id in people:
            parents.append(person.parent1_id.id)
        if person.parent2_id and person.parent2_id.id in people:
            parents.append(person.parent2_id.id)

        parents = sorted(set(parents))

        if len(parents) == 2:
            two_parent.setdefault((parents[0], parents[1]), []).append(person.id)
        elif len(parents) == 1:
            single_parent.setdefault(parents[0], []).append(person.id)

    return two_parent, single_parent