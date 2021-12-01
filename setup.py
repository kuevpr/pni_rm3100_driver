from setuptools import setup

setup(
    name='pni_rm3100',
    version='0.1.1',    
    description='I2C Driver for the PNI Corp. RM3100 Geomagnetic Sensor',
    url='https://github.com/kuevpr/pni_rm3100_driver/',
    author='Prince Kuevor and Justin Schachter',
    author_email='kuevpr@umich.edu',
    license='MIT',
    install_requires=['smbus2',                     
    ],

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',  
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
    ],
    
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)
