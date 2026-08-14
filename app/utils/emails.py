import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
import logging

logger = logging.getLogger(__name__)

def send_email(to_email, subject, template_name, context):
    """
    Send email via Gmail SMTP
    """
    try:
        from app.config import EMAIL_FROM, GMAIL_APP_PASSWORD
        
        if not GMAIL_APP_PASSWORD:
            logger.warning(f"Email not sent (GMAIL_APP_PASSWORD not configured): {subject}")
            return False
        
        # Email templates
        templates = {
            "analysis_complete": """Hello,

Your PBIX file analysis is complete!

File: {{ filename }}
Model Score: {{ scores.model }}/100
DAX Complexity: {{ scores.dax }}/100
Visual Density: {{ scores.visuals }}/100
File Size: {{ scores.size }}/100

View results: {{ results_url }}

Thanks,
pbix-diagnostic Team
""",
            "quota_warning": """Hello,

Your quota is running low this month.

Used: {{ used }}/{{ limit }}

Upgrade to continue: {{ pricing_url }}

Thanks,
pbix-diagnostic Team
"""
        }
        
        if template_name not in templates:
            logger.error(f"Template not found: {template_name}")
            return False
        
        body = Template(templates[template_name]).render(**context)
        
        # Gmail SMTP
        smtp_server = smtplib.SMTP("smtp.gmail.com", 587)
        smtp_server.starttls()
        smtp_server.login(EMAIL_FROM, GMAIL_APP_PASSWORD)
        
        msg = MIMEMultipart()
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        smtp_server.send_message(msg)
        smtp_server.quit()
        
        logger.info(f"Email sent to {to_email}: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False
