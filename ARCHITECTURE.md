# ARCHITECTURE.md — Power BI SaaS Diagnostic Tool

## Projenin Amacı

Power BI projelerinde ortaya çıkan performans sorunlarını (büyük PBIX dosyaları, kötü DAX, bozuk veri modeli, visual yoğunluğu) otomatik analiz eden, çok kiracılı (multi-tenant) bir SaaS web uygulaması.

Kullanıcı PBIX dosyasını yükler → sistem analiz eder → HTML rapor, PDF ve JSON API çıktısı üretir.

---

## Sunucu

| Parametre | Değer |
|-----------|-------|
| Sağlayıcı | Contabo VPS |
| CPU | **4 çekirdek** *(DÜZELTİLDİ 2026-07-29 — önceki "8 vCPU" yanlıştı)* |
| RAM | **8 GB** *(DÜZELTİLDİ 2026-07-29 — önceki "30 GB" yanlıştı)* |
| Disk | Kısıtsız |
| OS | Ubuntu 24.04 |
| Deploy kullanıcısı | `pbixapp` |
| Uygulama dizini | `/home/pbixapp/app` |

> ⚠️ **Önemli düzeltme:** Bu dosyanın önceki sürümü sunucuyu "8 vCPU / 30 GB RAM"
> olarak tanımlıyordu. Gerçek sunucu **4 çekirdek / 8 GB RAM**. Aşağıdaki
> `CELERY_WORKERS=8` ve "500 MB × 8 worker" hesapları bu yanlış varsayıma
> dayanıyordu — bkz. güncellenmiş "Eş zamanlı analiz kapasitesi" bölümü.

---

## Teknoloji Yığını

```
İnternet
    │
  Nginx          ← reverse proxy, SSL, max 512 MB upload
    │
  FastAPI        ← web framework, async, JWT auth
  Uvicorn        ← ASGI server (4 worker)
    │
  Celery         ← arka plan iş kuyruğu (8 worker)
  Redis          ← Celery broker + job durum cache
    │
  Analiz Motoru  ← saf Python (zipfile + json), pandas YOK
    │
  PostgreSQL     ← ana veritabanı
    │
  Jinja2         ← HTML rapor şablonları
  WeasyPrint     ← PDF export
```

---

## Mimari Kararlar ve Gerekçeleri

### 1. Pandas — sınırlı istisna (2026-07-29 güncellendi)
Önceki karar "pandas asla kullanılmaz" şeklindeydi. Gerekçesi (~60 MB RAM
maliyeti) doğru ama sonucu abartılıydı: gerçek sunucuda (4 çekirdek/8 GB)
bile 3 worker × 60 MB = ~180 MB, önemsiz bir maliyet.

**Asıl risk pandas değil, PBIX'in `DataModel` bileşeninin decompress
edilmiş haliydi** (VertiPaq/ABF ikili format, dosya boyutundan bağımsız
olarak çok daha büyük olabilir). Bu artık `pbixray` kütüphanesi ile
`on_disk=True` modunda çözülüyor: decompress edilen veri RAM'e değil
diske yazılıp memory-map ediliyor, sadece dokunulan sayfalar RAM'e
alınıyor. `pbixray`'in kendisi `apsw`+`kaitaistruct` kullanıyor ama
DataFrame API'si için pandas'a bağımlı — bu tek modül için pandas
istisnası kabul edildi. Diğer tüm modüllerde pandas kullanılmaz.

### 2. pbi-tools hâlâ kullanılmıyor — ama eski gerekçe hatalıydı
Önceki not "pbi-tools arka planda Java JVM başlatır" diyordu — bu
**yanlıştı**: pbi-tools .NET tabanlıdır ve yerel bir Analysis Services
motoru (`msmdsrv`) başlatır, JVM değil. Yine de RAM/kurulum maliyeti
nedeniyle pbi-tools kullanılmıyor; bunun yerine `pbixray` (saf Python +
ikili format çözücü, harici motor gerektirmez) tercih edildi.

