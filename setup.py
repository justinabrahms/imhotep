from setuptools import setup, find_packages

setup(
    name='imhotep',
    version='2.0.0',
    packages=find_packages(),
    url='https://github.com/justinabrahms/imhotep',
    license='MIT',
    author='Justin Abrahms',
    author_email='justin@abrah.ms',
    description='A tool to pipe linters into code review',
    python_requires='>=3.0',
    install_requires=[
        'requests==2.20.0',
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
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Testing',
        'Topic :: Internet :: WWW/HTTP',
        'License :: OSI Approved :: MIT License',
    ],
)
