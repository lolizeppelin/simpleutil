#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import os

from simpleutil import __version__

try:
    from setuptools import setup


except ImportError:

    from distutils.core import setup


f = open(os.path.join(os.path.dirname(__file__), 'README.rst'))
long_description = f.read()
f.close()

setup(
    # oslo_cfg 要求 netaddr!=0.7.16,>=0.7.12 # BSD
    install_requires=('netaddr>=0.7.5', 'eventlet>=0.15.2'),
    name='simpleutil',
    version=__version__,
    description='a simple copy of some utils from openstack',
    long_description=long_description,
    url='http://github.com/lolizeppelin/simpleutil',
    author='Lolizeppelin',
    author_email='lolizeppelin@gmail.com',
    maintainer='Lolizeppelin',
    maintainer_email='lolizeppelin@gmail.com',
    keywords=['simpleutil'],
    license='MIT',
    packages=['simpleutil'],
    # tests_require=['pytest>=2.5.0'],
    # cmdclass={'test': PyTest},
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ]
)
