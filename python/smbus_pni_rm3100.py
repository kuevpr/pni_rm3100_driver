import pni_rm3100
import time
import smbus2

"""
Writes CCR(Cycle Count Register) values assigned to parameters in 'pni3100_object'
Inputs:
        i2cbus         - object of class 'SMBus' that has been set to a specific I2C line
        pni3100_object - object of class 'pni_rm3100'
                        This function assumes 'pni3100_object.default_config()' has been run
                        and the member variables in the pni3100_object have been modified to
                        the user's desired values.
"""
def write_ccr(i2cbus, pni3100_object):
    # Raspberry Pi is Little Endian while the RM3100 is Big Endian 
    # Thus, any integer that is Two or more Bytes needs to have 
    # its endianness (order of its bytes) reversed before sending over I2C

    # CCRX
    send_x_ccr = pni3100_object.endian_swap_int16(pni3100_object.x_ccr)
    x_return = i2cbus.write_word_data(pni3100_object.device_addr, pni3100_object.CcrRegister.CCR_REGISTER_ADDR, send_x_ccr)

    # CCRY
    send_y_ccr = pni3100_object.endian_swap_int16(pni3100_object.y_ccr)
    y_return = i2cbus.write_word_data(pni3100_object.device_addr, pni3100_object.CcrRegister.CCR_REGISTER_ADDR + 0x02, send_y_ccr)

    # CCRZ
    send_z_ccr = pni3100_object.endian_swap_int16(pni3100_object.z_ccr)
    z_return = i2cbus.write_word_data(pni3100_object.device_addr, pni3100_object.CcrRegister.CCR_REGISTER_ADDR + 0x04, send_z_ccr)
    
    return x_return, y_return, z_return

"""
Reads CCR(Cycle Count Register) values from the three CCR registers on the device
Inputs:
        i2cbus         - object of class 'SMBus' that has been set to a specific I2C line
        pni3100_object - object of class 'pni_rm3100'
                        This function assumes 'pni3100_object.default_config()' only that a
                        proper 'device_address' has been set
"""
def read_ccr(i2cbus, pni3100_object):
    # CCRX
    read_x_ccr = i2cbus.read_word_data(pni3100_object.device_addr, pni3100_object.CcrRegister.CCR_REGISTER_ADDR       )

    # CCRY
    read_y_ccr = i2cbus.read_word_data(pni3100_object.device_addr, pni3100_object.CcrRegister.CCR_REGISTER_ADDR + 0x02)

    # CCRZ
    read_z_ccr = i2cbus.read_word_data(pni3100_object.device_addr, pni3100_object.CcrRegister.CCR_REGISTER_ADDR + 0x04)

    if pni3100_object.print_status_statements:
        print("read_ccr: (", hex(read_x_ccr), ", ", hex(read_y_ccr), ", ", hex(read_z_ccr), ")", )

    return read_x_ccr, read_y_ccr, read_z_ccr


"""
write_tmrc
"""
def write_tmrc(i2cbus, pni3100_object):
    # TMRC
    write_return = i2cbus.write_byte_data(pni3100_object.device_addr, pni3100_object.TmrcRegister.TMRC_REGISTER_ADDR, pni3100_object.tmrc_byte)
    return write_return

"""
write_cmm
"""
def write_cmm(i2cbus, pni3100_object):
    # CMM
    write_return = i2cbus.write_byte_data(pni3100_object.device_addr, pni3100_object.CmmRegister.CMM_REGISTER_ADDR, pni3100_object.cmm_byte)
    return write_return

"""
write_hshake
"""
def write_hshake(i2cbus, pni3100_object):
    # HSHAKE
    write_return = i2cbus.write_byte_data(pni3100_object.device_addr, pni3100_object.HshakeRegister.HSHAKE_REGISTER_ADDR, pni3100_object.hshake_byte)
    return write_return

"""
write_poll
"""
def write_poll(i2cbus, pni3100_object):
    # POLL
    write_return = i2cbus.write_byte_data(pni3100_object.device_addr, pni3100_object.PollRegister.POLL_REGISTER_ADDR, pni3100_object.poll_byte)
    return write_return

"""
write_bist
"""
def write_bist(i2cbus, pni3100_object):
    # BIST
    write_return = i2cbus.write_byte_data(pni3100_object.device_addr, pni3100_object.BistRegister.BIST_REGISTER_ADDR, pni3100_object.bist_byte)
    return write_return

"""
read_status
"""
def read_status(i2cbus, pni3100_object):
    #STATUS (which is really just reading the DRDY bit)
    status_val = i2cbus.read_byte_data(pni3100_object.device_addr, pni3100_object.StatusRegister.STATUS_REGISTER_ADDR)
    data_is_ready = bool(status_val & pni3100_object.StatusRegister.STATUS_DRDY)
    return data_is_ready

