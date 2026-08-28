from app.compatibility import compatible_checkbox
def build_tag_controls(ft,options,selected,on_change): return [compatible_checkbox(ft,x,x in selected,on_change) for x in options]
