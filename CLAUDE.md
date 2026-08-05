# CLAUDE.md — Power BI SaaS Diagnostic Tool

Bu dosya, projeyi devralan Claude oturumunun projeyi sıfırdan anlaması için yazılmıştır.
**ARCHITECTURE.md ve TASKS.md'yi de oku** — üçü birlikte eksiksiz bağlamı oluşturur.

---

## Projeyi Tek Cümlede Anla

Power BI PBIX dosyalarını analiz eden, çok kiracılı (multi-tenant) bir SaaS web uygulaması.
Kullanıcı PBIX yükler → Celery worker analiz eder → HTML/PDF/JSON rapor üretilir.

---

## Sunucu Durumu

- **Sağlayıcı:** Contabo VPS
- **CPU:** 4 çekirdek *(DÜZELTİLDİ 2026-07-29 — önceki sürümde yanlışlıkla "8 vCPU" yazıyordu)*
- **RAM:** 8 GB *(DÜZELTİLDİ 2026-07-29 — önceki sürümde yanlışlıkla "30 GB" yazıyordu)*
- **OS:** Ubuntu 24.04
- **Deploy kullanıcısı:** `pbixapp`
- **Uygulama dizini:** `/home/pbixapp/app`
- **SSH:** Root erişimi mevcut, ancak günlük işlemler için `pbixapp` kullanıcısı tercih edilmeli

### Kurulu olan (TASKS.md adım 1-5 tamamlandı):
- [x] `apt update && apt upgrade`
- [x] Nginx, Python 3.12, pip, venv
- [x] Redis (çalışıyor, `systemctl status redis-server` → active)
- [x] PostgreSQL 16 (çalışıyor)
- [x] PostgreSQL kullanıcısı: `pbixuser` / veritabanı: `pbixdb`
- [x] `pbixapp` sistem kullanıcısı oluşturuldu
- [x] `/home/pbixapp/app` dizini ve virtualenv hazır
- [x] Tüm pip paketleri kuruldu

