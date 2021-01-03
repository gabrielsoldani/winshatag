#!/usr/bin/env python

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name='winshatag',
    version="0.0.1",
    author="Gabriel Soldani",
    author_email="winshatag@gabrielsoldani.com",
    description="Detect silent data corruption under Windows using checksums in NTFS alternate data streams.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gabrielsoldani/winshatag",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Environment :: Win32 (MS Windows)",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Topic :: System :: Archiving"
        "Topic :: System :: Filesystems"
        "Topic :: System :: Monitoring",
        "Topic :: System :: Recovery Tools"
    ],
    python_requires='>=3.8',
    entry_points={
        'console_scripts': ['winshatag=winshatag:main']
    }
)
