import logbook
from task.main import celery, exception_safe_task
from model import Customer
from model.account.customer import CustomerCard
from service.payments import PaymentService


@celery.task(ignore_result=True)
@exception_safe_task(auto_commit=False)
def task_check_customers_for_payment():
    logbook.info("[check_customers_for_payment]")
    for customer in Customer.query.filter(Customer.blocked == False,
                                          Customer.auto_withdraw_enabled == True,
                                          Customer.customer_mode != Customer.CUSTOMER_TEST_MODE):
        account = customer.get_account(customer.tariff.currency)
        logbook.debug("[check_customers_for_payment] Check customer: {}, current: {}, balance_limit: {}",
                      customer, account.current, customer.auto_withdraw_balance_limit)
        if account.current < customer.auto_withdraw_balance_limit:
            # withdraw customer for auto_withdraw_amount
            card = CustomerCard.get_active_card(customer.customer_id)
            logbook.debug("[check_customers_for_payment] Check customer: {}, card: {}", customer, card)
            if card:
                PaymentService.auto_withdraw(customer, card)
