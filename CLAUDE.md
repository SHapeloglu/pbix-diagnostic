# Claude'ın Session 9 Notları

1. **Baseline tutarsızlığı bulundu:** Test dosyası (SatisSemantikModel.pbix) Session 8'den 133/1200/66 değerlerine sahip olmuş (eski 128/1163/68). Bu, dosyanın güncellenmiş olduğunu veya sunucudaki parsing mantığında hafif değişim olduğunu gösteriyor. Skorlar korunmuş (80/100/100/90), bu yüzden önemli değil, ama gözlemlenmiş.

2. **FEAT-7 başında hata yaptık:** RelyOnReferentialIntegrity numpy/pandas tipi (0/1 vs Python False) olduğu için `is False` identity check'i çalışmadı. Sonra hata-düzeltme patch'i uyguladık ama sonuçta özelliği iptal ettik (DirectQuery-only, Import-mode modellerde anlamsız gürültü).

3. **FEAT-8 başında expression preview kesintisi sorunu var:** İlk testte 66 duplicate tespit edildi ama tam expression'a geçince 0 oldu. Preview (200 karakter) farklı measure'ların ilk 200 karakterinin aynı olduğu, tam expression'ın ise farklı olduğu anlamına geliyordu. Düzeltme: _expression_full saklama, bu da çalışırken test dosyasında gerçekten dup yok çıktı.

4. **FEAT-9 / FEAT-10 zaten sunucuda:** Sunucu HEAD `3fc359c`, bu oturum başında `27cfec4`'te başlamıştık. Araya FEAT-8, FEAT-9, FEAT-10 commit'leri sıralanmış. FEAT-9/10 önceki oturumlara ait, v7.zip'a dahil olmamış.

5. **Sunucuda venv sorunları:** başta yanlış venv aktif idi (`/opt/fretflow/venv`, pbixray yok). Doğrusu `/home/pbixapp/app/venv`. Hızlıca düzeltildi.

**Sonra yapılacak:**
- FEAT-11 kontrol et: pbixray'in yeni versiyonu DataCategory expose ediyor mu?
- FEAT-12 (GitHub Action / MCP) stratejik karar.
