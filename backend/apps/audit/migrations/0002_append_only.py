from django.db import migrations

SQL = """
CREATE OR REPLACE FUNCTION audit_log_block_changes() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_auditlog is append-only (% blocked)', TG_OP USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_no_update_delete
    BEFORE UPDATE OR DELETE ON audit_auditlog
    FOR EACH ROW EXECUTE FUNCTION audit_log_block_changes();

CREATE TRIGGER audit_log_no_truncate
    BEFORE TRUNCATE ON audit_auditlog
    FOR EACH STATEMENT EXECUTE FUNCTION audit_log_block_changes();
"""

REVERSE = """
DROP TRIGGER IF EXISTS audit_log_no_truncate ON audit_auditlog;
DROP TRIGGER IF EXISTS audit_log_no_update_delete ON audit_auditlog;
DROP FUNCTION IF EXISTS audit_log_block_changes();
"""


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial")]
    operations = [migrations.RunSQL(SQL, REVERSE)]
