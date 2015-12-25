======================
Fitter metering plugin
======================

************
INSTALLATION
************

Metering plugin
===============
1. Install plugin **python ./setup.py install**

Ceilometer
==========
1. Update setup.cfg
    Add "ip.fixed = ceilometer_metering_plugin.ip_fixed:FitterFixedIPPollster"
    below section "[entry_points]" under namespace "ceilometer.poll.compute".
    For example::

      [entry_points]
      ceilometer.poll.compute =
          ....
          ip.fixed = ceilometer_metering_plugin.ip_fixed:FitterFixedIPPollster

2. Install Ceilometer.
