#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='ReviewBoard-Crowd',
      version='1.0',
      description='Reviewboard Crowd Authentication Backend',

      author='Joshua Colp',
      author_email='jcolp@digium.com',

      packages = find_packages(),

      entry_points={
        'reviewboard.auth_backends': [
            'auth_crowd = crowd:CrowdAuthBackend',
            ],
        }
      )
