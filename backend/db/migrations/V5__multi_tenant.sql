-- V5: multi-tenant SaaS model.
--
-- Before: a flat list of "clients" created by a single super-admin, with every
-- data row keyed by CLIENT_ID (a login identity doing double duty as a tenant).
--
-- After:  ORGANISATIONS are tenants, USERS are people who log in and belong to
--         exactly one organisation with a role. Every data row carries ORG_ID.
--
-- Existing data is preserved: each CLIENT_DETAILS row becomes an organisation
-- plus one owner user reusing the same password hash, and existing rows are
-- backfilled to that organisation, so issued certificates stay verifiable.

-- ---------------------------------------------------------------- tenants --
CREATE TABLE IF NOT EXISTS ORGANISATIONS (
    ORG_ID        VARCHAR(36)  NOT NULL,
    NAME          VARCHAR(160) NOT NULL,
    SLUG          VARCHAR(80)  NOT NULL,
    PLAN          VARCHAR(32)  NOT NULL DEFAULT 'free',
    BRAND_COLOR   VARCHAR(16)  DEFAULT NULL,
    LOGO_URL      LONGTEXT     DEFAULT NULL,
    STATUS        VARCHAR(16)  NOT NULL DEFAULT 'active',
    CREATED_ON    DATETIME     DEFAULT CURRENT_TIMESTAMP,
    UPDATED_ON    DATETIME     DEFAULT NULL,
    PRIMARY KEY (ORG_ID),
    UNIQUE KEY uq_org_slug (SLUG)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------------ users --
-- Email is globally unique: a person signs in with email + password, and the
-- organisation comes from their membership rather than being typed at login.
CREATE TABLE IF NOT EXISTS USERS (
    USER_ID       VARCHAR(36)  NOT NULL,
    ORG_ID        VARCHAR(36)  NOT NULL,
    EMAIL         VARCHAR(190) NOT NULL,
    FULL_NAME     VARCHAR(160) DEFAULT NULL,
    PASSWORD_HASH LONGTEXT     NOT NULL,
    ROLE          VARCHAR(16)  NOT NULL DEFAULT 'member',  -- owner | admin | member
    STATUS        VARCHAR(16)  NOT NULL DEFAULT 'active',
    LAST_LOGIN_ON DATETIME     DEFAULT NULL,
    CREATED_ON    DATETIME     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (USER_ID),
    UNIQUE KEY uq_user_email (EMAIL),
    KEY idx_user_org (ORG_ID),
    CONSTRAINT fk_user_org FOREIGN KEY (ORG_ID) REFERENCES ORGANISATIONS (ORG_ID) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------- org scoping on data --
-- Added nullable so the migration is safe to re-run and old rows survive;
-- the application always writes ORG_ID from the caller's token.
ALTER TABLE CERTIFICATE_DETAILS ADD COLUMN ORG_ID VARCHAR(36) NULL;
ALTER TABLE ID_DETAILS          ADD COLUMN ORG_ID VARCHAR(36) NULL;
ALTER TABLE TEMPLATE_DETAILS    ADD COLUMN ORG_ID VARCHAR(36) NULL;
ALTER TABLE CERTIFICATE_VERIFY  ADD COLUMN ORG_ID VARCHAR(36) NULL;
ALTER TABLE BATCH_JOBS          ADD COLUMN ORG_ID VARCHAR(36) NULL;

CREATE INDEX idx_cert_org     ON CERTIFICATE_DETAILS (ORG_ID);
CREATE INDEX idx_id_org       ON ID_DETAILS (ORG_ID);
CREATE INDEX idx_tpl_org      ON TEMPLATE_DETAILS (ORG_ID);
CREATE INDEX idx_verify_org   ON CERTIFICATE_VERIFY (ORG_ID);
CREATE INDEX idx_batch_org    ON BATCH_JOBS (ORG_ID);

-- ------------------------------------------------------------- backfill ---
-- One organisation per existing client. UUID() gives each a stable id; the
-- slug is derived from the old CLIENT_ID, which was already unique.
INSERT INTO ORGANISATIONS (ORG_ID, NAME, SLUG, PLAN, CREATED_ON)
SELECT UUID(),
       COALESCE(NULLIF(c.CLIENT_NAME, ''), c.CLIENT_ID),
       LOWER(REGEXP_REPLACE(c.CLIENT_ID, '[^A-Za-z0-9]+', '-')),
       'free',
       COALESCE(c.CREATED_ON, NOW())
FROM CLIENT_DETAILS c
WHERE NOT EXISTS (
    SELECT 1 FROM ORGANISATIONS o
    WHERE o.SLUG = LOWER(REGEXP_REPLACE(c.CLIENT_ID, '[^A-Za-z0-9]+', '-'))
);

-- The former client login becomes the organisation's owner. Old accounts had
-- no email, so a placeholder is derived from the client id; owners can change
-- it in settings, and it stays unique because CLIENT_ID was unique.
INSERT INTO USERS (USER_ID, ORG_ID, EMAIL, FULL_NAME, PASSWORD_HASH, ROLE, CREATED_ON)
SELECT UUID(),
       o.ORG_ID,
       CONCAT(LOWER(REGEXP_REPLACE(c.CLIENT_ID, '[^A-Za-z0-9]+', '.')), '@legacy.local'),
       COALESCE(NULLIF(c.CLIENT_NAME, ''), c.CLIENT_ID),
       c.PASSWORD,
       'owner',
       COALESCE(c.CREATED_ON, NOW())
FROM CLIENT_DETAILS c
JOIN ORGANISATIONS o
  ON o.SLUG = LOWER(REGEXP_REPLACE(c.CLIENT_ID, '[^A-Za-z0-9]+', '-'))
WHERE NOT EXISTS (SELECT 1 FROM USERS u WHERE u.ORG_ID = o.ORG_ID);

-- Point historical rows at the organisation that inherited their client id.
UPDATE CERTIFICATE_DETAILS d
  JOIN ORGANISATIONS o ON o.SLUG = LOWER(REGEXP_REPLACE(d.CLIENT_ID, '[^A-Za-z0-9]+', '-'))
   SET d.ORG_ID = o.ORG_ID WHERE d.ORG_ID IS NULL;

UPDATE ID_DETAILS d
  JOIN ORGANISATIONS o ON o.SLUG = LOWER(REGEXP_REPLACE(d.CLIENT_ID, '[^A-Za-z0-9]+', '-'))
   SET d.ORG_ID = o.ORG_ID WHERE d.ORG_ID IS NULL;

UPDATE TEMPLATE_DETAILS d
  JOIN ORGANISATIONS o ON o.SLUG = LOWER(REGEXP_REPLACE(d.CLIENT_ID, '[^A-Za-z0-9]+', '-'))
   SET d.ORG_ID = o.ORG_ID WHERE d.ORG_ID IS NULL;

UPDATE CERTIFICATE_VERIFY d
  JOIN ORGANISATIONS o ON o.SLUG = LOWER(REGEXP_REPLACE(d.CLIENT_ID, '[^A-Za-z0-9]+', '-'))
   SET d.ORG_ID = o.ORG_ID WHERE d.ORG_ID IS NULL;

UPDATE BATCH_JOBS d
  JOIN ORGANISATIONS o ON o.SLUG = LOWER(REGEXP_REPLACE(d.CLIENT_ID, '[^A-Za-z0-9]+', '-'))
   SET d.ORG_ID = o.ORG_ID WHERE d.ORG_ID IS NULL;
