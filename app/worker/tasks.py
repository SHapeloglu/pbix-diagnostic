import gc, os
from datetime import datetime
from app.worker.celery_app import celery_app
from app.analyzer.pbix_parser import parse_pbix

# Sync DB işlemleri için psycopg2 kullanıyoruz (Celery sync context)
import psycopg2
from app.core.config import settings
from app.utils.emails import send_email

def get_sync_conn():
    # asyncpg URL'ini psycopg2 formatına çevir
    url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(url)

@celery_app.task(bind=True, max_retries=2)
def analyze_pbix_task(self, job_id: str, tenant_id: str, file_path: str):
    conn = get_sync_conn()
    cur = conn.cursor()
    # DUZELTME: dosya silme islemi artik finally'de degil, sadece
    # basari veya KESIN (retry hakki bitmis) hata durumunda yapiliyor.
    # Eskiden finally her zaman calisip dosyayi sildigi icin, self.retry()
    # cagirildiginda bir sonraki deneme FileNotFoundError ile aninda
    # cokup retry mekanizmasini fiilen iscilevsiz birakiyordu.
    should_delete_file = False
    try:
        # Job'ı processing'e al
        cur.execute("UPDATE jobs SET status='processing', started_at=%s WHERE id=%s",
                    (datetime.utcnow(), job_id))
        conn.commit()

        # Analiz çalıştır
        result = parse_pbix(file_path)

        # Genel skor hesapla
        score_overall = int((
            result["scores"]["model"] +
            result["scores"]["dax"] +
            result["scores"]["visuals"] +
            result["scores"]["size"]
        ) / 4)

        # Sonucu kaydet
        import json, math

        def sanitize(obj):
            if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
                return None
            if isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [sanitize(i) for i in obj]
            return obj

        result = sanitize(result)
        cur.execute("""
            INSERT INTO analysis_results
            (id, job_id, tenant_id, score_overall, score_model, score_dax, score_visuals, score_size, result_json)
            VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            job_id, tenant_id, score_overall,
            result["scores"]["model"], result["scores"]["dax"],
            result["scores"]["visuals"], result["scores"]["size"],
            json.dumps(result)
        ))

        # Job'ı tamamlandı olarak işaretle
        cur.execute("UPDATE jobs SET status='completed', completed_at=%s WHERE id=%s",
                    (datetime.utcnow(), job_id))
        conn.commit()
        should_delete_file = True
        
        # Kullanıcıya email gönder (eğer user_id varsa)
        try:
            # User email'i al
            cur.execute("SELECT u.email FROM users u WHERE u.id = (SELECT user_id FROM jobs WHERE id=%s)", (job_id,))
            user_row = cur.fetchone()
            if user_row and user_row[0]:
                user_email = user_row[0]
                scores = result["scores"]
                context = {
                    "filename": result.get("filename", "Your file"),
                    "scores": scores,
                    "results_url": f"https://pbixdia.powerbi.com.tr/results/{job_id}"
                }
                send_email(
                    to_email=user_email,
                    subject="Your PBIX Analysis is Complete",
                    template_name="analysis_complete",
                    context=context
                )
        except Exception as e:
            # Email gönderme hatası analiz'i kırmasın
            import logging
            logging.error(f"Failed to send completion email for job {job_id}: {e}")

    except Exception as exc:
        conn.rollback()
        cur.execute("UPDATE jobs SET status='failed', error_message=%s WHERE id=%s",
                    (str(exc)[:500], job_id))
        conn.commit()

        if self.request.retries >= self.max_retries:
            # Retry hakki bitti -- artik dosyayi silmek guvenli.
            should_delete_file = True
            cur.close()
            conn.close()
            if should_delete_file and os.path.exists(file_path):
                os.remove(file_path)
            gc.collect()
            raise

        # Tekrar denenecek -- dosyaya DOKUNMA, yoksa bir sonraki
        # deneme FileNotFoundError ile aninda coker.
        cur.close()
        conn.close()
        gc.collect()
        raise self.retry(exc=exc, countdown=10)

    cur.close()
    conn.close()
    if should_delete_file and os.path.exists(file_path):
        os.remove(file_path)
    gc.collect()
