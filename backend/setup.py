from setuptools import setup, find_packages

install_requires = [
    "babel",
    "teamcity-messages",
    "flake8",
    "pytest",
    "pytest-cov",
    "coverage",
    "boss_client",
    "boss_lib",
    "bottle",
    "celery",
    "passlib",
    "redis>=2.10.1",
    "requests!=2.9.0,>=2.8.1",
    "mock",
    "metayaml",
    "attrdict",
    "sqlalchemy",
    "alembic",
    "docopt",
    "pymysql",
    "webtest",
    "arrow",
    "pytz",
    "transliterate",
    "billiard",
    "py3z3c.rml",
    "kids.cache",
    "graphiti",
    "pillow==9.0.1"
]

fitter_dependencies = [
    "PyYAML",
    "python-ceilometerclient",
    "python-keystoneclient",
    "python-neutronclient",
    "python-glanceclient",
    "python-cinderclient",
    "python-novaclient"
]
install_requires.extend(fitter_dependencies)


packages = find_packages(".")


def get_version():
    try:
        import yaml
    except ImportError:
        return "<unknown_version>"

    f = open("../version", "rb")
    version_config = yaml.load(f)["version"]
    base = str(version_config["base"])
    return ".".join((base, str(version_config["backend"])))


setup(
    name="boss_backend",
    version=get_version(),
    author="ASD Technologies",
    author_email="boss@asdco.ru",
    description="API backend server for the BOSS project",
    license="Private",
    url="https://bitbucket.org/asdtech/boss",
    packages=packages,
    package_data={
        '': ['*.sh', '*.ini', '*.pem', '*.txt'],
        'configs': ['*.yaml']},
    install_requires=install_requires,
    entry_points={
        'console_scripts':
        [
            'backend = view:main',
            'bootstrap = bootstrap:main',
            'backend.py = view:main',
            'migrate = model.migrate.migrate:main',
            'db_user = model.db_user:main',
            'fitter  = fitter.main:main',
            'i18n = utils.i18n:main',
            'db_clean = utils.db_clean:main',
            'openstack_clean = utils.openstack_clean:main',
            'celery = task.main:main',
            'metrics = fitter.metrics:main',
            'flake8 = flake8.main:main',
            'bossmngr = utils.management:main'
        ],
        'flake8.extension': [
            'P999 = utils.flake8_plugin',
        ]
    },
    classifiers=[
        "Development Status :: 1 - Planning",
        "Environment :: Web Environment",
        "License :: Other/Proprietary License",
        "Operating System :: Unix",
        "Programming Language :: Python :: 3.3",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Server",
        "Topic :: Multimedia :: Video :: Display",
    ],
)
