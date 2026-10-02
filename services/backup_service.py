import base64, os, sqlite3, zlib

REQUIRED_TABLES={"workout_sessions","workout_sets","exercise_dict","readiness_logs","meso_configs","meso_names","user_settings"}

class BackupService:
    def __init__(self, max_text_bytes=10_000_000, max_db_bytes=100_000_000):
        self.max_text_bytes=max_text_bytes; self.max_db_bytes=max_db_bytes

    def create_backup_string(self, db_path, app_version, schema_version, created_at):
        snapshot_path=db_path+".snapshot"
        try:
            with sqlite3.connect(db_path,timeout=5.0) as src:
                with sqlite3.connect(snapshot_path) as dst: src.backup(dst)
            with sqlite3.connect(snapshot_path) as conn:
                conn.executemany("INSERT OR REPLACE INTO user_settings (setting_key,setting_value) VALUES (?,?)",(("backup_app_version",app_version),("backup_schema_version",str(schema_version)),("backup_created_at",created_at)))
                conn.commit()
            return base64.b64encode(zlib.compress(open(snapshot_path,"rb").read(),9)).decode("utf-8")
        finally:
            try:
                if os.path.exists(snapshot_path): os.remove(snapshot_path)
            except Exception: pass

    def decode(self, text):
        compact="".join(str(text or "").split())
        if not compact: raise ValueError("Backup is empty.")
        if len(compact)>self.max_text_bytes: raise ValueError("Backup text is too large.")
        data=zlib.decompress(base64.b64decode(compact,validate=True))
        if len(data)>self.max_db_bytes: raise ValueError("Backup expands beyond the safety limit.")
        return data

    def validate_database(self, path):
        with sqlite3.connect(path) as conn:
            result=conn.execute("PRAGMA integrity_check").fetchone()[0]
            if str(result).lower()!="ok": raise ValueError(f"Integrity check failed: {result}")
            found={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing=REQUIRED_TABLES-found
        if missing: raise ValueError("Not a valid workout backup. Missing tables: "+", ".join(sorted(missing)))
        return True
    def inspect_backup_string(self, text):
        """Decode and validate a backup without changing the live database."""
        import tempfile
        raw = self.decode(text)
        fd, path = tempfile.mkstemp(prefix="ironcycle-backup-inspect-", suffix=".db")
        os.close(fd)
        try:
            with open(path, "wb") as handle:
                handle.write(raw)
            self.validate_database(path)
            with sqlite3.connect(path) as conn:
                settings = dict(conn.execute(
                    "SELECT setting_key, setting_value FROM user_settings "
                    "WHERE setting_key IN ('backup_app_version','backup_schema_version','backup_created_at')"
                ).fetchall())
                integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            return {
                "ok": True,
                "integrity": str(integrity),
                "app_version": settings.get("backup_app_version"),
                "schema_version": settings.get("backup_schema_version"),
                "created_at_present": bool(settings.get("backup_created_at")),
                "entitlement_embedded": False,
                "decoded_bytes": len(raw),
            }
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

