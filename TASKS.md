# TASKS.md — Power BI SaaS Diagnostic Tool

Görevler sırayla yapılır. Tamamlanan `[ ]` → `[x]` olarak işaretle.
Takıldığında ARCHITECTURE.md ve CLAUDE.md'ye bak.

> ⚠️ **2026-07-29 durum düzeltmesi:** Bu dosya önceden Phase 2–8'in hiç
> başlamadığını gösteriyordu, ama kod tabanı incelendiğinde bu fazların
> büyük kısmının ZATEN yazılmış olduğu görüldü (auth, jobs, reports,
> api_v1, modeller, worker, analyzer, deploy dosyaları mevcut). Aşağıdaki
> kutucuklar buna göre güncellendi. Ayrıca şu kritik düzeltmeler yapıldı:
> - `app/analyzer/pbix_parser.py`: DataModel artık `pbixray` ile
>   (gerçek ikili format) okunuyor, eskiden `json.loads()` sessizce
>   başarısız olup sahte "mükemmel" skor üretiyordu.
> - `app/worker/tasks.py`: Celery retry mantığındaki dosya-silme bug'ı
>   düzeltildi.
> - `requirements.txt`: eksik `email-validator` eklendi, `pbixray` +
>   `pandas` (sadece bu modül için istisna) eklendi.
> - `CELERY_WORKERS` 8 → 3 (gerçek sunucu 4 çekirdek/8 GB, eskiden
>   yanlışlıkla 8 vCPU/30 GB varsayılmıştı).
> - Zip içindeki çöp `{...}` dizinleri temizlendi.
> - **Henüz yapılmadı:** gerçek bir PBIX dosyasıyla uçtan uca RAM/disk
>   ölçümü (bkz. Phase 9.2) ve sunucuya deploy.

---

## Phase 1 — Sunucu Hazırlığı ✅

- [x] `apt update && apt upgrade -y`
- [x] Nginx, Python 3.12, pip, venv, build araçları kuruldu
- [x] Redis kuruldu ve çalışıyor (`systemctl status redis-server` → active)
- [x] PostgreSQL 16 kuruldu ve çalışıyor
- [x] PostgreSQL kullanıcısı oluşturuldu: `pbixuser` / veritabanı: `pbixdb`
- [x] Sistem kullanıcısı oluşturuldu: `pbixapp`
- [x] Uygulama dizini oluşturuldu: `/home/pbixapp/app`
- [x] Python virtualenv oluşturuldu: `/home/pbixapp/app/venv`
- [x] Pip paketleri kuruldu (fastapi, celery, sqlalchemy vb.)

---

## Phase 2 — Proje İskeleti

- [ ] **2.1** Klasör yapısını oluştur
  ```bash
  cd /home/pbixapp/app
  mkdir -p app/api app/core app/models app/schemas app/worker app/analyzer app/templates
  touch app/__init__.py app/api/__init__.py app/core/__init__.py
  touch app/models/__init__.py app/schemas/__init__.py
  touch app/worker/__init__.py app/analyzer/__init__.py
  ```

