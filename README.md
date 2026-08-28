# pbix-diagnostic

**Power BI PBIX Dosyası Analiz & Tanı Aracı**

Microsoft Power BI `.pbix` dosyalarını analiz eden ve model kalitesi, DAX karmaşıklığı, görsel yoğunluğu ve dosya boyutu verimliliği üzerinde puanlama yapmış kapsamlı tanı raporları üreten çok kiracılı (multi-tenant) SaaS web uygulaması.

🔗 **Canlı:** [pbixdia.powerbi.com.tr](https://pbixdia.powerbi.com.tr)

---

## Genel Bakış

Power BI modelleri sistematik analiz olmadan karmaşık, bakımı zor ve kaynak açısından verimsiz hale gelebilir. **pbix-diagnostic**, PBIX dosyalarınızdan anahtar metrikleri otomatik olarak çıkarır ve şu alanlardaki sorunları ortaya koymaktadır:

- **Model Tasarımı** (80/100 temel): ilişki bütünlüğü, kullanılmayan tablolar, kolon tekrar kullanılabilirliği, referansiyel bütünlük
- **DAX Karmaşıklığı** (100/100 temel): ölçü karmaşıklığı, döngüsel bağımlılıklar, hesaplama grupları
- **Görsel Yoğunluğu** (100/100 temel): sayfa/görsel sayısı optimizasyonu
- **Dosya Boyutu** (90/100 temel): sıkıştırma verimliliği, depolama ayak izi

Şu anda **tamamen ücretsiz geri bildirim fazındadır** — ürün olgunlaşırken tüm analiz tamamen ücretsizdir.

---

## Temel Özellikler

✅ **Otomatik PBIX Ayrıştırması** — `pbixray 0.15.4` kullanarak tabloları, ilişkileri, DAX ölçülerini, görselleri, RLS, KPI tanımlarını, hesaplama gruplarını, M parametrelerini, perspektif ve çevirilerini ve şema metaveri ayrıştırır

✅ **Çok Boyutlu Puanlama** — dört bağımsız puan boyutu (model, DAX, görseller, boyut) ve cezalandırma mantığının açık açıklaması

✅ **Güvenlik Bulguları** — maruz kalan bağlantı dizelerini ve doğrudan kimlik bilgilerini, model puanını cezalandırmadan ortaya koymaktadır (hijyen vs. tasarım ayrı kaygılardır)

✅ **E-posta Bildirimleri** — Gmail SMTP entegrasyonu ile async analiz; sonuçlar kullanıcının e-postasına teslim edilir

✅ **Çok Kiracılı Mimari** — kiracı başına kotalar, plan yönetimi, Celery üzerinden izole iş kuyrukları

✅ **REST API** — entegrasyon için basit `/upload` ve `/results/:job_id` endpoint'leri

✅ **Detaylı Raporlar** — DAX ölçü referansları, kolon istatistikleri, adlandırma kuralı ihlalleri, biçimlendirme tutarsızlıkları, hesaplama grubu tespiti içeren JSON tabanlı bulgular

---

## Teknoloji Yığını

| Bileşen | Teknoloji | Sürüm |
|---------|-----------|-------|
| **Backend** | FastAPI | En Son |
| **Görev Kuyruğu** | Celery + Redis | — |
| **Veritabanı** | PostgreSQL | 12+ |
| **PBIX Parser** | pbixray | 0.15.4 |
| **Web Sunucusu** | Nginx + Uvicorn | — |
| **SSL** | Let's Encrypt | Otomatik yenileme |
| **Python** | Python | 3.12 |

---

## Başlangıç

### Ön Koşullar

- Python 3.12+
- PostgreSQL 12+
- Redis 6+
- 4+ GB RAM (paylaşılan sunucu ortamı)

### Kurulum

\`\`\`bash
git clone https://github.com/SHapeloglu/pbix-diagnostic.git
cd pbix-diagnostic

# Sanal ortam oluştur
python3.12 -m venv venv
source venv/bin/activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# Ortam değişkenlerini ayarla
cp .env.example .env
# .env'yi düzenle:
#   - DATABASE_URL
#   - REDIS_URL
#   - EMAIL_FROM / GMAIL_APP_PASSWORD
#   - SECRET_KEY

# Veritabanı geçişlerini çalıştır
alembic upgrade head

# Hizmetleri başlat
# Terminal 1: FastAPI sunucusu
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Celery worker'ı
celery -A app.worker.tasks worker --loglevel=info
\`\`\`

### Yerel Test

\`\`\`bash
# PBIX dosyasını yükle
curl -F "file=@path/to/model.pbix" http://localhost:8000/upload

# Sonuçları kontrol et
curl http://localhost:8000/results/{job_id}
\`\`\`

---

## API Referansı

### \`POST /upload\`
Analiz için PBIX dosyası yükle.

**İstek:**
\`\`\`bash
curl -F "file=@model.pbix" https://pbixdia.powerbi.com.tr/upload
\`\`\`

**Yanıt:**
\`\`\`json
{
  "job_id": "abc-123-def",
  "message": "Analiz başladı. Sonuçlar için e-postanızı kontrol edin."
}
\`\`\`

### \`GET /results/{job_id}\`
Analiz sonuçlarını al (JSON).

**Yanıt:**
\`\`\`json
{
  "job_id": "abc-123-def",
  "status": "tamamlandı",
  "scores": {
    "model": 80,
    "dax": 100,
    "visuals": 100,
    "size": 90
  },
  "findings": {
    "tables": [...],
    "relationships": [...],
    "exposed_connections": [...],
    "naming_issues": [...],
    "formatting_info": {...},
    "referential_integrity_info": {...}
  }
}
\`\`\`

---

## Mimari

\`\`\`
/app
├── analyzer/              # Temel PBIX analiz mantığı
│   ├── pbix_parser.py     # PBIXRay sarıcısı + çıkarma
│   ├── model_analyzer.py  # Tablo, ilişki, RLS, KPI analizi
│   ├── dax_analyzer.py    # Ölçü karmaşıklığı puanlaması
│   └── visual_analyzer.py # Sayfa ve görsel sayımı
├── api/                   # FastAPI route'ları
│   ├── routes.py          # /upload, /results endpoint'leri
│   ├── auth.py            # /auth/register, /auth/login, /auth/me
│   └── deps.py            # Bağımlılık enjeksiyonu (get_current_user)
├── worker/                # Celery async görevleri
│   └── tasks.py           # analyze_pbix_task()
├── models/                # SQLAlchemy ORM
│   ├── user.py            # Kullanıcı modeli
│   └── tenant.py          # Kiracı modeli (çok kiracılılık)
├── utils/
│   └── emails.py          # Gmail SMTP entegrasyonu
├── core/
│   ├── database.py        # AsyncSession kurulumu
│   ├── security.py        # Şifre hashleme, JWT
│   └── jobs.py            # İş orkestrasyonu
└── main.py                # FastAPI uygulaması giriş noktası
\`\`\`

---

## Puanlama Mantığı

### Model Puanı (0–100)
- Cezalandırır: kullanılmayan tablolar, eksik ilişkiler, uygun satır filtreleri olmayan RLS, başvurulmayan kolonlar
- **Temel:** 80/100

### DAX Puanı (0–100)
- Cezalandırır: karmaşık ölçü tanımları, döngüsel ölçü bağımlılıkları, verimsiz filtre bağlamları
- **Temel:** 100/100

### Görsel Puanı (0–100)
- Cezalandırır: aşırı sayfa sayısı (>50), sayfa başına aşırı görsel (>20), kullanılmayan rapor sayfaları
- **Temel:** 100/100

### Boyut Puanı (0–100)
- Cezalandırır: tablo/kolon sayısına göre dosya boyutu, verimsiz sıkıştırma, büyük istatistikler
- **Temel:** 90/100

**Not:** Güvenlik bulguları (maruz kalan bağlantı dizesi) puanlanmaz — BT/hijyen kaygıları ile tasarım kalitesini ayırt etmek için ayrı olarak ortaya konur.

---

## Oturum Tabanlı Geliştirme

Bu proje, ilerlemeyi takip etmek için oturum tabanlı devamlılık kullanır. Önemli oturum dosyaları:

- **\`TASKS.md\`** — tamamlanan ve açık görev takibi
- **\`SESSION.md\`** — oturum başına notlar ve kararlar
- **\`CLAUDE.md\`** — AI asistanı bağlam özeti
- **\`ARCHITECTURE.md\`** — mevcut sistem tasarımı
- **\`backlog.md\`** — düşük öncelikli / stratejik maddeler

Ayrıntılar için \`.claude/\` dizinine bakın.

---

## Dağıtım

### Systemd Hizmetleri

\`\`\`bash
# pbixapp.service — FastAPI port 8000'de (Nginx üzerinden ters proxy)
sudo systemctl status pbixapp

# pbixworker.service — Async analiz için Celery worker'ı
sudo systemctl status pbixworker
\`\`\`

### SSL / HTTPS

Nginx ters proxy + Let's Encrypt SSL (otomatik yenileme). Sertifika **2026-11-04** tarihine kadar geçerlidir.

### Altyapı

- **Sunucu:** Contabo VPS (4 çekirdek, 8 GB RAM, paylaşılan ortam)
- **Ters Proxy:** Nginx (port 80 → port 8000)
- **Veritabanı:** PostgreSQL (asyncpg)
- **Önbellek/Kuyruk:** Redis (Celery broker)

---

## Bilinen Sınırlamalar & Gelecek Çalışmalar

### Mevcut Faz: Ücretsiz Geri Bildirim
- Tüm analiz ücretsizdir (henüz ödeme entegrasyonu yok)
- Kota sınırları: kullanıcı başına 3 analiz/ay (varsayılan, ayarlanabilir)
- Geçmiş analizlerde 30 gün saklama

### Yol Haritası

| Öncelik | Görev | Durum |
|---------|-------|-------|
| 1 | **BIZ-5:** E-posta doğrulama ile kullanıcı kaydı | Devam Ediyor |
| 2 | **BIZ-7:** Kiracı yönetimi için yönetim paneli | Planlı |
| 3 | **BIZ-6:** Stripe ödeme entegrasyonu | Ertelendi (3–6 ay) |
| — | **FEAT-12:** GitHub Actions / MCP sunucusu entegrasyonu | Backlog |
| — | **CAP-1 Ext:** 200+ MB PBIX stres testi | Backlog |

---

## Önemli Notlar

### Bellek Yönetimi
\`pbixray\`, context manager protokolünü (\`with\` deyimi) desteklemez. Her zaman açık temizlik kullanın:
\`\`\`python
del model
gc.collect()
\`\`\`

### NaN İşleme
pbixray, boş/tanımsız alanlar (\`DataCategory\` gibi) için \`float('nan')\` döndürür. Bunlar güvenli bir şekilde şu şekilde dönüştürülmelidir:
\`\`\`python
cat_str = str(cat) if cat is not None else ""
# Filtre: "nan" dizileri göz ardı edilir
\`\`\`

### Sanal Ortam
Her zaman doğru venv'yi etkinleştirin:
\`\`\`bash
source /home/pbixapp/app/venv/bin/activate
python3 -c "import sys; print(sys.executable)"  # Doğrulama
\`\`\`

### Git İşlemleri
Git işlemleri \`pbixapp\` kullanıcısı tarafından çalıştırılmalıdır (SSH kimlik bilgileri orada depolanır):
\`\`\`bash
su - pbixapp
cd /home/pbixapp/app
git pull && git push
\`\`\`

---

## Katkıda Bulunma

Bu proje şu anda aktif geliştirme aşamasındadır. Pull request'ler aracılığıyla katkılar hoş karşılanır. Lütfen şunları sağlayın:

- Kod mevcut stili (FastAPI en iyi uygulamalar) takip eder
- Veritabanı değişiklikleri Alembic geçişlerini içerir
- Yeni özellikler temel regresyon testlerine sahiptir

---

## Lisans

[Belirtilecek — şu anda geliştirme aşamasında]

---

## İletişim & Destek

Ücretsiz faz sırasında sorular veya geri bildirim için:
- **GitHub Issues:** [Bu depo](https://github.com/SHapeloglu/pbix-diagnostic/issues)

---

**Son Güncelleme:** Oturum 13 (2026-08-28)  
**Bakımcı:** Selim Hape Oğlu
