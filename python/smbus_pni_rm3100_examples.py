import pni_rm3100
import time
import smbus_pni_rm3100
import smbus2

"""
execute_self_test
    Example of running a BIST (Built In Selt Test) to check the 
    status of the three magnetic field sensors.
"""
def execute_self_test():
    # Instantiate Objects
    pni_object = pni_rm3100.PniRm3100()
    i2cbus = smbus2.SMBus(1) # Opens /dev/i2c-1

    # Select PNI Object Settings
    pni_object.print_status_statements = True

    # Set PNI Device Address
    pni_object.assign_device_addr(pni_object.DeviceAddress.I2C_ADDR_HH)

    # Select which Axes we'd like to test during the Built-In Self Test (BIST)
    pni_object.assign_poll_byte(poll_x = True, poll_y = True, poll_z = True)

    # Select the Timeout and LRP for the BIST. Then Enable Self-Test mode
    pni_object.assign_bist_timeout(pni_object.BistRegister.BIST_TO_120us)
    pni_object.assign_bist_lrp(pni_object.BistRegister.BIST_LRP_4)
    pni_object.assign_bist_ste(True)

    # Run the Self Test
    smbus_pni_rm3100.self_test(i2cbus, pni_object)
"""
execute_continuous_measurements
    This example shows how to setup the RM3100 in continuous measurement mode (CMM)
    In CMM, you set the frequency that the sensors are sampled (using CCR and TMRC registers pg 28 and 31 of datasheet)
    Once you have set the sampling frequency, you are free to read from the MEAS register and gather data

    Note, the "assign" functions from "pni_object" do not write anything over I2C. 
    These functions simply adjust parameters in a struct and prepare for that data to be written to the sensor. 

    The "write" and "read" functions from "smbus_pni_rm3100" are communicating with the sensor over I2C. 
    These functions take in a "pni_object" that has been configued to the user's preferences
"""
def execute_continuous_measurements(num_measurements = 20):
    # Instantiate Objects
    pni_object = pni_rm3100.PniRm3100()
    i2cbus = smbus2.SMBus(1) # Opens /dev/i2c-1

    # Select PNI Object Settings
    # Set this to False (the default) if you don't want print statements in the terminal
    pni_object.print_status_statements = True

    # Assign PNI Device Address
    # Default is I2C_ADDR_LL (0x20)
    pni_object.assign_device_addr(pni_object.DeviceAddress.I2C_ADDR_HH)

    # Assign CCR Values
    # Here, we set X, Y, and Z CCR values to the defaull value of 0x00C8 = 200
    # See page 28 of the datasheet for more details
    # Note: 'assign_xyz_ccr' also adjusts the 'scaling' values which are used to convert measured data to physical units of uT (microTesla)
    pni_object.assign_xyz_ccr(x_ccr_in = pni_object.CcrRegister.CCR_DEFAULT, 
                              y_ccr_in = pni_object.CcrRegister.CCR_DEFAULT, 
                              z_ccr_in = pni_object.CcrRegister.CCR_DEFAULT)

    # Assign TMRC Values
    # Here, we set X, Y, and Z TMRC values to allow the sensors to be read at approximately 37Hz
    # Note, if the sample rate set by TMRC is higher than allowable from the CCR values, 
    # then CCR values will be used for that axis and the TMRC value will be ignored for that axis
    # (See note at end of pg31 of datasheet for an example)
    pni_object.assign_tmrc(pni_object.TmrcRegister.TMRC_37HZ)


    # Here's an example of how to write to and read from a register. 
    # You can adjust the CCR values in the 'assign_xyz_ccr' function call above and ensure these are
    # Being written to the registers correctly
    # Note: 'smbus_pni_rm3100.init_rm3100' will write to the CCR address for you.
    print("About to write to and read from CCR Registers")
    smbus_pni_rm3100.write_ccr(i2cbus, pni_object)
    read_x_ccr, read_y_ccr, read_z_ccr = smbus_pni_rm3100.read_ccr(i2cbus, pni_object)

    # Here's an example on how to check some of the values internal to the 'pni_object' object
    # A complete list of the member variables appear at the start of the "PniRm3100" class defiend in "pni_rm3100.py"
    print("Gain :", 1.0/pni_object.x_scaling, "\tScaling: ", pni_object.x_scaling)

    # Take the settings we've assigned and write them their respective registers on the Magnetometer 
    # Note: 'init_rm3100()' will call the following functions and write values
    # to various registers on the RM3100
    #   write_bist   (bist register)
    #   write_poll   (poll register)
    #   write_ccr    (ccr register)
    #   write_tmrc   (tmrc register)
    #   write_hshake (hshake register)
    #   write_cmm    (cmm register)
    smbus_pni_rm3100.init_rm3100(i2cbus, pni_object)

    # Now that we've enables CMM (Continous Measurement Mode), let's read some magnetometer values!
    i = 0
    while i < num_measurements:
        smbus_pni_rm3100.read_meas(i2cbus, pni_object)
        time.sleep(1)


# This is the code that will execute when you type "python3 smbus_pni_rm3100_examples" in the terminal
# Please only um-comment one of these at a time.
if __name__=="__main__":
    execute_continuous_measurements()   # Read data form RM3100 in continuous mode
    # execute_self_test()               # Perform a BIST (built-in self test) on the RM3100
    

