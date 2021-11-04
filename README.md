# pni_rm3100_driver
Code to configure and read data from a PNI RM3100 Magnetometer

# Python Code
"smbus_pni_rm3100_examples.py"
- Dependancies: 'smbus_pni_3100.py', 'pni_rm3100.py', 'smbus2'
- This file has a couple examples on how to use the 'smbus_pni_3100.py' and 'pni_rm3100.py' functions to read data from the RM3100
- These examples have a lot of comments to walk the user through the steps

"smbus_pni_3100.py"
- Dependancies: 'pni_rm3100.py', 'smbus2', 'time'
- This file has functions to use I2C to write to and read from the registers on the 3100
- It relies on an object class from the 'pni_rm3100.py' file to make this processes easier

"pni_rm3100.py"
- Dependancies: 'enum'
This has many functions to help the user configure all the registers on the PNI RM3100





