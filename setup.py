#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


def long_description():
    with open("README.md", "r") as readme:
        return readme.read()


def packages():
    return find_packages(include=["parser_gen*", "scripts*"])


def install_requires():
    with open("requirements.txt", "r") as requirements:
        return requirements.readlines()


setup(
    name="parser_gen",
    version="0.0.1",
    description="EBNF Parser and Grammar Parser Generator",
    long_description=long_description(),
    url="https://github.com/PiJoules/ebnf-parser",
    author="Leonard Chan",
    author_email="lchan1994@yahoo.com",
    license="Unlicense",
    classifiers=[
        "Development Status :: 3 - Alpha",
    ],
    keywords="ebnf, parser",
    packages=packages(),
    install_requires=install_requires(),
    test_suite="nose.collector",
    entry_points={
        "console_scripts": [
            "create_parser=scripts.create_parser:main",
        ],
    },
)
