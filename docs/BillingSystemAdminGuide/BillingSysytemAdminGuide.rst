===============
BILLING SYSTEM
===============

Administrator Guide
---------------------

This guide is designed for Billing System Administrators and describes a 
common structure and a set of tools that are necessary to manage 
the Billing System.

.. contents:: Contents
   :depth: 3
   
1. Account Settings
---------------------
1.1. Administrator Sign In / Sign Out
+++++++++++++++++++++++++++++++++++++++++
Open the Billing System authorization page, enter your username/password 
and click on the **Sign in** button. The page that contains a list of current 
active Customers opens (Figure 1).

.. figure:: images\signin.png 
   :align: center
   :width: 420 px
   :height: 300 px

   Figure 1. Sign in

If you need to reset your password, visit the authorization page and click the
**Forgot?** link. A message with the password recovery instructions will 
be sent to the specified email address (Figure 2).

.. figure:: images\forgot.png 
   :align: center
   :width: 400 px
   :height: 310 px

   Figure 2. Reset the password
 
To sign out, click the Administrator name in the upper-right corner of 
the page and select the **Sign out** option in the dropdown list (Figure 3).

.. figure:: images\signout.png 
   :align: center
   :width: 800 px
   :height: 230 px

   Figure 3. Sign out
 
To reset your password, click the Administrator name in the upper right 
corner of the page, select the **Sign out** option in the dropdown list 
and follow the instructions described in Section Administrator Authorization.

1.2. Selecting UI Language
++++++++++++++++++++++++++++++++++++++++++++++
Click on the icon in the upper right corner of the page and select
the language in the dropdown list (Figure 4).

.. figure:: images\language.png 
   :align: center
   :width: 800 px
   :height: 230 px

   Figure 4. Language
 
2.	Start Working
---------------------
The home page in the sidebar menu contains the following UI elements:

1.	**Sidebar menu**:

* Customers;
* Services;
* Plans;
* Users;
* News;

2.	**Info unit** that displays additional functionality depending on 
the selected menu item;

3.	**Auxiliary form** that displays additional content depending on 
the selected menu item.


2.1.	Customers
++++++++++++++++++++
**The Customer** - a person or a company that signed a cloud services 
contract with the Cloud Provider. 

The Billing system ensures a trial and a production period. The trial 
period is offered to Customers to test the Cloud resources and functionality 
within a certain time period (N days) or with an offered certain sum (X) 
in certain currency that is transferred to the Customer’s account. After 
the trial period is over, the Customer starts to work in the working mode 
and uses Cloud resources on a fee-paid basis.

.. note::
 
     Parameters N and X are set in the Billing System settings.

.. note::

     After the trial period is over, all data about the Customer’s transactions are deleted.

2.1.1.	Creating Customer Account
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Customers** item, click on 
the **New customer** button. At **Step 1** – Data, enter the necessary 
information and click on the **Continue** button. At **Step 2** - Contacts 
select and enter the Customer’s contact information and click on 
the **Continue** button (Figure 5).
 
The Customer’s data are saved and available on the customers list.

.. note::

     To make the process more comfortable, the customer creation feature is available on all pages of the Customers menu. You just need to click on the icon  at the top of the page.

.. figure:: images\newcustom.png 
   :align: center
   :width: 800 px
   :height: 230 px

   Figure 5. Creating a new customer
   
2.1.2.	Editing Customer Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Customers** menu, select the Customer’s 
account on the customers list. The Billing System allows users to edit 
only the Customer’s contact information in the tab **Information**. 

Fill in the necessary info or edit the information in 
the fields.

In the **Save changes?** window, click on the **Save** button (Figure 6).

.. figure:: images\contacts.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 6. Editing customer data

2.1.3.	Reset Customer Password
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the Customers item, select the Customer’s account 
on the customers list. Under the Contacts tab, click on the Reset password 
button (Figure 7).

.. figure:: images\button.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 7. Reset the password

A message containing the password reset notification and a link to 
the authorization page is sent to the email address indicated by the Customer.

2.1.4.	Archiving Customer Account
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Customer accounts archiving is used to hide accounts of inactive customers 
from the list of active customers (the transactions history of such customers 
is stored in the System).

