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

        for parent in [person.parent1_id, person.parent2_id]:
            if parent and g.user.hasPrivacyLevel(parent.privacy):
                parent_edges.append((parent.id, person.id))
                if parent.id not in visited:
                    queue.append(parent)

        if person.spouse_id and g.user.hasPrivacyLevel(person.spouse_id.privacy):
            a, b = sorted([person.id, person.spouse_id.id])
            spouse_edges.append((a, b))
            if person.spouse_id.id not in visited:
                queue.append(person.spouse_id)

        children = Person.select().where(
            (Person.parent1_id == person) | (Person.parent2_id == person)
        )
        for child in children:
            if not g.user.hasPrivacyLevel(child.privacy):
                continue
            parent_edges.append((person.id, child.id))
            if child.id not in visited:
                queue.append(child)

    return people, list(set(parent_edges)), list(set(spouse_edges))


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

    for pid in people:
        generation.setdefault(pid, 0)

    return generation


def format_years(person):
    birth = str(person.birthDay.year) if person.birthDay else "?"
    death = str(person.deathDay.year) if getattr(person, "deathDay", None) else ""
    return f"{birth}-{death}" if death else f"{birth}-"


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


def add_junction_node(node_list, added, node_id, x, y, line_color="rgb(0,0,0,0)"):
    if node_id in added:
        return
    node_list.append({
        "id": node_id,
        "type": "familyJunction",
        "data": {
            "label": "",
            "lineColor": line_color,
        },
        "position": {"x": x, "y": y},
        "draggable": False,
        "selectable": False,
    })
    added.add(node_id)


def build_spouse_map(spouse_edges):
    spouse_map = defaultdict(set)
    for a, b in spouse_edges:
        spouse_map[a].add(b)
        spouse_map[b].add(a)
    return spouse_map


def build_family_groups(people, parent_edges=None):
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
            key = (parents[0], parents[1])
            two_parent.setdefault(key, []).append(person.id)
        elif len(parents) == 1:
            key = parents[0]
            single_parent.setdefault(key, []).append(person.id)

    for key in two_parent:
        two_parent[key] = sorted(two_parent[key])
    for key in single_parent:
        single_parent[key] = sorted(single_parent[key])

    return two_parent, single_parent


def build_person_to_own_family(two_parent_families, single_parent_families):
    person_to_family = {}

    for (p1_id, p2_id), child_ids in two_parent_families.items():
        fam_key = ("two", p1_id, p2_id)
        person_to_family[p1_id] = fam_key
        person_to_family[p2_id] = fam_key

    for parent_id, child_ids in single_parent_families.items():
        fam_key = ("one", parent_id)
        person_to_family[parent_id] = fam_key

    return person_to_family


def build_child_to_birth_family(two_parent_families, single_parent_families):
    child_to_birth_family = {}

    for key, child_ids in two_parent_families.items():
        fam_key = ("two", key[0], key[1])
        for cid in child_ids:
            child_to_birth_family[cid] = fam_key

    for parent_id, child_ids in single_parent_families.items():
        fam_key = ("one", parent_id)
        for cid in child_ids:
            child_to_birth_family[cid] = fam_key

    return child_to_birth_family


def build_root_families(two_parent_families, single_parent_families):
    child_to_birth_family = build_child_to_birth_family(two_parent_families, single_parent_families)
    roots = []

    for (p1_id, p2_id), child_ids in two_parent_families.items():
        if p1_id not in child_to_birth_family and p2_id not in child_to_birth_family:
            roots.append(("two", p1_id, p2_id))

    for parent_id, child_ids in single_parent_families.items():
        if parent_id not in child_to_birth_family:
            roots.append(("one", parent_id))

    roots.sort()
    return roots


def find_family_for_person(person_id, person_to_family):
    return person_to_family.get(person_id)


def compute_family_subtree_width(
    family_key,
    two_parent_families,
    single_parent_families,
    person_to_family,
    node_width=160,
    spouse_gap=40,
    sibling_gap=50,
    width_cache=None,
):
    if width_cache is None:
        width_cache = {}

    if family_key in width_cache:
        return width_cache[family_key]

    if family_key[0] == "two":
        _, p1_id, p2_id = family_key
        child_ids = two_parent_families.get((p1_id, p2_id), [])
        parent_width = node_width * 2 + spouse_gap
    else:
        _, parent_id = family_key
        child_ids = single_parent_families.get(parent_id, [])
        parent_width = node_width

    if not child_ids:
        width_cache[family_key] = parent_width
        return parent_width

    child_widths = []
    seen_child_families = set()

    for child_id in child_ids:
        child_family = find_family_for_person(child_id, person_to_family)

        if child_family is None:
            child_widths.append(node_width)
        else:
            if child_family in seen_child_families:
                continue
            seen_child_families.add(child_family)

            child_widths.append(
                compute_family_subtree_width(
                    child_family,
                    two_parent_families,
                    single_parent_families,
                    person_to_family,
                    node_width=node_width,
                    spouse_gap=spouse_gap,
                    sibling_gap=sibling_gap,
                    width_cache=width_cache,
                )
            )

    children_width = sum(child_widths) + max(0, len(child_widths) - 1) * sibling_gap
    total_width = max(parent_width, children_width)

    width_cache[family_key] = total_width
    return total_width


