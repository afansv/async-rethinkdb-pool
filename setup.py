#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()



setup(
    name='async_repool',
    version='0.1.0',
    description="AsyncIO connection pool for RethinkDB",
    long_description=readme,
    author="Bogdan Gladyshev",
    author_email='siredvin.dark@gmail.com',
    url='https://gitlab.com/AnjiProject/async-repool',
    packages=find_packages(include=['async_repool']),
    include_package_data=True,
    install_requires=[
        "rethinkdb>=2.3.0.post6"
    ],
    license="MIT license",
    zip_safe=False,
    keywords='rethinkdb asyncio connection pool',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    tests_require=[],
    setup_requires=[],
)
