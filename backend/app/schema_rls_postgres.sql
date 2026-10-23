-- ============================================================================
-- AICTE Approval Workflow Automation & Compliance System
-- PostgreSQL Row-Level Security (RLS) & Separation of Duties (SoD) Schema
-- Production Security Specification for PS SIH26262
-- ============================================================================

-- 1. Create dedicated non-superuser application role
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'aicte_app_user') THEN
    CREATE ROLE aicte_app_user WITH LOGIN PASSWORD 'secure_aicte_app_pass_2026';
  END IF;
END $$;

GRANT USAGE ON SCHEMA public TO aicte_app_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO aicte_app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO aicte_app_user;

-- Revoke UPDATE and DELETE on append-only audit & event tables from everyone
REVOKE UPDATE, DELETE ON TABLE audit_trail FROM aicte_app_user;
REVOKE UPDATE, DELETE ON TABLE case_events FROM aicte_app_user;

-- ============================================================================
-- 2. APPEND-ONLY TRIGGERS (Reject UPDATE & DELETE even if attempted)
-- ============================================================================
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'SECURITY VIOLATION: % table is strictly append-only. Modification or deletion is legally prohibited.', TG_TABLE_NAME;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_trail_immutable ON audit_trail;
CREATE TRIGGER trg_audit_trail_immutable
BEFORE UPDATE OR DELETE ON audit_trail
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

DROP TRIGGER IF EXISTS trg_case_events_immutable ON case_events;
CREATE TRIGGER trg_case_events_immutable
BEFORE UPDATE OR DELETE ON case_events
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

-- ============================================================================
-- 3. SEPARATION OF DUTIES (SoD) CHECK CONSTRAINTS & TRIGGERS
-- Pairwise: Submitter != Verifier, Verifier != Approver, Submitter != Approver
-- ============================================================================
CREATE OR REPLACE FUNCTION check_separation_of_duties_application()
RETURNS TRIGGER AS $$
BEGIN
  -- Check Submitter != Verifier
  IF NEW.verifier_id IS NOT NULL AND NEW.submitter_id = NEW.verifier_id THEN
    RAISE EXCEPTION 'SoD VIOLATION: Submitter cannot act as Verifier for application %', NEW.application_no;
  END IF;

  -- Check Verifier != Approver
  IF NEW.verifier_id IS NOT NULL AND NEW.approver_id IS NOT NULL AND NEW.verifier_id = NEW.approver_id THEN
    RAISE EXCEPTION 'SoD VIOLATION: Verifier cannot act as Approver for application %', NEW.application_no;
  END IF;

  -- Check Submitter != Approver
  IF NEW.approver_id IS NOT NULL AND NEW.submitter_id = NEW.approver_id THEN
    RAISE EXCEPTION 'SoD VIOLATION: Submitter cannot act as Approver for application %', NEW.application_no;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sod_application ON applications;
CREATE TRIGGER trg_sod_application
BEFORE INSERT OR UPDATE ON applications
FOR EACH ROW EXECUTE FUNCTION check_separation_of_duties_application();

-- SoD Trigger for AI Drafts: Requester != Approver
CREATE OR REPLACE FUNCTION check_separation_of_duties_ai_draft()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.approver_id IS NOT NULL AND NEW.requester_id = NEW.approver_id THEN
    RAISE EXCEPTION 'SoD VIOLATION: User who requested an AI draft cannot approve it as an official regulated record.';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sod_ai_draft ON llm_drafts;
CREATE TRIGGER trg_sod_ai_draft
BEFORE INSERT OR UPDATE ON llm_drafts
FOR EACH ROW EXECUTE FUNCTION check_separation_of_duties_ai_draft();

-- ============================================================================
-- 4. ENABLE & FORCE ROW LEVEL SECURITY (RLS)
-- FORCE ensures even table owners adhere to RLS policies.
-- ============================================================================
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications FORCE ROW LEVEL SECURITY;

ALTER TABLE institutional_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE institutional_documents FORCE ROW LEVEL SECURITY;

ALTER TABLE time_bound_undertakings ENABLE ROW LEVEL SECURITY;
ALTER TABLE time_bound_undertakings FORCE ROW LEVEL SECURITY;

ALTER TABLE evc_panels ENABLE ROW LEVEL SECURITY;
ALTER TABLE evc_panels FORCE ROW LEVEL SECURITY;

ALTER TABLE evc_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE evc_reports FORCE ROW LEVEL SECURITY;

ALTER TABLE llm_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_drafts FORCE ROW LEVEL SECURITY;

ALTER TABLE audit_trail ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_trail FORCE ROW LEVEL SECURITY;

-- Helper function to safely read session settings (returns NULL if not set)
CREATE OR REPLACE FUNCTION get_current_app_setting(setting_name text)
RETURNS text AS $$
BEGIN
  RETURN current_setting(setting_name, true);
EXCEPTION
  WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- 5. RLS POLICIES FOR APPLICATIONS TABLE
