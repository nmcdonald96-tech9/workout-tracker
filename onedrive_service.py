"""MSAL-backed OneDrive App Folder transport for IronCycle."""
import hashlib, json, os, threading, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
import msal

CLIENT_ID = "cab9c010-af5e-4d42-918f-51ae4a6ebdd8"
AUTHORITY = "https://login.microsoftonline.com/consumers"
GRAPH = "https://graph.microsoft.com/v1.0"
SCOPES = ["Files.ReadWrite.AppFolder"]

class OneDriveError(RuntimeError): pass

class OneDriveService:
    def __init__(self, cache_path, pending_path):
        self.cache_path, self.pending_path = cache_path, pending_path
        self.cache = msal.SerializableTokenCache()
        if os.path.exists(cache_path):
            try: self.cache.deserialize(open(cache_path, encoding="utf-8").read())
            except Exception: pass
        self.app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=self.cache)
        self._lock = threading.Lock()

    def _save_cache(self):
        if not self.cache.has_state_changed: return
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f: f.write(self.cache.serialize())
        try: os.chmod(self.cache_path, 0o600)
        except Exception: pass

    def _read_pending(self):
        try: return json.load(open(self.pending_path, encoding="utf-8"))
        except Exception: return None

    def _write_pending(self, flow):
        safe = {k:v for k,v in flow.items() if isinstance(v,(str,int,float,bool,list,dict,type(None)))}
        os.makedirs(os.path.dirname(self.pending_path), exist_ok=True)
        json.dump(safe, open(self.pending_path,"w",encoding="utf-8"))

    def clear_pending(self):
        try: os.remove(self.pending_path)
        except FileNotFoundError: pass

    def has_account(self): return bool(self.app.get_accounts())
    def disconnect(self):
        for account in self.app.get_accounts(): self.app.remove_account(account)
        self._save_cache(); self.clear_pending()

    def begin_device_flow(self):
        flow = self.app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow: raise OneDriveError(flow.get("error_description") or "Microsoft sign-in could not start.")
        self._write_pending(flow); return flow

    def pending_flow(self): return self._read_pending()

    def complete_device_flow(self, flow=None):
        flow = flow or self.pending_flow()
        if not flow: raise OneDriveError("No Microsoft sign-in is pending.")
        result = self.app.acquire_token_by_device_flow(flow)
        self._save_cache(); self.clear_pending()
        if "access_token" not in result:
            raise OneDriveError(result.get("error_description") or result.get("error") or "Microsoft sign-in failed.")
        return result

    def acquire_token(self):
        accounts = self.app.get_accounts()
        if not accounts: raise OneDriveError("Reconnect required: no Microsoft account is cached.")
        result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
        self._save_cache()
        if not result or "access_token" not in result:
            detail = (result or {}).get("error_description") or (result or {}).get("error") or "silent token acquisition failed"
            raise OneDriveError("Reconnect required: " + detail)
        return result["access_token"]

    def _request_json(self, url, token=None, data=None, method=None, content_type=None):
        headers = {}
        if token: headers["Authorization"] = "Bearer " + token
        if content_type: headers["Content-Type"] = content_type
        req = urllib.request.Request(url, data=data, headers=headers, method=method or ("POST" if data is not None else "GET"))
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                raw=response.read(); return json.loads(raw.decode("utf-8")) if raw else {}
        except urllib.error.HTTPError as exc:
            raw=exc.read().decode("utf-8","replace")
            try:
                payload=json.loads(raw); err=payload.get("error"); msg=err.get("message") if isinstance(err,dict) else payload.get("error_description") or err or raw
            except Exception: msg=raw
            raise OneDriveError(f"HTTP {exc.code}: {msg}")
        except urllib.error.URLError as exc: raise OneDriveError(f"Network unavailable: {exc.reason}")

    def _graph(self, path, data=None, method=None, content_type=None):
        return self._request_json(GRAPH+path, self.acquire_token(), data, method, content_type)

    def latest_manifest(self): return self._graph("/me/drive/special/approot:/latest.json:/content")

    def verify_connection(self):
        root=self._graph("/me/drive/special/approot"); manifest=None
        try: manifest=self.latest_manifest()
        except OneDriveError as exc:
            if "404" not in str(exc) and "itemnotfound" not in str(exc).lower(): raise
        return {"ok":bool(root.get("id")),"checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),"manifest":manifest}

    def upload_backup(self, text, reason, version, schema):
        with self._lock:
            stamp=datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S"); safe="".join(c if c.isalnum() or c=="-" else "-" for c in reason.lower()).strip("-") or "manual"
            name=f"{stamp}__{safe}.icbackup"; raw=text.encode(); digest=hashlib.sha256(raw).hexdigest(); q=urllib.parse.quote(name,safe="")
            item=self._graph(f"/me/drive/special/approot:/backups/{q}:/content",raw,"PUT","text/plain; charset=utf-8")
            manifest={"format":"ironcycle-cloud-backup-v1","backup_file":"backups/"+name,"created_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),"app_version":version,"schema_version":int(schema),"sha256":digest,"reason":reason,"size":len(raw),"drive_item_id":item.get("id")}
            self._graph("/me/drive/special/approot:/latest.json:/content",json.dumps(manifest).encode(),"PUT","application/json")
            return manifest

    def download_latest(self):
        manifest=self.latest_manifest(); path=manifest.get("backup_file")
        if not path: raise OneDriveError("No verified cloud recovery point is available.")
        metadata=self._graph("/me/drive/special/approot:/"+urllib.parse.quote(path,safe="/")+"?$select=id,name,size,@microsoft.graph.downloadUrl")
        url=metadata.get("@microsoft.graph.downloadUrl")
        if not url: raise OneDriveError("OneDrive did not provide a download URL.")
        try:
            with urllib.request.urlopen(urllib.request.Request(url),timeout=60) as response: raw=response.read()
        except urllib.error.HTTPError as exc: raise OneDriveError(f"Cloud file download failed: HTTP {exc.code}")
        if hashlib.sha256(raw).hexdigest()!=manifest.get("sha256"): raise OneDriveError("Cloud backup failed SHA-256 verification.")
        return raw.decode(),manifest
