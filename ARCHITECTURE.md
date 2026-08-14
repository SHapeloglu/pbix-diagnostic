# pbix-diagnostic Mimarisi (Session 9)

**Stack:** FastAPI + Celery + PostgreSQL + Redis + Nginx/SSL

**Ana Modüller:**
- `pbix_parser.py`: PBIX dosyasını parse (pbixray 0.15.4), exception'ları anlamlı hata mesajlarına dönüştür (FEAT-9)
- `model_analyzer.py`: Tablo/kolon/ilişki/RLS/KPI/perspective/translation analizi + star_schema score
- `dax_analyzer.py`: Measure complexity analizi + duplicate detection (FEAT-8)
- `visual_analyzer.py`: Sayfa/görsel/custom visual analizi
- `jobs.py` / `tasks.py`: Celery task orchestration, DB persistence
- `auth.py`: tenant-based auth (BIZ-1 dengan multi-plan quota)

**Veri Akışı:**
1. Upload → /upload endpoint → file_path + job_id
2. Celery task queue → analyze_pbix_task
3. parse_pbix() → model/dax/visuals analizi
4. Skorlar hesapla (4 boyut)
5. DB kaydet, /results/:job_id endpoint'i poll et

**Yeni Özellikler (Session 9):**
- FEAT-8: Duplicate measure detection (normalized expression)

**Not:** Baseline dosya (SatisSemantikModel.pbix) 133/1200/66 (eski 128/1163/68), skorlar korunmuş.
