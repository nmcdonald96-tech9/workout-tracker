"""OneDrive App Folder transport for IronCycle.
Public device-code client. No client secret. Tokens and pending authorization
are kept outside the workout database and are never included in backups.
"""
import hashlib, json, os, threading, time
import urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

CLIENT_ID = "cab9c010-af5e-4d42-918f-51ae4a6ebdd8"
AUTHORITY = "https://login.microsoftonline.com/common/oauth2/v2.0"
GRAPH = "https://graph.microsoft.com/v1.0"
SCOPES = "openid profile offline_access Files.ReadWrite.AppFolder"

class OneDriveError(RuntimeError): pass

class OneDriveService:
    def __init__(self, token_path, pending_path):
        self.token_path, self.pending_path = token_path, pending_path
        self._token = self._read(token_path)
        self._lock = threading.Lock()

    def _read(self, path):
        try:
            with open(path, encoding="utf-8") as f: return json.load(f)
        except Exception: return {}

    def _write(self, path, value):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f: json.dump(value, f)
        try: os.chmod(path, 0o600)
        except Exception: pass

    def _remove(self, path):
        try: os.remove(path)
        except FileNotFoundError: pass

    def has_saved_authorization(self):
        return bool(self._token.get("refresh_token") or self._token.get("access_token"))

    def disconnect(self):
        self._token = {}; self._remove(self.token_path); self.clear_pending()

    def pending_authorization(self):
        pending = self._read(self.pending_path)
        if pending and int(pending.get("expires_at", 0)) > int(time.time()): return pending
        if pending: self.clear_pending()
        return None

    def clear_pending(self): self._remove(self.pending_path)

    def _request(self, url, data=None, headers=None, method=None, timeout=60):
        req = urllib.request.Request(url, data=data, headers=headers or {}, method=method or ("POST" if data is not None else "GET"))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                raw = res.read(); return json.loads(raw.decode("utf-8")) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                payload = json.loads(raw); err = payload.get("error")
                msg = err.get("message") if isinstance(err, dict) else payload.get("error_description") or err or raw
            except Exception: msg = raw
            raise OneDriveError(f"HTTP {exc.code}: {msg}")
        except urllib.error.URLError as exc: raise OneDriveError(f"Network unavailable: {exc.reason}")

    def begin_device_code(self):
        result = self._request(AUTHORITY + "/devicecode", urllib.parse.urlencode({"client_id": CLIENT_ID, "scope": SCOPES}).encode())
        if not result.get("device_code"): raise OneDriveError("Microsoft sign-in could not start.")
        result["expires_at"] = int(time.time()) + int(result.get("expires_in", 900))
        self._write(self.pending_path, result); return result

    def poll_pending_once(self):
        p = self.pending_authorization()
        if not p: raise OneDriveError("No active Microsoft sign-in is waiting.")
        data = urllib.parse.urlencode({"grant_type":"urn:ietf:params:oauth:grant-type:device_code","client_id":CLIENT_ID,"device_code":p["device_code"]}).encode()
        try: token = self._request(AUTHORITY + "/token", data)
        except OneDriveError as exc:
            text = str(exc).lower()
            if any(x in text for x in ("authorization_pending","aadsts70016","has not yet been authorized","must input their code","authorization is pending")): return "pending"
            if "slow_down" in text:
                p["interval"] = int(p.get("interval", 5)) + 5; self._write(self.pending_path, p); return "pending"
            if "authorization_declined" in text or "access_denied" in text: self.clear_pending(); raise OneDriveError("Microsoft sign-in was declined.")
            if "expired_token" in text: self.clear_pending(); raise OneDriveError("Microsoft sign-in code expired.")
            raise
        if not token.get("access_token"): return "pending"
        token["expires_at"] = int(time.time()) + int(token.get("expires_in", 3600)) - 60
        self._write(self.token_path, token); self._token = token; self.clear_pending(); return "connected"

    def complete_device_code(self, cancel_event):
        while self.pending_authorization():
            if cancel_event.is_set(): self.clear_pending(); raise OneDriveError("Microsoft sign-in canceled.")
            if self.poll_pending_once() == "connected": return
            p = self.pending_authorization(); time.sleep(max(5, int((p or {}).get("interval", 5))))
        raise OneDriveError("Microsoft sign-in expired or was canceled.")

    def _access_token(self):
        token = self._token or self._read(self.token_path)
        if token.get("access_token") and int(token.get("expires_at", 0)) > int(time.time()): self._token = token; return token["access_token"]
        refresh = token.get("refresh_token")
        if not refresh: raise OneDriveError("Reconnect required: no refresh token is available.")
        try:
            updated = self._request(AUTHORITY + "/token", urllib.parse.urlencode({"client_id":CLIENT_ID,"grant_type":"refresh_token","refresh_token":refresh,"scope":SCOPES}).encode())
        except OneDriveError as exc:
            if "invalid_grant" in str(exc).lower() or "401" in str(exc): self.disconnect(); raise OneDriveError("Reconnect required: Microsoft rejected the saved authorization.")
            raise
        updated.setdefault("refresh_token", refresh); updated["expires_at"] = int(time.time()) + int(updated.get("expires_in",3600)) - 60
        self._write(self.token_path, updated); self._token = updated; return updated["access_token"]

    def _graph(self, path, data=None, method=None, ctype=None, retry=True):
        headers = {"Authorization":"Bearer " + self._access_token()}
        if ctype: headers["Content-Type"] = ctype
        try: return self._request(GRAPH + path, data, headers, method)
        except OneDriveError as exc:
            if retry and "HTTP 401" in str(exc):
                self._token["expires_at"] = 0; self._write(self.token_path, self._token)
                return self._graph(path, data, method, ctype, retry=False)
            raise

    def verify_connection(self):
        app_root = self._graph("/me/drive/special/approot")
        manifest = None
        try: manifest = self.latest_manifest()
        except OneDriveError as exc:
            if "404" not in str(exc) and "itemnotfound" not in str(exc).lower(): raise
        return {"ok":bool(app_root.get("id")),"checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),"manifest":manifest}

    def upload_backup(self, text, reason, version, schema):
        with self._lock:
            stamp=datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S"); safe="".join(c if c.isalnum() or c=="-" else "-" for c in reason.lower()).strip("-") or "manual"
            name=f"{stamp}__{safe}.icbackup"; raw=text.encode("utf-8"); digest=hashlib.sha256(raw).hexdigest(); q=urllib.parse.quote(name,safe="")
            item=self._graph(f"/me/drive/special/approot:/backups/{q}:/content",raw,"PUT","text/plain; charset=utf-8")
            manifest={"format":"ironcycle-cloud-backup-v1","backup_file":"backups/"+name,"created_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),"app_version":version,"schema_version":int(schema),"sha256":digest,"reason":reason,"size":len(raw),"drive_item_id":item.get("id")}
            self._graph("/me/drive/special/approot:/latest.json:/content",json.dumps(manifest).encode(),"PUT","application/json")
            return manifest

    def latest_manifest(self): return self._graph("/me/drive/special/approot:/latest.json:/content")

    def download_latest(self):
        manifest = self.latest_manifest(); path = manifest.get("backup_file")
        if not path: raise OneDriveError("No verified cloud recovery point is available.")
        # Request metadata, not /content. Graph returns a short-lived preauthenticated
        # download URL. It must be fetched without a bearer Authorization header.
        metadata = self._graph("/me/drive/special/approot:/" + urllib.parse.quote(path, safe="/") + "?$select=id,name,size,@microsoft.graph.downloadUrl")
        url = metadata.get("@microsoft.graph.downloadUrl")
        if not url: raise OneDriveError("OneDrive did not provide a download URL.")
        try:
            with urllib.request.urlopen(urllib.request.Request(url), timeout=60) as res: raw = res.read()
        except urllib.error.HTTPError as exc: raise OneDriveError(f"Cloud file download failed: HTTP {exc.code}")
        if hashlib.sha256(raw).hexdigest() != manifest.get("sha256"): raise OneDriveError("Cloud backup failed SHA-256 verification.")
        return raw.decode("utf-8"), manifest
