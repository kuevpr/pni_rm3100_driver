###############################################################################
#Authors: Prince Kuevor, Justin Schachter
#Purpose: This class serves as a hardware-level driver for the PNI Corp. RM3100
#         geomagnetic sensor. It currently only supports I2C (SMBus)
#         communications, but may be extended in the future to support SPI.  
###############################################################################

import time
from enum import IntEnum
import smbus2 as smbus

# from types import NoneType
class PniRm3100:
    """ Class for reading from PNI RM3100 Magnetometer"""

    ##################################################
    ##########      MEMBER VARIABLES        ##########
    ##################################################

    #TODO: make variables private via a leading underscore to make more official
    # The below set of variables may be:
    #   - configured in the object via 'assign_<>' functions
    #   - written to the device via 'write_<>' functions (see SMBus functions)
    #   - read from the device via 'read_<>' functions (see SMBus functions)
    device_addr = None  # Address of the RM3100
    x_ccr = None        # X axis Cycle Count Register
    y_ccr = None        # Y axis Cycle Count Register
    z_ccr = None        # Z axis Cycle Count Register
    x_scaling = None    # X axis LSB to uT scaling
    y_scaling = None    # Y axis LSB to uT scaling
    z_scaling = None    # Z axis LSB to uT scaling
    cmx = None          # X axis Continuous Mode
    cmy = None          # Y axis Continuous Mode
    cmz = None          # Z axis Continuous Mode
    cmm_byte = None     # Continuous Mode Byte
    tmrc_byte = None    # Timer for Continuous Mode
    lrp = None          # Built-In Self Test LR Periods
    hshake_byte = None  # Handshake byte: Effects how DRDY (Data Ready) register bit behaves
    bist_byte = None    # Built-In Self Test (BIST) Byte
    poll_byte = None    # Single Measurement POLL byte

    # Print statements useful for debugging code (really only useful for developer)
    print_debug_statements = False  

    # Intended to print register values when calling "read_" functions form I2C-side library
    print_status_statements = False

    # I2C Bus (SMBus)
    _i2c_bus = None 

    ##################################################
    ##########       MEMBER CLASSES         ##########
    ##################################################
    class DeviceAddress(IntEnum):
        I2C_ADDR_LL = 0x20 #SA0(MISO) pulled LOW, SA1(SSN) pulled LOW
        I2C_ADDR_HL = 0x21 #SA0(MISO) pulled LOW,  SA1(SSN) pulled HIGH
        I2C_ADDR_LH = 0x22 #SA0(MISO) pulled HIGH, SA1(SSN) pulled LOW
        I2C_ADDR_HH = 0x23 #SA0(MISO) pulled HIGH, SA1(SSN) pulled HIGH

    """
    CCR (Cycle Count Register) - pg28 of datasheet
        From Datasheet: Number of sensor oscillation cycles (cycle counts) during a measurment sequence. 
        Datasheet Recommendation: greater than ~30 Cycle Counts and less than ~400 Cycle Counts
        DEFAULT: 200 (0x00C8) Cycle Counts which gives 75 LSB/uT = 7.5 LSB/mG 
                 and a max sampling frequency of (440 / n) Hz where 'n' is number of axis read from
                 (e.g. 440Hz for single-axis reading and ~146Hz if reading from all 3 axes) 
    """
    class CcrRegister(IntEnum):
        CCR_REGISTER_ADDR   = 0x04
        CCR_DEFAULT         = 0x00C8 # 440Hz

    """
    CMM (Continuous Measurement Mode) Register - pg30 of datasheet
        These five bits are options when using Continuous Measurement Mode
    """
    class CmmRegister(IntEnum):
        CMM_REGISTER_ADDR = 0x01

        CMM_CMZ =    0x40   #Set this bit to read from the Z-axis magnetometer during CMM
        CMM_CMY =    0x20   #Set this bit to read from the Y-axis magnetometer during CMM
        CMM_CMX =    0x10   #Set this bit to read from the X-axis magnetometer during CMM

        CMM_DRDM =   0x04   #DRDY (Data Ready) Mode: Controls when DRDY pin will be set (Table 5-3)
                                #Set this bit for the DRDY pin to be set after a measurement on any axis
                                #Clear this bit for DRDY pin to be set after a full measurement as ...
                                #dictated by the CMX, CMY, and CMZ bits

        CMM_START =  0x01  #Set this bit (HIGH) to activate CMM
                            #Note: Writing to TMRC (below) will end CMM, so only start after TMRC is at desired value
                            #Note: Reading from the CMM register will end CMM


    """
    TMRC (TiMeR for Continuous mode) Register - pg31 of datasheet
        Sets the amount of time between measurements when using CMM (Continuous Measurement Mode)
    Note:CCR (Count Control Registers) determine the maximum sampling rate of sensors. 
            If the sampling frequency selected by TMRC is higher than CCR, then 
            the actual sampling rate will be CCR's value
            (See note at end of pg31 of datasheet for an example)
    """  
    class TmrcRegister(IntEnum): 
        TMRC_REGISTER_ADDR = 0x0B

        # RM3100 Timer Control Options (Continuous Measurement Mode)
        TMRC_600HZ =    0x92,   #~600  Hz
        TMRC_300HZ =    0x93,   #~300  Hz
        TMRC_150HZ =    0x94,   #~150  Hz
        TMRC_75HZ =     0x95,   #~75   Hz
        TMRC_37HZ =     0x96,   #~37   Hz (DEFAULT)
        TMRC_18HZ =     0x97,   #~18   Hz
        TMRC_9HZ =      0x98,   #~9    Hz
        TMRC_4_5HZ =    0x99,   #~4.5  Hz
        TMRC_2_3HZ =    0x9A,   #~2.3  Hz
        TMRC_1_2HZ =    0x9B,   #~1.2  Hz
        TMRC_0_6HZ =    0x9C,   #~0.6  Hz
        TMRC_0_3HZ =    0x9D,   #~0.3  Hz
        TMRC_0_015HZ =  0x9E,   #~0.015  Hz
        TMRC_0_0075HZ = 0x9F,   #~0.0075 Hz

    """
    POLL for a single measurement - pg 32 of datasheet
        Request a single measurement from the magnetometers
        DRDY will be HIGH after measurements from all requested axes have been completed
    Note: The POLL request will be ignored if in CMM (Continuous Measurement Mode)
    """
    class PollRegister(IntEnum):
        POLL_REGISTER_ADDR = 0x00

        POLL_PMZ = 0x40 #Set this bit to request a single measurement from the Z-axis magnetometer
        POLL_PMY = 0x20 #Set this bit to request a single measurement from the Y-axis magnetometer
        POLL_PMX = 0x10 #Set this bit to request a single measurement from the X-axis magnetometer
    
    """
    Status Register - pg33 of datsheet
        Read the DRDY (Data Ready) bit
        This is an alternative to reading the DRDY status from the DRDY pin
        Also, if in SPI mode, MISO will be pulled HIGH when DRDY goes HIGH
    Note: If in CMM (Continuous Measurement Mode), RM_3100_CCM_DRDM dictates when DRDY goes high
    """
    class StatusRegister(IntEnum):
        STATUS_REGISTER_ADDR = 0x34

        STATUS_DRDY = 0x80 # Yes, this is the only bit to be read from the STATUS register

    """
    Measurement Result Registers - pg33 of datsheet
        These nine consecutive registers (from 0x24 to 0x2C) hold the magnetic field reading from the three magnetometers. 
        Each axis has three bytes of data stored in 2's complement format
    Note: Conversion to these integer values to physical units depends on the CCR value chosen
    Note: You can read all 9 registers with a single 9-byte read request to 0x24
    Note: There's no sense in writing to these addresses
    """
    class MeasRegister(IntEnum):
        MEAS_REGISTER_ADDR = 0x24

    """
    BIST( Built-In Self Test) Register - pg 34 of datasheet
    """
    class BistRegister(IntEnum):
        BIST_REGISTER_ADDR = 0x33

        BIST_STE = 0x80     #Self-Test Enable: Set this bit to run the BIST (built-in self test) 
                            #   when POLL register is written to DRDY will go HIGH when the BIST is complete

        #The following bits are set to HIGH if the corresponding LR osccilator functioned correctly during the last self test
        #The value in these bits are only valid if STE is HIGH and the self test has been completed
        BIST_ZOK = 0x40   #Read-only. Status of Z-axis LR oscillators 
        BIST_YOK = 0x20   #Read-only. Status of Y-axis LR oscillators 
        BIST_XOK = 0x10   #Read-only. Status of X-axis LR oscillators 

        #Together, these two bits determine timeout period for the LR oscillator periods (Table 5-6)
        BIST_BW1 = 0x08
        BIST_BW0 = 0x04

        #There are three possible values for the Timeout bits of the BIST register
        BIST_TO_30us = BIST_BW0             #Timeout is 30us  (1 Sleep Oscillation Cycle)
        BIST_TO_60us = BIST_BW1             #Timeout is 60us  (2 Sleep Oscillation Cycles)
        BIST_TO_120us = BIST_BW1 + BIST_BW0 #Timeout is 120us (3 Sleep Oscillation Cycles)

        #Together, these two bits define number of LR periods for measurment during the BIST (Table 5-7)
        BIST_BP1 = 0x02
        BIST_BP0 = 0x01

        #There are three possible values for the LR Period bits of the BIST register
        BIST_LRP_1 = BIST_BP0            #1 LR Period
        BIST_LRP_2 = BIST_BP1            #2 LR Periods
        BIST_LRP_4 = BIST_BP1 + BIST_BP0 #4 LR Periods

    """
    HSHAKE (Handshake) Register - pg 36 of datasheet
        Determines when DRDY pin will be cleared (LOW)
        Also gives debugging information fora  few erros (see pg 36)
    """
    class HshakeRegister(IntEnum):
        HSHAKE_REGISTER_ADDR = 0x35

        HSHAKE_NACK2 = 0x40   #Read-only. Assigned HIGH when attempting to read from a Measurement Result register when DRDY is LOW (i.e. data is not ready)
        HSHAKE_NACK1 = 0x20   #Read-only. Assigned HIGH when writing to POLL when CMM is active or writing to CMM when POLL is active
        HSHAKE_NACK0 = 0x10   #Read-only. Assigned HIGH when writing to an undefined register

        HSHAKE_DRC1 =  0x02   #Setting this bit means DRDY is cleared when reading any Measurement Result Regisers (DEFAULT: HIGH)
        HSHAKE_DRC0 =  0x01   #Setting this bit means DRDY is cleared when writing to any RM3100 register (DEFAULT: HIGH)

    """
    REVID (Revision ID) Register - pg 36 of datasheet
        Read-only. Single byte register that returns revision identification of the MagI2C.
    """
    class RevidRegister(IntEnum):
        REVID_REGISTER_ADDR = 0x36

    ##################################################
    ##########      MEMBER METHODS          ##########
    ##################################################

    """
    __cycle_count_to_scaling "Cycle Count to Gain (uT/LSB)
    Table 3.1 (pg. 5 of datasheet) Gives the gain/scaling for three Cycle Count values
    The following link on the PNI Help Center confirms the relationship between Cycle Count and gain is linear
        https://pnisensor.zendesk.com/hc/en-us/articles/360016009534-WHAT-IS-THE-RELATIONSHIP-BETWEEN-CYCLE-COUNT-AND-GAIN-
    """
    def __cycle_count_to_scaling(self, cycle_count):
        gain = (150.0 / 400.0) * cycle_count    # [LSB / uT]
        scaling = 1.0 / gain                    # [uT / LSB]
        return scaling  


    """
    __init__() "Constructor"
    """
    def __init__(self):
        self.default_config()
        self.data = []


    """
    default_config() "Default Configuration"
    """
    def default_config(self):
        #I2C Bus Setup --> defaults to Raspberry Pi default I2C bus number
        self._i2c_bus = smbus.SMBus(1)

        # Device Address
        self.device_addr = self.DeviceAddress.I2C_ADDR_LL

        # Cycle Counter Register (CCR)
        self.x_ccr = self.CcrRegister.CCR_DEFAULT
        self.y_ccr = self.CcrRegister.CCR_DEFAULT
        self.z_ccr = self.CcrRegister.CCR_DEFAULT

        # LSB scaling (depends on CCR value)
        self.x_scaling = 1.0/75.0   # uT/LSB: conversion of 1/75 if x_ccr is 0x00C8 (default)
        self.y_scaling = 1.0/75.0   # uT/LSB: conversion of 1/75 if y_ccr is 0x00C8 (default)
        self.z_scaling = 1.0/75.0   # uT/LSB: conversion of 1/75 if z_ccr is 0x00C8 (default)

        # Timer for Continuous Mode (TMRC)
        self.tmrc_byte = self.TmrcRegister.TMRC_37HZ

        # Continuous Measurement Mode (CMM)
        # CMM register is a single byte that consists of the following bits
        cmx_bit = self.CmmRegister.CMM_CMX # Default: read from x magnetometer
        cmy_bit = self.CmmRegister.CMM_CMY # Default: read from y magnetometer
        cmz_bit = self.CmmRegister.CMM_CMZ # Default: read from z magnetometer
        self.cmx = self.cmy = self.cmz = True

        drdm_bit = self.CmmRegister.CMM_DRDM       # Read 'CmmRegister' Class of this code (or page 30 of datasheet) 
        cmm_start_bit = self.CmmRegister.CMM_START   # Default: Activate CMM (continuous measurement mode)

        self.cmm_byte = cmx_bit | cmy_bit | cmz_bit | drdm_bit | cmm_start_bit
        
        # Single Measurement (POLL)
        self.poll_byte = 0x00 # Disable Single measurement
        
        # Built-In Self Test (BIST)
        bist_timeout = self.BistRegister.BIST_TO_120us  # BIST Timeout (Table 5-6)
        bist_lrp = self.BistRegister.BIST_LRP_4         # BIST LR Period (Table 5-7)
        self.bist_byte = bist_timeout | bist_lrp

        # Handshake (HSHAKE)
        # HSHAKE register is a single byte that consists of the following bits
        drc1_bit = self.HshakeRegister.HSHAKE_DRC1 # Default: clear DRDY when writing to any register
        drc0_bit = self.HshakeRegister.HSHAKE_DRC0 # Default: clear DRDY when reading any Measurement Result
        self.hshake_byte = drc1_bit | drc0_bit

        #TODO: THERE ARE ISSUES WITH THIS SINCE default_addr selects 0x20 and if you are not using a 0x20 device it causes the lib to not work
        # # Write this configuration to the device
        # self.write_config()

    """
    change_i2c_bus() 
        Input: 
            bus - bus (int or str) – i2c bus number (e.g. 0 or 1) or an absolute file path (e.g. ‘/dev/i2c-42’).
            force - boolean
        Effects:
            self._i2c_bus
    """
    def change_i2c_bus(self, bus=None, force=None):
        self._i2c_bus = smbus.SMBus(bus, force)
    
    """
    assign_device_addr() "Assign Device Address"
        Input: 
            input_addr - One of the four possible device addresses for the PNI RM3100. 
                         Can be passed as enum (e.g. self.DeviceAddress.I2C_ADDR_HH) or Hex value (e.g. 0x23)
                         'H' and 'L' are in SA0 and SA1 order (the actual hardware pins)
        Effects:
            self.device_addr
    """
    def assign_device_addr(self, input_addr):
        if (input_addr == self.DeviceAddress.I2C_ADDR_LL) or (input_addr == 0x20):
            self.device_addr = self.DeviceAddress.I2C_ADDR_LL
        elif (input_addr == self.DeviceAddress.I2C_ADDR_HL) or (input_addr == 0x21):
            self.device_addr = self.DeviceAddress.I2C_ADDR_HL
        elif (input_addr == self.DeviceAddress.I2C_ADDR_LH) or (input_addr == 0x22):
            self.device_addr = self.DeviceAddress.I2C_ADDR_LH
        elif (input_addr == self.DeviceAddress.I2C_ADDR_HH) or (input_addr == 0x23):
            self.device_addr = self.DeviceAddress.I2C_ADDR_HH
        else:
            if self.print_status_statements:
                print("ERROR in 'assign_device_addr()': \n\tDevice address given is not one of the four valid addresses for the PNI RM3100")

    """
    assign_xyz_ccr() Assign CCR Values for X, Y, and Z axes
        Input: 
            x_ccr_in - Desired CCR value for X axis. 
            y_ccr_in - Desired CCR value for Y axis. 
            z_ccr_in - Desired CCR value for Z axis. 

            All Input CCR values must be 2-byte integers. Or 'None'.
            'None' will leave that particular axis unchanged
            See Line 37 of this document or page 28 of the datasheet for more information. 
        Effects:
            If x_ccr_in is a valid Integer
                self.x_ccr
                self.x_scaling
            If y_ccr_in is a valid Integer
                self.y_ccr
                self.y_scaling
            If z_ccr_in is a valid Integer
                self.z_ccr
                self.z_scaling        
    """
    def assign_xyz_ccr(self, x_ccr_in = None, y_ccr_in = None, z_ccr_in = None):
        ##### ERROR CHECKING #####
        # X axis error checking
        x_is_int = isinstance(x_ccr_in, int)
        x_is_none = x_ccr_in == None

        if not x_is_int and x_is_none:
            if self.print_status_statements:
                print("ERROR in 'assign_xyz_ccr()':\n\t 'x_ccr_in' input must be two-byte integer or None")
            return
        
        if x_is_int and (x_ccr_in < 0 or x_ccr_in > 0xFFFF):
            if self.print_status_statements:
                print("ERROR in 'assign_xyz_ccr()':\n\t 'x_ccr_in' must be >= 0 and <= 0xFFFF")
            return

    
        # Y axis error checking
        y_is_int = isinstance(y_ccr_in, int)
        y_is_none = y_ccr_in == None

        if not y_is_int and y_is_none:
            if self.print_status_statements:
                print("ERROR in 'assign_xyz_ccr()':\n\t 'y_ccr_in' input must be two-byte integer or None")
            return
        
        if y_is_int and (y_ccr_in < 0 or y_ccr_in > 0xFFFF):
            if self.print_status_statements:
                print("ERROR in 'assign_xyz_ccr()':\n\t 'y_ccr_in' must be >= 0 and <= 0xFFFF")
            return

        # Z axis error checking
        z_is_int = isinstance(z_ccr_in, int)
        z_is_none = z_ccr_in == None

        if not z_is_int and z_is_none:
            if self.print_status_statements:
                print("ERROR in 'assign_xyz_ccr()':\n\t 'z_ccr_in' input must be two-byte integer or None")
            return
        
        if z_is_int and (z_ccr_in < 0 or z_ccr_in > 0xFFFF):
            if self.print_status_statements:
                print("ERROR in 'assign_xyz_ccr()':\n\t 'z_ccr_in' must be >= 0 and <= 0xFFFF")
            return

        ##### ASSIGN VALUES #####
        if x_ccr_in != None:
            self.x_ccr = x_ccr_in
            self.x_scaling = self.__cycle_count_to_scaling(x_ccr_in)
        if y_ccr_in != None:
            self.y_ccr = y_ccr_in
            self.y_scaling = self.__cycle_count_to_scaling(y_ccr_in)
        if z_ccr_in != None:
            self.z_ccr = z_ccr_in
            self.z_scaling = self.__cycle_count_to_scaling(z_ccr_in)


    """
    assign_tmrc() Assign CCR Values for X, Y, and Z axes
        Input: 
            tmrc_in - Desired TMRC value. 
                      There are only 14 possible options here
                      (See Table 5-4 on pg 32 of Datasheet)
        Effects:
            self.tmrc_byte       
    """
    def assign_tmrc(self, tmrc_in = TmrcRegister.TMRC_37HZ):
        
        if tmrc_in == self.TmrcRegister.TMRC_600HZ:
            self.tmrc_byte = self.TmrcRegister.TMRC_600HZ

        elif tmrc_in == self.TmrcRegister.TMRC_300HZ:
            self.tmrc_byte = self.TmrcRegister.TMRC_300HZ

        elif tmrc_in == self.TmrcRegister.TMRC_150HZ:
            self.tmrc_byte = self.TmrcRegister.TMRC_150HZ

        elif tmrc_in == self.TmrcRegister.TMRC_75HZ:
            self.tmrc_byte = self.TmrcRegister.TMRC_75HZ

        elif tmrc_in == self.TmrcRegister.TMRC_37HZ:
            self.tmrc_byte = self.TmrcRegister.TMRC_37HZ

        elif tmrc_in == self.TmrcRegister.TMRC_18HZ:
            self.tmrc_byte = self.TmrcRegister.TMRC_18HZ

        elif tmrc_in == self.TmrcRegister.TMRC_9HZ:
            self.tmrc_byte = self.TmrcRegister.TMRC_9HZ

        elif tmrc_in == self.TmrcRegister.TMRC_4_5HZ:
            self.tmrc_byte = self.TmrcRegister.TMRC_4_5HZ

        elif tmrc_in == self.TmrcRegister.TMRC_2_3HZ:
            self.tmrc_byte = self.TmrcRegister.TMRC_2_3HZ

        elif tmrc_in == self.TmrcRegister.TMRC_1_2HZ:
            self.tmrc_byte = self.TmrcRegister.TMRC_1_2HZ

        elif tmrc_in == self.TmrcRegister.TMRC_0_6HZ:
            self.tmrc_byte = self.TmrcRegister.TMRC_0_6HZ

        elif tmrc_in == self.TmrcRegister.TMRC_0_3HZ:
            self.tmrc_byte = self.TmrcRegister.TMRC_0_3HZ

        elif tmrc_in == self.TmrcRegister.TMRC_0_015HZ:
            self.tmrc_byte = self.TmrcRegister.TMRC_0_015HZ

        elif tmrc_in == self.TmrcRegister.TMRC_0_0075HZ:
            self.tmrc_byte = self.TmrcRegister.TMRC_0_0075HZ

        else:
            print("ERROR in 'assign_tmrc()':\n\t 'tmrc_in' must be one of 14 possible values (See table 5-4 on Page 32)")

    """
    assign_cmm_byte() "Assign CMM (Continuous Measurement Mode) Byte"
        Input: 
            All Inputs must be boolean True or False
                cmx    
                    True : Read from X Magnetometer in CMM (default)
                    False: Ignore X Magnetometer in CMM
                cmy    
                    True : Read from Y Magnetometer in CMM (default)
                    False: Ignore Y Magnetometer in CMM
                cmz    
                    True : Read from Z Magnetometer in CMM (default)
                    False: Ignore Z Magnetometer in CMM
                drdm   
                    True : DRDY pin will be set HIGH after a measurement on _any_ axis (default)
                    False: DRDY pin will be set HIGH after a "full" measurement from all requested axes 
                           (as dictated by CMX, CMY, and CMZ bits)
                cmm_start
                    True : Start CMM (default)
                           Note: Writing to TMRC register will end CMM
                           Note: Reading from the CMM register will end CMM
                    False: Do not activate CMM

        Effects:
            self.cmm_byte
            self.cmx
            self.cmy
            self.cmz
    """
    def assign_cmm_byte(self, cmx = True, cmy = True, cmz = True, drdm = True, cmm_start = True):
        self.cmx = cmx
        self.cmy = cmy
        self.cmz = cmz

        self.cmm_byte = 0x00

        # Assign CMX Bit
        if cmx:
            self.cmm_byte |= self.CmmRegister.CMM_CMX

        # Assign CMY Bit
        if cmy:
            self.cmm_byte |= self.CmmRegister.CMM_CMY

        # Assign CMZ Bit
        if cmz:
            self.cmm_byte |= self.CmmRegister.CMM_CMZ

        # Assign DRDM Bit
        if drdm:
            self.cmm_byte |= self.CmmRegister.CMM_DRDM

        # Assign START Bit
        if cmm_start:
            self.cmm_byte |= self.CmmRegister.CMM_START


    """
    assign_hshake_byte() "Assign HSHAKE (Handshake) Byte"
        Input: 
            All Inputs must be boolean True or False
                drc1    
                    True : Clear DRDY when reading any Measurement Result (default)
                    False: Do NOT clear DRDY when reading any Measurement Result
                drc0    
                    True : Clear DRDY when writing to any register (default)
                    False: Do NOT clear DRDY when writing to any register
        Effects:
            self.hshake_byte
    """
    def assign_hshake_byte(self, drc1 = True, drc0 = True):
        self.hshake_byte = 0x00
        
        # Assign DRC1 Bit
        if drc1:
            self.hshake_byte |= self.HshakeRegister.HSHAKE_DRC1

        # Assign DRC0 Bit
        if drc0:
            self.hshake_byte |= self.HshakeRegister.HSHAKE_DRC0

    """
    assign_bist_timeout() "Assign BIST (Built-In Self Test) Timeout Bits"
        Input: 
            Input must be 'BIST_TO_30us', 'BIST_TO_60us', or 'BIST_TO_120us' from 'BistRegister' Class
                timeout   
                    BIST_TO_30us  : Timeout period for LR oscillations is 1 Sleep Oscillation Cycle (30us)
                    BIST_TO_60us  : Timeout period for LR oscillations is 2 Sleep Oscillation Cycles (60us)
                    BIST_TO_120us : Timeout period for LR oscillations is 4 Sleep Oscillation Cycles (120us)
        Effects:
            self.bist_byte
    """
    def assign_bist_timeout(self, timeout):
        if timeout == self.BistRegister.BIST_TO_30us:
            # Clear current Timeout Bits
            self.bist_byte &= ~(self.BistRegister.BIST_BW0 + self.BistRegister.BIST_BW1)
            self.bist_byte |= timeout
        elif timeout == self.BistRegister.BIST_TO_60us:
            # Clear current Timeout Bits
            self.bist_byte &= ~(self.BistRegister.BIST_BW0 + self.BistRegister.BIST_BW1)
            self.bist_byte |= timeout
        elif timeout == self.BistRegister.BIST_TO_120us:
            # Clear current Timeout Bits
            self.bist_byte &= ~(self.BistRegister.BIST_BW0 + self.BistRegister.BIST_BW1)
            self.bist_byte |= timeout
        else:
            if self.print_status_statements:
                print("ERROR in 'assign_bist_timeout()':\n\t 'timeout' must be BIST_TO_30us, BIST_TO_60us, or BIST_TO_120us")
            return
            
    """
    assign_bist_lrp() "Assign BIST (Built-In Self Test) LR (Inductor-Resistor) Period Bits"
        Input: 
            Input must be 'BIST_LRP_1', 'BIST_LRP_2', or 'BIST_LRP_4' from 'BistRegister' Class
                lrp
                    BIST_LRP_1 : 1 LR Periods for measurement during self test
                    BIST_LRP_2 : 2 LR Periods for measurement during self test
                    BIST_LRP_4 : 4 LR Periods for measurement during self test
        Effects:
            self.bist_byte
    """
    def assign_bist_lrp(self, lrp):
        if lrp == self.BistRegister.BIST_LRP_1:
            # Clear current Timeout Bits
            self.bist_byte &= ~(self.BistRegister.BIST_BP0 + self.BistRegister.BIST_BP1)
            self.bist_byte |= lrp
        elif lrp == self.BistRegister.BIST_LRP_2:
            # Clear current Timeout Bits
            self.bist_byte &= ~(self.BistRegister.BIST_BP0 + self.BistRegister.BIST_BP1)
            self.bist_byte |= lrp
        elif lrp == self.BistRegister.BIST_LRP_4:
            # Clear current Timeout Bits
            self.bist_byte &= ~(self.BistRegister.BIST_BP0 + self.BistRegister.BIST_BP1)
            self.bist_byte |= lrp
        else:
            if self.print_status_statements:
                print("ERROR in 'assign_bist_lrp()':\n\t 'lrp' must be BIST_LRP_1, BIST_LRP_2, or BIST_LRP_4")
            return

    """
    assign_bist_ste() "Assign BIST (Built-In Self Test) Self Test Enable bit"
        Input: 
            Input must be boolean True or False
                ste  
                    True : Run BIST when POLL register is written to
                           Self test ends when DRDY goes HIGH
                    False: Do not start BIST
        Effects:
            self.bist_byte
    """
    def assign_bist_ste(self, ste):
        if ste:
            self.bist_byte |= self.BistRegister.BIST_STE
        else:
            self.bist_byte &= ~self.BistRegister.BIST_STE

    """
    assign_poll_byte() "Assign POLL (Single Measurement) Byte"
        Input: 
            All Inputs must be boolean True or False
                poll_x    
                    True : Request a single measurement from the X Magnetometer
                    False: Do not request a single measurement from X Magnetometer (default)
                poll_y    
                    True : Request a single measurement from the Y Magnetometer
                    False: Do not request a single measurement from Y Magnetometer (default)
                poll_z    
                    True : Request a single measurement from the Z Magnetometer
                    False: Do not request a single measurement from Z Magnetometer (default)
        Effects:
            self.poll_byte
    """
    def assign_poll_byte(self, poll_x = False, poll_y = False, poll_z = False):
        self.poll_byte = 0x00

        # Assign CMX Bit
        if poll_x:
            self.poll_byte |= self.PollRegister.POLL_PMX

        # Assign CMY Bit
        if poll_y:
            self.poll_byte |= self.PollRegister.POLL_PMY

        # Assign CMZ Bit
        if poll_z:
            self.poll_byte |= self.PollRegister.POLL_PMZ

    """
    uint24_to_int24() "Convert from Unsigned three-byte number fo signed three-byte Number"
        This is needed for converting from RM3100 byte counts to a magnetic field value in uT (micro-Tesla)

        Input: 
            Input will be masked with 0x 00 FF FF FF to ensure value is only three bytes
                unsigned_int24    
                    - Three bytes from RM3100 MeasRegister

        Returns:
            Signed three-byte integer

    """
    def uint24_to_int24(self, unsigned_int24):
        # Python does not actually have a 3-byte integer object. So it'll give us four bytes
        # This line ensures that the Most Significant byte is zeroed out
        unsigned_int24 &= 0x00FFFFFF

        # If this bit is set, the integer is actually a negative number
        three_byte_sign_bit = 0x00800000

        # Convert our unsigned int to a signed int
        signed_int24 = unsigned_int24
        if signed_int24 & three_byte_sign_bit:
            signed_int24 = (signed_int24 & ~three_byte_sign_bit) - three_byte_sign_bit

        return signed_int24

    ##################################
    # Endian Swap Utility Functions
    ##################################
    """
    endian_swap_int16()
    """
    def endian_swap_int16(self, input_int16):
        output_int16 = ((input_int16 << 8) & 0xFF00) | \
                        ((input_int16 >> 8) & 0x00FF)

        return output_int16
    
    """
    endian_swap_int16()
    """
    def endian_swap_int32(self, input_int32):
        output_int32 = ((input_int32 << 24) & 0xFF000000) | \
                       ((input_int32 << 8)  & 0x00FF0000) | \
                       ((input_int32 >> 8)  & 0x0000FF00) | \
                       ((input_int32 >> 24) & 0x000000FF)

        return output_int32

    ##################################
    # SMBus Methods
    ##################################
    """
    write_ccr() 
    
    Writes CCR(Cycle Count Register) values assigned to parameters in self
    
    This function assumes member variables in the object have been 
    modified to the user's desired values.
    """
    def write_ccr(self):
        # Raspberry Pi is Little Endian while the RM3100 is Big Endian 
        # Thus, any integer that is Two or more Bytes needs to have 
        # its endianness (order of its bytes) reversed before sending over I2C

        # CCRX
        send_x_ccr = self.endian_swap_int16(self.x_ccr)
        x = self._i2c_bus.write_word_data(self.device_addr, 
                                          self.CcrRegister.CCR_REGISTER_ADDR, 
                                          send_x_ccr)

        # CCRY
        send_y_ccr = self.endian_swap_int16(self.y_ccr)
        y = self._i2c_bus.write_word_data(self.device_addr, 
                                          self.CcrRegister.CCR_REGISTER_ADDR + 0x02, 
                                          send_y_ccr)

        # CCRZ
        send_z_ccr = self.endian_swap_int16(self.z_ccr)
        z = self._i2c_bus.write_word_data(self.device_addr, 
                                          self.CcrRegister.CCR_REGISTER_ADDR + 0x04, 
                                          send_z_ccr)
        
        return x, y, z
    
    #TODO: chance self._i2c_bus and pni_obj to self._i2c_bus and self
    """
    read_ccr()
    
    Reads CCR(Cycle Count Register) values from the three CCR registers on the device
    """
    def read_ccr(self):
        # CCRX
        read_x_ccr = self._i2c_bus.read_word_data(self.device_addr, 
                                                  self.CcrRegister.CCR_REGISTER_ADDR)

        # CCRY
        read_y_ccr = self._i2c_bus.read_word_data(self.device_addr,
                                                  self.CcrRegister.CCR_REGISTER_ADDR + 0x02)

        # CCRZ
        read_z_ccr = self._i2c_bus.read_word_data(self.device_addr, 
                                                  self.CcrRegister.CCR_REGISTER_ADDR + 0x04)

        if self.print_status_statements:
            print("read_ccr: (x: ", hex(read_x_ccr), ", y: ", hex(read_y_ccr), ", z: ", hex(read_z_ccr), ")")

        return read_x_ccr, read_y_ccr, read_z_ccr

    """
    write_tmrc() 

    This function assumes member variables in the object have been 
    modified to the user's desired values.
    """
    def write_tmrc(self):
        # TMRC
        write_return_data = self._i2c_bus.write_byte_data(self.device_addr,
                                                          self.TmrcRegister.TMRC_REGISTER_ADDR,
                                                          self.tmrc_byte)
        return write_return_data

    """
    write_cmm()

    This function assumes member variables in the object have been 
    modified to the user's desired values.
    """
    def write_cmm(self):
        # CMM
        write_return_data = self._i2c_bus.write_byte_data(self.device_addr,
                                                          self.CmmRegister.CMM_REGISTER_ADDR,
                                                          self.cmm_byte)
        return write_return_data

    """
    write_hshake()

    This function assumes member variables in the object have been 
    modified to the user's desired values.
    """
    def write_hshake(self):
        # HSHAKE
        write_return_data = self._i2c_bus.write_byte_data(self.device_addr,
                                                          self.HshakeRegister.HSHAKE_REGISTER_ADDR,
                                                          self.hshake_byte)
        return write_return_data

    """
    write_poll()

    This function assumes member variables in the object have been 
    modified to the user's desired values.
    """
    def write_poll(self):
        # POLL
        write_return = self._i2c_bus.write_byte_data(self.device_addr,
                                                     self.PollRegister.POLL_REGISTER_ADDR,
                                                     self.poll_byte)
        return write_return

    """
    write_bist()

    This function assumes member variables in the object have been 
    modified to the user's desired values.
    """
    def write_bist(self):
        # BIST
        write_return = self._i2c_bus.write_byte_data(self.device_addr,
                                                     self.BistRegister.BIST_REGISTER_ADDR,
                                                     self.bist_byte,
                                                     force=True)
        return write_return

    """
    read_status()
    """
    def read_status(self):
        #STATUS (which is really just reading the DRDY bit)
        status_val = self._i2c_bus.read_byte_data(self.device_addr,
                                                  self.StatusRegister.STATUS_REGISTER_ADDR)

        data_is_ready = bool(status_val & self.StatusRegister.STATUS_DRDY)

        return data_is_ready

    """
    read_bist()
    """
    def read_bist(self):
        #BIST
        bist_value = self._i2c_bus.read_byte_data(self.device_addr,
                                                  self.BistRegister.BIST_REGISTER_ADDR)
        return bist_value

    """
    read_poll()
    """
    def read_poll(self):
        #POLL
        poll_value = self._i2c_bus.read_byte_data(self.device_addr,
                                                  self.PollRegister.POLL_REGISTER_ADDR)
        return poll_value

    """
    read_tmrc()
    """
    def read_tmrc(self):
        #TMRC
        tmrc_value = self._i2c_bus.read_byte_data(self.device_addr,
                                                  self.TmrcRegister.TMRC_REGISTER_ADDR)
        return tmrc_value

    """
    read_cmm()
    """
    def read_cmm(self):
        #CMM
        cmm_value = self._i2c_bus.read_byte_data(self.device_addr,
                                                 self.CmmRegister.CMM_REGISTER_ADDR)
        return cmm_value

    """
    read_hshake()
    """
    def read_hshake(self):
        #HSHAKE
        hshake_value = self._i2c_bus.read_byte_data(self.device_addr,
                                                    self.HshakeRegister.HSHAKE_REGISTER_ADDR)
        return hshake_value

    """
    read_revid()
    """
    def read_revid(self):
        #REVID
        revid_value = self._i2c_bus.read_byte_data(self.device_addr,
                                                   self.RevidRegister.REVID_REGISTER_ADDR)
        return revid_value

    """
    write_config()
    Writes the configuration parameters of the object to the i2c bus
    
    This function assumes member variables in the object have been 
    modified to the user's desired values.
    """
    def write_config(self):
        # write to bist register
        self.write_bist()

        # write to poll register
        self.write_poll()

        # write to ccr register
        self.write_ccr()

        # write to tmrc register
        self.write_tmrc()

        # write to hshake register
        self.write_hshake()
        
        # This will start Continuous Measurement Mode if CMM_START bit is set
        self.write_cmm()

    """
    read_meas_x() reads X-axis magnetometer and returns the valuein microtesla (uT)
    """
    def read_meas_x(self):
        # Check if a single measurement from either magnetometer has been requested
        single_meas_x = self.poll_byte & self.PollRegister.POLL_PMX
        
        # Read from X Magnetometer    
        if self.cmx or single_meas_x:
            x_mag_bytes = self._i2c_bus.read_i2c_block_data(self.device_addr,
                                                            self.MeasRegister.MEAS_REGISTER_ADDR,
                                                            3)
            
            # Convert the unsigned 3-byte integer to a signed 3-byte integer
            x_mag_unsigned = int.from_bytes(x_mag_bytes, "big")
            x_mag_int = self.uint24_to_int24(x_mag_unsigned)

            # Apply scaling
            x_mag_value = x_mag_int * self.x_scaling

            # If we're in single measurement mode and we just read the measurement, 
            # then clear the single measurement bit
            if single_meas_x:
                self.poll_byte &= ~self.PollRegister.POLL_PMX
        else:
            x_mag_value = None

        # Print the Measurements
        if self.print_status_statements:
            print("xMag: {:+.4f}uT".format(x_mag_value))


        if self.print_debug_statements:
            print("\tread_meas_x()")
            print("\t\tX bytes: [{}]".format(', '.join(hex(val) for val in x_mag_bytes)), 
                  "\n\t\tX Int Unsigned: ", hex(x_mag_unsigned), ", ", x_mag_unsigned, 
                  "\n\t\tX Int: ", x_mag_int, "\tX Value: ", x_mag_value)

        return x_mag_value

    """
    read_meas_y() reads Y-axis magnetometer and returns the value in microtesla (uT)
    """
    def read_meas_y(self):
        # Check if a single measurement from either magnetometer has been requested
        single_meas_y = self.poll_byte & self.PollRegister.POLL_PMY
        
        # Read from Y Magnetometer    
        if self.cmy or single_meas_y:
            y_mag_bytes = self._i2c_bus.read_i2c_block_data(self.device_addr,
                                                            self.MeasRegister.MEAS_REGISTER_ADDR + 0x03,
                                                            3)
            
            # Convert the unsigned 3-byte integer to a signed 3-byte integer
            y_mag_unsigned = int.from_bytes(y_mag_bytes, "big")
            y_mag_int = self.uint24_to_int24(y_mag_unsigned)

            # Apply scaling
            y_mag_value = y_mag_int * self.y_scaling

            # If we're in single measurement mode and we just read the measurement, 
            # then clear the single measurement bit
            if single_meas_y:
                self.poll_byte &= ~self.PollRegister.POLL_PMY
        else:
            y_mag_value = None

        # Print the Measurements
        if self.print_status_statements:
            print("yMag: {:+.4f}uT".format(y_mag_value))


        if self.print_debug_statements:
            print("\tread_meas_y()")
            print("\t\tY bytes: [{}]".format(', '.join(hex(val) for val in y_mag_bytes)), 
                  "\n\t\tY Int Unsigned: ", hex(y_mag_unsigned), ", ", y_mag_unsigned, 
                  "\n\t\tY Int: ", y_mag_int, "\tY Value: ", y_mag_value)

        return y_mag_value

    """
    read_meas_z() reads Z-axis magnetometer and returns the value in microtesla (uT)
    """
    def read_meas_z(self):
        # Check if a single measurement from either magnetometer has been requested
        single_meas_z = self.poll_byte & self.PollRegister.POLL_PMZ
        
        # Read from Z Magnetometer    
        if self.cmy or single_meas_y:
            z_mag_bytes = self._i2c_bus.read_i2c_block_data(self.device_addr,
                                                            self.MeasRegister.MEAS_REGISTER_ADDR + 0x06,
                                                            3)
            
            # Convert the unsigned 3-byte integer to a signed 3-byte integer
            z_mag_unsigned = int.from_bytes(z_mag_bytes, "big")
            z_mag_int = self.uint24_to_int24(z_mag_unsigned)

            # Apply scaling
            z_mag_value = z_mag_int * self.z_scaling

            # If we're in single measurement mode and we just read the measurement, 
            # then clear the single measurement bit
            if single_meas_z:
                self.poll_byte &= ~self.PollRegister.POLL_PMZ
        else:
            z_mag_value = None

        # Print the Measurements
        if self.print_status_statements:
            print("zMag: {:+.4f}uT".format(z_mag_value))


        if self.print_debug_statements:
            print("\tread_meas_z()")
            print("\t\tZ bytes: [{}]".format(', '.join(hex(val) for val in z_mag_bytes)), 
                  "\n\t\tZ Int Unsigned: ", hex(z_mag_unsigned), ", ", z_mag_unsigned, 
                  "\n\t\tZ Int: ", z_mag_int, "\tZ Value: ", z_mag_value)

        return z_mag_value

    """
    read_meas() reads X-,Y-,Z-axis magnetometers and returns a list of the values in microtesla (uT) [x,y,z]
    """
    def read_meas(self):
        x_mag_value = self.read_meas_x()
        y_mag_value = self.read_meas_y()
        z_mag_value = self.read_meas_z()
        
        # Print the Measurements
        if self.print_status_statements or self.print_debug_statements:
            print("read_meas()")
            # if debug mode is on, all the lower level read_meas_<>() funcs will print

        return [x_mag_value, y_mag_value, z_mag_value]

    """
    self_test()
    """
    def self_test(self, attempt_num=10):
        # Make sure CMM (Continuous Measurement Mode) is Disabled
        self.assign_cmm_byte(cmx=False, cmy=False, cmz=False, drdm=False, cmm_start=False)
        self.write_cmm()

        # Write to BIST (Built-In Self Test) Registers with desired settings 
        # It's assumed BIST bits are set to desired values
        self.write_bist()

        # Write to POLL to initiate Self Test 
        # It's assumed POLL bits are set to desired values
        self.write_poll()

        # Read DRDY bit until it is HIGH
        i = 0
        while ((not self.read_status()) and (i < attempt_num)):
            i += 1
            time.sleep(1) # Wait 1 second between each check of status bit

        if i == attempt_num:
            if self.print_status_statements:
                print("ERROR in 'self_test()': \n\tDRDY bit was not detected as HIGH")
            return None

        # Read XOK, YOK, and ZOK bits from BIST register
        bist_value = self.read_bist()

        if self.print_status_statements:
            print('self_test(i2c_addr={}) results:'.format(hex(self.device_addr)))
            if bist_value & self.BistRegister.BIST_XOK:
                print("\tX Magnetometer: OK")
            else:
                print("\tX Magnetometer: NOT OK")
            if bist_value & self.BistRegister.BIST_YOK:
                print("\tY Magnetometer: OK")
            else:
                print("\tY Magnetometer: NOT OK")
            if bist_value & self.BistRegister.BIST_ZOK:
                print("\tZ Magnetometer: OK")
            else:
                print("\tZ Magnetometer: NOT OK")

        return bist_value
    