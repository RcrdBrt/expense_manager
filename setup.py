from setuptools import setup, find_packages
import os

version = '0.0.2'

description = "A command-line expense manager and bank account logger."

install_requires = [
    'dataset',
    'pysqlcipher3',
    'cmd2',
    'colorama',
    'termcolor',
    'tabulate',
]

entry_points = {
    'console_scripts': ['expense_manager=expense_manager:start'],
}

setup(
    name='Expense_Manager',
    version=version,
    url='https://github.com/RcrdBrt/expense_manager',
    description=description,
    author='Riccardo Berto',
    author_email='riccardo@rcrdbrt.com',
    packages=find_packages(),
    entry_points=entry_points,
    #scripts=['bin/expense_manager'],
    install_requires=install_requires,
    include_package_data=True,
)
