import logbook
import conf
from task.main import celery
from utils import mail, exception_to_sentry


@celery.task(ignore_result=True,
             bind=True,
             max_retries=conf.email_server.max_retries,
             default_retry_delay=conf.email_server.retry_delay,
             rate_limit=conf.email_server.rate_limit)
def send_email(self, send_to, subject, body, from_addr=None, cc=None, attachments=None):
    try:
        mail.send_email(send_to, subject, body, from_addr, cc=cc,
                        attachments=attachments, timeout=conf.email_server.timeout)
    except Exception as e:
        if self.request.retries >= self.max_retries - 1:
            exception_to_sentry()
        else:
            logbook.warning("Exception during sending email to {} with subject {}: {} from: {}",
                            send_to, subject, e, from_addr, exc_info=True)
            send_email.retry(exc=e)
