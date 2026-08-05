#!/bin/bash
# ============================================================
# PBIX Diagnostic Tool — Contabo Deploy Script
# Ubuntu 24.04 | Kullanici: pbixapp | Dizin: /home/pbixapp/app
# ============================================================
set -e

APP_DIR="/home/pbixapp/app"
VENV="$APP_DIR/venv"

echo "==> Virtualenv aktif ediliyor..."
source $VENV/bin/activate

echo "==> Pip paketleri kuruluyor..."
pip install -r $APP_DIR/requirements.txt

echo "==> DB migration uygulaniyor..."
cd $APP_DIR
alembic upgrade head

echo "==> Servisler yeniden baslatiliyor..."
sudo systemctl restart pbixapp
sudo systemctl restart pbixworker

echo "==> Durum kontrolu..."
sudo systemctl status pbixapp --no-pager
sudo systemctl status pbixworker --no-pager

echo "==> Deploy tamamlandi!"
