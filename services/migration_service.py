class MigrationInspector:
    def __init__(self, db_context): self.db_context=db_context
    def columns(self, table):
        with self.db_context() as conn: return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    def schema_version(self):
        with self.db_context() as conn:
            row=conn.execute("SELECT setting_value FROM user_settings WHERE setting_key='schema_version'").fetchone()
        return int(row[0]) if row else 0
    def integrity(self):
        with self.db_context() as conn: return conn.execute("PRAGMA integrity_check").fetchone()[0]
