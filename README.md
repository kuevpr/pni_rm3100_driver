# -- UNDER CONSTRUCTION -- 

# pni_rm3100_driver
Code to configure and read data from a PNI RM3100 Magnetometer via a convenient Python 3 library. So far this code has only been tested on Raspberry Pi 4 computers. 

# Installation Instructions
Run: 

```
pip3 install git+https://github.com/kuevpr/pni_rm3100_driver.git@jschach_edits
```

# File Structure
* `src`
    * `pni_rm3100.py`
This file contains the class that is considered the 'driver' for the RM3100. In it you will find helpful sub-classes for register references and the implementation of the code to configure and use the `PniRm3100()` python object and sensor.  

    * `examples.py`
This examples script provides some helpful front end usage suggestions for the driver to be embedded in scripts or other libraries. In it you may choose from the various test options to run a sensor self test or run measurement tests. To run the code, ensure your sensor is connected to your host, this repository is cloned to your host, and  the setup options in the script are configured properly. Then, in the `src` directory run `python3 examples.py` to execute the test. 

* `tests`
Unit tests directory (currently not implemented)


For questions or comments about this library please reach out to the developers at: 
* kuevorpr@umich.edu
* jschach@umich.edu



