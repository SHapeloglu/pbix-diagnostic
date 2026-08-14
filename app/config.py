
# Email Configuration
EMAIL_ENABLED = True
EMAIL_PROVIDER = "gmail"  # atau "sendgrid"
EMAIL_FROM = "pbix-diagnostic@gmail.com"
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
