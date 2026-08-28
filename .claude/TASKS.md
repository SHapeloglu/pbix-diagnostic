# Tüm Görevler & Durum

## Tamamlanan (18 Task)

| # | Kategori | Görev | Commit | Tarih |
|---|----------|-------|--------|-------|
| SEC-1/2 | Infra | Systemd pbixapp user | — | 2026-08-05 |
| NGINX-1/2 | Infra | SSL + Nginx reverse proxy | — | 2026-08-05 |
| LIB-1 | Deps | pbixray 0.10.0 → 0.15.4 | 3a471b5 | 2026-08-08 |
| FEAT-1/DAX-1 | Analyzer | str() cast fix | 2012ef1 | 2026-08-08 |
| FEAT-2 | Analyzer | RLS + KPI analizi | 041fad5 | 2026-08-09 |
| FEAT-3 | Analyzer | Calculation Groups + M Parameters | 905615a | 2026-08-10 |
| CAP-1 | Testing | Kapasite doğrulama | — | 2026-08-10 |
| FEAT-5 | Analyzer | VertiPaq kolon istatistikleri | — | 2026-08-11 |
| FEAT-6 | Analyzer | DAX measure → unreferenced kolon | d426b68 | 2026-08-11 |
| BIZ-1 | Business | Fiyatlandırma + quota kontrolü | 39a22cf | 2026-08-12 |
| BIZ-2 | Business | 30 gün retention + cron cleanup | 2f26296 | 2026-08-12 |
| FEAT-4 | Analyzer | Perspectives + translations | 27cfec4 | 2026-08-12 |
| FEAT-8 | Analyzer | Duplicate measure detection | 0a42a0f | 2026-08-14 |
| FEAT-9 | Analyzer | Thin report / live-connection error | a3a7b9e | 2026-08-13 |
| FEAT-10 | Analyzer | Naming conventions checks | 3fc359c | 2026-08-13 |
| BIZ-3 | Business | Email notifications (Gmail SMTP) | af802f1 | 2026-08-14 |
| FEAT-11 | Analyzer | Formatting (DataCategory) | 3f2c31b | 2026-08-14 |
| FEAT-7 | Analyzer | Referential Integrity (DirectQuery) | 43a16cd | 2026-08-14 |

## Açık Görevler (Öncelik Sırası)

| # | Kategori | Görev | Öncelik | Durum |
|---|----------|-------|---------|-------|
| BIZ-6 | Business | Stripe payment integration | 1 | Tasarımda |
| BIZ-5 | Business | User registration sistemi | 2 | Tasarımda |
| BIZ-7 | Business | Admin panel (tenant yönetimi) | 2 | Tasarımda |
| FEAT-12 | Dev Tools | GitHub Action / MCP server | 6 | Stratejik |

## Bilinen Sorunlar

| Sorun | Durum | Not |
|-------|-------|-----|
| Skor Anomalisi | AÇIK | 80→100/90→100, sebep bilinmiyor, Session 11'de tespit |
| Scoring Logic | KONTROL GEREK | _calculate_scores() fonksiyonu audit edilmeli |

## Sonra Yapılacak (Sırasına göre)

1. Skor anomalisi araştırması (Session 12 başında) — URGENT
2. BIZ-6 Stripe (payment gateway)
3. BIZ-5 User registration (email invite + auth)
4. BIZ-7 Admin panel (tenant management)
5. FEAT-12 (stratejik karar — GitHub Action vs MCP)

## Business Model Kararı

- Ürün: Tamamen free (feedback phase)
- Stripe/Payments: 3-6 ay sonra (BIZ-6)
- Quota enforcement: Şu an disabled (BIZ-3 via 83ab595)
