# Broker settings.
BROKER_URL = 'amqp://innodev:innodev@localhost:5672/spiders'
CELERY_RESULT_BACKEND = 'amqp://innodev:innodev@localhost:5672/results'


# List of modules to import when celery starts.
CELERY_IMPORTS = ('product_spiders.tasks',)

ADMINS = [
    ('Emiliano M. Rudenick', 'emr.frei@gmail.com'),
]

CELERY_SEND_TASK_ERROR_EMAILS = True
SERVER_EMAIL = 'reporting@competitormonitor.com'
EMAIL_HOST = 'smtp.sparkpostmail.com'
EMAIL_HOST_USER = 'SMTP_Injection'
EMAIL_HOST_PASSWORD = '3eef967340aa0546a6eb2f722bea5d922ad63d6e'
EMAIL_PORT = 587
