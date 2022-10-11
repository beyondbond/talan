from setuptools import setup,find_packages
VERSION = '0.1.2' 
DESCRIPTION = 'Technical ALgorithmic ANalytics',
LONG_DESCRIPTION = 'Utility funcitions for financial analysis'

# Setting up
setup(
    name='talan',
    version=VERSION,
    description=DESCRIPTION,
    url='https://github.com/beyondbond/talan',
    author='Ted Hong',
    author_email='ted@beyondbond.com',
    license='BSD 2-clause',
    packages=['talan'],
    install_requires=['pandas','numpy','seaborn','scipy','matplotlib'],

    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Financial and Insurance Industry',
        'License :: OSI Approved :: BSD License',  
        'Operating System :: POSIX :: Linux',        
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.8',
    ],
)