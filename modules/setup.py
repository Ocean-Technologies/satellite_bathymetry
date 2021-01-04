from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path


# Get the long description from the README file
here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md')) as f:
    long_description = f.read()

# Get requirements
with open('requirements.txt') as f:
    install_requires = f.read().strip().split('\n')

setup(
    name='satellite_bathymetry',
    version='0.1.0',
    description='',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Ricardo Santa Cattarina and Vinícius Vaz',
    author_email='vinicvaz.dev@gmail.com',
    url='',
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires
)