In the sidebar menu, select the **Customers** item, select the Customer’s 
account on the customers list. Under the **Information** tab, click on 
the **Send to archive** button (Figure 7).

2.1.5.	Switching Working Mode for Customer Accounts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the sidebar menu, select the **Customers** item, select the Customer’s 
account on the customers list. Under the **Information** tab, click on 
the **Working Mode** button. In the **Save changes?** window, click on
the **Save** button (Figure 7).
 
2.1.6.	Locking Customer Accounts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Customers** item. Select the customer 
account on the list. Under the **Information** tab, click on the **Lock** 
button. Enter the locking reason in the corresponding field and click on 
the **Lock** account button (Figure 7).

**Customer Account Auto-lock Settings**

In the sidebar menu, select the **Customers** item. Select the customer 
account on the list. Under the **Notifications** tab, in the **Lock** 
account if balance lower than field specify the minimum balance sum (Figure 9). 
If this value is exceeded, the customer account will be automatically locked.

2.1.7.	Searching for Customer Accounts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Customers** item. In the upper left corner 
of the page, click on the magnifier icon. In the search section, on the filter
list, select any criteria to search for customer accounts The page displays 
a list of search results (Figure 8).

.. figure:: images\search.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 8. Seach the customer

Or you can enter a plan name / customer name and hit the **Enter** key. 
The page displays a list of search results.

2.1.8.	Setting Up Subscription Notifications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Customers** item, select a customer account 
on the list. Under the **Notifications** tab, in the 
**Customer subscriptions** form, move the sliders to the necessary position 
near the Customer’s name (Figure 9).

.. figure:: images\notifications.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 9. Setting up subscription notifications
 
2.1.9.	Adding Funds / Debiting Customer Accounts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
After the Customer adds funds to the balance in the Personal Account, 
the sum is transferred to the internal account of the Billing system.

In the sidebar menu, select the **Customers** item, select the customer 
account on the list. Under the **Account** tab, specify 
the recharge / debiting sum and add a comment for the transaction. 
Click on the **Add** or the **Debit** button (Figure 10).

.. figure:: images\balance.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 10. Add funds / Debit 
 
2.1.10.	Generating Reports for 1C Accounting Application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Customers** item, select the customer 
account on the list. Under the **Report** tab, select a time period 
(**week, 2 weeks, month, year**) for a report. You can also customize 
a time period by clicking the calendar icon and selecting the necessary 
dates. Select the necessary report format in the dropdown list and click 
on the **Create report** button (Figure 11).

To generate a detailed report that contains the comprehensive information 
on the resources used, check the **Detailed** box.

.. figure:: images\report.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 11. Generating reports 

2.1.11.	Viewing Customer Transactions History
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Customers** item, select the customer 
account on the list. Under the **History** tab, select a time period 
(**week, 2 weeks, month, year**) for a report. You can also customize 
a time period by clicking the calendar icon and selecting the necessary 
dates. A table that lists transactions history, dates and comments is 
displayed (Figure 12).

.. figure:: images\transactions.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 12. Transactions
 
2.1.12.	Viewing Quotas for Cloud Resources
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Customers** item, select the customer 
account on the list, then select the **Resources Quotas** tab. Create 
a new template for resource quotas or choose the existing one 
and enter the necessary data in the fields (Figure 13).  

If some changes were introduces, in the pop-up window, click on 
the **Save** or **Cancel** button.

.. figure:: images\quota.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 13. Resource quotas
 
2.1.13.	Changing Customer’s Plan
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Customers** item, select the customer 
account on the list, then select the **Plan** tab. In the opened window, 
select the plan’s name that will exchange the current customer’s plan. 
To immediately change the plan, click on the **Change now** button.
 
To change the plan by schedule, click on the **Change later** button. 
A special form to enter the dates appears. Fill in the fields and click 
on the **Schedule plan change** button (Figure 14). 

.. figure:: images\changeplan.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 14. Change customer's plan
  
2.1.14.	Viewing The Plan History
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Customers** item, select the customer 
account on the list, then select the **Plan history** tab. Select a time period 
(**week, 2 weeks, month, year, all time**) for a report (Figure 15). 

