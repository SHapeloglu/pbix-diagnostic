# Session Geçmişi

## Session 12 (2026-08-16)

### Başlangıç
- Skor anomalisi araştırması (100/100/100/100 vs beklenen 80/100/100/90)

### Yapılanlar

**Anomali Investigation & Fix**
1. **Root Cause**: FEAT-11 _analyze_formatting() fonksiyonunda float(nan).lower() exception
   - pbixray tmschema_columns DataCategory alanı NaN döndürüyor
   - `cat.lower()` direktif → "float object has no attribute 'lower'" hatası
   - Exception try-except bloğunda yutulup parse_error'a yazılıyor

2. **Bulgu**: Terminal vs Worker venv farklı
   - Terminal: /opt/fretflow/venv (başka proje, pbixray yok)
   - Worker: /home/pbixapp/app/venv (doğru)
   - Worker bytecode cache eski kodu tutuyordu

3. **Fix (e4ca6b6)**:
   - _analyze_formatting(): `cat_str = str(cat) if cat is not None else ""`
   - NaN → "nan" string olarak işlenip filter'leniyor
   - parse_error artık None
   - formatting_info düzgün doldurulu: 511 kolon, 7 category tipi

4. **Verification**:
   - Baseline PBIX (SatisSemantikModel.pbix, 181 MB):
     - Tables: 133 ✓
     - Columns: 1200 ✓
     - Relations: 66 (0 m2m, 2 bidirectional) ✓
     - Model size: 370.26 MB ✓
     - **SCORES: 80/100/100/90** ✓ (anomali çözüldü!)

### Commits
- e4ca6b6: bugfix: FEAT-11 fix float(nan).lower() in _analyze_formatting

### İlgili Görev
- BIZ-6 (Stripe) — sonraki
- BIZ-5 (Registration) — sonraki
- FEAT-12 (GitHub Action/MCP) — stratejik

### Sonuç
✓ Anomali root cause identifikasyonu: FEAT-11 NaN exception + venv cache
✓ Bug fix implemente ve verify edildi
✓ Baseline skorları doğru döndürüyor
✓ Worker restart bekleniyor

## Session 11 (2026-08-14)
[önceki session verileri — Session 11 dosyasına bakınız]
