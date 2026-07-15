-- Verifiable certificates: one row per issued certificate, keyed by a short UID
-- encoded in the certificate's QR. SIGNATURE is an HMAC over the identifying
-- fields (see verification.py) so records are tamper-evident. STATUS supports
-- revocation without deleting the audit trail.

CREATE TABLE IF NOT EXISTS CERTIFICATE_VERIFY (
    CERT_UID       VARCHAR(32) PRIMARY KEY,
    CLIENT_ID      VARCHAR(255) NOT NULL,
    RECIPIENT_NAME VARCHAR(255),
    EVENT_NAME     VARCHAR(255),
    ISSUE_DATE     VARCHAR(64),
    SIGNATURE      VARCHAR(64) NOT NULL,
    STATUS         VARCHAR(16) NOT NULL DEFAULT 'VALID',
    CREATED_ON     DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_verify_client (CLIENT_ID),
    CONSTRAINT fk_verify_client FOREIGN KEY (CLIENT_ID)
        REFERENCES CLIENT_DETAILS (CLIENT_ID)
);
