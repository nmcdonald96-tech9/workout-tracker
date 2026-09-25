from pathlib import Path
from services.structural_refresh_service import StructuralRefreshCoordinator
ROOT=Path(__file__).resolve().parents[1]
def test_coalesces_and_promotes_flags():
 q=[]; a=[]; c=StructuralRefreshCoordinator(q.append,a.append)
 assert c.request("add",remount_canvas=False)
 assert not c.request("remove",rebuild_navigation=True)
 assert not c.request("add",remount_canvas=True)
 assert len(q)==1; q.pop(0)(); r=a[0]
 assert r.reasons==("add","remove") and r.rebuild_navigation and r.remount_canvas
def test_reentrant_request_gets_second_drain():
 q=[]; a=[]; c=None
 def apply(r):
  a.append(r)
  if len(a)==1: c.request("follow_up")
 c=StructuralRefreshCoordinator(q.append,apply); c.request("first"); q.pop(0)()
 assert len(q)==1; q.pop(0)(); assert [x.reasons for x in a]==[("first",),("follow_up",)]
def test_exercise_card_callbacks_use_coordinator():
 s=(ROOT/'main.py').read_text(); card=s[:s.index('class WorkoutTrackerApp:')]
 assert 'self.app.rebuild_entire_display()' not in card
 assert card.count('request_structural_refresh(')>=8
 assert 'await asyncio.sleep(0)' in s
def test_release_contract():
 c=(ROOT/'constants.py').read_text()
 assert 'APP_VERSION = "1.92.3"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
 assert (ROOT/'docs/releases/RELEASE_1.92.0.md').exists()