#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()



setup(
    name='errbot_rethinkdb_storage',
    version='1.0.4',
    description="RethinkDB storage plugin for ErrBot",
    long_description=readme + '\n\n' + history,
    author="Bogdan Gladyshev",
    author_email='siredvin.dark@gmail.com',
    url='https://gitlab.com/AnjiProject/errbot-rethinkdb-storage',
    packages=find_packages(include=['errbot_rethinkdb_storage']),
    include_package_data=True,
    install_requires=[
        "rethinkdb==2.3.0.post6",
        "errbot>=5.1.0"
    ],
    dependency_links=[
        "git+https://github.com/njouanin/repool"
    ],
    license="MIT license",
    zip_safe=False,
    keywords='errbot_rethinkdb_storage',
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
