from distutils.core import setup
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='mlbv',
    version='0.1',
    packages=['mlbam'],
    url='https://github.com/kmac/mlbv',
    long_description=long_description,
    long_description_content_type='text/markdown',
    entry_points={
        "console_scripts": [
            "mlbv=mlbam.mlbv:main"
        ]
    },
    install_requires=[
        "configparser",
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