"""
read_meas
"""
def read_meas(i2cbus, pni3100_object):
    # Check if a single measurement from either magnetometer has been requested
    single_meas_x = pni3100_object.poll_byte & pni3100_object.PollRegister.POLL_PMX
    single_meas_y = pni3100_object.poll_byte & pni3100_object.PollRegister.POLL_PMY
    single_meas_z = pni3100_object.poll_byte & pni3100_object.PollRegister.POLL_PMZ
    
    # Read from X Magnetometer    
    if pni3100_object.cmx or single_meas_x:
        x_mag_bytes = i2cbus.read_i2c_block_data(pni3100_object.device_addr, pni3100_object.MeasRegister.MEAS_REGISTER_ADDR       , 3)
        
        # Convert the unsigned 3-byte integer to a signed 3-byte integer
        x_mag_unsigned = int.from_bytes(x_mag_bytes, "big")
        x_mag_int = pni3100_object.uint24_to_int24(x_mag_unsigned)

        # Apply scaling
        x_mag_value = x_mag_int * pni3100_object.x_scaling

        # If we're in single measurement mode and we just read the measurement, clear the single measurement bit
        if single_meas_x:
            pni3100_object.poll_byte &= ~pni3100_object.PollRegister.POLL_PMX

    # Read from Y Magnetometer
    if pni3100_object.cmy or single_meas_y:
        y_mag_bytes = i2cbus.read_i2c_block_data(pni3100_object.device_addr, pni3100_object.MeasRegister.MEAS_REGISTER_ADDR + 0x03, 3)
        
        # Convert the unsigned 3-byte integer to a signed 3-byte integer
        y_mag_unsigned = int.from_bytes(y_mag_bytes, "big")
        y_mag_int = pni3100_object.uint24_to_int24(y_mag_unsigned)

        # Apply scaling
        y_mag_value = y_mag_int * pni3100_object.y_scaling

        # If we're in single measurement mode and we just read the measurement, clear the single measurement bit
        if single_meas_y:
            pni3100_object.poll_byte &= ~pni3100_object.PollRegister.POLL_PMY

    # Read from Z magnetometer
    if pni3100_object.cmz or single_meas_z:
        z_mag_bytes = i2cbus.read_i2c_block_data(pni3100_object.device_addr, pni3100_object.MeasRegister.MEAS_REGISTER_ADDR + 0x06, 3)
        
        # Convert the unsigned 3-byte integer to a signed 3-byte integer
        z_mag_unsigned = int.from_bytes(z_mag_bytes, "big")
        z_mag_int = pni3100_object.uint24_to_int24(z_mag_unsigned)

        # Apply scaling
        z_mag_value = z_mag_int * pni3100_object.z_scaling

        # If we're in single measurement mode and we just read the measurement, clear the single measurement bit
        if single_meas_z:
            pni3100_object.poll_byte &= ~pni3100_object.PollRegister.POLL_PMZ

    if pni3100_object.print_debug_statements:
        print("Read Meas")
        print("\tX bytes: [{}]".format(', '.join(hex(val) for val in x_mag_bytes)), "\tX Int Unsigned: ", hex(x_mag_unsigned), ", ", x_mag_unsigned, "\tX Int: ", x_mag_int, "\tX Value: ", x_mag_value)
        print("\tY Bytes: [{}]".format(', '.join(hex(val) for val in y_mag_bytes)), "\tY Int Unsigned: ", hex(y_mag_unsigned), ", ", y_mag_unsigned, "\tY Int: ", y_mag_int, "\tX Value: ", y_mag_value)
        print("\tZ Bytes: [{}]".format(', '.join(hex(val) for val in z_mag_bytes)), "\tZ Int Unsigned: ", hex(z_mag_unsigned), ", ", z_mag_unsigned, "\tZ Int: ", z_mag_int, "\tX Value: ", z_mag_value)


"""
read_bist
"""
def read_bist(i2cbus, pni3100_object):
    #BIST
    bist_value = i2cbus.read_byte_data(pni3100_object.device_addr, pni3100_object.BistRegister.BIST_REGISTER_ADDR)
    return bist_value

"""
read_poll
"""
def read_poll(i2cbus, pni3100_object):
    #POLL
    poll_value = i2cbus.read_byte_data(pni3100_object.device_addr, pni3100_object.PollRegister.POLL_REGISTER_ADDR)
    return poll_value

"""
read_tmrc
"""
def read_tmrc(i2cbus, pni3100_object):
    #TMRC
    tmrc_value = i2cbus.read_byte_data(pni3100_object.device_addr, pni3100_object.TmrcRegister.TMRC_REGISTER_ADDR)
    return tmrc_value

"""
read_cmm
"""
def read_cmm(i2cbus, pni3100_object):
    #CMM
    cmm_value = i2cbus.read_byte_data(pni3100_object.device_addr, pni3100_object.CmmRegister.CMM_REGISTER_ADDR)
    return cmm_value

