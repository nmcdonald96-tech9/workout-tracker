import json
import os
from pathlib import Path

import pytest

import onedrive_service
from onedrive_service import OneDriveService, _atomic_write_text

ROOT=Path(__file__).resolve().parents[1]


class ChangedCache:
    has_state_changed=True
    def serialize(self):
        return '{"cache":"preserved"}'


class FakeApp:
    def initiate_device_flow(self,scopes):
        return {"user_code":"ABCD-EFGH","device_code":"secret","expires_in":900}


def bare_service(tmp_path):
    service=object.__new__(OneDriveService)
    service.cache_path=str(tmp_path/'msal_cache.json')
    service.pending_path=str(tmp_path/'onedrive_pending.json')
    service.cache=ChangedCache()
    service.app=FakeApp()
    return service


def test_atomic_write_replaces_content_and_limits_permissions(tmp_path):
    destination=tmp_path/'state.json'
    destination.write_text('old',encoding='utf-8')
    _atomic_write_text(str(destination),'new')
    assert destination.read_text(encoding='utf-8')=='new'
    if os.name=='posix':
        assert destination.stat().st_mode & 0o777==0o600
    assert not list(tmp_path.glob('.ironcycle-*.tmp'))


def test_atomic_write_failure_preserves_destination_and_cleans_temp(tmp_path,monkeypatch):
    destination=tmp_path/'state.json'
    destination.write_text('old',encoding='utf-8')
    def fail_replace(source,target):
        raise OSError('simulated interruption')
    monkeypatch.setattr(onedrive_service.os,'replace',fail_replace)
    with pytest.raises(OSError,match='simulated interruption'):
        _atomic_write_text(str(destination),'new')
    assert destination.read_text(encoding='utf-8')=='old'
    assert not list(tmp_path.glob('.ironcycle-*.tmp'))


def test_cache_and_pending_flow_use_atomic_writer(tmp_path,monkeypatch):
    service=bare_service(tmp_path)
    calls=[]
    def capture(path,text):
        calls.append((path,text))
    monkeypatch.setattr(onedrive_service,'_atomic_write_text',capture)
    service._save()
    flow=service.begin_device_flow()
    assert calls[0]==(service.cache_path,'{"cache":"preserved"}')
    assert calls[1][0]==service.pending_path
    pending=json.loads(calls[1][1])
    assert pending['device_code']=='secret' and pending['user_code']=='ABCD-EFGH'
    assert pending['verification_uri']==onedrive_service.VERIFY_URI_FALLBACK
    assert pending['expires_at']>0
    assert flow==pending


def test_wifi_picker_accepts_current_and_legacy_backup_formats():
    source=(ROOT/'main.py').read_text(encoding='utf-8')
    assert 'accept=".icbackup,.txt"' in source
    assert 'Select an IronCycle .icbackup file or a legacy compressed .txt backup' in source
    assert 'Maximum 10MB' in source

