from alembic import op
import json
from pathlib import Path
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    for statement in json.loads((Path(__file__).resolve().parents[1] / "initial_schema.json").read_text()):
        op.execute(statement)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO rental_app")
    op.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO rental_app")
    for table in ["quotes", "quote_items", "reservation_versions", "rate_plans", "pricing_rules", "rental_policies", "audit_events"]:
        op.execute(f"REVOKE UPDATE, DELETE ON {table} FROM rental_app")
    # Manual privacy operations never touch contractual records or booking audits.
    op.execute("""CREATE FUNCTION purge_chat_history(p_conversation uuid) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM conversations WHERE id=p_conversation AND retention_due_at<=now() AND status='CLOSED') THEN
        RAISE EXCEPTION 'Conversation is not eligible for manual purge';
      END IF;
      UPDATE chat_logs SET agent_run_id=NULL WHERE conversation_id=p_conversation;
      DELETE FROM agent_runs WHERE conversation_id=p_conversation;
      DELETE FROM chat_logs WHERE conversation_id=p_conversation;
      UPDATE conversations SET contact_name=NULL, contact_email=NULL, contact_phone=NULL,
        session_state='{}'::jsonb, active_draft_id=NULL WHERE id=p_conversation;
      DELETE FROM agent_state.checkpoint_writes WHERE thread_id=p_conversation::text;
      DELETE FROM agent_state.checkpoint_blobs WHERE thread_id=p_conversation::text;
      DELETE FROM agent_state.checkpoints WHERE thread_id=p_conversation::text;
      UPDATE escalation_cases SET summary='History manually deleted', source_log_ids='[]'::jsonb,
        resolution=NULL WHERE conversation_id=p_conversation;
    END $$""")
    op.execute("REVOKE EXECUTE ON FUNCTION purge_chat_history(uuid) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION purge_chat_history(uuid) TO rental_app")
def downgrade():
    raise RuntimeError("Destructive downgrade is intentionally unsupported")