def layout_family_subtree(
    family_key,
    x_left,
    y_top,
    positions,
    two_parent_families,
    single_parent_families,
    person_to_family,
    node_width=160,
    spouse_gap=40,
    level_gap=180,
    sibling_gap=50,
    width_cache=None,
):
    if width_cache is None:
        width_cache = {}

    subtree_width = compute_family_subtree_width(
        family_key,
        two_parent_families,
        single_parent_families,
        person_to_family,
        node_width=node_width,
        spouse_gap=spouse_gap,
        sibling_gap=sibling_gap,
        width_cache=width_cache,
    )

    family_center = x_left + subtree_width / 2

    if family_key[0] == "two":
        _, p1_id, p2_id = family_key
        child_ids = two_parent_families.get((p1_id, p2_id), [])
        parent_block_width = node_width * 2 + spouse_gap

        left_parent_x = family_center - parent_block_width / 2
        positions[p1_id] = {"x": left_parent_x, "y": y_top}
        positions[p2_id] = {"x": left_parent_x + node_width + spouse_gap, "y": y_top}
    else:
        _, parent_id = family_key
        child_ids = single_parent_families.get(parent_id, [])
        positions[parent_id] = {"x": family_center - node_width / 2, "y": y_top}

    if not child_ids:
        return

    child_entries = []
    seen_child_families = set()

    for child_id in child_ids:
        child_family = find_family_for_person(child_id, person_to_family)

        if child_family is None:
            child_entries.append(("leaf", child_id, node_width))
        else:
            if child_family in seen_child_families:
                continue
            seen_child_families.add(child_family)

            child_width = compute_family_subtree_width(
                child_family,
                two_parent_families,
                single_parent_families,
                person_to_family,
                node_width=node_width,
                spouse_gap=spouse_gap,
                sibling_gap=sibling_gap,
                width_cache=width_cache,
            )
            child_entries.append(("family", child_family, child_width))

    children_total_width = sum(entry[2] for entry in child_entries) + max(0, len(child_entries) - 1) * sibling_gap
    child_x = family_center - children_total_width / 2
    child_y = y_top + level_gap

    for entry_type, payload, width in child_entries:
        if entry_type == "leaf":
            child_id = payload
            positions[child_id] = {
                "x": child_x + (width - node_width) / 2,
                "y": child_y,
            }
        else:
            child_family = payload
            layout_family_subtree(
                child_family,
                child_x,
                child_y,
                positions,
                two_parent_families,
                single_parent_families,
                person_to_family,
                node_width=node_width,
                spouse_gap=spouse_gap,
                level_gap=level_gap,
                sibling_gap=sibling_gap,
                width_cache=width_cache,
            )

        child_x += width + sibling_gap


def layout_full_tree(
    people,
    generation,
    two_parent_families,
    single_parent_families,
    node_width=160,
    spouse_gap=40,
    level_gap=180,
    root_gap=120,
    sibling_gap=50,
):
    positions = {}
    person_to_family = build_person_to_own_family(two_parent_families, single_parent_families)
    roots = build_root_families(two_parent_families, single_parent_families)

    width_cache = {}
    root_widths = []

    for root_family in roots:
        root_widths.append(
            compute_family_subtree_width(
                root_family,
                two_parent_families,
                single_parent_families,
                person_to_family,
                node_width=node_width,
                spouse_gap=spouse_gap,
                sibling_gap=sibling_gap,
                width_cache=width_cache,
            )
        )

    total_width = sum(root_widths) + max(0, len(root_widths) - 1) * root_gap
    cursor_x = -total_width / 2

    for root_family, width in zip(roots, root_widths):
        layout_family_subtree(
            root_family,
            cursor_x,
            0,
            positions,
            two_parent_families,
            single_parent_families,
            person_to_family,
            node_width=node_width,
            spouse_gap=spouse_gap,
            level_gap=level_gap,
            sibling_gap=sibling_gap,
            width_cache=width_cache,
        )
        cursor_x += width + root_gap

    # fallback for any visible people missed by the family recursion
    unplaced_by_gen = defaultdict(list)
    for pid in people:
        if pid not in positions:
            unplaced_by_gen[generation.get(pid, 0)].append(pid)

    for gen, pids in unplaced_by_gen.items():
        pids.sort()
        y = gen * level_gap
        start_x = 0
        for i, pid in enumerate(pids):
            positions[pid] = {
                "x": start_x + i * (node_width + 40),
                "y": y,
            }

    return positions

