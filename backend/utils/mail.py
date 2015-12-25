# -*- coding: utf-8 -*-
import conf
import smtplib
import socket
import logbook
from collections import namedtuple
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email.header import Header
from email import encoders


class SendEmailError(Exception):
    """ Exception, raised in case send is failed.
    """


def send_email(email, subject, body, from_addr, cc=None, attachments=None, timeout=None):
    """ Sends email, returns True on success

    If called in test environment (conf.test == True) it just adds message to ``outbox`` list.
    """
    if conf.test:
        return _tests_send_email(email, subject, from_addr, body, attachments, cc)

    emails = [email] if isinstance(email, str) else list(email)
    if cc:
        if isinstance(cc, str):
            emails.append(cc)
        else:
            emails.extend(cc)
    test_emails = list(filter(lambda mail: conf.test_email_server.address_pattern in mail, emails))
    if test_emails:
        config = conf.test_email_server
        logbook.debug("Use test server for email sending")
    else:
        config = conf.email_server
    server_host = config.host
    user = config.user
    password = config.password
    ssl = config.ssl
    debug = config.debug
    port = config.port
    starttls = config.starttls
    from_addr = from_addr or conf.provider.noreply

    return _smtp_send_email(email, subject, from_addr, body, server_host, port, user, password, cc=cc,
                            attachments=attachments, timeout=timeout, ssl=ssl, debug=debug, starttls=starttls)


def verify_black_list(email):
    for black_listed_pattern in conf.email_server.black_list:
        if black_listed_pattern in email:
            logbook.info("Sending message to {} skipped, because of blacklist pattern: {}", email, black_listed_pattern)
            return True
    return False


def _smtp_send_email(email, subject, from_addr, body, server_host, port=None, user=None, password=None,
                     cc=None, attachments=None, timeout=None, ssl=False, debug=False, starttls=False):
    msg = MIMEMultipart()

    if not isinstance(email, (list, tuple)):
        email = [email]

    if cc and not isinstance(cc, (list, tuple)):
        cc = [cc]

    to_emails = [e for e in email if not verify_black_list(e)]
    cc_emails = [e for e in (cc or []) if not verify_black_list(e)]
    if not to_emails and not cc_emails:
        return

    msg['To'] = ';'.join(to_emails)
    if cc_emails:
        msg['CC'] = ';'.join(cc_emails)
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['Date'] = formatdate(localtime=True)
    msg.attach(MIMEText(body, _charset="utf-8"))
    for name, data in attachments or []:
        part = MIMEBase('application', "octet-stream")
        part.set_payload(data)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment', filename=(Header(name, 'utf-8').encode()))
        msg.attach(part)

    mail_description = "to '{}' (cc: '{}') from '{}' with subject '{}'".format(
        msg['To'], ",".join(cc_emails or []), from_addr, subject)
    logbook.debug("Try to send email {}", mail_description)

    try:
        smtp_class = smtplib.SMTP_SSL if ssl else smtplib.SMTP
        s = smtp_class(server_host, port=port, timeout=timeout or socket._GLOBAL_DEFAULT_TIMEOUT)
        if starttls:
            s.starttls()
        if debug:
            s.set_debuglevel(1)
        if user and password:
            s.login(user, password)
        emails = to_emails + cc_emails
        s.sendmail(from_addr, emails, msg.as_string())
        s.quit()
        logbook.info("Sent email {}", mail_description)
    except (smtplib.SMTPConnectError, smtplib.SMTPException, IOError) as e:
        logbook.warning("Sending email failed {}: {}", mail_description, e)
        raise SendEmailError(e)


def _tests_send_email(email, subject, from_addr, body, attachments=None, cc=None):
    msg = Message(email, subject, from_addr, body, attachments or [], cc or [])
    logbook.debug("Send test email to {} (cc: {}) with subject {} from: {}", email, cc, subject, from_addr)
    outbox.append(msg)

# Used only in tests
Message = namedtuple("Message", "to subject from_addr body attachments cc")
outbox = []
