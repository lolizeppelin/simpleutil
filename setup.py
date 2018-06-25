#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import os

from simpleutil import __version__

try:
    from setuptools import setup, find_packages, Extension
except ImportError:
    from distutils.core import setup


f = open(os.path.join(os.path.dirname(__file__), 'README.rst'))
long_description = f.read()
f.close()

cutils = Extension('simpleutil.utils._cutils',
                   sources=['libs/_cutils.c'],
                   extra_compile_args=["-lrt"])

setup(
    ext_modules=[cutils],
    # oslo_cfg 要求 netaddr!=0.7.16,>=0.7.12 # BSD
    # kombu>=3.0.25否则timeout参数有问题
    install_requires=('netaddr>=0.7.5', 'eventlet>=0.18.4', 'six>=1.9.0',
                      'dateutil>=2.4.2',
                      'argparse>=1.2.1',
                      'funcsigs>=0.4',  # python3 do not need it
                      'importlib>=1.0',  # python2.7+ do not need it
                      'ntplib>=0.3.3',
                      'jsonschema>=2.0.0',
                      'jsonschema<3.0.0',
                      'jsonschema!=2.5.0',),
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
    packages=find_packages(include=['simpleutil*']),
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
