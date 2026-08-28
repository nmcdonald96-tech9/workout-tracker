def effective_settings(*args,**kwargs):
    from database import get_effective_progression_settings
    return get_effective_progression_settings(*args,**kwargs)
def next_set_targets(*args,**kwargs):
    from database import calculate_set_specific_progression
    return calculate_set_specific_progression(*args,**kwargs)
def classify_set(*args,**kwargs):
    from database import classify_set_progression
    return classify_set_progression(*args,**kwargs)
