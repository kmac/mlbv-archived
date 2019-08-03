from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='mlbv',
    version='0.0.14',
    packages=find_packages(),
    url='https://github.com/kmac/mlbv',
    description="Command-line interface to MLB game information, game schedule and scores",
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        'Programming Language :: Python :: 3',
        'Environment :: Console',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Intended Audience :: End Users/Desktop',
    ],
    license="GPLv3",
    entry_points={
        "console_scripts": [
            "mlbv=mlbv.mlbam.mlbv:main"
        ]
    },
    package_data={
        'mlbv': [
            'README.md',
            'config.template'
        ]
    },
    install_requires=[
        "requests",
        "lxml",
        "streamlink",
        "python-dateutil"
    ],
    project_urls={
        'Bug Reports': 'https://github.com/kmac/mlbv/issues',
        'Source': 'https://github.com/kmac/mlbv'
    }
)
