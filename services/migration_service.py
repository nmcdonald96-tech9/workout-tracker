class MigrationInspector:
    def __init__(self,db): self.db=db
    def columns(self,table):
        with self.db() as c:return {r[1] for r in c.execute(f'PRAGMA table_info({table})')}
    def schema_version(self):
        with self.db() as c:r=c.execute("SELECT setting_value FROM user_settings WHERE setting_key='schema_version'").fetchone();return int(r[0])
