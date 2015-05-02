import os
import sys
from setuptools import setup
from relogger import __version__

setup(
    name = "relogger",
    version = __version__,
    url = 'https://github.com/caesar0301/relogger',
    author = 'Xiaming Chen',
    author_email = 'chenxm35@gmail.com',
    description = 'A syslog sender, relay and receiver.',
    long_description='''A relayer or replicator to send SYSLOG
from one or multiple sources to one or multiple destinations.''',
    license = "The MIT License",
    packages = ['relogger'],
    scripts=['bin/relogger'],
    keywords = ['syslog', 'relay'],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
            'Intended Audience :: Developers',
            'License :: Freely Distributable',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
            'Topic :: Software Development :: Libraries :: Python Modules',
   ],
)