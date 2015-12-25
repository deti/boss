# -*- coding: utf-8 -*-
import posixpath
import requests
import time
import logbook
from dateutil import parser
from dateutil.tz import tzlocal
from pytz import utc
import configs


class MailTrapError(Exception):
    pass


class MailTrapApi(object):
    def __init__(self, token, default_mailbox=None, show_all_messages=False, verbose=False):
        self.token = token
        self.url = "http://mailtrap.io/"
        self.url_api = posixpath.join(self.url, "api/v1/inboxes")
        self._mailboxes = {}
        self.default_mailbox = default_mailbox if default_mailbox else 'boss'
        self._session = requests.Session()
        self._session.headers = {"Api-Token": self.token}
        self.show_all_messages = show_all_messages
        self.verbose = verbose

    @classmethod
    def create_default(cls):
        return cls(configs.mailtrap.token)

    def _get(self, resource, **kwargs):
        return self._request_api("GET", resource, params=kwargs)

    def _post(self, resource, params=None, data=None):
        return self._request_api("POST", resource, params, data)

    def _delete(self, resource, **kwargs):
        return self._request_api("DELETE", resource, params=kwargs,
                                 expected_status_codes=[requests.codes.ok, requests.codes.not_found])

    def _request_api(self, method, resource, params=None, data=None, parse_json=True, expected_status_codes=None):
        if resource.startswith("http"):
            url = resource
        else:
            url = posixpath.join(self.url_api, resource)

        retry = 0
        max_retry = 4
        response = None
        while retry < max_retry:
            try:
                response = self._session.request(method, url, params=params, data=data)
                break
            except requests.RequestException as e:
                logbook.info("Mailtrap error for {} {} {}: {}", method, url, params, e)
                retry += 1
                if retry >= max_retry:
                    raise
                time.sleep(1)

        if expected_status_codes is None:
            expected_status_codes = [requests.codes.ok]

        if isinstance(expected_status_codes, int):
            expected_status_codes = [expected_status_codes]

        req = "%s %s" % (response.request.method, response.url)

        if response.status_code not in expected_status_codes:
            msg = "Mailtrap: %s, expected statuses %s, but returned: %s" % \
                  (req, expected_status_codes, response.status_code)
            raise ValueError(msg)

        if not parse_json:
            return response.text

        try:
            j = response.json()
            if self.verbose:
                js = str(j)[:500]
                logbook.debug("Mailtrap: {}, status: {}, response: {}", req, response.status_code, js)
        except ValueError:
            msg = "Mailtrap: %s, status: %s, response: %s" % (req, response.status_code, response.text)
            logbook.warning(msg)
            if response.status_code == requests.codes.ok:
                raise ValueError(msg)
            j = {}
        return j

    def get_mailboxes(self, force=False):
        if not self._mailboxes or force:
            mailboxes = self._get("")
            self._mailboxes = {m[u"name"]: m for m in mailboxes}
        return self._mailboxes

    def _mailbox_url(self, mailbox):
        mailboxes = self.get_mailboxes()
        return "%s/messages" % mailboxes[mailbox or self.default_mailbox]["id"]

    @staticmethod
    def to_utc(dt):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tzlocal())
        return utc.normalize(dt)

    @staticmethod
    def short_message_str(message):
        return u"to: '%(to_email)s' sent: '%(sent_at)s' subject: '%(subject)s'" % message

    @staticmethod
    def short_messages_str(messages, separator=u"\n"):
        return separator.join(MailTrapApi.short_message_str(m) for m in messages)

    def get_messages(self, mailbox=None, created_after=None, search=None, prefix=None):
        messages = self._get(self._mailbox_url(mailbox), search=search)
        total = len(messages)

        if created_after:
            created_after = self.to_utc(created_after)
            messages = [m for m in messages if parser.parse(m["created_at"]) >= created_after]
        if prefix:
            messages = [m for m in messages if m["to_email"].startswith(prefix)]

        logbook.debug("Searching emails in mailbox: {}, created_after: {}, search: {}, prefix: {}. "
                      "Total messages in box: {}, found {} messages:\n{}",
                      mailbox or self.default_mailbox, created_after, search, prefix, total, len(messages),
                      self.short_messages_str(messages))

        if not messages and (search or created_after) and self.show_all_messages:
            # no messages found... try get all messages without filters
            all_messages = self._get(self._mailbox_url(mailbox))
            logbook.debug("Inbox {} has %d messages:\n{}", mailbox or self.default_mailbox, len(all_messages),
                          self.short_messages_str(all_messages))

        return messages

    def get_count(self, mailbox=None):
        return len(self.get_messages(mailbox))

    def get_message(self, message_id, mailbox=None):
        message = self._get(posixpath.join(self._mailbox_url(mailbox), str(message_id)))
        if "error" in message:
            raise MailTrapError(message["error"]["text"])
        return message

    def get_attachments(self, message_id, mailbox=None):
        attachments = self._get(posixpath.join(self._mailbox_url(mailbox), str(message_id), "attachments"))
        if "error" in attachments:
            raise MailTrapError(attachments["error"]["text"])
        return self._request_api("GET", attachments[0]["download_url"], parse_json=False)

    def cleanup(self, mailbox=None, created_after=None, search=None, prefix=None):
        try:
            messages = self.get_messages(mailbox, created_after, search, prefix)
        except Exception as e:
            logbook.error("Failed to cleanup mailtrap: {}", e)
            return
        logbook.debug("Deleting {} messages by filter {}".format(len(messages), search))
        for message in messages:
            logbook.debug("Mailtrap deleting: {}", self.short_message_str(message))
            self._delete(posixpath.join(self._mailbox_url(mailbox), str(message["id"])))
            #time.sleep(0.1)  # TODO remove emails in single request

    def delete(self, message_id, mailbox=None):
        self._delete(posixpath.join(self._mailbox_url(mailbox), str(message_id)))
