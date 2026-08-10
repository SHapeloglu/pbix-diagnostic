# TASKS.md — Power BI SaaS Diagnostic Tool

Tamamlanan `[ ]` → `[x]` olarak işaretle.

---

## Tamamlananlar (2026-08-08 itibarıyla)

- [x] Sunucu hazırlığı (pbixapp kullanıcısı, dizin, Redis, PostgreSQL)
- [x] Python venv + tüm pip paketleri
- [x] PostgreSQL pbixuser/pbixdb + migration (4 tablo)
- [x] FastAPI auth sistemi (register/login/me)
- [x] PBIX upload (stream, chunk-by-chunk)
- [x] Celery worker (Redis broker, concurrency=1)
- [x] pbixray ile gerçek DataModel analizi
- [x] NaN sanitize fix
- [x] Celery retry/dosya-silme bug fix
- [x] Systemd servisleri (pbixapp + pbixworker, otomatik başlama)
- [x] Uçtan uca test: 135 MB PBIX, 8.8 sn, 92/100 skor
- [x] GitHub push: https://github.com/SHapeloglu/pbix-diagnostic
- [x] **DAX-1** — `dax_analyzer.py` expression `str()` cast fix, commit 2012ef1
- [x] **SEC-1** — Systemd servislerinde `User=pbixapp`, `chown` tamamlandı
- [x] **SEC-2** — `.env`'de `ACCESS_TOKEN_EXPIRE_MINUTES=1440` yapıldı
- [x] **NGINX-1** — Nginx konfigürasyonu: `pbixdia.powerbi.com.tr`, port 8004
- [x] **NGINX-2** — SSL sertifikası: Let's Encrypt, certbot, geçerlilik 2026-11-04
- [x] **LIB-1** — pbixray 0.10.0 → 0.15.4 upgrade, regresyon testi geçti (128 tablo/1163 kolon/68 ilişki korundu), commit `3a471b5`, push `2012ef1..3a471b5`
- [x] **FEAT-1** — RLS analizi eklendi (`model.rls` → `rls_enabled`, `rls_roles`), commit `041fad5`
- [x] **FEAT-2** — KPI analizi eklendi (`model.tmschema_kpis` → `kpis`), commit `041fad5`, push `3a471b5..041fad5`
- [x] **GIT-1** — Sunucuda HTTPS push credential sorunu çözüldü: `credential.helper store` + PAT ile interaktif `su - pbixapp` oturumunda bir kerelik giriş yapıldı, kalıcı olarak kayıtlı

---

## Kalan Görevler

### Öncelik 2 — Kapasite Ölçümü

- [x] **CAP-1 (tamamlandı)** — Gerçek müşteri verisiyle (136 MB, sentetik değil) ölçüm yapıldı:
  - Süre: 11.89s
  - Peak RSS: 412.3 MB (dosya boyutunun ~3x'i)
  - Model boyutu (deserialize): 284.46 MB
  - Sunucu: 7.8 GB RAM, ölçüm anında 4.5 GB available, swap 1.9 GB kullanımda (dikkat: paylaşımlı VPS'te diğer servislerden kaynaklanan bellek baskısı olabilir, izlenmeli)
  - 200 MB+ için ekstrapolasyon (doğrulanmadı): ~600 MB peak RSS; 500 MB dosya için ~1.5 GB peak RSS tahmini
  - **Açık kalan:** Gerçek 200 MB+ dosya ile doğrulama henüz yapılmadı — sentetik büyütme (Power BI'da veri çoğaltma) ya da gerçek büyük müşteri dosyası bulunduğunda tekrar test edilecek

### Öncelik 3 — Açık İş Kararları

- [ ] **BIZ-1** Fiyatlandırma modeli seç
  Önerilen yapı:
  | Plan | Analiz/ay | Fiyat |
  |------|-----------|-------|
  | Free | 3 | Ücretsiz |
  | Pro | 50 | ~$19/ay |
  | Business | Sınırsız | ~$49/ay |
  `tenants.plan` ve `tenants.quota_monthly` alanları hazır, kod yazılacak.

- [ ] **BIZ-2** Analiz retention süresi belirle
  Önerilen: Free → 30 gün, Pro → 90 gün, Business → 1 yıl.
  Otomatik temizleme için Celery beat görevi yazılacak.

---

## Tamamlanma Durumu

| Phase | Durum |
|-------|-------|
| Sunucu hazırlığı | ✅ Tamamlandı |
| Kod tabanı | ✅ Tamamlandı |
| Uçtan uca test | ✅ Tamamlandı |
| DAX fix | ✅ Tamamlandı |
| Production güvenliği (SEC-1/2) | ✅ Tamamlandı |
| Nginx + SSL | ✅ Tamamlandı |
| pbixray upgrade (LIB-1) | ✅ Tamamlandı |
| RLS + KPI analizi (FEAT-1/2) | ✅ Tamamlandı |
| Git credential sorunu (GIT-1) | ✅ Tamamlandı |
| Kapasite ölçümü (CAP-1) | ✅ Tamamlandı — iki gerçek dosya (136 MB + 180 MB), 300 MB sınır pratik olarak doğrulandı |
| Fiyatlandırma/retention | ⏳ Karar bekleniyor |
