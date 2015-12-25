import bottle
import json
import logbook
from utils.i18n import _, translate
from lib import exception_safe


class ErrorWithFormattedMessage(Exception):
    def __init__(self, message=None, *args, **kwargs):
        super().__init__()

        assert not (kwargs and args)

        self.message_args = args
        self.message_kwargs = kwargs

        if message:
            self.message = message

    def __str__(self):
        if self.message_args:
            return self.message.format(*self.message_args)
        else:
            return self.message.format(**self.message_kwargs)


# base errors
class BadRequest(ErrorWithFormattedMessage, bottle.HTTPError):
    default_status = 400
    message = ""

    def __str__(self):
        message = super().__str__()
        return "<{}({}): {}>".format(self.__class__.__name__, self.default_status, message)

    @exception_safe
    def format_response(self):
        import conf
        if self.message_args:
            formatter = lambda msg: msg.format(*self.message_args)
        elif self.message_kwargs:
            formatter = lambda msg: msg.format(**self.message_kwargs)
        else:
            formatter = lambda msg: msg

        try:
            localized_message = translate(self.message)
        except ValueError as e:
            logbook.warning("Translate error: {}", e)
            localized_message = self.message

        formatted_message = formatter(self.message)
        localized_formatted_message = formatter(localized_message)

        field = None
        if isinstance(self, BadParameter):
            field = self.parameter_name

        res = {
            'message': formatted_message,
            'localized_message': localized_formatted_message
        }
        if field:
            res["field"] = field

        if conf.devel.debug and self.traceback:
            if conf.test:
                print(self.traceback)
            res["traceback"] = self.traceback.split("\n")

        self.content_type = 'application/json'
        self.body = json.dumps(res, indent=4 if conf.devel.debug else None)

        return self


class BadParameter(BadRequest):
    def __init__(self, exc, parameter_name):
        super().__init__(exc.message, *exc.message_args, **exc.message_kwargs)
        self.parameter_name = parameter_name


class Unauthorized(BadRequest):
    default_status = 401


class PaymentRequired(BadRequest):
    default_status = 402


class Forbidden(BadRequest):
    default_status = 403


class NotFound(BadRequest):
    default_status = 404
    message = _("Not Found")


class MethodNotAllowed(BadRequest):
    default_status = 405


class NotAcceptable(BadRequest):
    default_status = 406


class Timeout(BadRequest):
    default_status = 408


class Conflict(BadRequest):
    default_status = 409


class ServiceUnavailable(BadRequest):
    default_status = 503


class MethodNotImplemented(MethodNotAllowed):
    message = _("Method is not implemented")


class DatabaseIsDown(ServiceUnavailable):
    message = _("Database is down. Please try again a bit later")


class CacheDatabaseIsDown(DatabaseIsDown):
    message = _("Cache database is down. Please try again a bit later")


class HasToHaveDefinedNameInDefaultLanguage(Conflict):
    message = _("Has to have translation for default language: '{}'")

    def __init__(self):
        from utils.i18n import DEFAULT_LANGUAGE
        super().__init__(None, DEFAULT_LANGUAGE)


class UserAlreadyExists(Conflict):
    message = _("User account already exists")


class UserRemoved(Conflict):
    message = _("User account is removed")


class CustomerAlreadyExists(Conflict):
    message = _("Customer account already exists")


class UserUnauthorized(Unauthorized):
    message = _("Incorrect email/password")


class CustomerUnauthorized(Unauthorized):
    message = _("Incorrect email/password")


class UserInvalidToken(Unauthorized):
    message = _("Invalid token")


class CustomerInvalidToken(Unauthorized):
    message = _("Invalid token")


class UserInvalidRole(MethodNotAllowed):
    message = _("Not enough rights to perform this action")


class SendingEmailException(Conflict):
    message = _("Email sending is impossible")


class UserNotFound(NotFound):
    message = _("User account not found")


class CustomerNotFound(NotFound):
    message = _("Customer account not found")


class ServiceNotFound(NotFound):
    message = _("Service not found")


class ServiceAlreadyExisted(NotFound):
    message = _("Service already exists")


class RemovingUsedService(Conflict):
    message = _("Used service cannot be removed")


class ImmutableService(Conflict):
    message = _("Immutable service cannot be changed")


class RemovedService(Conflict):
    message = _("Removed service cannot be changed")


class RemovedServiceInTariff(NotFound):
    message = _("Removed service cannot be included in plan")


