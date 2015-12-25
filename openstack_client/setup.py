import os
from setuptools import setup, find_packages

install_requires = ['logbook',
                    "python-ceilometerclient",
                    "python-keystoneclient",
                    "python-neutronclient",
                    "python-glanceclient",
                    "python-cinderclient",
                    "python-novaclient"]

if os.name == "nt":
    install_requires.append('netifaces')
    dependency_links = []
else:
    install_requires.append('netifaces>=0.10.5')
    dependency_links = ["https://github.com/sashgorokhov/Netifaces/archive/master.zip#egg=netifaces-0.10.5"]


packages = find_packages(".")

setup(
    name='openstack_client',
    version='0.0.1',
    packages=packages,
    install_requires=install_requires,
    dependency_links=dependency_links,
    url='https://bitbucket.org/asdtech/boss',
    license='Private',
    author='ASD Technologies',
    author_email='boss@asdco.ru',
    description='Openstack client for the BOSS project'
)
