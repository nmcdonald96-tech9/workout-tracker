"""Pure exercise-card presentation classification."""
from dataclasses import dataclass
from enum import Enum
class ExerciseCardMode(str,Enum):
 PENDING_FULL="pending_full"; COMPLETED_COMPACT="completed_compact"; SKIPPED_COMPACT="skipped_compact"; REVISION_FULL="revision_full"
@dataclass(frozen=True)
class ExerciseCardState:
 mode:ExerciseCardMode
 editable:bool
 show_set_controls:bool
 allow_structure_edit:bool
 summary:str
 actions:tuple[str,...]
def classify_exercise_card(status,*,revision_active=False,prescribed_sets=0):
 status=str(status or "")
 if revision_active:return ExerciseCardState(ExerciseCardMode.REVISION_FULL,True,True,True,"Revision",("cancel_revision","save_revision"))
 if status=="Completed":return ExerciseCardState(ExerciseCardMode.COMPLETED_COMPACT,False,False,False,"Completed",("history","revise","return_to_pending"))
 if status=="Skipped":return ExerciseCardState(ExerciseCardMode.SKIPPED_COMPACT,False,False,False,f"Skipped • {int(prescribed_sets or 0)} prescribed sets",("history","unskip"))
 return ExerciseCardState(ExerciseCardMode.PENDING_FULL,True,True,True,"Pending",("skip","add_set","remove_set","log"))
