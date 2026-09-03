"""MSAL-backed OneDrive App Folder transport for IronCycle 1.41.6."""
import base64, hashlib, json, os, threading, time
import urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
import msal

CLIENT_ID = "cab9c010-af5e-4d42-918f-51ae4a6ebdd8"
AUTHORITY = "https://login.microsoftonline.com/common"
GRAPH = "https://graph.microsoft.com/v1.0"
SCOPES = ["https://graph.microsoft.com/Files.ReadWrite.AppFolder"]
VERIFY_URI_FALLBACK = "https://microsoft.com/devicelogin"
CACHE_FORMAT_VERSION = 2

class OneDriveError(RuntimeError): pass

class OneDriveService:
    def __init__(self, cache_path, pending_path):
        self.cache_path, self.pending_path = cache_path, pending_path
        self.cache_marker = cache_path + ".v2"
        self._migrate_cache_once()
        self.cache = msal.SerializableTokenCache()
        if os.path.exists(cache_path):
            try:
                with open(cache_path, encoding="utf-8") as f: self.cache.deserialize(f.read())
            except Exception: pass
        self.app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=self.cache)
        self._io_lock = threading.Lock(); self._flow_lock = threading.Lock()

    def _migrate_cache_once(self):
        if os.path.exists(self.cache_marker): return
        try: os.remove(self.cache_path)
        except FileNotFoundError: pass
        try: os.remove(self.pending_path)
        except FileNotFoundError: pass
        os.makedirs(os.path.dirname(self.cache_marker), exist_ok=True)
        with open(self.cache_marker, "w", encoding="utf-8") as f: f.write(str(CACHE_FORMAT_VERSION))

    def _save_cache(self):
        if not self.cache.has_state_changed: return
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f: f.write(self.cache.serialize())
        try: os.chmod(self.cache_path, 0o600)
        except Exception: pass

    def _read_pending_raw(self):
        try:
            with open(self.pending_path, encoding="utf-8") as f: return json.load(f)
        except Exception: return None

    def _write_pending(self, flow):
        safe={k:v for k,v in flow.items() if isinstance(v,(str,int,float,bool,list,dict,type(None)))}
        safe["saved_at"] = int(time.time()); safe["expires_at"] = int(time.time()) + int(flow.get("expires_in",900))
        os.makedirs(os.path.dirname(self.pending_path), exist_ok=True)
        with open(self.pending_path,"w",encoding="utf-8") as f: json.dump(safe,f)

    def clear_pending(self):
        try: os.remove(self.pending_path)
        except FileNotFoundError: pass

    def pending_flow(self):
        flow=self._read_pending_raw()
        if not flow: return None
        if not flow.get("device_code") or not flow.get("user_code") or int(flow.get("expires_at",0)) <= int(time.time()):
            self.clear_pending(); return None
        return flow

    def has_account(self): return bool(self.app.get_accounts())
    def disconnect(self):
        for account in self.app.get_accounts(): self.app.remove_account(account)
        self._save_cache(); self.clear_pending()

    def begin_device_flow(self, force_new=False):
        if force_new: self.clear_pending()
        existing=self.pending_flow()
        if existing: return existing
        flow=self.app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow: raise OneDriveError(flow.get("error_description") or "Microsoft sign-in could not start.")
        flow["verification_uri"] = flow.get("verification_uri") or VERIFY_URI_FALLBACK
        self._write_pending(flow); return self.pending_flow()

    def complete_device_flow(self):
        if not self._flow_lock.acquire(blocking=False): raise OneDriveError("Microsoft sign-in completion is already running.")
        try:
            flow=self.pending_flow()
            if not flow: raise OneDriveError("No valid Microsoft sign-in is pending. Generate a new code.")
            result=self.app.acquire_token_by_device_flow(flow); self._save_cache()
            if "access_token" not in result:
                error=result.get("error") or "device_flow_failed"; detail=result.get("error_description") or error
                if error not in ("authorization_pending","slow_down"): self.clear_pending()
                raise OneDriveError(detail)
            self.clear_pending(); self.validate_token_claims(result["access_token"]); return result
        finally: self._flow_lock.release()

    def _decode_claims(self, token):
        try:
            payload=token.split(".")[1]; payload += "=" * (-len(payload) % 4)
            return json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
        except Exception: return {}

    def validate_token_claims(self, token):
        claims=self._decode_claims(token); aud=str(claims.get("aud", "")); scopes=set(str(claims.get("scp", "")).split())
        graph_audiences={"00000003-0000-0000-c000-000000000000","https://graph.microsoft.com"}
        if aud not in graph_audiences: raise OneDriveError(f"Token audience is not Microsoft Graph (aud={aud or 'missing'}).")
        if "Files.ReadWrite.AppFolder" not in scopes: raise OneDriveError("Token is missing Files.ReadWrite.AppFolder permission.")
        if int(claims.get("exp",0) or 0) <= int(time.time()): raise OneDriveError("Microsoft Graph token is expired.")
        return {"aud":aud,"scp":"Files.ReadWrite.AppFolder","tid":claims.get("tid"),"exp":claims.get("exp")}

    def acquire_token(self):
        accounts=self.app.get_accounts()
        if not accounts: raise OneDriveError("Reconnect required: no Microsoft account is cached.")
        result=self.app.acquire_token_silent(SCOPES, account=accounts[0]); self._save_cache()
        if not result or "access_token" not in result:
            detail=(result or {}).get("error_description") or (result or {}).get("error") or "silent token acquisition failed"
            raise OneDriveError("Reconnect required: "+detail)
        self.validate_token_claims(result["access_token"]); return result["access_token"]

    def _json(self,url,token=None,data=None,method=None,ctype=None):
        headers={}
        if token: headers["Authorization"]="Bearer "+token
        if ctype: headers["Content-Type"]=ctype
        req=urllib.request.Request(url,data=data,headers=headers,method=method or ("POST" if data is not None else "GET"))
        try:
            with urllib.request.urlopen(req,timeout=60) as response:
                raw=response.read(); return json.loads(raw.decode()) if raw else {}
        except urllib.error.HTTPError as exc:
            raw=exc.read().decode("utf-8","replace")
            try:
                payload=json.loads(raw); err=payload.get("error"); msg=err.get("message") if isinstance(err,dict) else payload.get("error_description") or err or raw
            except Exception: msg=raw
            raise OneDriveError(f"HTTP {exc.code}: {msg}")
        except urllib.error.URLError as exc: raise OneDriveError(f"Network unavailable: {exc.reason}")

    def _graph(self,path,data=None,method=None,ctype=None): return self._json(GRAPH+path,self.acquire_token(),data,method,ctype)
    def latest_manifest(self): return self._graph("/me/drive/special/approot:/latest.json:/content")
    def verify_connection(self):
        root=self._graph("/me/drive/special/approot"); manifest=None
        try: manifest=self.latest_manifest()
        except OneDriveError as exc:
            if "404" not in str(exc) and "itemnotfound" not in str(exc).lower(): raise
        return {"ok":bool(root.get("id")),"checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),"manifest":manifest}

    def upload_backup(self,text,reason,version,schema):
        with self._io_lock:
            stamp=datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S"); safe="".join(c if c.isalnum() or c=="-" else "-" for c in reason.lower()).strip("-") or "manual"
            name=f"{stamp}__{safe}.icbackup"; raw=text.encode(); digest=hashlib.sha256(raw).hexdigest(); q=urllib.parse.quote(name,safe="")
            item=self._graph(f"/me/drive/special/approot:/backups/{q}:/content",raw,"PUT","text/plain; charset=utf-8")
            manifest={"format":"ironcycle-cloud-backup-v1","backup_file":"backups/"+name,"created_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),"app_version":version,"schema_version":int(schema),"sha256":digest,"reason":reason,"size":len(raw),"drive_item_id":item.get("id")}
            self._graph("/me/drive/special/approot:/latest.json:/content",json.dumps(manifest).encode(),"PUT","application/json"); return manifest

    def download_latest(self):
        manifest=self.latest_manifest(); path=manifest.get("backup_file")
        if not path: raise OneDriveError("No verified cloud recovery point is available.")
        metadata=self._graph("/me/drive/special/approot:/"+urllib.parse.quote(path,safe="/")+"?$select=id,name,size,@microsoft.graph.downloadUrl")
        url=metadata.get("@microsoft.graph.downloadUrl")
        if not url: raise OneDriveError("OneDrive did not provide a download URL.")
        with urllib.request.urlopen(urllib.request.Request(url),timeout=60) as response: raw=response.read()
        if hashlib.sha256(raw).hexdigest()!=manifest.get("sha256"): raise OneDriveError("Cloud backup failed SHA-256 verification.")
        return raw.decode(),manifest