class OnlyImmutableService(Conflict):
    message = _("Only immutable service can be included in plan")


class TariffNotFound(NotFound):
    message = _("Plan not found")


class RoleNotFound(NotFound):
    message = _("Role not found")

class NewsNotFound(NotFound):
    message = _("News not found")


class HarakiriIsNotAllowed(Forbidden):
    message = _("Can not delete self")


class ImmutableTariff(Conflict):
    message = _("Immutable plan cannot be changed")


class RemovedTariff(Conflict):
    message = _("Removed plan cannot be changed")


class PasswordResetTokenInvalid(BadRequest):
    message = _("Password reset link is invalid, expired or was already used. Please try to request password reset again")


class EmailConfirmationTokenInvalid(BadRequest):
    message = _("Email confirmation link is invalid, expired or was already used. Please try to resend a confirmation email")


class TariffAlreadyExists(Conflict):
    message = _("Plan already exists")


class ReportAggregationIsNotReady(NotFound):
    message = _("Report aggregation is not ready")


class TariffHistoryNotFound(NotFound):
    message = _("Plan history entry not found")


class NothingForUpdate(BadRequest):
    message = _("Nothing to update")


class MessageTemplateError(BadRequest):
    message = _("Error while rendering a template")


class InvalidMoney(BadRequest):
    message = _("Invalid number format")


class ParentTariffCurrency(Conflict):
    message = _("Parent plan should have the same currency")


class SubscriptionAlreadyExists(Conflict):
    message = _("Subscription already exists")


class SubscriptionSwitchAlreadyExists(Conflict):
    message = _("Subscription already exists")


class InvalidSubscription(BadRequest):
    message = _("Invalid subscription data")


class RemoveUsedTariff(Conflict):
    message = _("Used plan cannot be removed")


class AssignMutableTariff(Conflict):
    message = _("Mutable plan cannot be assigned to a customer")


class MutableTariffCantBeDefault(Conflict):
    message = _("Mutable plan cannot be default")


class QuotaAlreadyExist(Conflict):
    message = _("Quota for this customer already exists")


class NewsAlreadyExist(Conflict):
    message = _("The news already exists")


class RemovedNews(Conflict):
    messahe = _("Removed news cannot be changed")


class BotVerifyFailed(Unauthorized):
    message = _("Invalid reCAPTCHA token. You are bot.")


class CustomerWithoutHorizonUser(BadRequest):
    message = _("Customer has no OpenStack login. Please contact the administrator.")


class HorizonRequestError(BadRequest):
    message = _("Unsuccessful request to Horizon. Please contact the administrator.")


class HorizonUnauthorized(BadRequest):
    message = _("Unable to login into Horizon the current OpenStack login/password. Please contact the administrator.")


class ProductionModeNeedMoreInfo(BadRequest):
    message = _("Need to fill in all mandatory fields to switch to production mode.")


class StartShouldBeEarlierFinish(BadRequest):
    message = _("start parameter should be earlier than finish")


class TenantIsnotCreated(Conflict):
    message = _("Tenant is not created yet. Try again latter")


class CustomerEmailIsNotConfirmed(Conflict):
    message = _("Customer email is not confirmed")


class CustomerBlocked(Conflict):
    message = _("Customer is blocked")


class CustomerRemoved(Conflict):
    message = _("Customer is removed")


class PaymentCardRemoved(Conflict):
    message = _("Payment card already removed.")


class PaymentCardNotFound(Conflict):
    message = _("Payment card not found.")

class OptionAlreadyExists(Conflict):
    message = _("Option already exists")


class CustomerPaymentCardAlreadyExists(Conflict):
    message = _("Payment card already exists")


class CustomerIsNotEntity(Conflict):
    message = _("Customer is not entity")


class PromocodeInvalid(Unauthorized):
    message = _("Invalid promo code.")


class PromocodeOnly(BadRequest):
    message = _("Registration with promo code only.")


class PromocodeRemoved(Conflict):
    message = _("Promo code already removed")


class ReportFormatIsNotSupported(Conflict):
    message = _("Report format is not supported")


class FlavorAlreadyExists(Conflict):
    message = _("Flavor already exists")


class FlavorNotFound(NotFound):
    message = _("Flavor not found")


class OsFlavorExistsWithDifferentParams(Conflict):
    message = _("Flavor already exists in OS with different parameters")