"""
read_hshake
"""
def read_hshake(i2cbus, pni3100_object):
    #HSHAKE
    hshake_value = i2cbus.read_byte_data(pni3100_object.device_addr, pni3100_object.HshakeRegister.HSHAKE_REGISTER_ADDR)
    return hshake_value

"""
read_revid
"""
def read_revid(i2cbus, pni3100_object):
    #REVID
    revid_value = i2cbus.read_byte_data(pni3100_object.device_addr, pni3100_object.RevidRegister.REVID_REGISTER_ADDR)
    return revid_value

"""
init_rm3100
"""
def init_rm3100(i2cbus, pni3100_object):
    # write to bist register
    write_bist(i2cbus, pni3100_object)
    bist_val = read_bist(i2cbus, pni3100_object)

    # write to poll register
    write_poll(i2cbus, pni3100_object)
    poll_val = read_poll(i2cbus, pni3100_object)

    # write to ccr register
    write_ccr(i2cbus, pni3100_object)
    read_ccr(i2cbus, pni3100_object)

    # write to tmrc register
    write_tmrc(i2cbus, pni3100_object)
    tmrc_val = read_tmrc(i2cbus, pni3100_object)

    # write to hshake register
    write_hshake(i2cbus, pni3100_object)
    hshake_val = read_hshake(i2cbus, pni3100_object)
    
    # This will start Continuous Measurement Mode if CMM_START bit is set
    write_cmm(i2cbus, pni3100_object)
    cmm_val = read_cmm(i2cbus, pni3100_object)

"""
self_test
"""
def self_test(i2cbus, pni3100_object, attempt_num=10):
    # Make sure CMM (Continuous Measurement Mode) is Disabled
    pni3100_object.assign_cmm_byte(cmx=False, cmy=False, cmz=False, drdm=False, cmm_start=False)
    write_cmm(i2cbus, pni3100_object)

    # Write to BIST (Built-In Self Test) Registers with desired settings 
    # It's assumed BIST bits are set to desired values
    write_bist(i2cbus, pni3100_object)

    # Write to POLL to initiate Self Test 
    # It's assumed POLL bits are set to desired values
    write_poll(i2cbus, pni3100_object)

    # Read DRDY bit until it is HIGH
    i = 0
    while ((not read_status(i2cbus, pni3100_object)) and (i < attempt_num)):
        i += 1
        time.sleep(1) # Wait 1 second between each check of status bit

    if i == attempt_num:
        if pni3100_object.print_status_statements:
            print("ERROR in 'self_test()': \n\tDRDY bit never went high")
        return None

    # Read XOK, YOK, and ZOK bits from BIST register
    bist_value = read_bist(i2cbus, pni3100_object)

    if pni3100_object.print_status_statements:
        if bist_value & pni3100_object.BistRegister.BIST_XOK:
            print("X Magnetometer is OK")
        else:
            print("X Magnetometer is NOT OK")
        if bist_value & pni3100_object.BistRegister.BIST_YOK:
            print("Y Magnetometer is OK")
        else:
            print("Y Magnetometer is NOT OK")
        if bist_value & pni3100_object.BistRegister.BIST_ZOK:
            print("Z Magnetometer is OK")
        else:
            print("Z Magnetometer is NOT OK")

    return bist_value


"""
Writes the configuration parameters of a 'pni_rm3100' object to the 'i2cbus'
    Inputs:
        i2cbus         - object of class 'SMBus' that has been set to a specific I2C line
        pni3100_object - object of class 'pni_rm3100'
                        This function assumes 'pni3100_object.default_config()' has been run
                        and the member variables in the pni3100_object have been modified to
                        the user's desired values.
"""
def write_config(i2cbus, pni3100_object):
    blah = 0


# Defining main function
def main():
    # Instantiate Objects
    pni_object = pni_rm3100.PniRm3100()
    i2cbus = smbus2.SMBus(1) # Opens /dev/i2c-1

    # Select PNI Object Settings
    pni_object.print_debug_statements = True
    pni_object.print_status_statements = True

    # Assign PNI Device Address
    pni_object.assign_device_addr(pni_object.DeviceAddress.I2C_ADDR_HH)

    # Assign CCR Values
    # pni_object.assign_xyz_ccr(pni_object.CcrRegister.CCR_DEFAULT + 0x0002, pni_object.CcrRegister.CCR_DEFAULT + 0x0004, pni_object.CcrRegister.CCR_DEFAULT + 0x0006)

    print("About to read from CCR registers")
    # write_ccr(i2cbus, pni_object)
    read_ccr(i2cbus, pni_object)
    # print("Just read from CCR registers")

    print("Gain :", 1.0/pni_object.x_scaling, "\tScaling: ", pni_object.x_scaling)

    init_rm3100(i2cbus, pni_object)

    while 1:
        read_meas(i2cbus, pni_object)
        time.sleep(1)

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
    self_test(i2cbus, pni_object)
  
# Using the special variable 
if __name__=="__main__":
    main()
    # execute_self_test()