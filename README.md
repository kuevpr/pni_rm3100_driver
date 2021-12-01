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

# Example Use Case
Import the library into your code and instantiate a `PniRm3100` object:
*NOTE: this will invoke an smbus transaction to write the configuration presets in PniRm3100.default_config()*

```
import pni_rm3100

# instantiate the device object and configures everything to the defaults
# NOTE: this will invoke an smbus transaction to write the configuration presets in PniRm3100.default_config() 
pni_rm3100_device = PniRm3100()

# Assign PNI Device Address for the pni_rm3100_device object to use in comms on the smbus
# Default is I2C_ADDR_LL (0x20) if it is not manually assigned as below
# device_address = pni_rm3100_device.DeviceAddress.I2C_ADDR_LL #0x20
# device_address = pni_rm3100_device.DeviceAddress.I2C_ADDR_HL #0x21
# device_address = pni_rm3100_device.DeviceAddress.I2C_ADDR_LH #0x22
device_address = pni_rm3100_device.DeviceAddress.I2C_ADDR_HH #0x23

#Alternatively:
pni_rm3100_device.assign_device_addr(0x21) #you can also input hex values here :)
```

Optional debug/status print statements enable/disable:
```
pni_rm3100_device.print_status_statements = True
pni_rm3100_device.print_debug_statements = True
```

Configure device registers (if you need to change them from the default presets):
*NOTE: In this driver, `assign_` functions set variable values in the software object only, `write_` functions must executed in order the values to be transmitted to the device, and `read_` functions are available to check the current values set on the device registers. The `write_config()` function can be used to write all the current object values to the device.*
```
    # Assign CCR Values
    # Here, we set X, Y, and Z CCR values to the defaull value of 0x00C8 = 200
    # See page 28 of the datasheet for more details
    pni_rm3100_device.assign_xyz_ccr(x_ccr_in=pni_rm3100_device.CcrRegister.CCR_DEFAULT, 
                                     y_ccr_in=pni_rm3100_device.CcrRegister.CCR_DEFAULT, 
                                     z_ccr_in=pni_rm3100_device.CcrRegister.CCR_DEFAULT)

    # Assign TMRC Values
    # Here, we set X, Y, and Z TMRC values to allow the sensors to be read at approximately 37Hz
    # Note, if the sample rate set by TMRC is higher than allowable from the CCR values, 
    # then CCR values will be used for that axis and the TMRC value will be ignored for that axis
    # (See note at end of pg31 of datasheet for an example)
    pni_rm3100_device.assign_tmrc(pni_rm3100_device.TmrcRegister.TMRC_37HZ)

    # Here's an example of how to write to and read from a single register. 
    # You can adjust the CCR values in the 'assign_xyz_ccr' function call above and ensure these are
    # Being written to the registers correctly
    # Note: 'smbus_pni_rm3100.write_config' will write to the CCR address for you.
    print("---- About to write to and read from CCR Registers ----\n")
    #write CCR: 
    pni_rm3100_device.write_ccr()
    #read CCR:
    read_x_ccr, read_y_ccr, read_z_ccr = pni_rm3100_device.read_ccr()

    # Here's an example on how to check some of the values internal to the 'pni_rm3100_device' object
    # A complete list of the member variables appear at the start of the "PniRm3100" class defiend in "src/pni_rm3100.py"
    print("Gain :", 1.0/pni_rm3100_device.x_scaling, "\tScaling: ", pni_rm3100_device.x_scaling,"\n")

    # Take the settings we've assigned (over the defaults) and write them their respective registers on the device 
    # Note: 'write_config()' will call the following functions and write values
    # to various registers on the RM3100
    #   write_bist   (bist register)
    #   write_poll   (poll register)
    #   write_ccr    (ccr register)
    #   write_tmrc   (tmrc register)
    #   write_hshake (hshake register)
    #   write_cmm    (cmm register)
    pni_rm3100_device.write_config()
    ```

    Cool! Now we've setup our RM3100 device, let's use it to collect single measurements:
    *NOTE: Returned units will be in microtesla unless otherwise specified*
    ```
    #single x reading:
    x_reading_microtesla = pni_rm3100_device.read_meas_x()

    #single y reading:
    y_reading_microtesla = pni_rm3100_device.read_meas_y()

    #single z reading:
    z_reading_microtesla = pni_rm3100_device.read_meas_z()

    #read and return all 3-axis in a single function call (returns a list)
    readings = pni_rm3100_device.read_meas()
    x_reading_microtesla = readings[0]
    y_reading_microtesla = readings[1]
    z_reading_microtesla = readings[2]
    ```

    End to end fucntion file that uses the device in a continuous read and average the values over some time:
    ```
    import pni_rm3100
    import math  
    import time

    pni_rm3100_device_0x20 = pni_rm3100.PniRm3100()
    pni_rm3100_device_0x20.print_status_statements = False
    pni_rm3100_device_0x20.print_debug_statements = False

    def collect_averaged_continuous_measurements(pni_rm3100_device, moving_avg_window = 10, dt_seconds = 0.1):
        # Now that we've enabled CMM (Continous Measurement Mode), let's read some magnetometer values!
        print("Reading measurements: [starting measurement loop]")
        x_mag_sum = y_mag_sum = z_mag_sum = 0
        for i in range(moving_avg_window):
            # Print measurement loop progress
            print("\n\n\t{} of {} in moving avg window".format(i, moving_avg_window))

            #Read magnetic field data (microtesla/uT output)
            magnetometer_readings = pni_rm3100_device.read_meas()

            x_mag = magnetometer_readings[0]
            y_mag = magnetometer_readings[1]
            z_mag = magnetometer_readings[2]

            # Update our summations
            x_mag_sum += x_mag
            y_mag_sum += y_mag
            z_mag_sum += z_mag

            # Sleep and incremenet iterator
            time.sleep(dt_seconds)

            # Take average of measurements and print
            x_mag_avg = x_mag_sum / moving_avg_window
            y_mag_avg = y_mag_sum / moving_avg_window
            z_mag_avg = z_mag_sum / moving_avg_window
            total_mag_avg = math.sqrt(pow(x_mag_avg,2) + pow(y_mag_avg,2) + pow(z_mag_avg,2))

            print(f"\nAverage magnetic field values over {moving_avg_window} iterations are:")
            print(f"\tmag_avg_x [uT]: {x_mag_avg}")
            print(f"\tmag_avg_y [uT]: {y_mag_avg}")
            print(f"\tmag_avg_z [uT]: {z_mag_avg}")
            print("\t--------------------------------")
            print(f"\tmag_field magnitude [uT]: {total_mag_avg}")

            return [x_mag_avg, y_mag_avg, z_mag_avg]
    ```

For questions or comments about this library please reach out to the developers at: 
* kuevorpr@umich.edu
* jschach@umich.edu



