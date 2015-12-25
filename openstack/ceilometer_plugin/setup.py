import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


NAME = "ceilometer_metering_plugin"

setup(
    name=NAME,
    version="0.0.1",
    url="asdco.ru",
    author="ASD Technologies",
    author_email="boss@asdco.ru",
    description="BOSS metering plugin",
    license="Private",
    packages=['ceilometer_metering_plugin'],
    long_description=read('README.rst'),
    # install_requires=[],
    classifiers=[
        "Development Status :: 1 - Alpha",
        "Topic :: Utilities",
    ],
    entry_points={
        'ceilometer.poll.compute': [
            'ip.fixed = %s.ip_fixed:FitterFixedIPPollster' % NAME,
            'ip.floating = %s.ip_floating:FitterFloatingIPPollster' % NAME,
            'volume.size = %s.volume_size:FitterVolumeSizePollster' % NAME,
            'snapshot.size = %s.snapshot_size:FitterSnapshotSizePollster' % NAME,
        ],
        # 'ceilometer.poll.central': [
        #     'ip.floating = %s.ip_floating:FloatingIPPollster' % NAME,
        # ]
    }
)
