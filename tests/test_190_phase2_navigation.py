from services.workout_navigation_service import *
class N:
 def __init__(self,key=None,height=None,content=None):self.key=key;self.height=height;self.content=content;self.controls=[]
def test_jump():
 s,r=jump_to_category_state({},['A','B'],'B');assert s=={'a':True,'b':False} and r.remount
def test_offset():
 xs=[N('category-a',40),N(height=100),N(content=N('category-b'))];h=lambda x:x.height or 64
 assert find_control_offset(xs,'category-b',height_estimator=h)==144
