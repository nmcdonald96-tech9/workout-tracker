from services.backup_service import BackupCodec
def test_codec():
 c=BackupCodec(); raw=b'IronCycle'; assert c.decode(c.encode(raw))==raw