### Henüz yapılmayan:
- [ ] Proje dosyaları yazılmadı (TASKS.md Phase 2'den başla)
- [ ] DB tabloları oluşturulmadı
- [ ] Nginx yapılandırılmadı
- [ ] Systemd servisleri kurulmadı
- [ ] SSL sertifikası alınmadı

---

## Kritik Teknik Kurallar

Bu kurallar konuşma boyunca alınan kararları yansıtır. **Değiştirme.**

### RAM Yönetimi (2026-07-29 güncellendi)
```python
# pbix_parser.py DISINDA pandas kullanma
import json, collections, gc

# Her Celery task sonunda zorunlu
gc.collect()
```
**İstisna:** `app/analyzer/pbix_parser.py`, gerçek `DataModel` ikili
formatını okumak için `pbixray` kullanır (bu da pandas'a bağımlıdır).
Bu, projedeki TEK pandas import noktasıdır. Sunucu 4 çekirdek/8 GB
olduğu için 3 worker × ~60 MB = ~180 MB önemsizdir. Asıl RAM riski
decompress edilmiş VertiPaq modelinin boyutuydu — bu `on_disk=True`
(diske yaz + memory-map) ile çözüldü.

### PBIX Parse Stratejisi — DÜZELTİLDİ
`DataModel` bileşeni **JSON DEĞİLDİR** — sıkıştırılmış ikili bir
VertiPaq/Analysis Services formatıdır. `json.loads()` ile okumaya
çalışmak neredeyse her zaman sessizce başarısız olur ve model/DAX
analizi hiç çalışmadan yanıltıcı "mükemmel" skor üretir. Doğru yöntem:

```python
from pbixray import PBIXRay

with PBIXRay(pbix_path, on_disk=True, temp_dir=upload_dir) as model:
    schema = model.schema.to_dict("records")
    relationships = model.relationships.to_dict("records")
    measures = model.dax_measures.to_dict("records")
    # with bloğu kapanınca spill dosyası otomatik silinir

# Report/Layout GERÇEKTEN JSON'dur, stream ile okumaya devam:
from zipfile import ZipFile
with ZipFile(pbix_path) as zf:
    with zf.open('Report/Layout') as f:
        layout = json.load(f)
```

### pbi-tools Yasak (gerekçe düzeltildi)
```bash
# Kurma — ama eski gerekçe ("JVM başlatır") YANLIŞTI.
# pbi-tools .NET tabanlıdır, yerel bir Analysis Services motoru
# (msmdsrv) başlatır, JVM değil. Yine de kurulum/RAM maliyeti
# nedeniyle tercih edilmiyor; pbixray (harici motor gerektirmez)
# kullanılıyor.
pip install pbi-tools  # ← kurma, pbixray kullan
```

### Tenant İzolasyonu — Asla Atlanmaz
```python
# Her DB sorgusunda tenant_id filtresi zorunlu
results = await db.execute(
    select(Job).where(
        Job.tenant_id == current_user.tenant_id,  # ← zorunlu
        Job.id == job_id
    )
)
```

### Upload — Stream, RAM'e Alma
```python
# FastAPI'de doğru upload pattern
@router.post("/jobs/upload")
async def upload_pbix(
    file: UploadFile,
    current_user: User = Depends(get_current_user)
):
    job_id = str(uuid4())
    path = f"{UPLOAD_DIR}/{current_user.tenant_id}/{job_id}.pbix"
    
    # Chunk chunk diske yaz, RAM'e alma
    async with aiofiles.open(path, 'wb') as f:
        while chunk := await file.read(1024 * 1024):  # 1 MB chunk
            await f.write(chunk)
    
    # Kuyruğa ekle
    analyze_pbix.delay(job_id, str(current_user.tenant_id))
    return {"job_id": job_id}
```

---

## Kullanılacak Teknolojiler

| Katman | Teknoloji | Versiyon |
|--------|-----------|----------|
| Web framework | FastAPI | latest |
| ASGI server | Uvicorn | latest |
| Task queue | Celery | latest |
| Message broker | Redis | sistem paketi |
| Veritabanı | PostgreSQL 16 | sistem paketi |
| ORM | SQLAlchemy (async) | latest |
| Migration | Alembic | latest |
| Auth | python-jose + passlib | latest |
| Şablonlar | Jinja2 | latest |
| PDF | WeasyPrint | latest |
| Dosya I/O | aiofiles | latest |

---

## Pip Paketleri (requirements.txt)

```
fastapi
uvicorn[standard]
celery
redis
sqlalchemy[asyncio]
asyncpg
psycopg2-binary
alembic
python-jose[cryptography]
passlib[bcrypt]
python-multipart
jinja2
weasyprint
python-dotenv
aiofiles
email-validator      # EmailStr (pydantic) icin zorunlu, eskiden eksikti
pbixray               # gercek DataModel (VertiPaq) parse icin — bkz. yukarida
pandas                # pbixray'in bagimliligi, SADECE bu modul icin istisna
```

---

## Klasör Yapısı (hedef)

```
/home/pbixapp/app/
├── main.py
├── .env
├── requirements.txt
├── alembic.ini
├── alembic/versions/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── jobs.py
│   │   ├── reports.py
│   │   └── api_v1.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── security.py
│   │   └── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── tenant.py
│   │   ├── user.py
│   │   ├── job.py
│   │   └── result.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── job.py
│   │   └── result.py
│   ├── worker/
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   └── tasks.py
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── pbix_parser.py
│   │   ├── model_analyzer.py
│   │   ├── dax_analyzer.py
│   │   └── visual_analyzer.py
│   └── templates/
│       ├── report.html
│       └── report_pdf.html
├── uploads/
├── results/
└── logs/
```

---

## Geliştirme Akışı

Yeni Claude oturumu TASKS.md'yi açar ve ilk tamamlanmamış görevi bulur.
Her görev tamamlandığında TASKS.md'de `[ ]` → `[x]` olarak işaretlenir.

Kod yazarken:
1. Dosyayı tam yaz, yarım bırakma
2. Her modülün başına kısa bir yorum ekle
3. Hata mesajları Türkçe olabilir (kullanıcı Türk)
4. API response'ları İngilizce kalsın (JSON standart)

---

## .env Şablonu

```env
DATABASE_URL=postgresql+asyncpg://pbixuser:BURAYA_SIFRE@localhost/pbixdb
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=BURAYA_EN_AZ_32_KARAKTER_RASTGELE_STRING
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
UPLOAD_DIR=/home/pbixapp/app/uploads
RESULTS_DIR=/home/pbixapp/app/results
MAX_UPLOAD_MB=512
CELERY_WORKERS=3
ENVIRONMENT=production
```

---

## Netleşmemiş Kararlar

Aşağıdaki iki karar henüz alınmadı. Kullanıcıya sor:

1. **Fiyatlandırma modeli:** Tenant başına sabit ücret mi, analiz sayısı başına mı, freemium mu?
   - Bu karar `tenants.plan` ve `tenants.quota_monthly` alanlarını etkiliyor.

2. **Analiz retention süresi:** Sonuçlar ne kadar saklanacak?
   - Öneri: 90 gün + otomatik temizleme cron job.
   - Kullanıcı onayı bekleniyor.

---

## Bağlam Özeti (bu konuşmadan)

- Kullanıcı Power BI uzmanı, teknik altyapıyı biliyor
- Önce cPanel hosting düşünüldü, memory sorunu nedeniyle Contabo'ya geçildi
- 50+ eş zamanlı kullanıcı hedefi, 150–500 MB PBIX dosyaları
- Monitoring özelliği (Power BI REST API) şimdilik kapsam dışı
- Çıktı formatları: HTML + PDF + JSON API — üçü de istenıyor
- Multi-tenant: her müşteri ayrı workspace
- DB loglama: tüm analizler saklanacak
