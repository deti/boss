from setuptools import setup, find_packages

install_requires = [
    'logbook',
    'raven'
]


def get_version():
    try:
        import yaml
    except ImportError:
        return "<unknown_version>"

    f = open("../version", "rb")
    version_config = yaml.load(f)["version"]
    base = str(version_config["base"])
    return ".".join((base, str(version_config["backend"])))


packages = find_packages(".")
setup(
    name="boss_lib",
    version=get_version(),
    author="ASD Technologies",
    author_email="boss@asdco.ru",
    description="Set of libraries and axillary functions for BOSS project",
    license="Private",
    url="https://bitbucket.org/asdtech/boss",
    packages=packages,
    package_data={
        '': ['*.sh', '*.ini', '*.pem', '*.txt'],
        'configs': ['*.yaml']},
    install_requires=install_requires,
    entry_points={
        'console_scripts':
        []
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
