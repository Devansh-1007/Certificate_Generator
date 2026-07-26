-- V6: Google sign-in and work-email domain rules.
--
-- Two related ideas:
--   1. A user may authenticate with a password OR with Google, so PASSWORD_HASH
--      becomes optional and the provider is recorded.
--   2. An organisation can claim its email domain. Colleagues who sign in with
--      an address at that domain join the existing tenant instead of silently
--      creating a second, empty one — the classic B2B onboarding papercut.

-- users: OAuth identity
ALTER TABLE USERS MODIFY COLUMN PASSWORD_HASH LONGTEXT NULL;
ALTER TABLE USERS ADD COLUMN AUTH_PROVIDER  VARCHAR(16)  NOT NULL DEFAULT 'password';  -- password | google
ALTER TABLE USERS ADD COLUMN GOOGLE_SUB     VARCHAR(64)  DEFAULT NULL;
ALTER TABLE USERS ADD COLUMN AVATAR_URL     LONGTEXT     DEFAULT NULL;
ALTER TABLE USERS ADD COLUMN EMAIL_VERIFIED TINYINT(1)   NOT NULL DEFAULT 0;

-- Google's `sub` is the stable account id; email can change, sub cannot.
CREATE UNIQUE INDEX uq_user_google_sub ON USERS (GOOGLE_SUB);

-- organisations: domain claim + join policy
ALTER TABLE ORGANISATIONS ADD COLUMN EMAIL_DOMAIN     VARCHAR(190) DEFAULT NULL;
ALTER TABLE ORGANISATIONS ADD COLUMN ALLOW_DOMAIN_JOIN TINYINT(1)  NOT NULL DEFAULT 1;
CREATE INDEX idx_org_domain ON ORGANISATIONS (EMAIL_DOMAIN);

-- Backfill: adopt the owner's domain where it is a real work domain. Consumer
-- domains are skipped so unrelated gmail.com accounts never pool into one org.
UPDATE ORGANISATIONS o
  JOIN USERS u ON u.ORG_ID = o.ORG_ID AND u.ROLE = 'owner'
   SET o.EMAIL_DOMAIN = SUBSTRING_INDEX(u.EMAIL, '@', -1)
 WHERE o.EMAIL_DOMAIN IS NULL
   AND SUBSTRING_INDEX(u.EMAIL, '@', -1) NOT IN (
        'gmail.com','googlemail.com','yahoo.com','yahoo.co.in','outlook.com','hotmail.com',
        'live.com','icloud.com','proton.me','protonmail.com','aol.com','mail.com',
        'yandex.com','zoho.com','gmx.com','rediffmail.com','legacy.local'
   );

-- Existing password accounts are considered verified by their owner's action.
UPDATE USERS SET EMAIL_VERIFIED = 1 WHERE AUTH_PROVIDER = 'password';
