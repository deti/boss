======================
BOSS API documentation
======================

This file was generated |today| for version |version|

Branch: |git_branch| (|git_commit|)

.. contents:: Table of Contents

Types
=====

.. _str:

**str**
  Any utf-8 encoding string

.. _Date:

.. index:: Date

**Date**
  Date and time type. The following formats are supported:

  - ISO format -- 2013-01-28T00:37:12
  - ISO format without delimiter -- 20130128003712
  - Unix Timestamp -- 1359718708 (2013-02-01 5:38:28)

 .. _Day:

.. index:: Day

**Day**
  Date type. The following formats are supported:

  - ISO format -- 2013-01-28
  - ISO format without delimiter -- 20130128
  - Unix Timestamp -- 1359331200 (2013-01-28 00:00:00)

.. _Email:

**Email**
  User email. It must match to :rfc:`822`

.. _Regexp:

**Regexp**
  String type which should match to Perl-compatible regular expression

.. _Role:


**Role**
  User role


Short description of errors
===========================

.. errorsummary:: errors


Short API description
=====================


Methods marked **service method** are available only in development environment
(api.internal_methods_enabled = true in the config file).

.. apisummary:: view.admin_api_handler


.. apisummary:: view.cabinet_api_handler



Detailed API description
========================

Detailed description of BOSS API

.. note::

   Admin user is created during first migration. The email and password is set in config file::

  default_users:
    - email: ${__FIX_ME__}
      password: {$__FIX_ME__}



.. default-domain:: pyapi

Admin API
---------

.. autoapi:: view::admin_api_handler
      :members:
      :undoc-members:

Cabinet API
-----------

.. autoapi:: view::cabinet_api_handler
      :members:
      :undoc-members:


Links
=====

* :ref:`genindex`

