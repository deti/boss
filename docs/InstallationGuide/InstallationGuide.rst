===============
BILLING SYSTEM
===============

Installation Guide
------------------


TODO REWRITE IS NEEDED

The guide is designed for Software Engineers and System Administrators who
install and maintain the Billing System. The guide describes software
installation process and a set of software tools that are necessary to
deploy the Billing system.

.. contents:: Contents
   :depth: 3

Software Installation
+++++++++++++++++++++
Developer�s tools are set up automatically by means of Ansible.

To successfully work with the source code, the operating system Linux must
have the following software installed:

* DBMS Redis;
* DBMS MySQL;
* Ansible (for the administrator node).

Documentation
+++++++++++++
Before software installation, please read `the Linux Administration Manual`_.

.. _the Linux Administration Manual: https://www.ibm.com/developerworks/ru/training/kp/l-kp-command/.

Ansible Software Installation
+++++++++++++++++++++++++++++

#. To install Ansible, please enter the command yum install ansible.
#. From the project repository folder ddeploy/ansible, copy the files to
   the snapshot repository /etc/ansible.
#. Install the docker-registry package on the server that works as
   a snapshot repository.

The list of snapshots is as follows:

* galera;
* frontend_lk;
* frontend_admin;
* project_backend.

4. Copy snapshots of docker containers from the ASD Technologies repository
   to the local snapshots repository: ::

      #docker pull registry-docker.asdco.ru:5000/project/image_name
      #docker tag docker.asdco.ru:5000/project/image_name loca-
      rregistry.cloud:5000/project/image_name
      #docker push rregistry.cloud:5000/project/image_name

5. Create a yaml-file that contains an an environment description
   (a sample file can be found here: deploy/ansible/playbooks/dev.yaml
   and dev_infra.yaml).

   Enter the name of the environment (e.g.: stage) instead of the dev element.


6. Edit the file that contains variables for the new environment.
   The file name must be the same as the environment name, e.g.: ::

     etcd_rpm: http://cbs.centos.org/kojifiles/packages/etcd/0.4.6/7.
     el7.centos/x86_64/etcd-0.4.6-7.el7.centos.x86_64.rpm
     etcdctl_rpm: http://copr-be.cloud.fedoraproject.org/results/maxamillion/
	 epel7-kubernetes/epel-7-x86_64/etcdctl-0.4.6-1.fc22/etcdctl-0.4.6-1.el7.
	 centos.x86_64.rpm
     etcd_token: 4e2c4c57f7b6c2fbc029f5fe353ae1c4
     registry: 192.168.3.155:5000
     etcd_ip: "{{ ansible_eth0.ipv4.address }}:4001"
     mysql_root_pass: "{{ lookup('password',
	 'credentials/dev/mysql/root length=15') }}"
     galera_image: "project/galera:latest"
     redis_image: "project/infrastructure_redis:latest"
     frontend_lk_image: "project/frontend_lk:latest"
     frontend_admin_image: "project/frontend_admin:latest"
     backend_image: "project/boss_backend:latest"

7. To set up the system that launches installation scripts in the Billing
   system catalogue, sequentially run the following commands: ::

     # ansible-playbook stage_infra.yaml
     # ansible-playbook stage.yaml