.. figure:: images\planhistory.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 15. Plan history

2.1.15.	Changing The Openstack Horizon/Skyline Console
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Customers** item. Select the customer 
account on the list. Under the **Information** tab, select the type of
the console in the dropdown menu (Figure 16).

.. figure:: images\console.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 16. Changing the console
 
2.2.	Services
++++++++++++++++++++++
**Service** - cloud resources used by the Customer for which the Cloud 
Provider charges the Customer.

2.2.1.	Creating New Services
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the side bar, select the **Services** menu and click on 
the **New Service** button at the top of the page. Fill in the necessary
fields and select the necessary options in the dropdown lists. Click on 
the **Create** button. A new service is saved and available on the services 
list (Figure 17).
 
.. note::
    
	 Some fields need to be filled out in Russian or English.
	 
.. note::

     The service creation feature is available on all pages of the Users menu. You just need to click on a corresponding icon at the top of the page.

.. figure:: images\newservice.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 17. Creating a new service
	 
2.2.2.	Viewing Service Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Services** item. Select a service in 
the list. An auxiliary form opens under the **Parameters** tab. The form 
contains additional info on the service (Figure 18).

.. figure:: images\param.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 18. Service parameters
 
2.2.3.	Viewing Service’s Plan
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Services** item. Select a service on the 
list. An auxiliary form opens. Select the **Plans with this Service** tab (Figure 19).

The tab lists all plans that include this service as well as the number of 
customers who use this plan.

.. figure:: images\plans.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 19. Service parameters

2.2.4.	Sending Service To The Archive
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Services** item. Select a service in 
the list. An auxiliary form opens under the **Parameters** tab. Click on 
the **Send to archive** button (Figure 18).

2.3. VM Templates
+++++++++++++++++++

2.3.1.	Creating VM Templates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **VM Templates** item, click on 
the **New template** button (Figure 20).
 
An auxiliary form opens. Enter the requited information and click on 
the **Create** button.

.. note::
    
	 Some fields need to be filled out in Russian or English.

.. figure:: images\creataevm.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 20. Creating VM template 
   
2.3.2.	Viewing VM Template Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Services** item. Select a template in 
the list. An auxiliary form opens under the **Parameters** tab (Figure 21). The form 
contains additional info on the template.

.. figure:: images\vmparam.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 21. VM template parameters

2.2.3.	Viewing VM Template's Plan
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **VM Templates** item. Select a template on the 
list. An auxiliary form opens. Select the **Plans with this template** tab (Figure 22).

The tab lists all plans that include this template as well as the number of 
customers who use this plan.

.. figure:: images\vmplans.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 22. VM template plans  

2.4.	Plans
+++++++++++++++++++
2.4.1.	Creating Plans
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Plans** item, click on the **New plan** 
button.
 
An auxiliary form opens. At the **Step 1** – Information stage, fill in the 
fields or select the existing plan and click on the **Continue** button (Figure 23).

.. figure:: images\createplan.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 23. Creating a new plan
 
At the **Step 2** – Services stage, select the necessary services in the 
dropdown lists. In the Services added to the plan section, specify resources 
volume used on an hourly basis. Click on the **Save** button. The plan is 
saved and is now available on the plans list (Figure 24).
 
.. note::

     A special **+** icon to create a new plan is available on all pages 
	 of the Plans menu. 

.. figure:: images\createplan2.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 24. Creating a new plan
	 
2.4.2.	Viewing Plans History
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Plans** item. Select a customer on the list. 
Select the **History** tab in the opened form. The page displays a table that 
lists all actions, dates and Customers names who performed these actions (Figure 25).

.. figure:: images\history.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 25. Plan history
 
2.4.3.	Archiving Plans
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The feature is used to archive plans that are not assigned to Customer's 
accounts.

In the sidebar menu, select the **Plans** item, select a plan on the list. 
Under the **Information** tab, click on the **Send to archive** button (Figure 26)

.. figure:: images\archive.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 26. Archiving plans

2.4.4.	Creating Plans Based on Existing Templates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Plans** item. Select a plan on which base 
you need to create a new plan. Under the **Information** tab, fill in the 
fields and click on the **Create a plan based on this one** button (Figure 26).

