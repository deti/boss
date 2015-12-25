import conf
import errors

from api.check_params import check_params
from api import get, post, delete, AdminApi
from api.validator import Choose, TokenId
from api.admin.role import TokenAdmin

AllCurrencies = Choose(list(conf.currency.all.keys()))
ActiveCurrencies = Choose(list(conf.currency.active))


class CurrencyApi(AdminApi):
    @staticmethod
    def _prepare_currency_description(code, description):
        return {"code": code, "currency": description["currency"], "decimal": description["decimal"]}

    @staticmethod
    def active_list():
        return {"currencies": [CurrencyApi._prepare_currency_description(c, conf.currency.all[c])
                               for c in conf.currency.active]}

    @get("currency/")
    @check_params(token=TokenId)
    def get_currency(self):
        """
        Returns list of currency

        :return list currency: List of currency descriptions

        **Example**::

            {
                "currencies": [
                    {
                        "code": "RUB",
                        "currency": "Russian rouble",
                        "decimal": 2
                    },
                        "code": "USD",
                        "currency": "United States dollar",
                        "decimal": 2
                    }
                ]
            }
        """
        return {"currencies": [self._prepare_currency_description(code, desc)
                               for code, desc in conf.currency.all.items()]}

    @get("currency/active/")
    @check_params(token=TokenId)
    def get_currency_active(self):
        """
        Return list of active currencies

        :return dict currency_info: Dictionary with descriptions of active currencies

        **Example**::

            {
                "currencies": [
                    {
                        "code": "RUB",
                        "currency": "Russian rouble",
                        "decimal": 2
                    },
                        "code": "USD",
                        "currency": "United States dollar",
                        "decimal": 2
                    }
                ]
            }

        """
        return self.active_list()

    @post("currency/")
    @check_params(token=TokenAdmin, currency=AllCurrencies)
    def add(self, code):
        """
        Add currency to list of available (NOT IMPLEMENTED)

        :param str code: Currency code
        :return dict currencies: List of active currencies

        **Example**::

            {
                "currencies": [
                    {
                        "code": "RUB",
                        "currency": "Russian rouble",
                        "decimal": 2
                    },
                        "code": "USD",
                        "currency": "United States dollar",
                        "decimal": 2
                    }
                ]
            }
        """
        raise errors.MethodNotImplemented()
        return self.active_list()

    @delete("currency/")
    @check_params(token=TokenAdmin, code=ActiveCurrencies)
    def remove(self, code):
        """
        Remove currency from active list (NOT IMPLEMENTED)

        :param str code: Currency code
        :return dict currencies: List of active currencies

        **Example**::

            {
                "currencies": [
                    {
                        "code": "RUB",
                        "currency": "Russian rouble",
                        "decimal": 2
                    },
                        "code": "USD",
                        "currency": "United States dollar",
                        "decimal": 2
                    }
                ]
            }
        """
        raise errors.MethodNotImplemented()
        # from model.tariff import Tariff
        # currency = currency.upper()
        # if Tariff.count({"currency": currency, "deleted": None}):
        #     raise errors.CurrencyUsedByTariff()
        # Option.remove_currency(currency)
        # return self.active_list()
