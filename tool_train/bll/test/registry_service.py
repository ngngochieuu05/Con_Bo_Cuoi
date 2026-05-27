from dal.jsonb.tester_repository import load_compare_registry, save_compare_registry


def load_registry_data():
    data = load_compare_registry()
    if not data:
        return None, [], False
    if isinstance(data, dict):
        groups = data.get("groups")
        if not groups and data.get("models"):
            groups = [{
                "id": "default",
                "name": "Danh sách",
                "collapsed": False,
                "models": data["models"],
            }]
            return data, groups, True
        return data, groups or [], False
    return data, [], False


def save_registry_data(data, groups, top_level):
    if top_level:
        data["models"] = groups[0].get("models", [])
        data.pop("groups", None)
    else:
        data["groups"] = groups
    save_compare_registry(data)


def move_selected_registry_items(groups, selected: list[int], move_up: bool):
    flat = []
    for gi, group in enumerate(groups):
        for mi, model in enumerate(group.get("models", [])):
            if not model.get("duong_dan"):
                continue
            flat.append((gi, mi, model))

    changed = False
    if move_up:
        for idx in selected:
            if idx <= 0 or idx - 1 in selected:
                continue
            gi, mi, _ = flat[idx]
            prev_gi, prev_mi, _ = flat[idx - 1]
            if gi == prev_gi:
                group = groups[gi]["models"]
                group[prev_mi], group[mi] = group[mi], group[prev_mi]
                flat[idx - 1], flat[idx] = flat[idx], flat[idx - 1]
                changed = True
    else:
        for idx in reversed(selected):
            if idx >= len(flat) - 1 or idx + 1 in selected:
                continue
            gi, mi, _ = flat[idx]
            next_gi, next_mi, _ = flat[idx + 1]
            if gi == next_gi:
                group = groups[gi]["models"]
                group[next_mi], group[mi] = group[mi], group[next_mi]
                flat[idx + 1], flat[idx] = flat[idx], flat[idx + 1]
                changed = True

    return changed, groups, flat
