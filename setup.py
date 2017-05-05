from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='awesome-crud',
    version='0.0',
    description='A sample Python project',
    long_description=long_description,
    url='https://github.com/yoshrote/awesome-crud',
    author='Josh Forman',
    author_email='josh@yoshrote.com',
    zip_safe=False,
    packages=find_packages(exclude=['example.py', 'docs', 'tests']),
    install_requires=['webob'],
)