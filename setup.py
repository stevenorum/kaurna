#!/usr/bin/env python

from setuptools import setup

setup(name='kaurna',
      version='0.1.0',
      description='Secure secret storage utilities.',
      author='Quinn Raskin',
      author_email='quinn@edofleini.com',
      url='www.edofleini.com',
      packages=['kaurna'],
      package_dir={'kaurna': 'kaurna'},
      scripts=['scripts/kaurna'],
      test_suite='tests',
     )
