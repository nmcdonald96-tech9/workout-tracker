"""IronCycle OneDrive App Folder transport.
Public-client device flow only. No client secret is embedded.
Pending authorization and tokens are stored outside the workout database.
"""
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
AUTHORITY = "https://login.microsoftonline.com/common/oauth2/v2.0"
GRAPH = "https://graph.microsoft.com/v1.0"
SCOPES = "openid profile offline_access Files.ReadWrite.AppFolder"

class OneDriveError(RuntimeError):
    pass

class OneDriveService:
    def __init__(self, token_path, pending_path):
        self.token_path = token_path
        self.pending_path = pending_path
        self._token = self._read_json(token_path)
        self._lock = threading.Lock()

    def _read_json(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_json(self, path, value):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(value, f)
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass

    def _remove(self, path):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    def is_connected(self):
        return bool(self._token.get("refresh_token") or self._token.get("access_token"))

    def disconnect(self):
        self._token = {}
        self._remove(self.token_path)
        self.clear_pending()

    def pending_authorization(self):
        pending = self._read_json(self.pending_path)
        if not pending:
            return None
        if int(pending.get("expires_at", 0)) <= int(time.time()):
            self.clear_pending()
            return None
        return pending

    def clear_pending(self):
        self._remove(self.pending_path)

    def begin_device_code(self):
        response = self._request(
            AUTHORITY + "/devicecode",
            data=urllib.parse.urlencode({"client_id": CLIENT_ID, "scope": SCOPES}).encode(),
        )
        if not response.get("device_code"):
            raise OneDriveError(response.get("error_description", "Microsoft sign-in could not start."))
        response["created_at"] = int(time.time())
        response["expires_at"] = int(time.time()) + int(response.get("expires_in", 900))
        self._write_json(self.pending_path, response)
        return response

    def _pending_error(self, text):
        lowered = text.lower()
        return any(marker in lowered for marker in (
            "authorization_pending", "aadsts70016", "has not yet been authorized",
            "must input their code", "authorization is pending"
        ))

    def poll_pending_once(self):
        pending = self.pending_authorization()
        if not pending:
            raise OneDriveError("No active Microsoft sign-in is waiting.")
        data = urllib.parse.urlencode({
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": CLIENT_ID,
            "device_code": pending["device_code"],
        }).encode()
        try:
            token = self._request(AUTHORITY + "/token", data=data)
        except OneDriveError as exc:
            text = str(exc)
            lowered = text.lower()
            if self._pending_error(text):
                return {"state": "pending"}
            if "slow_down" in lowered:
                pending["interval"] = int(pending.get("interval", 5)) + 5
                self._write_json(self.pending_path, pending)
                return {"state": "pending"}
            if "authorization_declined" in lowered or "access_denied" in lowered:
                self.clear_pending()
                raise OneDriveError("Microsoft sign-in was declined.")
            if "expired_token" in lowered or "code expired" in lowered:
                self.clear_pending()
                raise OneDriveError("Microsoft sign-in code expired.")
            raise
        if not token.get("access_token"):
            return {"state": "pending"}
        token["expires_at"] = int(time.time()) + int(token.get("expires_in", 3600)) - 60
        self._write_json(self.token_path, token)
        self._token = token
        self.clear_pending()
        return {"state": "connected"}

    def complete_device_code(self, cancel_event=None):
        while self.pending_authorization():
            if cancel_event and cancel_event.is_set():
                self.clear_pending()
                raise OneDriveError("Microsoft sign-in canceled.")
            result = self.poll_pending_once()
            if result["state"] == "connected":
                return result
            pending = self.pending_authorization()
            time.sleep(max(5, int((pending or {}).get("interval", 5))))
        raise OneDriveError("Microsoft sign-in expired or was canceled.")

    def _request(self, url, data=None, headers=None, method=None, timeout=60):
        request = urllib.request.Request(
            url, data=data, headers=headers or {},
            method=method or ("POST" if data is not None else "GET")
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                payload = json.loads(raw)
                message = payload.get("error_description") or payload.get("error", {}).get("message") or payload.get("error") or raw
            except Exception:
                message = raw
            raise OneDriveError(f"HTTP {exc.code}: {message}")
        except urllib.error.URLError as exc:
            raise OneDriveError(f"Network unavailable: {exc.reason}")

    def _access_token(self):
        token = self._token or self._read_json(self.token_path)
        if token.get("access_token") and int(token.get("expires_at", 0)) > int(time.time()):
            self._token = token
            return token["access_token"]
        refresh = token.get("refresh_token")
        if not refresh:
            raise OneDriveError("Reconnect required: no refresh token is available.")
        try:
            updated = self._request(
                AUTHORITY + "/token",
                data=urllib.parse.urlencode({
                    "client_id": CLIENT_ID, "grant_type": "refresh_token",
                    "refresh_token": refresh, "scope": SCOPES,
                }).encode(),
            )
        except OneDriveError as exc:
            if "401" in str(exc) or "invalid_grant" in str(exc).lower():
                self._token = {}
                self._remove(self.token_path)
                raise OneDriveError("Reconnect required: Microsoft rejected the saved authorization.")
            raise
        updated.setdefault("refresh_token", refresh)
        updated["expires_at"] = int(time.time()) + int(updated.get("expires_in", 3600)) - 60
        self._write_json(self.token_path, updated)
        self._token = updated
        return updated["access_token"]

    def _graph(self, path, data=None, method=None, content_type=None):
        headers = {"Authorization": "Bearer " + self._access_token()}
        if content_type:
            headers["Content-Type"] = content_type
        try:
            return self._request(GRAPH + path, data=data, headers=headers, method=method)
        except OneDriveError as exc:
            if "HTTP 401" in str(exc):
                self._token["expires_at"] = 0
                self._write_json(self.token_path, self._token)
                headers["Authorization"] = "Bearer " + self._access_token()
                return self._request(GRAPH + path, data=data, headers=headers, method=method)
            raise

    def verify_connection(self):
        item = self._graph("/me/drive/special/approot")
        return {
            "ok": bool(item.get("id")), "item_id": item.get("id"),
            "web_url": item.get("webUrl"),
            "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    def upload_backup(self, backup_text, reason, app_version, schema_version):
        with self._lock:
            stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
            safe_reason = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in reason.lower()).strip("-") or "manual"
            name = f"{stamp}__{safe_reason}.icbackup"
            raw = backup_text.encode("utf-8")
            digest = hashlib.sha256(raw).hexdigest()
            encoded = urllib.parse.quote(name, safe="")
            item = self._graph(f"/me/drive/special/approot:/backups/{encoded}:/content", raw, "PUT", "text/plain; charset=utf-8")
            manifest = {
                "format": "ironcycle-cloud-backup-v1", "backup_file": "backups/" + name,
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "app_version": app_version, "schema_version": int(schema_version),
                "sha256": digest, "reason": reason, "size": len(raw), "drive_item_id": item.get("id"),
            }
            self._graph("/me/drive/special/approot:/latest.json:/content", json.dumps(manifest).encode(), "PUT", "application/json")
            return manifest

    def latest_manifest(self):
        return self._graph("/me/drive/special/approot:/latest.json:/content")

    def download_latest(self):
        manifest = self.latest_manifest()
        path = manifest.get("backup_file")
        if not path:
            raise OneDriveError("No verified cloud recovery point is available.")
        req = urllib.request.Request(
            GRAPH + "/me/drive/special/approot:/" + urllib.parse.quote(path, safe="/") + ":/content",
            headers={"Authorization": "Bearer " + self._access_token()},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                self._token["expires_at"] = 0
                self._write_json(self.token_path, self._token)
                req.headers["Authorization"] = "Bearer " + self._access_token()
                with urllib.request.urlopen(req, timeout=60) as response:
                    raw = response.read()
            else:
                raise OneDriveError(f"Cloud download failed: HTTP {exc.code}")
        if hashlib.sha256(raw).hexdigest() != manifest.get("sha256"):
            raise OneDriveError("Cloud backup failed SHA-256 verification.")
        return raw.decode("utf-8"), manifest
