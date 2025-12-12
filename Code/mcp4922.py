#!/usr/bin/python
#-------------------------------------------------------------------------------
# Name:        MCP4922.py
# Purpose:     Set a static output level for the DAC
#
# Author:      paulv
#
# Created:     18-09-2015
# Copyright:   (c) paulv 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------

# Modified from 4911 to 4922 by ESH

import spidev
from time import sleep
#import RPi.GPIO as GPIO
DEBUG = False
spi_max_speed = 4 * 1000000 # 4 MHz
V_Ref = 5000 # 5.0V in mV
Resolution = 2**12 # 10 bits for the MCP 4911
CE = 0 # CE0 or CE1, select SPI device on bus
# setup and open an SPI channel
spi = spidev.SpiDev()
 # spi.open(0,CE)
spi.open(0,0) 
spi.max_speed_hz = spi_max_speed

def setOutput(val):
    # lowbyte has 8 data bits
    # B7, B6, B5, B4, B3, B2, B1, B0
    # D5, D4, D3, D2, D1, D0,  X,  X
    lowByte = val & 0xff
    # highbyte has control and 4 data bits
    # B7, B6,   B5, B4,     B3,  B2,  B1, B0
    # CH ,BUF, !GA, !SHDN,  D11, D10, D9, D8
    # B7=0:write to DAC, B6=0:unbuffered, B5=1:Gain=1X, B4=1:Output is active
    # highByte = ((val >> 6) & 0xff) | 0b0 << 7 | 0b0 << 6 | 0b1 << 5 | 0b1 << 4
    highByte = ((val >> 8) & 0xff) | 0b0 << 7 | 0b0 << 6 | 0b1 << 5 | 0b1 << 4    
    # by using spi.xfer2(), the CS is released after each block, transferring the
    # value to the output pin.
    if DEBUG :
        print("Highbyte = {0:8b}".format(highByte))
        print("Lowbyte =  {0:8b}".format(lowByte))
    spi.xfer2([highByte, lowByte])

try:
    while(True):
        outputlevel = int(input('Enter an output level from 0-4095 : '))
#        if DEBUG : print( "Binary value is : {0:10b} (10 bit)".format(outputlevel))
        # with a DAC gain of 1x
        print( "Output level should be : {0} mV".format(outputlevel * V_Ref / Resolution))
        setOutput(outputlevel)
        sleep(0.1)

except (KeyboardInterrupt, Exception) as e:
    print(e)
    print( "Closing SPI channel")
#    GPIO(cleanup)
    spi.close()
def main():
    pass
if __name__ == '__main__':
    main()

