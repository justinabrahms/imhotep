from setuptools import setup, find_packages

setup(
    name='imhotep',
    version='1.1.1',
    packages=find_packages(),
    url='https://github.com/justinabrahms/imhotep',
    license='MIT',
    author='Justin Abrahms',
    author_email='justin@abrah.ms',
    description='A tool to pipe linters into code review',
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*',
    install_requires=[
        'requests==2.24.0',
        'six',
    ],
    extras_require={'pylint': 'PyLint'},
    entry_points={
        'console_scripts': [
            'imhotep = imhotep.main:main',
        ],
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Testing',
        'Topic :: Internet :: WWW/HTTP',
        'License :: OSI Approved :: MIT License',
    ],
)
