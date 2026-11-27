"""Initial schema with all tables and RLS policies.

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable required extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    # Note: pgvector extension must be installed separately in the database
    # op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    # ========================================================================
    # ENUMS (created as PostgreSQL enum types)
    # ========================================================================
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE channel_type AS ENUM (
                'EMAIL', 'CHAT', 'TICKET_ZENDESK', 'TICKET_INTERCOM', 'IN_APP', 'SLACK'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE severity_level AS ENUM (
                'LOW_P3', 'MEDIUM_P2', 'HIGH_P1', 'CRITICAL_P0'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE ticket_status AS ENUM (
                'NEW', 'PROCESSING', 'AWAITING_CUSTOMER', 'AWAITING_APPROVAL',
                'RESOLVED', 'ESCALATED', 'CLOSED'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE action_risk_level AS ENUM (
                'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE action_status AS ENUM (
                'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'EXECUTING',
                'SUCCESS', 'FAILED', 'ROLLED_BACK'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE role_type AS ENUM (
                'SUPER_ADMIN', 'TENANT_ADMIN', 'SUPPORT_MANAGER',
                'TIER1_AGENT', 'TIER2_ENGINEER', 'READ_ONLY'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE customer_tier AS ENUM (
                'STANDARD', 'PREMIUM', 'ENTERPRISE'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE sender_type AS ENUM (
                'CUSTOMER', 'AI_AGENT', 'HUMAN_AGENT', 'SYSTEM'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE issue_category AS ENUM (
                'ACCOUNT_ACCESS', 'BILLING_SUBSCRIPTION', 'FEATURE_HOW_TO',
                'BASIC_TROUBLESHOOTING', 'ORDER_STATUS', 'TECHNICAL_BUG',
                'API_ISSUE', 'INTEGRATION_PROBLEM', 'COMPLEX_BILLING_DISPUTE',
                'FEATURE_REQUEST'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # ========================================================================
    # TENANTS
    # ========================================================================
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('domain', sa.String(255), unique=True, nullable=False),
        sa.Column('config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_tenants_domain', 'tenants', ['domain'], unique=True)

    # ========================================================================
    # USERS
    # ========================================================================
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('SUPER_ADMIN', 'TENANT_ADMIN', 'SUPPORT_MANAGER', 'TIER1_AGENT', 'TIER2_ENGINEER', 'READ_ONLY', name='role_type', create_type=False), nullable=False, server_default='TIER1_AGENT'),
        sa.Column('skills', postgresql.ARRAY(sa.String), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_tenant_email', 'users', ['tenant_id', 'email'], unique=True)
    op.create_foreign_key('fk_users_tenant_id', 'users', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')

    # ========================================================================
    # CUSTOMERS
    # ========================================================================
    op.create_table(
        'customers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('organization', sa.String(255), nullable=True),
        sa.Column('tier', sa.Enum('STANDARD', 'PREMIUM', 'ENTERPRISE', name='customer_tier', create_type=False), nullable=False, server_default='STANDARD'),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_customers_tenant_id', 'customers', ['tenant_id'])
    op.create_index('ix_customers_email', 'customers', ['email'])
    op.create_index('ix_customers_tenant_email', 'customers', ['tenant_id', 'email'], unique=True)
    op.create_index('ix_customers_external_id', 'customers', ['external_id'])
    op.create_foreign_key('fk_customers_tenant_id', 'customers', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')

    # ========================================================================
    # TICKETS
    # ========================================================================
    op.create_table(
        'tickets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('channel', sa.Enum('EMAIL', 'CHAT', 'TICKET_ZENDESK', 'TICKET_INTERCOM', 'IN_APP', 'SLACK', name='channel_type', create_type=False), nullable=False),
        sa.Column('external_ref_id', sa.String(255), nullable=True),
        sa.Column('subject', sa.String(500), nullable=True),
        sa.Column('status', sa.Enum('NEW', 'PROCESSING', 'AWAITING_CUSTOMER', 'AWAITING_APPROVAL', 'RESOLVED', 'ESCALATED', 'CLOSED', name='ticket_status', create_type=False), nullable=False, server_default='NEW'),
        sa.Column('severity', sa.Enum('LOW_P3', 'MEDIUM_P2', 'HIGH_P1', 'CRITICAL_P0', name='severity_level', create_type=False), nullable=False, server_default='MEDIUM_P2'),
        sa.Column('category', sa.Enum('ACCOUNT_ACCESS', 'BILLING_SUBSCRIPTION', 'FEATURE_HOW_TO', 'BASIC_TROUBLESHOOTING', 'ORDER_STATUS', 'TECHNICAL_BUG', 'API_ISSUE', 'INTEGRATION_PROBLEM', 'COMPLEX_BILLING_DISPUTE', 'FEATURE_REQUEST', name='issue_category', create_type=False), nullable=True),
        sa.Column('subcategory', sa.String(100), nullable=True),
        sa.Column('sentiment_score', sa.Numeric(3, 2), nullable=True),
        sa.Column('confidence_score', sa.Numeric(3, 2), nullable=True),
        sa.Column('is_autonomous_resolved', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('resolution_summary', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_tickets_tenant_id', 'tickets', ['tenant_id'])
    op.create_index('ix_tickets_customer_id', 'tickets', ['customer_id'])
    op.create_index('ix_tickets_assigned_agent_id', 'tickets', ['assigned_agent_id'])
    op.create_index('ix_tickets_tenant_status', 'tickets', ['tenant_id', 'status'])
    op.create_index('ix_tickets_external_ref_id', 'tickets', ['external_ref_id'])
    op.create_foreign_key('fk_tickets_tenant_id', 'tickets', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_tickets_customer_id', 'tickets', 'customers', ['customer_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_tickets_assigned_agent_id', 'tickets', 'users', ['assigned_agent_id'], ['id'], ondelete='SET NULL')

    # ========================================================================
    # TICKET MESSAGES
    # ========================================================================
    op.create_table(
        'ticket_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_type', sa.Enum('CUSTOMER', 'AI_AGENT', 'HUMAN_AGENT', 'SYSTEM', name='sender_type', create_type=False), nullable=False),
        sa.Column('sender_id', sa.String(255), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('cleaned_content', sa.Text, nullable=True),
        sa.Column('attachments', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_ticket_messages_tenant_id', 'ticket_messages', ['tenant_id'])
    op.create_index('ix_ticket_messages_ticket_id', 'ticket_messages', ['ticket_id'])
    op.create_foreign_key('fk_ticket_messages_tenant_id', 'ticket_messages', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_ticket_messages_ticket_id', 'ticket_messages', 'tickets', ['ticket_id'], ['id'], ondelete='CASCADE')

    # ========================================================================
    # ACTION AUDITS
    # ========================================================================
    op.create_table(
        'action_audits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action_name', sa.String(150), nullable=False),
        sa.Column('tool_name', sa.String(150), nullable=False),
        sa.Column('risk_level', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='action_risk_level', create_type=False), nullable=False),
        sa.Column('parameters', postgresql.JSONB, nullable=False),
        sa.Column('status', sa.Enum('PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'EXECUTING', 'SUCCESS', 'FAILED', 'ROLLED_BACK', name='action_status', create_type=False), nullable=False, server_default='PENDING_APPROVAL'),
        sa.Column('parameters', postgresql.JSONB, nullable=False),
        sa.Column('requested_by', sa.String(100), nullable=False),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approval_comment', sa.Text, nullable=True),
        sa.Column('execution_result', postgresql.JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('rollback_parameters', postgresql.JSONB, nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_action_audits_tenant_id', 'action_audits', ['tenant_id'])
    op.create_index('ix_action_audits_ticket_id', 'action_audits', ['ticket_id'])
    op.create_index('ix_action_audits_status', 'action_audits', ['status'])
    op.create_foreign_key('fk_action_audits_tenant_id', 'action_audits', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_action_audits_ticket_id', 'action_audits', 'tickets', ['ticket_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_action_audits_approved_by', 'action_audits', 'users', ['approved_by'], ['id'], ondelete='SET NULL')

    # ========================================================================
    # RESOLVED CASES (Episodic Memory)
    # ========================================================================
    op.create_table(
        'resolved_cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), unique=True, nullable=True),
        sa.Column('issue_summary', sa.Text, nullable=False),
        sa.Column('root_cause', sa.Text, nullable=False),
        sa.Column('resolution_steps', sa.Text, nullable=False),
        sa.Column('category', sa.Enum('ACCOUNT_ACCESS', 'BILLING_SUBSCRIPTION', 'FEATURE_HOW_TO', 'BASIC_TROUBLESHOOTING', 'ORDER_STATUS', 'TECHNICAL_BUG', 'API_ISSUE', 'INTEGRATION_PROBLEM', 'COMPLEX_BILLING_DISPUTE', 'FEATURE_REQUEST', name='issue_category', create_type=False), nullable=True),
        sa.Column('embedding', postgresql.ARRAY(sa.Float), nullable=True),
        sa.Column('csat_score', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_resolved_cases_tenant_id', 'resolved_cases', ['tenant_id'])
    op.create_index('ix_resolved_cases_ticket_id', 'resolved_cases', ['ticket_id'], unique=True)
    op.create_index('ix_resolved_cases_category', 'resolved_cases', ['category'])
    op.create_foreign_key('fk_resolved_cases_tenant_id', 'resolved_cases', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_resolved_cases_ticket_id', 'resolved_cases', 'tickets', ['ticket_id'], ['id'], ondelete='SET NULL')

    # ========================================================================
    # ROW LEVEL SECURITY (RLS) POLICIES
    # ========================================================================
    # Enable RLS on all tenant-scoped tables
    tables_with_rls = [
        'users', 'customers', 'tickets', 'ticket_messages',
        'action_audits', 'resolved_cases'
    ]

    for table in tables_with_rls:
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')

    # Create RLS policies
    # Users: tenant isolation
    op.execute("""
        CREATE POLICY users_tenant_isolation ON users
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)

    # Customers: tenant isolation
    op.execute("""
        CREATE POLICY customers_tenant_isolation ON customers
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)

    # Tickets: tenant isolation
    op.execute("""
        CREATE POLICY tickets_tenant_isolation ON tickets
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)

    # Ticket Messages: tenant isolation
    op.execute("""
        CREATE POLICY ticket_messages_tenant_isolation ON ticket_messages
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)

    # Action Audits: tenant isolation
    op.execute("""
        CREATE POLICY action_audits_tenant_isolation ON action_audits
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)

    # Resolved Cases: tenant isolation
    op.execute("""
        CREATE POLICY resolved_cases_tenant_isolation ON resolved_cases
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)

    # Special: Super admins bypass RLS (they can set app.current_tenant_id = '00000000-0000-0000-0000-000000000000' to bypass)
    # This is handled at the application layer by not setting the session variable for super admins


def downgrade() -> None:
    # Drop RLS policies
    tables_with_rls = [
        'users', 'customers', 'tickets', 'ticket_messages',
        'action_audits', 'resolved_cases'
    ]
    for table in tables_with_rls:
        op.execute(f'DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}')
        op.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY')

    # Drop tables in reverse order
    op.drop_table('resolved_cases')
    op.drop_table('action_audits')
    op.drop_table('ticket_messages')
    op.drop_table('tickets')
    op.drop_table('customers')
    op.drop_table('users')
    op.drop_table('tenants')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS issue_category')
    op.execute('DROP TYPE IF EXISTS sender_type')
    op.execute('DROP TYPE IF EXISTS customer_tier')
    op.execute('DROP TYPE IF EXISTS role_type')
    op.execute('DROP TYPE IF EXISTS action_status')
    op.execute('DROP TYPE IF EXISTS action_risk_level')
    op.execute('DROP TYPE IF EXISTS ticket_status')
    op.execute('DROP TYPE IF EXISTS severity_level')
    op.execute('DROP TYPE IF EXISTS channel_type')

    # Note: Extensions are not dropped (uuid-ossp, pgcrypto)