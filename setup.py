from setuptools import find_packages, setup

setup(
    name='pni_rm3100_lib',
    packages=find_packages(include=['pni_rm3100_lib']),
    version='0.0.1',
    description='A Python library to configure and interface with the PNI RM3100 geomagnetic sensor over I2C via smbus2',
    author='Price Kuevor, Justin Schachter',
    license='MIT',
    install_requires=[],
    setup_requires=['smbus2'],
)
