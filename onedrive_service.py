"""MSAL-backed OneDrive App Folder transport for IronCycle 1.41.7."""
import hashlib, json, os, threading, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
import msal

CLIENT_ID="cab9c010-af5e-4d42-918f-51ae4a6ebdd8"
AUTHORITY="https://login.microsoftonline.com/common"
GRAPH="https://graph.microsoft.com/v1.0"
SCOPES=["Files.ReadWrite.AppFolder", "User.Read"]
VERIFY_URI_FALLBACK="https://microsoft.com/devicelogin"
CACHE_FORMAT_VERSION=4

class OneDriveError(RuntimeError):
 def __init__(self,message,status=None,stage=None,graph_code=None,request_id=None,www_authenticate=None):
  super().__init__(message);self.status=status;self.stage=stage;self.graph_code=graph_code;self.request_id=request_id;self.www_authenticate=www_authenticate


class OneDriveService:
 def __init__(self,cache_path,pending_path):
  self.cache_path,self.pending_path=cache_path,pending_path;self.cache_marker=cache_path+".v4";self._migrate_once();self.cache=msal.SerializableTokenCache()
  if os.path.exists(cache_path):
   try:self.cache.deserialize(open(cache_path,encoding='utf-8').read())
   except Exception:pass
  self.app=msal.PublicClientApplication(CLIENT_ID,authority=AUTHORITY,token_cache=self.cache);self._flow_lock=threading.Lock();self._io_lock=threading.Lock()
 def _migrate_once(self):
  if os.path.exists(self.cache_marker):return
  for p in (self.cache_path,self.pending_path):
   try:os.remove(p)
   except FileNotFoundError:pass
  os.makedirs(os.path.dirname(self.cache_marker),exist_ok=True);open(self.cache_marker,'w').write(str(CACHE_FORMAT_VERSION))
 def _save(self):
  if self.cache.has_state_changed:
   os.makedirs(os.path.dirname(self.cache_path),exist_ok=True);open(self.cache_path,'w',encoding='utf-8').write(self.cache.serialize())
 def clear_pending(self):
  try:os.remove(self.pending_path)
  except FileNotFoundError:pass
 def pending_flow(self):
  try:f=json.load(open(self.pending_path,encoding='utf-8'))
  except Exception:return None
  if not f.get('device_code') or not f.get('user_code') or int(f.get('expires_at',0))<=int(time.time()):self.clear_pending();return None
  return f
 def has_account(self):return bool(self.app.get_accounts())
 def begin_device_flow(self,force_new=False):
  if force_new:self.clear_pending()
  if self.pending_flow():return self.pending_flow()
  f=self.app.initiate_device_flow(scopes=SCOPES)
  if 'user_code' not in f:raise OneDriveError(f.get('error_description') or 'Microsoft sign-in could not start.')
  f['verification_uri']=f.get('verification_uri') or VERIFY_URI_FALLBACK;f['expires_at']=int(time.time())+int(f.get('expires_in',900));os.makedirs(os.path.dirname(self.pending_path),exist_ok=True);json.dump(f,open(self.pending_path,'w',encoding='utf-8'));return f
 def complete_device_flow(self):
  if not self._flow_lock.acquire(blocking=False):return {'state':'already_running'}
  try:
   f=self.pending_flow()
   if not f:
    if self.has_account():return {'state':'account_available'}
    raise OneDriveError('No valid Microsoft sign-in is pending. Generate a new code.')
   r=self.app.acquire_token_by_device_flow(f);self._save()
   if 'access_token' not in r:
    err=r.get('error') or 'device_flow_failed';detail=r.get('error_description') or err
    if err not in ('authorization_pending','slow_down'):self.clear_pending()
    raise OneDriveError(detail)
   self.clear_pending();return {'state':'token_acquired'}
  finally:self._flow_lock.release()
 def acquire_token(self):
  a=self.app.get_accounts()
  if not a:raise OneDriveError('Reconnect required: no Microsoft account is cached.')
  r=self.app.acquire_token_silent(SCOPES,account=a[0]);self._save()
  if not r or 'access_token' not in r:raise OneDriveError('Reconnect required: '+((r or {}).get('error_description') or (r or {}).get('error') or 'silent token acquisition failed'))
  # Access tokens are opaque to clients. Microsoft Graph is the authority that validates them.
  return r['access_token']
 def _json(self,url,token=None,data=None,method=None,ctype=None,stage=None):
  h={}
  if token:h['Authorization']='Bearer '+token
  if ctype:h['Content-Type']=ctype
  try:
   with urllib.request.urlopen(urllib.request.Request(url,data=data,headers=h,method=method or ('POST' if data is not None else 'GET')),timeout=60) as response:
    raw=response.read();return json.loads(raw.decode()) if raw else {}
  except urllib.error.HTTPError as e:
   raw=e.read().decode('utf-8','replace')
   try:p=json.loads(raw);x=p.get('error');msg=x.get('message') if isinstance(x,dict) else p.get('error_description') or x or raw
   except Exception:msg=raw
   graph_code=None
   try:graph_code=(p.get('error') or {}).get('code') if isinstance(p.get('error'),dict) else None
   except Exception:pass
   raise OneDriveError(f'HTTP {e.code}: {msg}',status=e.code,stage=stage,graph_code=graph_code,request_id=e.headers.get('request-id'),www_authenticate=e.headers.get('WWW-Authenticate'))
  except urllib.error.URLError as e:raise OneDriveError(f'Network unavailable: {e.reason}')
 def _graph(self,path,data=None,method=None,ctype=None,stage=None):return self._json(GRAPH+path,self.acquire_token(),data,method,ctype,stage)
 def latest_manifest(self):return self._graph('/me/drive/special/approot:/latest.json:/content',stage='manifest')
 def verify_connection(self):
  stages=[]
  identity=self._graph('/me?$select=id',stage='identity');stages.append({'stage':'identity','ok':bool(identity.get('id'))})
  drive=self._graph('/me/drive?$select=id,driveType',stage='drive');stages.append({'stage':'drive','ok':bool(drive.get('id'))})
  root=self._graph('/me/drive/special/approot',stage='approot');stages.append({'stage':'approot','ok':bool(root.get('id'))})
  manifest=None
  try:manifest=self.latest_manifest();stages.append({'stage':'manifest','ok':True})
  except OneDriveError as e:
   if e.status==404 or 'itemnotfound' in str(e).lower():stages.append({'stage':'manifest','ok':True,'missing':True})
   else:raise
  return {'ok':all(x.get('ok') for x in stages),'checked_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'manifest':manifest,'stages':stages}
 def upload_backup(self,text,reason,version,schema):
  with self._io_lock:
   stamp=datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M%S');safe=''.join(c if c.isalnum() or c=='-' else '-' for c in reason.lower()).strip('-') or 'manual';name=f'{stamp}__{safe}.icbackup';raw=text.encode();digest=hashlib.sha256(raw).hexdigest();q=urllib.parse.quote(name,safe='')
   item=self._graph(f'/me/drive/special/approot:/backups/{q}:/content',raw,'PUT','text/plain; charset=utf-8');m={'format':'ironcycle-cloud-backup-v1','backup_file':'backups/'+name,'created_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'app_version':version,'schema_version':int(schema),'sha256':digest,'reason':reason,'size':len(raw),'drive_item_id':item.get('id')};self._graph('/me/drive/special/approot:/latest.json:/content',json.dumps(m).encode(),'PUT','application/json');return m
 def download_latest(self):
  m=self.latest_manifest();path=m.get('backup_file')
  if not path:raise OneDriveError('No verified cloud recovery point is available.')
  meta=self._graph('/me/drive/special/approot:/'+urllib.parse.quote(path,safe='/')+'?$select=id,name,size,@microsoft.graph.downloadUrl');url=meta.get('@microsoft.graph.downloadUrl')
  if not url:raise OneDriveError('OneDrive did not provide a download URL.')
  with urllib.request.urlopen(urllib.request.Request(url),timeout=60) as response:raw=response.read()
  if hashlib.sha256(raw).hexdigest()!=m.get('sha256'):raise OneDriveError('Cloud backup failed SHA-256 verification.')
  return raw.decode(),m