**Önemli düzeltme:** `DataModel` bileşeni JSON DEĞİLDİR — sıkıştırılmış
ikili bir VertiPaq veritabanıdır. Önceki analiz motoru bunu `json.loads()`
ile okumaya çalışıyordu, bu neredeyse her zaman sessizce başarısız olup
model/DAX analizini hiç çalıştırmadan "mükemmel" (100/100) skor
üretiyordu. Bkz. `app/analyzer/pbix_parser.py`.

### 3. Stream-based upload
PBIX dosyası RAM'e alınmaz. FastAPI chunk-by-chunk diske yazar. Dosya `/tmp/uploads/{tenant_id}/{job_id}.pbix` yoluna kaydedilir.

### 4. Celery iş kuyruğu
50+ eş zamanlı kullanıcı hedefi. **3** Celery worker paralel çalışır
*(eskiden 8 — 8 vCPU/30 GB yanlış varsayımına dayanıyordu; gerçek sunucu
4 çekirdek/8 GB)*. Fazlası kuyruğa alınır. Kullanıcı `job_id` ile durumu
takip eder (polling veya SSE).

### 5. Eş zamanlı analiz kapasitesi — ÖLÇÜLDܠ(2026-08-10)
İki gerçek dosyayla ölçüldü: 136 MB → 412 MB peak RSS (~3.0x),
180 MB → 499 MB peak RSS (2.77x). Oran lineer ve tutarlı.
300 MB üst sınır için ekstrapolasyon: ~870 MB peak RSS.
Sunucu 8 GB RAM, 1 Celery worker ile güvenli alan içinde.
Pratik üst sınır: 300 MB nadiren geçilir, büyük projeler datamart mimarisine bölünür.

---

## Multi-Tenant İzolasyonu

- Her müşteri bir **tenant**'tır
- Tüm DB tablolarında `tenant_id` kolonu zorunludur
- Her API isteğinde JWT'den `tenant_id` çekilir
- Sorgulara otomatik `WHERE tenant_id = :tid` eklenir — hiçbir zaman atlanmaz
- JSON API erişimi için tenant bazlı `api_key` kullanılır (`X-API-Key` header)

---

## Veritabanı Şeması

```sql
-- Kiracılar
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    api_key VARCHAR(64) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'free',   -- free | pro | enterprise
    quota_monthly INT DEFAULT 10,       -- aylık analiz hakkı
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Kullanıcılar
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'analyst', -- admin | analyst
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Analiz işleri
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    filename VARCHAR(500) NOT NULL,
    file_size_mb NUMERIC(10,2),
    status VARCHAR(20) DEFAULT 'pending', -- pending | processing | completed | failed
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Analiz sonuçları
CREATE TABLE analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    score_overall INT,        -- 0-100 genel skor
    score_model INT,          -- veri modeli skoru
    score_dax INT,            -- DAX skoru
    score_visuals INT,        -- visual skoru
    score_size INT,           -- boyut skoru
    result_json JSONB,        -- tam analiz sonucu
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- İndeksler
CREATE INDEX idx_jobs_tenant ON jobs(tenant_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_results_tenant ON analysis_results(tenant_id);
CREATE INDEX idx_results_job ON analysis_results(job_id);
```

---

## API Endpoint Yapısı

```
POST   /auth/register              → tenant + admin kullanıcı oluştur
POST   /auth/login                 → JWT token al
GET    /auth/me                    → mevcut kullanıcı bilgisi

POST   /jobs/upload                → PBIX yükle, job_id döner
GET    /jobs/{job_id}/status       → iş durumu (pending/processing/completed/failed)
GET    /jobs/                      → tenant'a ait tüm işler

GET    /reports/{job_id}           → HTML rapor
GET    /reports/{job_id}/pdf       → PDF indir
GET    /reports/compare?a={id}&b={id} → iki analizi karşılaştır

GET    /api/v1/results/{job_id}    → JSON API (api_key auth)
GET    /api/v1/history             → tenant analiz geçmişi
```

---

## PBIX Analiz Motoru — Parse Edilen Bileşenler

