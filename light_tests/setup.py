from setuptools import setup, find_packages

install_requires = ['requests', 'metayaml', 'teamcity-messages']

packages = find_packages(".")

setup(
    name='boss_light_tests',
    extras_require={
        'openstack':  ['python-novaclient', 'python-neutronclient'],
    },
    version='0.1.0',
    packages=packages,
    install_requires=install_requires,
    url='https://bitbucket.org/asdtech/boss',
    license='Private',
    author='ASD Technologies',
    author_email='boss@asdco.ru',
    description='Backend tests for the BOSS project',
    console_scripts=[
        'light_tests = light_tests.tests:main',
    ],
)

