import conf
import errors
from api import get, post, delete, put, AdminApi, API_ALL, API_CABINET, request_api_type
from model import News, Customer, MessageTemplate
from model import display, autocommit
from api.admin.role import TokenManager, TokenId
from api.check_params import check_params
from api.validator import String, ModelId, IntRange, Bool, Date, CustomerTokenId, StringWithLimits, List, SortFields
from task.mail import send_email
from utils.i18n import preferred_language

NewsIdExpand = ModelId(News, errors.NewsNotFound)


class GeneralTokenId:
    def __call__(self, value):
        res = False
        exception = None
        for validator in [TokenId(), CustomerTokenId()]:
            try:
                validator(value)
            except (errors.UserInvalidToken, errors.CustomerInvalidToken) as e:
                res = not res
                exception = e

        if not res:
            raise exception


class NewsApi(AdminApi):
    @post('news/')
    @check_params(
        token=TokenManager,
        subject=StringWithLimits(max_length=78),
        body=String
    )
    @autocommit
    def create_news(self, subject, body):
        """
        Creates news

        :param subject: News' subject
        :param body: News' body
        :return dict news_info: News' info

        **Example**::

            {"news_info":
                {"news_id": 1,
                 "subject": "test subject",
                 "body": "test body",
                 "deleted": None,
                 "published": None
                }
            }

        """
        news = News.create_news(subject, body)
        return {"news_info": display(news)}

    @get('news/', api_type=API_ALL)
    @check_params(
        all_parameters=True,
        token=GeneralTokenId,
        subject=String,
        body=String,
        published=Bool,
        deleted_before=Date(), deleted_after=Date(),
        published_before=Date(), published_after=Date(),
        visible=Bool,
        page=IntRange(1),
        sort=List(SortFields(News)),
        limit=IntRange(1, conf.api.pagination.limit)
    )
    def list(self, all_parameters, subject=None, body=None, visible=True, published=None,
             deleted_before=None, deleted_after=None,
             published_before=None, published_after=None,
             page=1, sort=None, limit=conf.api.pagination.limit):
        """
        Returns news list

        :param subject: news' subject
        :param body: news' body
        :param page: page number
        :param visible: are deleted and not published news visible for user
        :param published: filter by publishing date
        :param limit: number of news per page
        :param str or List sort: Field name or list of field names which is used for sorting.
                                 Ascending ordering is default.
                                 For descending ordering use "-" before.
        :return list news_list: list of news

        **Example**::

            {
                "news_list": {
                    "per_page": 100,
                    "total": 1,
                    "limit": 200,
                    "offset": 0
                    "items": [
                    {
                        "news_id": 1,
                        "subject": "test subject",
                        "body": "test body",
                        "deleted": None,
                        "published": None
                    }]
                }
            }
        """
        # noinspection PyUnresolvedReferences
        all_parameters.setdefault("limit", limit)
        # noinspection PyUnresolvedReferences
        all_parameters.setdefault("page", page)
        exact = None
        if request_api_type() == API_CABINET:
            all_parameters['deleted'] = None
            exact = ['deleted']
            all_parameters['published'] = ''

        else:
            if visible:
                all_parameters['deleted'] = None
                exact = ['deleted']
            if published:
                all_parameters['published'] = ''

        all_parameters.pop('visible', None)
        query = News.api_filter(all_parameters, exact=exact)
        return {"news_list": self.paginated_list(query)}

    @put('news/<news>/')
    @check_params(
        all_parameters=True,
        token=TokenManager,
        news=NewsIdExpand,
        subject=StringWithLimits(max_length=78),
        body=String
    )
    @autocommit
    def update_news(self, news, all_parameters, subject=None, body=None):
        """
        Updates news with specified subject and body

        :param news: News' id
        :param subject: subject to update
        :param body: body to update
        :return dict news_info: News' info

        **Example**::

            {"news_info":
                {"news_id": 1,
                 "subject": "test subject",
                 "body": "test body",
                 "deleted": None,
                 "published": None
                }
            }

        """
        if news.deleted:
            raise errors.RemovedNews()
        all_parameters.pop('news', None)
        news.update(all_parameters)
        return {"news_info": display(news)}

    @delete('news/<news>/')
    @check_params(
        token=TokenManager,
        news=NewsIdExpand
    )
    @autocommit
    def delete_news(self, news):
        """
        Deletes news with specified id

        :param news: News' id
        :return: None
        """
        if not news.mark_removed():
            raise errors.RemovedNews()
        return {}

    @staticmethod
    def send_email_with_news(subject, body):
        if subject.startswith(conf.devel.test_prefix):
            return
        customers = Customer.news_subscribers()
        subject, body = MessageTemplate.get_rendered_message(MessageTemplate.NEWS,
                                                             language=preferred_language(),
                                                             news_subject=subject, news_body=body)
        for customer in customers:
            send_email.delay(customer.subscription_info()['news']['email'], subject, body)

    @post('news/<news>/')
    @check_params(
        token=TokenManager,
        news=NewsIdExpand,
        publish=Bool()
    )
    @autocommit
    def publish(self, news, publish):
        """
        Publishes and unpublishes news with specified id

        :param news: News' id
        :param Bool publish: what to do with news - publish or unpublish
        :return dict news_info: News' info

        **Example**::

            {"news_info":
                {"news_id": 1,
                 "subject": "test subject",
                 "body": "test body",
                 "deleted": None,
                 "published": 2015-06-15T16:24:47
                }
            }
        """
        if news.deleted:
            raise errors.RemovedNews()
        news.publish(publish)
        if publish:
            self.send_email_with_news(news.subject, news.body)
        return {"news_info": display(news)}




