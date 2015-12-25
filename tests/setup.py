from setuptools import setup, find_packages
# test
install_requires = ['pytest',
                    'boss_lib',
                    'bottle',
                    'teamcity-messages',
                    'pytest-cov',
                    'metayaml',
                    'pytz',
                    'python-dateutil',
                    'attrdict',
                    'requests!=2.9.0,>=2.8.1',
                    'pyyaml',
                    'nose',
                    'nose_parameterized',
                    'boss_client',
                    'openstack_client']

packages = find_packages(".")

setup(
    name='boss_tests',
    version='0.0.1',
    packages=packages,
    install_requires=install_requires,
    package_data={
        'configs': ['*.yaml']
    },
    url='https://bitbucket.org/asdtech/boss',
    license='Private',
    author='ASD Technologies',
    author_email='boss@asdco.ru',
    description='Backend tests for the BOSS project'
)
