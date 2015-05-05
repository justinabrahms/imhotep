from setuptools import setup, find_packages

setup(
    name='imhotep',
    version='0.3.0',
    packages=find_packages(),
    url='https://github.com/justinabrahms/imhotep',
    license='MIT',
    author='Justin Abrahms',
    author_email='justin@abrah.ms',
    description='A tool to pipe linters into code review',
    install_requires=[
        'requests==2.6.0',
        'six',
    ],
    extras_require={'pylint': 'PyLint'},
    entry_points = {
        'console_scripts': [
            'imhotep = imhotep.main:main',
        ],
    }
)
