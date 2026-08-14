# pbix-diagnostic Mimarisi (Session 11)

**Stack:** FastAPI + Celery + PostgreSQL + Redis + Nginx/SSL

**Ana Modüller:**

- `pbix_parser.py`: PBIX dosyasını parse (pbixray 0.15.4), DataCategory extraction (NEW — Session 11)
- `model_analyzer.py`: Tablo/kolon/ilişki/RLS/KPI/perspective/translation + **formatting** (Session 11) analizi
- `dax_analyzer.py`: Measure complexity + duplicate detection (FEAT-8)
- `visual_analyzer.py`: Sayfa/görsel/custom visual analizi
- `jobs.py` / `tasks.py`: Celery task orchestration + email notification (Session 10)
- `auth.py`: Tenant-based auth (multi-plan quota)
- `utils/emails.py`: Gmail SMTP email gönderiş (Session 10)

**Veri Akışı:**

1. Upload → /upload endpoint → file_path + job_id
2. Celery task queue → analyze_pbix_task
3. parse_pbix() → model/dax/visuals analizi (+ DataCategory formatting)
4. Skorlar hesapla (4 boyut — formatting skor etkisiz)
5. DB kaydet
6. User email'e completion notification gönder
7. /results/:job_id endpoint'i poll et

**Yeni Özellikler (Session 11):**

- Formatting (DataCategory) analizi: tmschema_columns → columns_with_datacategory (bilgi bulgusu)

**Not:** Baseline dosya (SatisSemantikModel.pbix) 133/1200/66, skorlar korunmuş (80/100/100/90).
