-- Apply to hosted Postgres before deploying Birthday support.
ALTER TABLE crm.people ADD COLUMN IF NOT EXISTS birthday text;
ALTER TABLE crm.leads ADD COLUMN IF NOT EXISTS birthday text;