-- ============================================================================
DROP POLICY IF EXISTS p_app_select ON applications;
CREATE POLICY p_app_select ON applications
FOR SELECT
USING (
  -- 1. Missing context returns NOTHING (Default Deny)
  get_current_app_setting('app.current_user_role') IS NOT NULL
  AND
  (
    -- 2. Senior Authority / Bureau / Auditor have pan-India read scope
    get_current_app_setting('app.current_user_role') IN ('SUPER_ADMIN', 'BUREAU_OFFICER', 'AUDITOR')
    OR
    -- 3. Regional Officer: Restricted strictly to own region
    (
      get_current_app_setting('app.current_user_role') = 'REGIONAL_OFFICER'
      AND region_id = get_current_app_setting('app.current_region_id')
    )
    OR
    -- 4. Institution User: Restricted strictly to own institution
    (
      get_current_app_setting('app.current_user_role') = 'INSTITUTION_USER'
      AND institution_id = get_current_app_setting('app.current_institution_id')
    )
    OR
    -- 5. Committee Member: Restricted to cases assigned to them in EVC assignments
    (
      get_current_app_setting('app.current_user_role') = 'COMMITTEE_MEMBER'
      AND id IN (
        SELECT p.application_id
        FROM evc_panels p
        JOIN evc_assignments a ON a.panel_id = p.id
        WHERE a.user_id = get_current_app_setting('app.current_user_id')
      )
    )
  )
);

-- Write Policy for Applications (Auditors have NO write policy at all)
DROP POLICY IF EXISTS p_app_insert ON applications;
CREATE POLICY p_app_insert ON applications
FOR INSERT
WITH CHECK (
  -- Only Institution Users can submit for their own institution, or Admins
  (
    get_current_app_setting('app.current_user_role') = 'INSTITUTION_USER'
    AND institution_id = get_current_app_setting('app.current_institution_id')
  )
  OR get_current_app_setting('app.current_user_role') IN ('SUPER_ADMIN', 'REGIONAL_OFFICER')
);

DROP POLICY IF EXISTS p_app_update ON applications;
CREATE POLICY p_app_update ON applications
FOR UPDATE
USING (
  -- Auditors CANNOT update
  get_current_app_setting('app.current_user_role') != 'AUDITOR'
  AND (
    get_current_app_setting('app.current_user_role') IN ('SUPER_ADMIN', 'BUREAU_OFFICER')
    OR (
      get_current_app_setting('app.current_user_role') = 'REGIONAL_OFFICER'
      AND region_id = get_current_app_setting('app.current_region_id')
    )
    OR (
      get_current_app_setting('app.current_user_role') = 'INSTITUTION_USER'
      AND institution_id = get_current_app_setting('app.current_institution_id')
      AND status = 'DEFICIENT' -- Institution can only edit while curing deficiency
    )
  )
)
WITH CHECK (
  get_current_app_setting('app.current_user_role') != 'AUDITOR'
);

-- ============================================================================
-- 6. RLS POLICIES FOR DOCUMENTS & UNDERTAKINGS
-- ============================================================================
DROP POLICY IF EXISTS p_doc_select ON institutional_documents;
CREATE POLICY p_doc_select ON institutional_documents
FOR SELECT
USING (
  get_current_app_setting('app.current_user_role') IS NOT NULL
  AND (
    get_current_app_setting('app.current_user_role') IN ('SUPER_ADMIN', 'BUREAU_OFFICER', 'AUDITOR')
    OR (
      get_current_app_setting('app.current_user_role') = 'INSTITUTION_USER'
      AND institution_id = get_current_app_setting('app.current_institution_id')
    )
    OR (
      get_current_app_setting('app.current_user_role') = 'REGIONAL_OFFICER'
      AND institution_id IN (
        SELECT id FROM institutions WHERE region_id = get_current_app_setting('app.current_region_id')
      )
    )
  )
);

-- Auditor Write Deny: Auditor has NO INSERT, UPDATE, DELETE policies on any table.
-- Cross-institution write blocked: Institution users can only insert for their own institution.
DROP POLICY IF EXISTS p_doc_insert ON institutional_documents;
CREATE POLICY p_doc_insert ON institutional_documents
FOR INSERT
WITH CHECK (
  get_current_app_setting('app.current_user_role') = 'INSTITUTION_USER'
  AND institution_id = get_current_app_setting('app.current_institution_id')
);

-- ============================================================================
-- 7. RLS POLICIES FOR AUDIT TRAIL
-- Auditors and Admins have read-only access.
-- Zero UPDATE / DELETE policies exist.
-- ============================================================================
DROP POLICY IF EXISTS p_audit_select ON audit_trail;
CREATE POLICY p_audit_select ON audit_trail
FOR SELECT
USING (
  get_current_app_setting('app.current_user_role') IN ('SUPER_ADMIN', 'BUREAU_OFFICER', 'AUDITOR', 'REGIONAL_OFFICER')
);

DROP POLICY IF EXISTS p_audit_insert ON audit_trail;
CREATE POLICY p_audit_insert ON audit_trail
FOR INSERT
WITH CHECK (true); -- Any authenticated action can append to the audit log
