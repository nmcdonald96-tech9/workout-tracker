"""Trial and entitlement foundation with non-persistent developer simulation.

Real entitlement data remains outside workout_tracker.db. Developer simulations
exist only in memory, are never written to disk, and can never establish real
lifetime ownership.
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
VALID_SIMULATIONS = (NOT_STARTED, TRIAL_ACTIVE, TRIAL_EXPIRED, LIFETIME_UNLOCKED,
                     PURCHASE_CHECK_PENDING, TEMPORARILY_OFFLINE)

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
    simulated: bool = False
    real_state: str | None = None

class EntitlementService:
    FORMAT_VERSION = 1
    def __init__(self, path, trial_days=14, product_id="ironcycle_lifetime_unlock"):
        self.path=os.path.abspath(path); self.trial_days=int(trial_days); self.product_id=product_id
        self._lock=threading.RLock(); self._data=self._load(); self._simulation=None
    @staticmethod
    def _now(): return datetime.now(timezone.utc)
    @staticmethod
    def _iso(value): return value.astimezone(timezone.utc).isoformat(timespec="seconds")
    @staticmethod
    def _parse(value):
        if not value:return None
        try:
            parsed=datetime.fromisoformat(str(value).replace("Z","+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception:return None
    def _default(self):
        return {"format":self.FORMAT_VERSION,"trial_started_at":None,"trial_expires_at":None,
                "last_seen_at":None,"lifetime_unlocked":False,"billing_provider":"not_connected",
                "clock_rollback_detected":False,"purchase_verified_at":None,"purchase_source":None}
    def _load(self):
        try:
            raw=json.loads(open(self.path,encoding="utf-8").read())
            return {**self._default(),**raw} if isinstance(raw,dict) else self._default()
        except Exception:return self._default()
    def _save(self):
        os.makedirs(os.path.dirname(self.path),exist_ok=True)
        fd,tmp=tempfile.mkstemp(prefix=".entitlement-",suffix=".json",dir=os.path.dirname(self.path))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as f:json.dump(self._data,f,sort_keys=True,indent=2)
            os.chmod(tmp,0o600);os.replace(tmp,self.path)
        finally:
            try:
                if os.path.exists(tmp):os.remove(tmp)
            except Exception:pass
    def _real_snapshot(self):
        now=self._now();last=self._parse(self._data.get("last_seen_at"));changed=False
        if last and now < last-timedelta(minutes=5):self._data["clock_rollback_detected"]=True;changed=True
        if not last or now>last:self._data["last_seen_at"]=self._iso(now);changed=True
        if changed:self._save()
        started=self._parse(self._data.get("trial_started_at"));expires=self._parse(self._data.get("trial_expires_at"))
        if self._data.get("lifetime_unlocked"):state=LIFETIME_UNLOCKED
        elif not started:state=NOT_STARTED
        elif expires and now<expires and not self._data.get("clock_rollback_detected"):state=TRIAL_ACTIVE
        else:state=TRIAL_EXPIRED
        seconds=max(0,(expires-now).total_seconds()) if expires else 0
        days=int((seconds+86399)//86400) if seconds else 0
        return EntitlementSnapshot(state,self._data.get("trial_started_at"),self._data.get("trial_expires_at"),days,
            state==TRIAL_EXPIRED,bool(self._data.get("billing_provider") == "google_play"),self.product_id,bool(self._data.get("clock_rollback_detected")),False,state)
    def start_trial_if_needed(self):
        with self._lock:
            if self._simulation:return self.snapshot()
            if self._data.get("lifetime_unlocked") or self._parse(self._data.get("trial_started_at")):return self.snapshot()
            now=self._now();self._data["trial_started_at"]=self._iso(now)
            self._data["trial_expires_at"]=self._iso(now+timedelta(days=self.trial_days))
            self._data["last_seen_at"]=self._iso(now);self._save();return self.snapshot()
    def snapshot(self):
        with self._lock:
            real=self._real_snapshot()
            if not self._simulation:return real
            state=self._simulation
            days=self.trial_days if state==TRIAL_ACTIVE else 0
            # Pending/offline preserve access if the real state was already entitled.
            transient_entitled=real.state in (TRIAL_ACTIVE,LIFETIME_UNLOCKED)
            limited=(state==TRIAL_EXPIRED) or (state in (PURCHASE_CHECK_PENDING,TEMPORARILY_OFFLINE) and not transient_entitled)
            return EntitlementSnapshot(state,real.trial_started_at,real.trial_expires_at,days,limited,False,
                self.product_id,real.clock_rollback_detected,True,real.state)
    def set_test_simulation(self,state):
        with self._lock:
            if state is not None and state not in VALID_SIMULATIONS:raise ValueError("Unsupported entitlement simulation.")
            self._simulation=state
            return self.snapshot()
    def clear_test_simulation(self):return self.set_test_simulation(None)
    @property
    def simulation_state(self):return self._simulation
    def allow_premium_action(self,start_trial=True):
        snap=self.start_trial_if_needed() if start_trial else self.snapshot()
        if snap.state in (TRIAL_ACTIVE,LIFETIME_UNLOCKED):return True,snap
        if snap.state in (PURCHASE_CHECK_PENDING,TEMPORARILY_OFFLINE) and snap.real_state in (TRIAL_ACTIVE,LIFETIME_UNLOCKED):return True,snap
        return False,snap
    def record_google_play_ownership(self, verification_source="google_play"):
        """Persist an ownership result returned by the installed Google Play billing client."""
        with self._lock:
            if self._simulation:
                raise RuntimeError("Cannot persist ownership while entitlement simulation is active.")
            now=self._now()
            self._data["lifetime_unlocked"]=True
            self._data["billing_provider"]="google_play"
            self._data["purchase_verified_at"]=self._iso(now)
            self._data["purchase_source"]=str(verification_source or "google_play")
            self._data["last_seen_at"]=self._iso(now)
            self._save()
            return self.snapshot()
    def billing_diagnostics(self):
        with self._lock:
            return {
                "provider":self._data.get("billing_provider","not_connected"),
                "verified_at":self._data.get("purchase_verified_at"),
                "source":self._data.get("purchase_source"),
                "owned":bool(self._data.get("lifetime_unlocked")),
            }
    def purchase_unavailable_message(self):
        return "Lifetime Unlock purchasing is not connected in this test build. No charge was attempted."
    def restore_unavailable_message(self):
        return "Google Play purchase restoration is not connected in this test build."
