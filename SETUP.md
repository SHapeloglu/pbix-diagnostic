# SETUP.md — Sunucuya Kurulum Adımları

## Ön Koşul
Phase 1 tamamlandı (TASKS.md). Sunucuda:
- Ubuntu 24.04, pbixapp kullanıcısı, /home/pbixapp/app dizini
- PostgreSQL, Redis, Nginx, Python 3.12, virtualenv kurulu

---

## 1. Dosyaları sunucuya kopyala

Yerel makineden:
```bash
scp -r ./pbix-diagnostic/* pbixapp@SUNUCU_IP:/home/pbixapp/app/
```

Ya da git kullan:
```bash
# Sunucuda
cd /home/pbixapp/app
git init && git remote add origin REPO_URL
git pull origin main
```

---

## 2. .env dosyasını oluştur

```bash
cp .env.example .env
nano .env
# DATABASE_URL, SECRET_KEY, UPLOAD_DIR değerlerini doldur
```

---

## 3. Pip paketlerini kur

```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

## 4. DB tablolarını oluştur

```bash
alembic upgrade head
# Başarılıysa: "Running upgrade -> xxxx, initial_tables"
```

---

## 5. Test çalıştır

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
# http://SUNUCU_IP:8000/docs açılmalı
```

---

## 6. Systemd servislerini kur

```bash
sudo cp pbixapp.service /etc/systemd/system/
sudo cp pbixworker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pbixapp pbixworker
sudo systemctl start pbixapp pbixworker
```

---

## 7. Nginx ayarla

```bash
# nginx.conf içinde ALAN_ADINIZI_YAZIN kısmını düzenle
sudo cp nginx.conf /etc/nginx/sites-available/pbixapp
sudo ln -s /etc/nginx/sites-available/pbixapp /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 8. SSL (alan adı varsa)

```bash
sudo certbot --nginx -d alan-adin.com
```

---

## Hızlı Test

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"tenant_name":"Test Firma","email":"admin@test.com","password":"test123"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"test123"}'
```
