"""UI-neutral exercise completion orchestration."""
from dataclasses import dataclass
from enum import Enum
class CompletionAction(str,Enum):
 ADVANCE="advance"; APPLY_EXECUTION="apply_execution"; LOG_EXERCISE="log_exercise"; NO_ACTION="no_action"
@dataclass(frozen=True)
class CompletionInstruction:
 action:CompletionAction
 all_done:bool=False
 reason_code:str=""
def resolve_completion_action(*,requested_complete,set_index,total_sets,all_done,execution_available):
 if not requested_complete:return CompletionInstruction(CompletionAction.NO_ACTION,all_done,"SET_REOPENED")
 if execution_available:return CompletionInstruction(CompletionAction.APPLY_EXECUTION,all_done,"EXECUTION_TARGET")
 if all_done and int(set_index)==int(total_sets)-1:return CompletionInstruction(CompletionAction.LOG_EXERCISE,True,"FINAL_SET_COMPLETE")
 return CompletionInstruction(CompletionAction.ADVANCE,all_done,"NEXT_SET")
