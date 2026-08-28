# Session Geçmişi

## Session 11 (2026-08-14)

### Başlangıç
- Scoring anomalisi flagged (Session 10'den carry over)
- FEAT-11 ve FEAT-7 teknik sorun analizi

### Yapılanlar

**FEAT-11 (Formatting DataCategory) — TAMAMLANDI**
- Bulgu: pbixray 0.15.4 model.tmschema_columns DataCategory expose ediyor
- pbix_parser.py: tmschema_columns_records extraction eklendi
- model_analyzer.py: _analyze_formatting() → columns_with_datacategory
- Result key: result["model"]["formatting_info"]
- Skor: ETKILEMEZ (bilgi bulgusu)
- Baseline test: 80/100/100/90 → sonra 100/100/100/100 (anomali!)

**FEAT-7 (Referential Integrity) — TAMAMLANDI**
- Bulgu: model.relationships zaten RelyOnReferentialIntegrity alanı içeriyor
- Dar kapsamlı: DirectQuery bağlamı + RI=False olanları raporla
- model_analyzer.py: _analyze_referential_integrity() eklendi
- Result key: result["model"]["referential_integrity_info"]
- Skor: ETKILEMEZ (bilgi bulgusu)

### Commits
- 3f2c31b — FEAT-11 (Formatting)
- 0007c9a — docs: FEAT-11 session update
- 43a16cd — FEAT-7 (Referential Integrity)
- 57db057 — docs: FEAT-7 session update

### Skor Anomalisi UYARI
Önceki (Session 10):  model:80 / dax:100 / visuals:100 / size:90
Şu anki (Session 11): model:100 / dax:100 / visuals:100 / size:100

- Dosya değişmemiş: md5 c8cb5f6ed6c669d9fb1707bf312ca6b4
- Her iki test PBIX'i de 100/100/100/100 döndürüyor
- Potansiyel sebep: _calculate_scores() fonksiyonunda değişiklik (kontrol et)

### Baseline
- Dosya: SatisSemantikModel.pbix (181 MB)
- Yapı: 133 tablo / 1200 kolon / 66 ilişki
- Skorlar: ???? (anomali nedeniyle belirsiz)

## Session 10 (2026-08-14)

- BIZ-3 (Email Notifications) TAMAMLANDI
  - app/utils/emails.py (Gmail SMTP)
  - tasks.py hook
  - Commit: af802f1

## Önceki Sessions (1-9)

Detaylı TASKS.md'de — 16 özellik/iş tamamlanmış.
