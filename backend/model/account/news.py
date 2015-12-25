import errors

from model import db, AccountDb, duplicate_handle
from sqlalchemy import Column
from arrow import utcnow


class News(db.Model, AccountDb):
    id_field = "news_id"
    unique_field = "subject"

    news_id = Column(db.Integer, primary_key=True)
    subject = Column(db.String(78))
    body = Column(db.Text)
    published = Column(db.DateTime())
    deleted = Column(db.DateTime())

    display_fields = frozenset(['news_id', 'subject', 'body', 'published', 'deleted'])

    @classmethod
    @duplicate_handle(errors.NewsAlreadyExist)
    def create_news(cls, subject, body):
        news = cls()
        news.subject = subject
        news.body = body
        news.published = None
        news.deleted = None

        db.session.add(news)
        return news

    def update(self, new_parameters):
        if self.published:
            new_parameters['published'] = utcnow().datetime
        super().update(new_parameters)

    def publish(self, publish):
        self.published = utcnow().datetime if publish else None
