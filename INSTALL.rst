BOSS
====

Billing for OpenStack Solution

API doc: TODO

Requirement
===========
* MySQL
* Redis


Local backend dev installation
======================
* python3 bootstrap-buildout.py     (add flag --allow-site-packages for windows machine)
* bin/buildout -c backend.cfg


System Tests installation
=========================
* python3 bootstrap-buildout.py     (add flag --allow-site-packages for windows machine)
* bin/buildout -c tests.cfg
* TODO


DB initializing
===============

my.cnf::

	[mysqld]
	query_cache_size=0
	default_storage_engine=InnoDB
	innodb_autoinc_lock_mode=2
	innodb_file_per_table
	collation-server = utf8_general_ci
	init-connect = 'SET NAMES utf8'
	character-set-server = utf8

* bin/db_user create -u root -p <mysql root password>

If you would like to run unittests, please run this command

* bin/db_user create_test -u root -p <mysql root password>

DB migration:

* bin/migrate upgrade


Local UI development (frontend)
===============================
* install node and npm
* python3 bootstrap-buildout.py     (add flag --allow-site-packages for windows machine)
* bin/buildout -c backend_frontend.cfg or
* bin/buildout -c frontend.cfg      (if only frontend is needed)
* steps from DB initializing


Buildout Windows installation issues
====================================
To properly compile depended C libraries (during bildout run) the following changes in environment are required::

    SET VS90COMNTOOLS=%VS100COMNTOOLS%  # with Visual Studio 2010 installed (Visual Studio Version 10)
    or
    SET VS90COMNTOOLS=%VS110COMNTOOLS%  # with Visual Studio 2012 installed (Visual Studio Version 11)
    or
    SET VS90COMNTOOLS=%VS120COMNTOOLS%  # with Visual Studio 2013 installed (Visual Studio Version 12)

The list of precompiled libraries for windows you can find here http://www.lfd.uci.edu/~gohlke/pythonlibs/


Migration to new flavor management
==================================

Run boostrap script to create flavors using API::
 
  bin/boostrap.py <stage_config> configs/bootstrap.yaml


Update existed tariffs in database::

  UPDATE service_price JOIN flavor ON service_price.service_id = CONCAT("vm.",  flavor.flavor_id) SET service_price.service_id = flavor.service_id;

