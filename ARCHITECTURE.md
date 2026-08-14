# pbix-diagnostic Mimarisi (Session 10)

**Stack:** FastAPI + Celery + PostgreSQL + Redis + Nginx/SSL

**Ana Modüller:**

- `pbix_parser.py`: PBIX dosyasını parse (pbixray 0.15.4), exception'ları anlamlı hata mesajlarına dönüştür
- `model_analyzer.py`: Tablo/kolon/ilişki/RLS/KPI/perspective/translation analizi
- `dax_analyzer.py`: Measure complexity + duplicate detection (FEAT-8)
- `visual_analyzer.py`: Sayfa/görsel/custom visual analizi
- `jobs.py` / `tasks.py`: Celery task orchestration + **email notification** (Session 10)
- `auth.py`: Tenant-based auth (multi-plan quota)
- `utils/emails.py`: Gmail SMTP email gönderiş (NEW — Session 10)

**Veri Akışı:**

1. Upload → /upload endpoint → file_path + job_id
2. Celery task queue → analyze_pbix_task
3. parse_pbix() → model/dax/visuals analizi
4. Skorlar hesapla (4 boyut)
5. DB kaydet
6. **User email'e completion notification gönder (NEW)** 
7. /results/:job_id endpoint'i poll et

**Yeni Özellikler (Session 10):**

- Email notifications: analysis complete, quota warning templates
- Graceful error handling: email hatası analizi kırmaması

**Not:** Baseline dosya (SatisSemantikModel.pbix) artık 133/1200/66 (eski 128/1163/68), skorlar korunmuş.