PBIX dosyası bir ZIP arşividir. İçindeki hedef dosyalar:

| ZIP içi yol | İçerik |
|-------------|--------|
| `DataModel` | Tablolar, kolonlar, ilişkiler, DAX measure'lar |
| `Report/Layout` | Sayfa yapısı, visual'lar, filtreler |
| `Connections` | Veri kaynağı bağlantıları |
| `[Content_Types].xml` | Dosya tipi bildirimi |

Her bileşen **sırayla** açılır, parse edilir, kapatılır. Aynı anda yalnızca bir bileşen RAM'dedir.

### Üretilen Analiz Çıktıları

**Veri Modeli:**
- Tablo listesi (satır sayısı tahmini, kolon sayısı)
- Kullanılmayan kolonlar
- GUID / yüksek kardinalite text kolonları
- İlişki haritası (M:M tespiti, bi-directional filter)
- Star schema uyum skoru

**DAX:**
- Tüm measure listesi
- Her measure için karmaşıklık skoru (0–100)
- Nested CALCULATE derinliği
- Iterator fonksiyon yoğunluğu (SUMX, AVERAGEX vb.)
- Riskli measure listesi + öneri

**Visual:**
- Sayfa başına visual sayısı
- Matrix ağırlık skoru
- Custom visual tespiti
- Slicer yoğunluğu

**Boyut:**
- Tahmini dataset MB
- Incremental refresh aktif mi?
- Partition yapısı var mı?

---

## Klasör Yapısı

```
/home/pbixapp/app/
├── main.py                  # FastAPI uygulama giriş noktası
├── .env                     # ortam değişkenleri (git'e ekleme)
├── requirements.txt
├── alembic/                 # DB migration
│   └── versions/
├── app/
│   ├── api/
│   │   ├── auth.py          # /auth endpoint'leri
│   │   ├── jobs.py          # /jobs endpoint'leri
│   │   ├── reports.py       # /reports endpoint'leri
│   │   └── api_v1.py        # /api/v1 JSON API
│   ├── core/
│   │   ├── config.py        # ayarlar (.env okuma)
│   │   ├── security.py      # JWT, password hash
│   │   └── database.py      # SQLAlchemy async engine
│   ├── models/
│   │   ├── tenant.py
│   │   ├── user.py
│   │   ├── job.py
│   │   └── result.py
│   ├── schemas/             # Pydantic şemaları
│   ├── worker/
│   │   ├── celery_app.py    # Celery konfigürasyonu
│   │   └── tasks.py         # PBIX analiz task'ı
│   ├── analyzer/
│   │   ├── pbix_parser.py   # ZIP açma, bileşen yönlendirme
│   │   ├── model_analyzer.py
│   │   ├── dax_analyzer.py
│   │   └── visual_analyzer.py
│   └── templates/
│       ├── report.html      # Jinja2 HTML rapor
│       └── report_pdf.html  # PDF için ayrı şablon
├── uploads/                 # geçici PBIX dosyaları
├── results/                 # JSON sonuç dosyaları (DB yedek)
└── logs/
```

---

## Ortam Değişkenleri (.env)

```env
DATABASE_URL=postgresql+asyncpg://pbixuser:SIFRE@localhost/pbixdb
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=cok-uzun-rastgele-bir-string-buraya
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
UPLOAD_DIR=/home/pbixapp/app/uploads
RESULTS_DIR=/home/pbixapp/app/results
MAX_UPLOAD_MB=512
CELERY_WORKERS=3
```

---

## Nginx Konfigürasyonu (özet)

```nginx
server {
    listen 80;
    server_name alan-adin.com;
    client_max_body_size 512M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;  # büyük dosya upload için
    }
}
```

---

## Systemd Servisleri

İki servis çalışır:

1. `pbixapp.service` — FastAPI + Uvicorn
2. `pbixworker.service` — Celery (8 worker)

Her ikisi de `pbixapp` kullanıcısıyla çalışır, sistem başlangıcında otomatik başlar.
