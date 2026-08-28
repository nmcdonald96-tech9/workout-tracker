def active_set_index(rows):
    for i,row in enumerate(rows or []):
        if not row.get('done'):return i
    return len(rows)-1 if rows else 0
