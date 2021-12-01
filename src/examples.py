import math
import time

import pni_rm3100
###############################################################################
###Setup: 
## Instantiate Objects
pni_rm3100_device = pni_rm3100.PniRm3100()

## Choose (not assigning yet) a PNI Device Address (using PniRm3100() sub-classes), 
## uncomment one of the below lines:
# device_address = pni_rm3100_device.DeviceAddress.I2C_ADDR_LL #0x20
# device_address = pni_rm3100_device.DeviceAddress.I2C_ADDR_HL #0x21
# device_address = pni_rm3100_device.DeviceAddress.I2C_ADDR_LH #0x22
device_address = pni_rm3100_device.DeviceAddress.I2C_ADDR_HH #0x23

## Choose which test case/option you would like to run:
## uncomment one of the below lines:
# test_execution = 1 #execute_self_test()
test_execution = 2 #execute_continuous_measurements_with_assigned_settings()
# test_execution = 3 #execute_continuous_measurements_with_default_config
###############################################################################

"""
execute_self_test
    Example of running a BIST (Built In Selt Test) to check the 
    status of the three magnetic field sensors.
"""
def execute_self_test():
    # Set Print Settings
    pni_rm3100_device.print_status_statements = True
    pni_rm3100_device.print_debug_statements = True

    # Set PNI Device Address
    pni_rm3100_device.assign_device_addr(device_address)

    # Select which axes to test during the Built-In Self Test (BIST)
    pni_rm3100_device.assign_poll_byte(poll_x = True, poll_y = True, poll_z = True)

    # Select the Timeout and LRP for the BIST. Then Enable Self-Test mode
    pni_rm3100_device.assign_bist_timeout(pni_rm3100_device.BistRegister.BIST_TO_120us)
    pni_rm3100_device.assign_bist_lrp(pni_rm3100_device.BistRegister.BIST_LRP_4)
    pni_rm3100_device.assign_bist_ste(True)

    # Run the Self Test
    pni_rm3100_device.self_test()

###############################################################################
"""
execute_continuous_measurements_with_assigned_settings()
    This example shows how to setup the RM3100 in continuous measurement mode (CMM) with measurement averaging
    In CMM, you set the frequency that the sensors are sampled (using CCR and TMRC registers pg 28 and 31 of datasheet)
    Once you have set the sampling frequency, you are free to read from the MEAS register and gather data

    Note, the "assign" functions from "pni_rm3100_device" do not write anything over I2C. 
    These functions simply adjust parameters in a struct and prepare for that data to be written to the sensor. 

    The "write" and "read" functions from "smbus_pni_rm3100" are communicating with the sensor over I2C. 
    These functions take in a "pni_rm3100_device" that has been configued to the user's preferences
"""
def execute_continuous_measurements_with_assigned_settings(moving_avg_window = 10, dt_seconds = 0.1):
    # Select PNI Object Settings
    # Set this to False (the default) if you don't want the "read" functions printing data in the terminal
    pni_rm3100_device.print_status_statements = True
    pni_rm3100_device.print_debug_statements = True

    # Assign PNI Device Address
    # Default is I2C_ADDR_LL (0x20)
    # Note: this line is only necessary if you want to change from the default values --> see execute_continuous_measurements_with_default_config(),
    #       (it is still good to be explicit in your code/documentation!)
    pni_rm3100_device.assign_device_addr(device_address)

    # Assign CCR Values
    # Here, we set X, Y, and Z CCR values to the defaull value of 0x00C8 = 200
    # See page 28 of the datasheet for more details
    # Note: 'assign_xyz_ccr' also adjusts the 'scaling' values which are used to convert measured data to physical units of uT (microTesla)
    # Note: this line is only necessary if you want to change from the default values --> see execute_continuous_measurements_with_default_config()
    pni_rm3100_device.assign_xyz_ccr(x_ccr_in=pni_rm3100_device.CcrRegister.CCR_DEFAULT, 
                                     y_ccr_in=pni_rm3100_device.CcrRegister.CCR_DEFAULT, 
                                     z_ccr_in=pni_rm3100_device.CcrRegister.CCR_DEFAULT)

    # Assign TMRC Values
    # Here, we set X, Y, and Z TMRC values to allow the sensors to be read at approximately 37Hz
    # Note, if the sample rate set by TMRC is higher than allowable from the CCR values, 
    # then CCR values will be used for that axis and the TMRC value will be ignored for that axis
    # (See note at end of pg31 of datasheet for an example)
    # Note: this line is only necessary if you want to change from the default values --> see execute_continuous_measurements_with_default_config()
    pni_rm3100_device.assign_tmrc(pni_rm3100_device.TmrcRegister.TMRC_37HZ)


    # Here's an example of how to write to and read from a register. 
    # You can adjust the CCR values in the 'assign_xyz_ccr' function call above and ensure these are
    # Being written to the registers correctly
    # Note: 'smbus_pni_rm3100.write_config' will write to the CCR address for you.
    print("---- About to write to and read from CCR Registers ----\n")
    #write CCR: 
    pni_rm3100_device.write_ccr()
    #read CCR:
    read_x_ccr, read_y_ccr, read_z_ccr = pni_rm3100_device.read_ccr()

    # Here's an example on how to check some of the values internal to the 'pni_rm3100_device' object
    # A complete list of the member variables appear at the start of the "PniRm3100" class defiend in "pni_rm3100.py"
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
    
###############################################################################
"""
execute_continuous_measurements_with_default_config()
    This example shows how to setup the RM3100 in continuous measurement mode (CMM) with measurement averaging
    In CMM, you set the frequency that the sensors are sampled (using CCR and TMRC registers pg 28 and 31 of datasheet)
    Once you have set the sampling frequency, you are free to read from the MEAS register and gather data

    Note, the "assign" functions from "pni_rm3100_device" do not write anything over I2C. 
    These functions simply adjust parameters in a struct and prepare for that data to be written to the sensor. 

    The "write" and "read" functions from "smbus_pni_rm3100" are communicating with the sensor over I2C. 
    These functions take in a "pni_rm3100_device" that has been configued to the user's preferences
"""
def execute_continuous_measurements_with_default_config(moving_avg_window = 10, dt_seconds = 0.1):
    # Instantiate Objects
    pni_rm3100_device = pni_rm3100.PniRm3100()

    # Assign PNI Device Address
    # Default is I2C_ADDR_LL (0x20)
    # Note: this line is only necessary if you want to change from the default values --> see execute_continuous_measurements_with_default_config(),
    #       (it is still good to be explicit in your code/documentation!)
    pni_rm3100_device.assign_device_addr(device_address)

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

# This is the code that will execute when you type "python3 smbus_pni_rm3100_examples" in the terminal
# Please only un-comment one of these at a time.
if __name__=="__main__":
    if test_execution == 1:
        execute_self_test()                                      # Perform a BIST (built-in self test) on the RM3100
    elif test_execution == 2:
        execute_continuous_measurements_with_assigned_settings() # Read data form RM3100 in continuous mode
    elif test_execution == 3:
        execute_continuous_measurements_with_default_config()    # Read data form RM3100 in continuous mode
    else:
        print("UNDEFINED TEST CASE SELECTED")
