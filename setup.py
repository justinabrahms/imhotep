from setuptools import setup, find_packages

setup(
    name='imhotep',
    version='0.1.0',
    packages=find_packages(),
    url='https://github.com/justinabrahms/imhotep',
    license='MIT',
    author='Justin Abrahms',
    author_email='justin@abrah.ms',
    description='A tool to pipe linters into code review',
    requires=['requests'],
    extras_require={'pylint': 'PyLint'},
    entry_points = {
        'console_scripts': [
            'imhotep = imhotep.main:main',
        ],
    }
)
