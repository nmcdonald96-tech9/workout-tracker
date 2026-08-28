def navigation_items(rows):
    return [{"category":c,"total":int(t or 0),"pending":int(p or 0),"complete":int(p or 0)==0} for c,t,p in rows]
