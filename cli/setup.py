from setuptools import setup

setup(
   name='i4c',
   version='1.0',
   description='CLI tool and module for I4C',
   author='Alimed',
   author_email='info@alimed.hu',
   packages=['i4c'],
   install_requires=['PyYAML', 'jsonpath_ng', 'click', 'jinja2', 'pynacl'],
)