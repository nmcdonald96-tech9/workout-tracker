import hashlib,json,os,threading,time,urllib.error,urllib.parse,urllib.request
from datetime import datetime,timezone
CLIENT_ID="cab9c010-af5e-4d42-918f-51ae4a6ebdd8"
AUTHORITY="https://login.microsoftonline.com/common/oauth2/v2.0"
GRAPH="https://graph.microsoft.com/v1.0"
SCOPES="openid profile offline_access Files.ReadWrite.AppFolder"
class OneDriveError(RuntimeError):pass
class OneDriveService:
 def __init__(self,token_path):self.token_path=token_path;self._token=self._load();self._lock=threading.Lock()
 def _load(self):
  try:return json.load(open(self.token_path,encoding='utf-8'))
  except:return {}
 def _save(self,t):
  os.makedirs(os.path.dirname(self.token_path),exist_ok=True);json.dump(t,open(self.token_path,'w',encoding='utf-8'));self._token=t
 def is_connected(self):return bool(self._token.get('refresh_token') or self._token.get('access_token'))
 def disconnect(self):
  self._token={}
  try:os.remove(self.token_path)
  except:pass
 def _request(self,url,data=None,headers=None,method=None,timeout=60):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,data=data,headers=headers or {},method=method or ('POST' if data is not None else 'GET')),timeout=timeout) as r:
    raw=r.read();return json.loads(raw.decode()) if raw else {}
  except urllib.error.HTTPError as e:
   raw=e.read().decode('utf-8','replace')
   try:
    p=json.loads(raw);msg=p.get('error_description') or p.get('error',{}).get('message') or p.get('error') or raw
   except:msg=raw
   raise OneDriveError(f"HTTP {e.code}: {msg}")
  except urllib.error.URLError as e:raise OneDriveError(f"Network unavailable: {e.reason}")
 def begin_device_code(self):return self._request(AUTHORITY+'/devicecode',urllib.parse.urlencode({'client_id':CLIENT_ID,'scope':SCOPES}).encode())
 def complete_device_code(self,d):
  interval=max(5,int(d.get('interval',5)));deadline=time.time()+int(d.get('expires_in',900))
  while time.time()<deadline:
   data=urllib.parse.urlencode({'grant_type':'urn:ietf:params:oauth:grant-type:device_code','client_id':CLIENT_ID,'device_code':d['device_code']}).encode()
   try:t=self._request(AUTHORITY+'/token',data)
   except OneDriveError as e:
    x=str(e).lower()
    if any(m in x for m in ('authorization_pending','aadsts70016','has not yet been authorized','must input their code','authorization is pending')):time.sleep(interval);continue
    if 'slow_down' in x:interval+=5;time.sleep(interval);continue
    if 'authorization_declined' in x or 'access_denied' in x:raise OneDriveError('Microsoft sign-in was declined.')
    if 'expired_token' in x:raise OneDriveError('Microsoft sign-in code expired.')
    raise
   if t.get('access_token'):
    t['expires_at']=int(time.time())+int(t.get('expires_in',3600))-60;self._save(t);return t
   time.sleep(interval)
  raise OneDriveError('Microsoft sign-in code expired.')
 def _token_value(self):
  if self._token.get('access_token') and self._token.get('expires_at',0)>time.time():return self._token['access_token']
  r=self._token.get('refresh_token')
  if not r:raise OneDriveError('OneDrive is not connected.')
  t=self._request(AUTHORITY+'/token',urllib.parse.urlencode({'client_id':CLIENT_ID,'grant_type':'refresh_token','refresh_token':r,'scope':SCOPES}).encode());t.setdefault('refresh_token',r);t['expires_at']=int(time.time())+int(t.get('expires_in',3600))-60;self._save(t);return t['access_token']
 def _graph(self,path,data=None,method=None,ctype=None):
  h={'Authorization':'Bearer '+self._token_value()};
  if ctype:h['Content-Type']=ctype
  return self._request(GRAPH+path,data,h,method)
 def upload_backup(self,text,reason,version,schema):
  with self._lock:
   stamp=datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M%S');name=f"{stamp}__{reason}.icbackup";raw=text.encode();digest=hashlib.sha256(raw).hexdigest();q=urllib.parse.quote(name,safe='')
   item=self._graph(f'/me/drive/special/approot:/backups/{q}:/content',raw,'PUT','text/plain')
   manifest={'format':'ironcycle-cloud-backup-v1','backup_file':'backups/'+name,'created_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'app_version':version,'schema_version':schema,'sha256':digest,'reason':reason,'drive_item_id':item.get('id')}
   self._graph('/me/drive/special/approot:/latest.json:/content',json.dumps(manifest).encode(),'PUT','application/json');return manifest
 def download_latest(self):
  m=self._graph('/me/drive/special/approot:/latest.json:/content');path=urllib.parse.quote(m['backup_file'],safe='/');req=urllib.request.Request(GRAPH+'/me/drive/special/approot:/'+path+':/content',headers={'Authorization':'Bearer '+self._token_value()})
  with urllib.request.urlopen(req,timeout=60) as r:raw=r.read()
  if hashlib.sha256(raw).hexdigest()!=m.get('sha256'):raise OneDriveError('Cloud backup hash verification failed.')
  return raw.decode(),m
