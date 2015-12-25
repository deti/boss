import os
from setuptools import setup, find_packages

install_requires = ['requests!=2.9.0,>=2.8.1',
                    'logbook']

if os.name == "nt":
    install_requires.append('netifaces')
    dependency_links = []
else:
    install_requires.append('netifaces>=0.10.5')
    dependency_links = ["https://github.com/sashgorokhov/Netifaces/archive/master.zip#egg=netifaces-0.10.5"]


packages = find_packages(".")

setup(
    name='boss_client',
    version='0.0.1',
    packages=packages,
    install_requires=install_requires,
    dependency_links=dependency_links,
    url='https://bitbucket.org/asdtech/boss',
    license='Private',
    author='ASD Technologies',
    author_email='boss@asdco.ru',
    description='Backend api clients for the BOSS project'
)
