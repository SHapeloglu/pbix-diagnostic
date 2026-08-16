# pbix-diagnostic Mimarisi (Current)

## Stack

Backend: FastAPI + Celery + PostgreSQL + Redis
Infrastructure: Nginx/SSL (Let's Encrypt) + systemd
Parser: pbixray 0.15.4
Server: Contabo VPS 95.111.242.96 (4 cores, 8 GB RAM, shared)

## Ana Dizin Yapısı

/home/pbixapp/app/
├── app/
│   ├── analyzer/
│   │   ├── pbix_parser.py         (PBIX → extract, DataCategory NEW)
│   │   ├── model_analyzer.py      (tablo/kolon/ilişki/RLS/KPI/... + formatting + RI)
│   │   ├── dax_analyzer.py        (measure complexity)
│   │   └── visual_analyzer.py     (sayfalar/görseller)
│   ├── api/
│   │   └── routes.py              (/upload, /results/:job_id)
│   ├── core/
│   │   └── jobs.py                (job orchestration)
│   ├── worker/
│   │   └── tasks.py               (Celery tasks + email hook)
│   ├── utils/
│   │   └── emails.py              (Gmail SMTP, Jinja2 templates)
│   ├── models/
│   │   └── db.py                  (SQLAlchemy models)
│   ├── auth.py                    (tenant-based multi-plan)
│   └── config.py                  (ENV, EMAIL_*)
├── main.py                        (FastAPI app entry)
├── requirements.txt
├── alembic/                       (DB migrations)
├── venv/                          (Python 3.12)
├── uploads/                       (PBIX files)
├── logs/                          (application logs)
└── .claude/                       (session continuity)

## Veri Akışı (High-Level)

1. User: POST /upload → PBIX file
   ↓
2. FastAPI: Save → Redis queue → Celery job_id
   ↓
3. Worker: analyze_pbix_task()
   ├─ parse_pbix() 
   │  ├─ PBIXRay(file)
   │  ├─ extract: tables, schema, relationships, statistics, DAX, visuals, 
   │  │           RLS, KPI, calc_groups, m_parameters, perspectives, 
   │  │           translations, tmschema_columns (NEW)
   │  └─ analyze_model() + analyze_dax() + analyze_visuals()
   │
   ├─ Findings (score-independent):
   │  ├─ exposed_connections
   │  ├─ column_statistics (unreferenced, vertipaq size)
   │  ├─ naming_issues
   │  ├─ formatting_info (DataCategory) — FEAT-11
   │  └─ referential_integrity_info (DirectQuery RI) — FEAT-7
   │
   ├─ Scores: model / dax / visuals / size (4 categories)
   │
   ├─ Database: INSERT analyses table
   │
   └─ Email: user email + scores
   ↓
4. User: GET /results/:job_id → JSON report

## Model Analyzer Output

result = {
    "tables": [...],
    "relations": [...],
    "rls_roles": [...],
    "kpis": [...],
    "calculation_groups": [...],
    "measures": [...],
    "perspectives": [...],
    "translations": [...],
    "m_parameters": [...],
    
    # Score-independent findings:
    "exposed_connections": [...],
    "column_statistics": {...},
    "naming_issues": [...],
    "formatting_info": {...},           # FEAT-11 (NEW)
    "referential_integrity_info": {...} # FEAT-7 (NEW)
}

## Key Classes

- PBIXRay (pbixray 0.15.4): Örnek yok destructor gerekli (del model; gc.collect())
- PBIXRayError, LiveConnectionError, NoEmbeddedModelError
- Celery: app/worker/tasks.py → analyze_pbix_task.delay(job_id)
- PostgreSQL: analyses, jobs, users (multi-tenant auth via job.user_id)

## Önemli Notlar

1. Memory Management: pbixray context manager desteklemiyor → del model; gc.collect() mutlaka
2. NaN Handling: pbixray NaN dönderiyor → PostgreSQL JSONB uyumluluğu için sanitize et
3. Venv: /home/pbixapp/app/venv (çok önemli, /opt/fretflow/venv DEĞİL)
4. Score-Independent Findings: Connection hygiene (IT concern) vs Model design ayrı
5. Tenant Quota: multi-plan support, auth.py → job analysis count kontrol

## Deployment

systemd services:
  - pbixapp.service → FastAPI (Uvicorn)
  - pbixworker.service → Celery Worker (1 worker, RAM-constrained)
SSL: Let's Encrypt (cert valid until 2026-11-04)
Nginx: reverse proxy port 80→8000 (FastAPI)
