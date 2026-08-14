# TASKS.md

## Tamamlanan Görevler

| # | Görev | Commit | Tarih |
|---|---|---|---|
| SEC-1/2 | Systemd pbixapp kullanıcısı | — | 2026-08-05 |
| NGINX-1/2 | SSL + Nginx reverse proxy | — | 2026-08-05 |
| LIB-1 | pbixray 0.10.0 → 0.15.4 | `3a471b5` | 2026-08-08 |
| FEAT-1/DAX-1 | str() cast fix | `2012ef1` | 2026-08-08 |
| FEAT-2 | RLS + KPI analizi | `041fad5` | 2026-08-09 |
| FEAT-3 | Calculation Groups + M Parameters | `905615a` | 2026-08-10 |
| CAP-1 | Kapasite doğrulama | — | 2026-08-10 |
| FEAT-5 | VertiPaq kolon istatistikleri | — | 2026-08-11 |
| FEAT-6 | DAX measure → unreferenced kolon | `d426b68` | 2026-08-11 |
| BIZ-1 | Fiyatlandırma + quota kontrolü | `39a22cf` | 2026-08-12 |
| BIZ-2 | 30 gün retention + cron cleanup | `2f26296` | 2026-08-12 |
| FEAT-4 | Perspectives + translations | `27cfec4` | 2026-08-12 |
| FEAT-8 | Duplicate measure detection | `0a42a0f` | 2026-08-14 |
| FEAT-9 | Thin report / live-connection error | `a3a7b9e` | 2026-08-13 |
| FEAT-10 | Naming conventions checks | `3fc359c` | 2026-08-13 |
| BIZ-3 | Email notifications | `af802f1` | 2026-08-14 |

## Açık Görevler (rakip araştırması sonrası eklendi)

| # | Görev | Öncelik | Durum |
|---|---|---|---|
| ~~FEAT-7~~ | ~~Referential integrity~~ | ~~1~~ | **REDDEDİLDİ** — DirectQuery-only, Import-mode gürültüsü |
| ~~FEAT-11~~ | ~~Formatting kontrolü~~ | ~~5~~ | **ERTELENDİ** — pbixray 0.15.4 DataCategory expose etmiyor |
| FEAT-12 | GitHub Action / MCP server | 6 | Uzun vadeli, stratejik karar bekleniyor |
| BIZ-5 | User registration sistemi | 2 | Yapılmadı |
| BIZ-6 | Stripe payment integration | 1 | Yapılmadı |
| BIZ-7 | Admin panel (tenant yönetimi) | 2 | Yapılmadı |

## Olası Sonraki Adımlar (talep gelmeden yapılmaz)

- Email notifications templates (quota warning, etc.)
- Kullanıcı kayıt/davet sistemi
- Ödeme entegrasyonu (Stripe)
- Admin paneli (tenant yönetimi)
- BACKUP-1 / MONITOR-1
