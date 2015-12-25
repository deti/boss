import logbook
from report import Report
from utils.money import decimal_to_string


class ReceiptsReport(Report):
    report_type = "receipts"

    def aggregate(self, report_id):
        logbook.info("Get receipts aggregation for {}", report_id)
        from model import AccountHistory, User

        result = []
        users = {user.user_id: user.name for user in User.query}
        users[None] = ""
        for row in AccountHistory.report(report_id.start, report_id.end):
            r = {"email": row[0].email,
                 "date": row[1].date,
                 "amount": decimal_to_string(row[1].delta),
                 "currency": row[2].currency,
                 "comment": row[1].comment,
                 "user": users[row[1].user_id]}
            result.append(r)
        return result

