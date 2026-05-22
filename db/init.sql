-- db/init.sql
-- 수직 슬라이스 단계: schema 3개만 (CLAUDE.md §2). 나머지 3개는 Sprint 2.
-- (metadata / lineage / agent_logs)  ※ processed / ml_results / rag_vectors 는 연기

CREATE EXTENSION IF NOT EXISTS vector;  -- pgvector (RAG는 Sprint 2지만 확장만 미리)

-- 1) 데이터셋·컬럼·제약 메타데이터
CREATE SCHEMA IF NOT EXISTS metadata;
CREATE TABLE IF NOT EXISTS metadata.datasets (
    dataset_id   TEXT PRIMARY KEY,
    modality     TEXT NOT NULL,            -- timeseries|inspection-image|event-log|order
    n_rows       BIGINT,
    n_cols       INT,
    encoding     TEXT,
    registered_at TIMESTAMPTZ DEFAULT now()
);

-- 2) 변환 체인 추적 (SI 컴플라이언스 핵심)
CREATE SCHEMA IF NOT EXISTS lineage;
CREATE TABLE IF NOT EXISTS lineage.transformations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id          TEXT NOT NULL,
    source_column       TEXT,
    transformation_type TEXT NOT NULL,
    transformation_params JSONB DEFAULT '{}'::jsonb,
    result_column       TEXT,
    applied_at          TIMESTAMPTZ DEFAULT now(),
    applied_by_agent    TEXT,
    user_approval_id    TEXT,
    can_rollback        BOOLEAN DEFAULT true
);
CREATE INDEX IF NOT EXISTS idx_lineage_dataset ON lineage.transformations(dataset_id);

-- 3) 에이전트 의사결정 로그
CREATE SCHEMA IF NOT EXISTS agent_logs;
CREATE TABLE IF NOT EXISTS agent_logs.decisions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id  TEXT,
    agent_name  TEXT NOT NULL,            -- inspector|planner|executor|validator
    permission_level TEXT,                -- L1|L2|L3
    input_summary  JSONB,
    output_summary JSONB,
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_agentlogs_dataset ON agent_logs.decisions(dataset_id);
