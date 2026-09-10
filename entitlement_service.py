"""Local trial and entitlement foundation for IronCycle.

Licensing data is intentionally stored outside workout_tracker.db so workout,
local, Wi-Fi, backup-code, and OneDrive restores cannot reset a trial or grant
lifetime ownership. Google Play Billing is not connected in this foundation.
"""
from __future__ import annotations
import json, os, tempfile, threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

TRIAL_ACTIVE = "TRIAL_ACTIVE"
TRIAL_EXPIRED = "TRIAL_EXPIRED"
LIFETIME_UNLOCKED = "LIFETIME_UNLOCKED"
PURCHASE_CHECK_PENDING = "PURCHASE_CHECK_PENDING"
TEMPORARILY_OFFLINE = "TEMPORARILY_OFFLINE"
NOT_STARTED = "NOT_STARTED"

@dataclass(frozen=True)
class EntitlementSnapshot:
    state: str
    trial_started_at: str | None
    trial_expires_at: str | None
    days_remaining: int
    limited_mode: bool
    billing_available: bool
    product_id: str
    clock_rollback_detected: bool

class EntitlementService:
    FORMAT_VERSION = 1
    def __init__(self, path, trial_days=14, product_id="ironcycle_lifetime_unlock"):
        self.path=os.path.abspath(path); self.trial_days=int(trial_days); self.product_id=product_id
        self._lock=threading.RLock(); self._data=self._load()

    @staticmethod
    def _now(): return datetime.now(timezone.utc)
    @staticmethod
    def _iso(value): return value.astimezone(timezone.utc).isoformat(timespec="seconds")
    @staticmethod
    def _parse(value):
        if not value: return None
        try:
            parsed=datetime.fromisoformat(str(value).replace("Z","+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception: return None

    def _default(self):
        return {"format":self.FORMAT_VERSION,"trial_started_at":None,"trial_expires_at":None,
                "last_seen_at":None,"lifetime_unlocked":False,"billing_provider":"not_connected",
                "clock_rollback_detected":False}
    def _load(self):
        try:
            raw=json.loads(open(self.path,encoding="utf-8").read())
            return {**self._default(),**raw} if isinstance(raw,dict) else self._default()
        except Exception: return self._default()
    def _save(self):
        os.makedirs(os.path.dirname(self.path),exist_ok=True)
        fd,tmp=tempfile.mkstemp(prefix=".entitlement-",suffix=".json",dir=os.path.dirname(self.path))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as f: json.dump(self._data,f,sort_keys=True,indent=2)
            os.chmod(tmp,0o600); os.replace(tmp,self.path)
        finally:
            try:
                if os.path.exists(tmp): os.remove(tmp)
            except Exception: pass
    def start_trial_if_needed(self):
        with self._lock:
            if self._data.get("lifetime_unlocked") or self._parse(self._data.get("trial_started_at")):
                return self.snapshot()
            now=self._now(); self._data["trial_started_at"]=self._iso(now)
            self._data["trial_expires_at"]=self._iso(now+timedelta(days=self.trial_days))
            self._data["last_seen_at"]=self._iso(now); self._save(); return self.snapshot()
    def snapshot(self):
        with self._lock:
            now=self._now(); last=self._parse(self._data.get("last_seen_at"))
            if last and now < last-timedelta(minutes=5): self._data["clock_rollback_detected"]=True
            if not last or now>last: self._data["last_seen_at"]=self._iso(now); self._save()
            started=self._parse(self._data.get("trial_started_at")); expires=self._parse(self._data.get("trial_expires_at"))
            if self._data.get("lifetime_unlocked"): state=LIFETIME_UNLOCKED
            elif not started: state=NOT_STARTED
            elif expires and now<expires and not self._data.get("clock_rollback_detected"): state=TRIAL_ACTIVE
            else: state=TRIAL_EXPIRED
            seconds=max(0,(expires-now).total_seconds()) if expires else 0
            days=int((seconds+86399)//86400) if seconds else 0
            return EntitlementSnapshot(state,self._data.get("trial_started_at"),self._data.get("trial_expires_at"),days,
                state==TRIAL_EXPIRED,False,self.product_id,bool(self._data.get("clock_rollback_detected")))
    def allow_premium_action(self, start_trial=True):
        snap=self.start_trial_if_needed() if start_trial else self.snapshot()
        return snap.state in (TRIAL_ACTIVE,LIFETIME_UNLOCKED),snap
    def purchase_unavailable_message(self):
        return "Lifetime Unlock purchasing is not connected in this foundation build. No charge was attempted."
    def restore_unavailable_message(self):
        return "Google Play purchase restoration is not connected in this foundation build."
