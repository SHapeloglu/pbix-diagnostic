# Session Geçmişi

## Session 12 (2026-08-16)

### Başlangıç
- Skor anomalisi araştırması (100/100/100/100 vs beklenen 80/100/100/90)

### Yapılanlar

**Skor Anomalisi Root Cause & Fix**
1. **Investigation**: 
   - Terminal test ile baseline PBIX doğru skorlar döndürüyor (80/100/100/90)
   - Canlı API (100/100/100/100) anormallik gösteriyor
   - pbixray 0.15.4 ile her test aynı kodu çalıştırıyor

2. **Root Cause**: FEAT-11 _analyze_formatting() NaN exception
   - pbixray tmschema_columns DataCategory alanı float(nan) döndürüyor
   - Code: `if cat and cat.lower()` → exception
   - Exception try-except bloğunda yutulup parse_error'a yazılıyor
   - Sonrası fonksiyonlar (FEAT-7, naming_issues) kısmen atlanıyor

3. **Bulgu**: Venv karmaşası
   - Terminal: `/opt/fretflow/venv` (başka proje)
   - Worker: `/home/pbixapp/app/venv` (doğru)
   - Session başında `source /home/pbixapp/app/venv/bin/activate` kritik

4. **Fix (Commit e4ca6b6)**:
```python
   cat_str = str(cat) if cat is not None else ""
   if cat_str and cat_str.lower() not in ("none", "nan", ""):
```
   - float(nan) → "nan" string'e dönüştürülüyor
   - "nan" filter'leniyor
   - parse_error artık None
   - formatting_info doğru doldurulu: 511 kolon

5. **Baseline Verification** (SatisSemantikModel.pbix):
   - Tables: 133 ✓
   - Columns: 1200 ✓
   - Relations: 66 (m2m:0, bidirectional:2) ✓
   - Model size: 370.26 MB ✓
   - **SCORES: 80/100/100/90** ✓ (Anomali çözüldü!)

### Commits
- e4ca6b6: bugfix: FEAT-11 fix float(nan).lower() in _analyze_formatting

### Session Hızlı Özet
- ✓ Anomali root cause: pbixray NaN döndürüyor, `.lower()` patlıyor
- ✓ Fix: NaN → string, "nan" filter
- ✓ Baseline verification: 133t/1200c/66r → 80/100/100/90
- ✓ Worker restart + cache temizle

## Session 11 (2026-08-14)
FEAT-11 + FEAT-7 implementasyonu (skor anomalisi başladığı yer)

## Önceki Sessions (1-10)
16 özellik + 2 business task tamamlandı