A new plan based on the existing one is created and is displayed on the plans 
list.

.. note::

     The functionality is also available when you create a new plan (see Section Creating Plans).

2.4.5.	Assigning Default Plans
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Plans** item. Select a plan on the list and
open the **Information** tab. Fill in the fields and click on the **Assign as
a default plan** button (Figure 26).

2.4.6.	Viewing Adding Services
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Plans** item. Select a plan on the list and
open the **Services** tab. The page displays a list of services added
to the plan and their pricing (Figure 27).
 
.. figure:: images\addservice.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 27. Adding services to the plan 


2.4.7.	Adding Customers to a Certain Plan
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Plans** item. Select a plan on the list. 
Open the **Plan customers** tab. Check the boxes next to the customers and click on the **Add to the plan**
button (Figure 28).

.. figure:: images\plancustomers.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 28. Adding customers to the plan

2.5.	Users
++++++++++++++
**The User** - is an employee who has access to the Billing System.

2.5.1.	User Roles in Billing System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Table 1 describes user roles in the Billing System. For more info about 
assigning roles to a new or existing user, see Section Creating User Profile.

 .. table:: 

    =====================  ===================================================   
    Term                    Description    
    =====================  ===================================================   
    Administrator          Full access and read/write rights.  
    Business Manager       Performs analysis of the current plans, adds new plans and services. Has full access and read/write rights (except for the system settings and editing customer profiles). 
 
    Account Manager        Decides if a user account is approved after the user registers in the System. The Account Manager approves and assigns plans but cannot create/edit/delete a plan or a service. Has partial access and partial read/write rights.   

    Tech Support Engineer  Performs technical support. Has a partial access and read rights.

    =====================  ===================================================  

2.5.2.	Creating User Profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar, select the **Users** menu, click on the **New user** button. 
 
Enter the required information, select the role on the list and click on 
the **Create** button.
 
A message with the generated password and registration information is sent 
to the indicated email address. 

To open the **Authorization** page, the User follows the link in the message. 
To enter **Personal Cloud Account**, the User clicks on the **Enter** button
(Figure 29).

.. note::

     User roles available in the Billing system are described in Section User 
	 Roles in Billing System. 

.. note::

     The user creation feature is available on all pages of the Users menu. 
	 You just need to click on a corresponding icon at the top of the page.

.. note::

     You can reset the password when you first sign in the Billing System.

.. figure:: images\edituser.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 29. Creating a new user

2.5.3.	Editing User Profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the sidebar menu, select the **Users** item. On the users list, select 
a user profile that needs to be edited, enter and select the necessary data. 
In the pop-up menu, click on the Save button. The user data are changed and 
available on the users list (Figure 30).
 
.. figure:: images\createuser.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 30. Edit a user profile

2.5.4.	Archiving User Accounts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **Users** item. On the users list, select 
a user profile and click on the **Send to archive** button (Figure 31).
 
.. figure:: images\archiveuser.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 31. Archieving user account

2.6.	News
+++++++++++++

2.6.1.	Creating News
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **News** item and click on the **Create news** 
button. A special form to create the news opens in the right part of the page.
Enter the news title and text and click on the **Create** button (Figure 32).
 
.. figure:: images\createnews.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 32. Creating news

2.6.2.	Editing News
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **News** item and select the news on the news 
list. Enter changes in the news text and click on the **Save button** in the 
**Save changes?** window (Figure 33).
 
.. figure:: images\editnews.png 
   :align: center
   :width: 800 px
   :height: 350 px

   Figure 33. Editing news

2.6.3.	Publishing / Withdraw News from Publication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **News** item and select the news on the news 
list. In a special form that opens in the right part of the page, click on the
**Publish news** button to publish the news or the **Delete news** button to 
delete the news completely from the list (Figure 33). 

To hide the news from the list of the news visible to the users, select 
the news title on the list and click on the Withdrawn from publication button 
in the form that opens in the right part of the page.

2.6.4.	Deleting News
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In the sidebar menu, select the **News** item and select the news on the news 
list. A special form to edit/publish/delete the news opens in the right part 
of the page (Figure 33).
