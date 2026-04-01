-- ============================================================
-- Multi-Disease Prediction System — PostgreSQL Schema
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Users ───────────────────────────────────────────────────
CREATE TYPE user_role AS ENUM ('admin', 'user');

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50)  UNIQUE NOT NULL,
    email           VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role            user_role    NOT NULL DEFAULT 'user',
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email    ON users(email);

-- ─── Predictions ─────────────────────────────────────────────
CREATE TYPE disease_type AS ENUM ('heart', 'diabetes', 'kidney');

CREATE TABLE IF NOT EXISTS predictions (
    id                 SERIAL PRIMARY KEY,
    user_id            INT REFERENCES users(id) ON DELETE SET NULL,
    disease_type       disease_type NOT NULL,
    model_used         VARCHAR(50)  NOT NULL,
    input_data         JSONB        NOT NULL,
    prediction_result  SMALLINT     NOT NULL CHECK (prediction_result IN (0, 1)),
    prediction_label   VARCHAR(50)  NOT NULL,
    confidence         NUMERIC(6,4) NOT NULL,
    shap_values        JSONB,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_predictions_user_id      ON predictions(user_id);
CREATE INDEX idx_predictions_disease      ON predictions(disease_type);
CREATE INDEX idx_predictions_created_at   ON predictions(created_at DESC);

-- ─── Model Metrics ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS model_metrics (
    id                      SERIAL PRIMARY KEY,
    disease_type            disease_type NOT NULL,
    model_name              VARCHAR(50)  NOT NULL,
    accuracy                NUMERIC(8,6),
    precision               NUMERIC(8,6),
    recall                  NUMERIC(8,6),
    f1_score                NUMERIC(8,6),
    roc_auc                 NUMERIC(8,6),
    confusion_matrix        JSONB,
    classification_report   TEXT,
    is_best_model           BOOLEAN NOT NULL DEFAULT FALSE,
    trained_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (disease_type, model_name)
);

CREATE INDEX idx_model_metrics_disease ON model_metrics(disease_type);

-- ─── Seed: default admin user (password: admin123) ───────────
-- Replace hash with bcrypt of your chosen password
INSERT INTO users (username, email, hashed_password, role)
VALUES (
    'admin',
    'admin@mdps.local',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    'admin'
) ON CONFLICT DO NOTHING;
