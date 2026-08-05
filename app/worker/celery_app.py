from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "pbix_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Istanbul",
    enable_utc=True,
    # NOT: CELERY_WORKERS varsayilani (.env) 8'den 3'e dusuruldu.
    # Eski deger 8 vCPU/30 GB varsayimiyla hesaplanmisti; gercek sunucu
    # 4 cekirdek/8 GB. Sabit servis yuku (~1.4 GB) dusulunce ve
    # decompress edilen PBIX modeli disk-mmap (on_disk=True) ile RAM'e
    # tam alinmadigi icin 3 eszamanli worker guvenli bir baslangic
    # noktasi -- gercek 200 MB+ dosyalarla olcum sonrasi ayarlanmali.
    worker_concurrency=settings.CELERY_WORKERS,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
)
