# 4/6/25 modified to include LED
# 12/6/25 modified to transfer data (Sarah)

##### VARIABLES TO EDIT AS DESIRED #####
import auto_AcquireSingle_sarah
import os
import elliptec_rotation_stage
import subprocess  # for shell commands
from time import sleep
import spidev
import time
import RPi.GPIO as GPIO

# DAC value [0,4095] corresponding to input voltage to BuckPuck driver
DAC = 3000
t_rot = 2.5  # time delay for rotation stage movement
t_cam = 2.5  # time delay for camera acquisition

DEBUG = False
spi_max_speed = 4 * 1000000  # 4 MHz
V_Ref = 5000  # 5.0V in mV
Resolution = 2**12  # 10 bits for the MCP 4911
CE = 0  # CE0 or CE1, select SPI device on bus
# setup and open an SPI channel
spi = spidev.SpiDev()
# spi.open(0,CE)
spi.open(0, 0)
spi.max_speed_hz = spi_max_speed


def export_data(file):
    save_path = "sarahsheng@10.193.47.130:/Users/sarahsheng/Desktop/SFDI_spiral_handheld/code/code_scripts"
    data_path = f"/home/roblyer-admin/Downloads/Python/code_scripts/{file}"
    subprocess.run([
        "scp",
        data_path,
        save_path
    ], check=True)
    print(f"Transfer {file} complete")


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
    if DEBUG:
        print("Highbyte = {0:8b}".format(highByte))
        print("Lowbyte =  {0:8b}".format(lowByte))
    spi.xfer2([highByte, lowByte])


# turn LED on to desired voltage
time.sleep(1)
print("turning LED on")
time.sleep(1)

setOutput(DAC)

mount = elliptec_rotation_stage.ElliptecRotationStage(
    '/dev/ttyUSB0', offset=0)  # changed from /dev/ttyUSB0

print('homing motor\n')
mount.home()
time.sleep(t_rot)
print('homing complete')
_, filename1 = auto_AcquireSingle_sarah.main("manual")
time.sleep(t_cam)
# print('image 1 captured')


mount.move_by(120)
time.sleep(t_rot)
print('rotated 120 degrees CCW')
_, filename2 = auto_AcquireSingle_sarah.main("manual")
time.sleep(t_cam)
# print('image 2 captured')

mount.move_by(120)
time.sleep(t_rot)
print('rotated 120 degrees CCW')
_, filename3 = auto_AcquireSingle_sarah.main("manual")
time.sleep(t_cam)
# print('image 3 captured')

mount.move_by(120)
time.sleep(t_rot)
print('rotated 120 degrees CCW')
time.sleep(1)
print('\nturning LED off')
time.sleep(1)
setOutput(4095)
time.sleep(1)
print('\n---end of code---')

spi.close()
time.sleep(1)

export_data(filename1)
export_data(filename2)
export_data(filename3)
