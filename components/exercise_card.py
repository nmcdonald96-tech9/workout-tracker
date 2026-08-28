def active_set_index(rows):
    for index,row in enumerate(rows or []):
        if not row.get("done"): return index
    return len(rows)-1 if rows else 0
