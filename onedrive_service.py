"""OneDrive App Folder transport for IronCycle cloud recovery points.
Uses OAuth 2.0 device-code flow for a public client. No client secret is used.
Tokens remain outside the workout database so database backups never contain credentials.
"""
import base64
import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

CLIENT_ID = "cab9c010-af5e-4d42-918f-51ae4a6ebdd8"
TENANT_ID = "c76d5ab5-d520-4686-9cac-60db68f2c7dc"
AUTHORITY = "https://login.microsoftonline.com/common/oauth2/v2.0"
GRAPH = "https://graph.microsoft.com/v1.0"
SCOPES = "openid profile offline_access Files.ReadWrite.AppFolder"

class OneDriveError(RuntimeError):
    pass

class OneDriveService:
    def __init__(self, token_path, status_callback=None):
        self.token_path = token_path
        self.status_callback = status_callback
        self._lock = threading.Lock()
        self._token = self._load_token()

    def _status(self, state, detail=""):
        if self.status_callback:
            try: self.status_callback(state, detail)
            except Exception: pass

    def _load_token(self):
        try:
            with open(self.token_path, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: return {}

    def _save_token(self, token):
        os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
        token["saved_at"] = int(time.time())
        with open(self.token_path, "w", encoding="utf-8") as f: json.dump(token, f)
        try: os.chmod(self.token_path, 0o600)
        except Exception: pass
        self._token = token

    def disconnect(self):
        self._token = {}
        try: os.remove(self.token_path)
        except FileNotFoundError: pass

    def is_connected(self):
        return bool(self._token.get("refresh_token") or self._token.get("access_token"))

    def begin_device_code(self):
        data = urllib.parse.urlencode({"client_id": CLIENT_ID, "scope": SCOPES}).encode()
        result = self._json_request(f"{AUTHORITY}/devicecode", data=data)
        if not result.get("device_code"): raise OneDriveError(result.get("error_description", "Device sign-in could not start."))
        return result

    def complete_device_code(self, device):
        interval = max(5, int(device.get("interval", 5)))
        deadline = time.time() + int(device.get("expires_in", 900))
        while time.time() < deadline:
            data = urllib.parse.urlencode({
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": CLIENT_ID,
                "device_code": device["device_code"],
            }).encode()
            try:
                token = self._json_request(f"{AUTHORITY}/token", data=data)
            except OneDriveError as exc:
                text = str(exc)
                if "authorization_pending" in text:
                    time.sleep(interval); continue
                if "slow_down" in text:
                    interval += 5; time.sleep(interval); continue
                raise
            if token.get("access_token"):
                token["expires_at"] = int(time.time()) + int(token.get("expires_in", 3600)) - 60
                self._save_token(token)
                self._status("connected", "Microsoft account connected")
                return token
            time.sleep(interval)
        raise OneDriveError("Microsoft sign-in expired. Start Connect OneDrive again.")

    def _access_token(self):
        token = self._token or self._load_token()
        if token.get("access_token") and int(token.get("expires_at", 0)) > time.time(): return token["access_token"]
        refresh = token.get("refresh_token")
        if not refresh: raise OneDriveError("OneDrive is not connected.")
        data = urllib.parse.urlencode({
            "client_id": CLIENT_ID,
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "scope": SCOPES,
        }).encode()
        new = self._json_request(f"{AUTHORITY}/token", data=data)
        if not new.get("access_token"): raise OneDriveError(new.get("error_description", "OneDrive authorization could not be refreshed."))
        if not new.get("refresh_token"): new["refresh_token"] = refresh
        new["expires_at"] = int(time.time()) + int(new.get("expires_in", 3600)) - 60
        self._save_token(new)
        return new["access_token"]

    def _json_request(self, url, data=None, method=None, headers=None, timeout=30):
        request = urllib.request.Request(url, data=data, method=method or ("POST" if data is not None else "GET"), headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                payload = json.loads(raw)
                message = payload.get("error_description") or payload.get("error", {}).get("message") or payload.get("error") or raw
            except Exception: message = raw
            raise OneDriveError(f"HTTP {exc.code}: {message}")
        except urllib.error.URLError as exc:
            raise OneDriveError(f"Network unavailable: {exc.reason}")

    def _graph(self, path, data=None, method=None, content_type=None):
        headers = {"Authorization": f"Bearer {self._access_token()}"}
        if content_type: headers["Content-Type"] = content_type
        return self._json_request(GRAPH + path, data=data, method=method, headers=headers, timeout=60)

    def upload_backup(self, backup_text, reason, app_version, schema_version):
        with self._lock:
            self._status("uploading", reason)
            stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
            safe_reason = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in reason.lower()).strip("-") or "automatic"
            name = f"{stamp}__{safe_reason}.icbackup"
            payload = backup_text.encode("utf-8")
            digest = hashlib.sha256(payload).hexdigest()
            encoded_name = urllib.parse.quote(name, safe="")
            item = self._graph(f"/me/drive/special/approot:/backups/{encoded_name}:/content", data=payload, method="PUT", content_type="text/plain; charset=utf-8")
            manifest = {
                "format": "ironcycle-cloud-backup-v1",
                "backup_file": f"backups/{name}",
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "app_version": app_version,
                "schema_version": int(schema_version),
                "sha256": digest,
                "reason": reason,
                "size": len(payload),
                "drive_item_id": item.get("id"),
            }
            self._graph("/me/drive/special/approot:/latest.json:/content", data=json.dumps(manifest, indent=2).encode(), method="PUT", content_type="application/json")
            self._status("up_to_date", name)
            return manifest

    def latest_manifest(self):
        return self._graph("/me/drive/special/approot:/latest.json:/content")

    def download_latest(self):
        manifest = self.latest_manifest()
        path = manifest.get("backup_file")
        if not path: raise OneDriveError("The cloud manifest does not identify a backup file.")
        token = self._access_token()
        req = urllib.request.Request(GRAPH + "/me/drive/special/approot:/" + urllib.parse.quote(path, safe="/") + ":/content", headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=60) as response: raw = response.read()
        except Exception as exc: raise OneDriveError(f"Cloud backup download failed: {exc}")
        if hashlib.sha256(raw).hexdigest() != manifest.get("sha256"): raise OneDriveError("Cloud backup failed SHA-256 verification.")
        return raw.decode("utf-8"), manifest

    def list_backups(self, limit=20):
        try:
            result = self._graph("/me/drive/special/approot:/backups:/children?$orderby=lastModifiedDateTime%20desc&$top=" + str(int(limit)))
        except OneDriveError as exc:
            if "itemNotFound" in str(exc): return []
            raise
        return result.get("value", [])
