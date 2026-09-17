"""IronCycle onboarding choices and starter-plan metadata.
Exercise definitions are sourced exclusively from exercise_catalog.py.
"""
import json
from exercise_catalog import BUILTIN_EXERCISE_CATALOG
CATALOG_VERSION=2
STARTER_TEMPLATES=[
 {'id':'general_full_body','name':'General Full Body','focus':'Balanced','days':'2-4','description':'Balanced push, pull, squat, hinge, single-leg, and core work.'},
 {'id':'chest_focus','name':'Chest Focus','focus':'Chest','days':'3-5','description':'Additional pressing with balanced pulling and lower-body work.'},
 {'id':'back_focus','name':'Back Focus','focus':'Back','days':'3-5','description':'Additional pulling with balanced pressing and lower-body work.'},
 {'id':'leg_focus','name':'Leg Focus','focus':'Legs','days':'3-5','description':'Additional squat, hinge, and single-leg work with upper-body maintenance.'},
 {'id':'upper_lower','name':'Upper / Lower','focus':'Balanced','days':'4','description':'Alternating upper-body and lower-body sessions.'},
 {'id':'push_pull_legs','name':'Push / Pull / Legs','focus':'Balanced','days':'3-6','description':'Sessions organized by pushing, pulling, and lower-body patterns.'},
 {'id':'home_dumbbell','name':'Home Dumbbell Full Body','focus':'Balanced','days':'2-4','description':'A compact plan for dumbbells, bodyweight, and an optional bench.'},
]
EQUIPMENT=['Bodyweight','Dumbbells','Barbell','Adjustable bench','Cable station','Machine','Plate-loaded machine','Smith machine','Resistance bands','Kettlebell','Pull-up bar','Cardio machine','Sled','Medicine ball','Other']
EXPERIENCE_LEVELS=['New to resistance training','Some experience','Experienced','Prefer not to specify']
GOALS=['General strength','Muscle development','General fitness','Return to consistent training','Technique and movement practice']
EQUIPMENT_TO_CATALOG={'Dumbbells':'Dumbbell','Cable station':'Cable','Resistance bands':'Band','Kettlebell':'Kettlebell','Cardio machine':'Machine','Medicine ball':'Medicine Ball','Smith machine':'Machine','Plate-loaded machine':'Machine','Adjustable bench':'Dumbbell'}
def canonical_equipment(values):
 out={'Bodyweight'}
 for value in values or []:out.add(EQUIPMENT_TO_CATALOG.get(value,value))
 return out
def filter_exercises(equipment=None,favorites=None,query=''):
 allowed=canonical_equipment(equipment);favorites=set(favorites or []);q=str(query or '').strip().lower()
 rows=[x for x in BUILTIN_EXERCISE_CATALOG if (not equipment or x.get('equipment') in allowed or x.get('equipment')=='Bodyweight') and (not q or q in (x['name']+' '+x['category']+' '+x['pattern']).lower())]
 return sorted(rows,key=lambda x:(x['id'] not in favorites,x['category'],x['name']))
def recommend_starter_template(goal,training_days,equipment):
 equipment=set(equipment or [])
 if equipment and equipment.issubset({'Bodyweight','Dumbbells','Adjustable bench'}):return 'home_dumbbell'
 if goal=='General strength' and int(training_days or 0)>=4:return 'upper_lower'
 if goal=='Muscle development' and int(training_days or 0)>=5:return 'push_pull_legs'
 return 'general_full_body'
def parse_favorites(raw):
 try:return set(json.loads(raw or '[]'))
 except Exception:return set()