def snap_spouse_only_people(
    positions,
    people,
    two_parent_families,
    single_parent_families,
    node_width=160,
    spouse_gap=40,
):
    """
    Move spouse-only people next to their spouse after subtree layout.

    This fixes cases like:
    - Nora + test spouse
    where Nora is in a parent family but test spouse is not.
    """
    parent_ids = set()

    for (p1_id, p2_id) in two_parent_families.keys():
        parent_ids.add(p1_id)
        parent_ids.add(p2_id)

    for parent_id in single_parent_families.keys():
        parent_ids.add(parent_id)

    moved = set()

    for pid, person in people.items():
        if pid in moved:
            continue

        if not person.spouse_id:
            continue

        sid = person.spouse_id.id
        if sid not in people or sid not in positions:
            continue

        # If this person already belongs to a laid-out parent family, leave it alone
        if pid in parent_ids:
            continue

        # If spouse is part of a laid-out family, snap this person next to them
        if sid in parent_ids:
            spouse_x = positions[sid]["x"]
            spouse_y = positions[sid]["y"]

            # default: place spouse-only leaf to the right
            positions[pid]["x"] = spouse_x + node_width + spouse_gap
            positions[pid]["y"] = spouse_y
            moved.add(pid)
            continue
        
def center_top_families_over_immediate_children(
    positions,
    generation,
    two_parent_families,
    single_parent_families,
    node_width=160,
    spouse_gap=40,
):
    """
    Move only the top-generation parent blocks so they are centered over
    their immediate children, not over the full width of all descendants.
    """
    if not generation:
        return

    top_gen = min(generation.values())

    # two-parent top families
    for (p1_id, p2_id), child_ids in two_parent_families.items():
        if generation.get(p1_id) != top_gen or generation.get(p2_id) != top_gen:
            continue

        visible_children = [cid for cid in child_ids if cid in positions]
        if not visible_children:
            continue

        child_centers = [positions[cid]["x"] + node_width / 2 for cid in visible_children]
        family_center = sum(child_centers) / len(child_centers)

        total_parent_width = (2 * node_width) + spouse_gap
        left_x = family_center - (total_parent_width / 2)

        positions[p1_id]["x"] = left_x
        positions[p2_id]["x"] = left_x + node_width + spouse_gap

    # single-parent top families
    for parent_id, child_ids in single_parent_families.items():
        if generation.get(parent_id) != top_gen:
            continue

        visible_children = [cid for cid in child_ids if cid in positions]
        if not visible_children:
            continue

        child_centers = [positions[cid]["x"] + node_width / 2 for cid in visible_children]
        family_center = sum(child_centers) / len(child_centers)

        positions[parent_id]["x"] = family_center - node_width / 2
        
def spread_top_family_blocks(
    positions,
    generation,
    two_parent_families,
    single_parent_families,
    node_width=160,
    spouse_gap=40,
    family_gap=60,
):
    """
    After centering top families over their immediate children,
    pack the top-generation family blocks left-to-right so they do not overlap.
    """
    if not generation:
        return

    top_gen = min(generation.values())
    blocks = []

    # two-parent families on top row
    for (p1_id, p2_id), child_ids in two_parent_families.items():
        if generation.get(p1_id) != top_gen or generation.get(p2_id) != top_gen:
            continue

        left = min(positions[p1_id]["x"], positions[p2_id]["x"])
        right = max(positions[p1_id]["x"], positions[p2_id]["x"]) + node_width
        center = (left + right) / 2

        blocks.append({
            "kind": "two",
            "ids": (p1_id, p2_id),
            "left": left,
            "width": right - left,
            "center": center,
        })

    # single-parent families on top row
    for parent_id, child_ids in single_parent_families.items():
        if generation.get(parent_id) != top_gen:
            continue

        left = positions[parent_id]["x"]
        right = left + node_width
        center = (left + right) / 2

        blocks.append({
            "kind": "one",
            "ids": (parent_id,),
            "left": left,
            "width": right - left,
            "center": center,
        })

    if not blocks:
        return

    # sort by current center
    blocks.sort(key=lambda b: b["center"])

    # remember average center so row does not drift
    old_avg_center = sum(b["center"] for b in blocks) / len(blocks)

    # left-to-right packing
    prev_right = None
    for block in blocks:
        desired_left = block["left"]

        if prev_right is None:
            new_left = desired_left
        else:
            new_left = max(desired_left, prev_right + family_gap)

        block["left"] = new_left
        block["center"] = new_left + block["width"] / 2
        prev_right = new_left + block["width"]

    # recenter the whole top row approximately where it was
    new_avg_center = sum(b["center"] for b in blocks) / len(blocks)
    shift = old_avg_center - new_avg_center

    for block in blocks:
        block["left"] += shift

    # write positions back
    for block in blocks:
        if block["kind"] == "two":
            p1_id, p2_id = block["ids"]
            positions[p1_id]["x"] = block["left"]
            positions[p2_id]["x"] = block["left"] + node_width + spouse_gap
        else:
            (parent_id,) = block["ids"]
            positions[parent_id]["x"] = block["left"]