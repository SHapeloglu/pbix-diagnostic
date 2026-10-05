# Backlog (Düşük Öncelik / Stratejik)

Bu dosya `TASKS.md`'deki aktif "Açık Görevler" listesinden ayrı olarak,
şu an sıraya girmemiş ama gelecekte değerlendirilecek maddeleri tutar.

| # | Kategori | Görev | Durum / Not |
|---|----------|-------|-------------|
| BIZ-6 | Business | Stripe payment integration | Ertelendi (3-6 ay) — ürün olgunlaşma bekliyor, şu an tamamen ücretsiz |
| FEAT-12 | Dev Tools | GitHub Action / MCP server | Stratejik, talep bekleniyor |
| FEAT-4-ext | Analyzer | Ek TMSCHEMA alanları (perspectives/translations genişletme) | Düşük öncelik, talep yok |
| CAP-1-ext | Testing | 200 MB+ PBIX ile RAM kapasite testi | Kısmen tamamlandı (~2.8-3x RAM çarpanı bulundu), tam test bekliyor |

## Ertelenmiş Kararların Gerekçeleri

- **BIZ-6 (Stripe)**: Ürün şu an feedback toplama fazında, ödeme gerektirmiyor.
  Kayıt sistemi (BIZ-5) ve admin panel (BIZ-7) tamamlanmadan ödeme entegrasyonu
  yapılırsa tenant/subscription eşleştirmesi sonradan yeniden yapılmak zorunda kalır.
- **FEAT-12**: Kullanıcı tabanı küçükken dev-tool yatırımı erken.
