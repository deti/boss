"""
Get metrics from ceilometer

Usage:
    metrics [options]

Options:
  -h --help                 Show this screen.
  -c --customer=CUSTOMER    Specify customer email or id
  -m --metric=METRIC        Specify metric
  -s --service=SERVICE      Specify service
  -t --tenant=TENANT        Specify tenant
  --start=START             Specify start metric range. By default 15 minutes ago is used.
                            Format like this: 2013-05-11T13:23:58
  --end=END                 Specify end metric range. By default current time is used.
                            Format like this: 2013-05-11T13:23:58
  --limit=LIMIT             Limit for number of returned samples [default: 10]


"""
import conf
import logbook
import arrow
from pprint import pprint
from os_interfaces.openstack_wrapper import openstack
from datetime import timedelta


def main():
    import docopt
    from model import Customer

    opt = docopt.docopt(__doc__)

    tenant_id = opt["--tenant"]
    customer_id = opt["--customer"]
    if customer_id:
        try:
            customer_id = int(customer_id)
            customer = Customer.get_by_id(customer_id)
        except ValueError:
            customer = Customer.get_by_email(customer_id)
        if not customer:
            logbook.warning("Customer {} not found", customer_id)
            return
        else:
            tenant_id = customer.tenant.tenant_id
    start = opt["--start"]
    end = opt["--end"]
    now = arrow.utcnow().date()

    start = arrow.get(start) if start else now - timedelta(minutes=15)
    end = arrow.get(end) if end else now

    metric = opt["--metric"]
    service = opt["--service"]
    if service:
        service_mapping = {data["service"]: name for name, data in conf.fitter.collection.meter_mappings.items()}
        if service not in service_mapping:
            logbook.warning("Service {} not found", service)
            return
        metric = service_mapping[service]

    samples = openstack.get_tenant_usage(tenant_id, metric, start, end, limit=int(opt["--limit"]))
    logbook.info("Found {} samples", len(samples))
    for s in samples:
        pprint(s._info)

if __name__ == '__main__':
    main()