- [ ] **2.2** `.env` dosyasını oluştur (CLAUDE.md'deki şablonu kullan, şifreleri doldur)

- [ ] **2.3** `requirements.txt` dosyasını oluştur ve `pip install -r requirements.txt` çalıştır

- [ ] **2.4** `app/core/config.py` yaz — `.env` okuma, ayar değişkenleri

- [ ] **2.5** `app/core/database.py` yaz — SQLAlchemy async engine, session factory

- [ ] **2.6** `app/core/security.py` yaz — JWT oluşturma/doğrulama, bcrypt hash

---

## Phase 3 — Veritabanı Modelleri ve Migration

- [ ] **3.1** `app/models/tenant.py` yaz — Tenant SQLAlchemy modeli

- [ ] **3.2** `app/models/user.py` yaz — User SQLAlchemy modeli

- [ ] **3.3** `app/models/job.py` yaz — Job SQLAlchemy modeli

- [ ] **3.4** `app/models/result.py` yaz — AnalysisResult SQLAlchemy modeli

- [ ] **3.5** Alembic başlat ve ilk migration oluştur
  ```bash
  cd /home/pbixapp/app
  source venv/bin/activate
  alembic init alembic
  # alembic/env.py'yi async için düzenle
  alembic revision --autogenerate -m "initial_tables"
  alembic upgrade head
  ```

- [ ] **3.6** Migration'ı PostgreSQL'e uygula ve tabloları doğrula
  ```bash
  psql -U pbixuser -d pbixdb -h localhost -c "\dt"
  ```

---

## Phase 4 — Auth Sistemi

- [ ] **4.1** `app/schemas/auth.py` yaz — Pydantic şemaları (RegisterRequest, LoginRequest, TokenResponse)

- [ ] **4.2** `app/api/auth.py` yaz — endpoint'ler:
  - `POST /auth/register` → tenant + admin kullanıcı oluştur
  - `POST /auth/login` → JWT token döner
  - `GET /auth/me` → mevcut kullanıcı bilgisi

- [ ] **4.3** JWT middleware yaz — her korumalı endpoint için `get_current_user` dependency

- [ ] **4.4** `main.py` yaz — FastAPI app, router'ları bağla, CORS ayarla

- [ ] **4.5** Uvicorn ile test et:
  ```bash
  cd /home/pbixapp/app
  source venv/bin/activate
  uvicorn main:app --host 0.0.0.0 --port 8000
  ```
  - `/docs` açılmalı
  - Register ve login endpoint'leri çalışmalı

---

## Phase 5 — Upload ve Kuyruk Sistemi

- [ ] **5.1** `app/worker/celery_app.py` yaz — Celery konfigürasyonu, Redis broker

- [ ] **5.2** Upload dizinlerini oluştur:
  ```bash
  mkdir -p /home/pbixapp/app/uploads
  mkdir -p /home/pbixapp/app/results
  chmod 750 /home/pbixapp/app/uploads
  ```

- [ ] **5.3** `app/schemas/job.py` yaz — JobCreateResponse, JobStatusResponse

- [ ] **5.4** `app/api/jobs.py` yaz — endpoint'ler:
  - `POST /jobs/upload` → stream upload, job kaydı, kuyruğa ekle
  - `GET /jobs/{job_id}/status` → iş durumu
  - `GET /jobs/` → tenant'ın tüm işleri

- [ ] **5.5** Celery worker'ı test başlat:
  ```bash
  celery -A app.worker.celery_app worker --loglevel=info --concurrency=8
  ```

- [ ] **5.6** Test: küçük bir PBIX yükle, `job_id` al, durum endpoint'ini kontrol et

---

## Phase 6 — Analiz Motoru

- [ ] **6.1** `app/analyzer/pbix_parser.py` yaz
  - PBIX ZIP'i aç (stream)
  - İçindeki bileşenleri tespit et (DataModel, Report/Layout, Connections)
  - Her bileşeni ilgili analyzer'a yönlendir
  - Sonuçları birleştir
  - `gc.collect()` çağır
  - Temp dosyayı sil

- [ ] **6.2** `app/analyzer/model_analyzer.py` yaz
  - DataModel JSON'ından tabloları çıkar
  - Kolonları listele, kardinalite hesapla
  - İlişkileri çıkar (M:M tespiti, bi-dir filter)
  - Kullanılmayan kolون tespiti
  - Star schema uyum skoru (0–100)

- [ ] **6.3** `app/analyzer/dax_analyzer.py` yaz
  - Tüm measure metinlerini çıkar
  - Nested CALCULATE derinliğini say
  - SUMX, AVERAGEX, FILTER(FILTER()) tespiti
  - Her measure için 0–100 risk skoru
  - Genel DAX skoru

- [ ] **6.4** `app/analyzer/visual_analyzer.py` yaz
  - Report/Layout JSON'ından sayfaları çıkar
  - Her sayfadaki visual sayısını say
  - Matrix visual tespiti ve ağırlık skoru
  - Custom visual tespiti
  - Slicer sayısı

- [ ] **6.5** `app/worker/tasks.py` yaz — Celery task:
  ```python
  @celery_app.task
  def analyze_pbix(job_id: str, tenant_id: str):
      # 1. Job'ı processing'e al
      # 2. pbix_parser.parse() çağır
      # 3. Sonucu DB'ye yaz
      # 4. Job'ı completed'a al
      # 5. Temp dosyayı sil
      # 6. gc.collect()
  ```

- [ ] **6.6** Gerçek bir PBIX dosyasıyla uçtan uca test
  - Upload → kuyruk → analiz → DB'de sonuç kontrolü

---

## Phase 7 — Rapor Çıktıları

- [ ] **7.1** `app/templates/report.html` yaz — Jinja2 HTML rapor şablonu
  - Genel skor kartı (0–100)
  - Kategori bazlı bulgular (model, DAX, visual, boyut)
  - Öneri listesi
  - Responsive tasarım

- [ ] **7.2** `app/templates/report_pdf.html` yaz — PDF için optimize şablon
  - Print CSS
  - Sayfa numaraları
  - Logo ve tenant adı

- [ ] **7.3** `app/api/reports.py` yaz — endpoint'ler:
  - `GET /reports/{job_id}` → HTML rapor
  - `GET /reports/{job_id}/pdf` → WeasyPrint ile PDF
  - `GET /reports/compare?a={id}&b={id}` → karşılaştırma

- [ ] **7.4** `app/api/api_v1.py` yaz — JSON API:
  - `GET /api/v1/results/{job_id}` → ham JSON sonuç (api_key auth)
  - `GET /api/v1/history` → tenant geçmişi

- [ ] **7.5** PDF export testi — WeasyPrint'in Ubuntu 24.04'te çalıştığını doğrula:
  ```bash
  python3 -c "from weasyprint import HTML; HTML(string='<h1>Test</h1>').write_pdf('/tmp/test.pdf')"
  ```

---

## Phase 8 — Production Yapılandırması

- [ ] **8.1** Nginx konfigürasyonu yaz `/etc/nginx/sites-available/pbixapp`:
  ```nginx
  server {
      listen 80;
      server_name ALAN_ADIN_BURAYA;
      client_max_body_size 512M;
      
      location / {
          proxy_pass http://127.0.0.1:8000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_read_timeout 300s;
      }
  }
  ```
  ```bash
  ln -s /etc/nginx/sites-available/pbixapp /etc/nginx/sites-enabled/
  nginx -t && systemctl reload nginx
  ```

- [ ] **8.2** SSL sertifikası al (alan adı hazırsa):
  ```bash
  certbot --nginx -d alan-adin.com
  ```

- [ ] **8.3** FastAPI systemd servisi oluştur `/etc/systemd/system/pbixapp.service`:
  ```ini
  [Unit]
  Description=PBIX Diagnostic FastAPI
  After=network.target postgresql.service redis.service

  [Service]
  User=pbixapp
  WorkingDirectory=/home/pbixapp/app
  Environment=PATH=/home/pbixapp/app/venv/bin
  ExecStart=/home/pbixapp/app/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4
  Restart=always

  [Install]
  WantedBy=multi-user.target
  ```

- [ ] **8.4** Celery systemd servisi oluştur `/etc/systemd/system/pbixworker.service`:
  ```ini
  [Unit]
  Description=PBIX Diagnostic Celery Worker
  After=network.target redis.service

  [Service]
  User=pbixapp
  WorkingDirectory=/home/pbixapp/app
  Environment=PATH=/home/pbixapp/app/venv/bin
  ExecStart=/home/pbixapp/app/venv/bin/celery -A app.worker.celery_app worker --loglevel=info --concurrency=8
  Restart=always

  [Install]
  WantedBy=multi-user.target
  ```

- [ ] **8.5** Servisleri başlat ve enable et:
  ```bash
  systemctl daemon-reload
  systemctl enable pbixapp pbixworker
  systemctl start pbixapp pbixworker
  systemctl status pbixapp pbixworker
  ```

- [ ] **8.6** Log rotasyonu ayarla (`/etc/logrotate.d/pbixapp`)

- [ ] **8.7** Temp dosya temizleme cron job:
  ```bash
  # pbixapp kullanıcısı crontab'ına ekle
  0 3 * * * find /home/pbixapp/app/uploads -mtime +1 -delete
  ```

---

## Phase 9 — Test ve Doğrulama

- [ ] **9.1** Uçtan uca akış testi:
  1. Yeni tenant kayıt ol
  2. PBIX yükle (küçük dosya, <50 MB)
  3. Job durumunu takip et
  4. HTML raporu görüntüle
  5. PDF indir
  6. JSON API'dan sonucu oku

- [ ] **9.2** Büyük dosya testi (150–500 MB PBIX):
  - Upload başarılı mı?
  - Worker crash olmadı mı? (`systemctl status pbixworker`)
  - RAM kullanımı kontrol et: `free -h`

- [ ] **9.3** Çoklu tenant izolasyon testi:
  - İki farklı tenant kayıt ol
  - Her birinin sadece kendi analizlerini gördüğünü doğrula

- [ ] **9.4** Eş zamanlı yük testi (isteğe bağlı):
  - 5 farklı PBIX aynı anda yükle
  - Celery kuyruğunun doğru çalıştığını doğrula

---

## Phase 10 — Açık Kararlar (Kullanıcıya Sor)

- [ ] **10.1** Fiyatlandırma modelini belirle:
  - Seçenekler: sabit aylık / analiz başına / freemium
  - `tenants.plan` ve `tenants.quota_monthly` alanları buna göre kullanılacak

- [ ] **10.2** Retention süresini belirle:
  - Öneri: 90 gün + otomatik temizleme
  - Planlar arası farklı retention (free: 30 gün, pro: 90 gün, enterprise: sınırsız)

- [ ] **10.3** Alan adı ve SSL:
  - Contabo'da IP var, alan adı bağlanacak mı?
  - Let's Encrypt için alan adı gerekli

---

## Tamamlanma Durumu

| Phase | Durum | Not |
|-------|-------|-----|
| 1 — Sunucu hazırlığı | ✅ Tamamlandı | — |
| 2 — Proje iskeleti | ✅ Kod yazılmış | .env sunucuda doldurulmalı |
| 3 — DB modelleri | ✅ Kod yazılmış | Migration sunucuda çalıştırılmadı |
| 4 — Auth sistemi | ✅ Kod yazılmış | Test edilmedi |
| 5 — Upload & kuyruk | ✅ Kod yazılmış | Test edilmedi |
| 6 — Analiz motoru | ✅ Düzeltildi (pbixray) | **Gerçek dosyayla RAM/disk testi bekliyor** |
| 7 — Rapor çıktıları | ✅ Kod yazılmış | Test edilmedi |
| 8 — Production yapılandırması | ✅ Kod yazılmış (worker sayısı düzeltildi) | Sunucuya deploy edilmedi |
| 9 — Test | ⏳ Bekliyor | Hiç çalıştırılmadı — öncelik burada |
| 10 — Açık kararlar | ⏳ Bekliyor | Fiyatlandırma + retention hâlâ karara bağlanmadı |
