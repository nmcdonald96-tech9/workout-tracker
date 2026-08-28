import base64,zlib
class BackupCodec:
    def encode(self,data): return base64.b64encode(zlib.compress(data,9)).decode('ascii')
    def decode(self,text,max_bytes=100_000_000):
        data=zlib.decompress(base64.b64decode(''.join(text.split()),validate=True))
        if len(data)>max_bytes: raise ValueError('Backup is too large')
        return data
