import setuptools

setuptools.setup(
    name='pypi-cloudfiles',
    version='0.2.2',
    description=('A setuptools wrapper script for uploading packages to '
                 'Rackspace CloudFiles and building a PyPI compatible index'),
    #long_description=open('README.rst').read(),
    keywords='rackspace cloudfiles pypi package packaging',
    author='Matt Martz',
    author_email='matt@sivel.net',
    url='https://github.com/sivel/pypi-cloudfiles',
    license='Apache License, Version 2.0',
    py_modules=['pypi_cloudfiles'],
    install_requires=[
        'pyrax>=1.6.0',
    ],
    entry_points={
        'console_scripts': [
            'pypicf=pypi_cloudfiles:main'
        ]
    },
    classifiers=[
        'Programming Language :: Python',
        'Environment :: Console',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent'
    ]
)
