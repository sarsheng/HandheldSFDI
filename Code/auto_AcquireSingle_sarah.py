# coding=utf-8
# =============================================================================
# Copyright (c) 2024 FLIR Integrated Imaging Solutions, Inc. All Rights Reserved.
#

import os
import PySpin
import sys
import platform


class StreamMode:
    """
    'Enum' for choosing stream mode
    """
    STREAM_MODE_TELEDYNE_GIGE_VISION = 0
    STREAM_MODE_PGRLWF = 1
    STREAM_MODE_SOCKET = 2


system = platform.system()
print(system)
if system == "Windows":
    CHOSEN_STREAMMODE = StreamMode.STREAM_MODE_TELEDYNE_GIGE_VISION
elif system == "Linux" or system == "Darwin":
    CHOSEN_STREAMMODE = StreamMode.STREAM_MODE_SOCKET
else:
    CHOSEN_STREAMMODE = StreamMode.STREAM_MODE_SOCKET

NUM_IMAGES = 1  # number of images to grab


def set_stream_mode(cam):
    """
    This function changes the stream mode

    :param cam: Camera to change stream mode.
    :type cam: CameraPtr
    :type nodemap_tlstream: INodeMap
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    streamMode = "Socket"

    if CHOSEN_STREAMMODE == StreamMode.STREAM_MODE_TELEDYNE_GIGE_VISION:
        streamMode = "TeledyneGigeVision"
    elif CHOSEN_STREAMMODE == StreamMode.STREAM_MODE_PGRLWF:
        streamMode = "LWF"
    elif CHOSEN_STREAMMODE == StreamMode.STREAM_MODE_SOCKET:
        streamMode = "Socket"

    result = True

    # Retrieve Stream nodemap
    nodemap_tlstream = cam.GetTLStreamNodeMap()

    # In order to access the node entries, they have to be casted to a pointer type (CEnumerationPtr here)
    node_stream_mode = PySpin.CEnumerationPtr(
        nodemap_tlstream.GetNode('StreamMode'))

    # The node "StreamMode" is only available for GEV cameras.
    # Skip setting stream mode if the node is inaccessible.
    if not PySpin.IsReadable(node_stream_mode) or not PySpin.IsWritable(node_stream_mode):
        return True

    # Retrieve the desired entry node from the enumeration node
    node_stream_mode_custom = PySpin.CEnumEntryPtr(
        node_stream_mode.GetEntryByName(streamMode))

    if not PySpin.IsReadable(node_stream_mode_custom):
        # Failed to get custom stream node
        print('Stream mode ' + streamMode + ' not available. Aborting...')
        return False

    # Retrieve integer value from entry node
    stream_mode_custom = node_stream_mode_custom.GetValue()

    # Set integer as new value for enumeration node
    node_stream_mode.SetIntValue(stream_mode_custom)

    # print('Stream Mode set to %s...' % node_stream_mode.GetCurrentEntry().GetSymbolic())
    return result


def run_single_camera_auto(cam):
    """
    This function acts as the body of the example; please see NodeMapInfo example
    for more in-depth comments on setting up cameras.

    :param cam: Camera to run on.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True

        # Retrieve TL device nodemap and print device information
        nodemap_tldevice = cam.GetTLDeviceNodeMap()
        # result &= print_device_info(nodemap_tldevice)

        # Initialize camera
        cam.Init()

        # Set Stream Mode - Sarah
        tl_stream_nodemap = cam.GetTLStreamNodeMap()

        # 1. Set buffer handling to Newest Only (drops old frames automatically)
        handling = PySpin.CEnumerationPtr(
            tl_stream_nodemap.GetNode('StreamBufferHandlingMode'))
        if PySpin.IsWritable(handling):
            entry = handling.GetEntryByName('NewestOnly')
            handling.SetIntValue(entry.GetValue())

        # 2. Increase number of buffers
        buf_count = PySpin.CIntegerPtr(
            tl_stream_nodemap.GetNode('StreamDefaultBufferCount'))
        if PySpin.IsWritable(buf_count):
            buf_count.SetValue(max(buf_count.GetMin(), 20))  # e.g. 20 buffers

        # 3. Optionally enable packet resend / adjust packet size/delay if supported
        # (GigE only — details depend on camera model)

        # Retrieve GenICam nodemap
        nodemap = cam.GetNodeMap()

        # Grab dummy frame so auto can settle
        cam.BeginAcquisition()
        _ = cam.GetNextImage(15000)
        cam.EndAcquisition()

        # Sarah - Print out Auto Settings (node map info)

        # EXPOSURE
        # Set to Auto
        exposure_auto = PySpin.CEnumerationPtr(nodemap.GetNode('ExposureAuto'))
        exposure_auto.SetIntValue(
            exposure_auto.GetEntryByName('Once').GetValue())
        print("Exposure = ", cam.ExposureTime.GetValue())
        # GAIN
        # Set to Auto
        gain_auto = PySpin.CEnumerationPtr(nodemap.GetNode('GainAuto'))
        gain_auto.SetIntValue(gain_auto.GetEntryByName('Once').GetValue())
        print("Gain = {:.2f}".format(cam.Gain.GetValue()))
        # GAMMA
        # we want a linear relationship between pixel ratio and intensity
        cam.Gamma.SetValue(1.0)
        print("Gain = ", cam.Gamma.GetValue())
        # ## AUTO EXPOSURE DAMPENING
        # print('Auto Exposure Damping: ', end='')
        # exposure_damping = PySpin.CFloatPtr(nodemap.GetNode('AutoExposureControlLoopDamping'))
        # print(exposure_damping.GetValue())

        # Acquire images
        filestr = 'autoimg'
        result &= acquire_images(cam, nodemap, nodemap_tldevice, filestr)
        # Deinitialize camera
        cam.DeInit()

        # END OF ADDED SECTION

        # # Acquire images
        # result &= acquire_images(cam, nodemap, nodemap_tldevice)

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result, filestr


def acquire_images(cam, nodemap, nodemap_tldevice):
    """
    This function acquires and saves images from a device.

    :param cam: Camera to acquire images from.
    :param nodemap: Device nodemap.
    :param nodemap_tldevice: Transport layer device nodemap.
    :type cam: CameraPtr
    :type nodemap: INodeMap
    :type nodemap_tldevice: INodeMap
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    # print('*** IMAGE ACQUISITION ***')
    try:
        result = True
        filename = None

        # Set acquisition mode to continuous
        #
        #  *** NOTES ***
        #  Because the example acquires and saves 10 images, setting acquisition
        #  mode to continuous lets the example finish. If set to single frame
        #  or multiframe (at a lower number of images), the example would just
        #  hang. This would happen because the example has been written to
        #  acquire 10 images while the camera would have been programmed to
        #  retrieve less than that.
        #
        #  Setting the value of an enumeration node is slightly more complicated
        #  than other node types. Two nodes must be retrieved: first, the
        #  enumeration node is retrieved from the nodemap; and second, the entry
        #  node is retrieved from the enumeration node. The integer value of the
        #  entry node is then set as the new value of the enumeration node.
        #
        #  Notice that both the enumeration and the entry nodes are checked for
        #  availability and readability/writability. Enumeration nodes are
        #  generally readable and writable whereas their entry nodes are only
        #  ever readable.
        #
        #  Retrieve enumeration node from nodemap

        # In order to access the node entries, they have to be casted to a pointer type (CEnumerationPtr here)
        node_acquisition_mode = PySpin.CEnumerationPtr(
            nodemap.GetNode('AcquisitionMode'))
        if not PySpin.IsReadable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
            print(
                'Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
            return False

        # Retrieve entry node from enumeration node
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName(
            'Continuous')
        if not PySpin.IsReadable(node_acquisition_mode_continuous):
            print(
                'Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
            return False

        # Retrieve integer value from entry node
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()

        # Set integer value from entry node as new value of enumeration node
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        # print('Acquisition mode set to continuous...')

        #  Begin acquiring images
        #
        #  *** NOTES ***
        #  What happens when the camera begins acquiring images depends on the
        #  acquisition mode. Single frame captures only a single image, multi
        #  frame catures a set number of images, and continuous captures a
        #  continuous stream of images. Because the example calls for the
        #  retrieval of 10 images, continuous mode has been set.
        #
        #  *** LATER ***
        #  Image acquisition must be ended when no more images are needed.
        cam.BeginAcquisition()

        print('Acquiring images...')

        device_serial_number = ''
        node_device_serial_number = PySpin.CStringPtr(
            nodemap_tldevice.GetNode('DeviceSerialNumber'))
        if PySpin.IsReadable(node_device_serial_number):
            device_serial_number = node_device_serial_number.GetValue()

        # Retrieve, convert, and save images

        # Create ImageProcessor instance for post processing images
        processor = PySpin.ImageProcessor()

        # Set default image processor color processing method
        #
        # *** NOTES ***
        # By default, if no specific color processing algorithm is set, the image
        # processor will default to NEAREST_NEIGHBOR method.

        processor.SetColorProcessing(
            PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR)

        for i in range(NUM_IMAGES):
            try:

                #  Retrieve next received image
                #
                #  *** NOTES ***
                #  Capturing an image houses images on the camera buffer. Trying
                #  to capture an image that does not exist will hang the camera.
                #
                #  *** LATER ***
                #  Once an image from the buffer is saved and/or no longer
                #  needed, the image must be released in order to keep the
                #  buffer from filling up.
                image_result = cam.GetNextImage(5000)  # timeout time

                #  Ensure image completion
                #
                #  *** NOTES ***
                #  Images can easily be checked for completion. This should be
                #  done whenever a complete image is expected or required.
                #  Further, check image status for a little more insight into
                #  why an image is incomplete.
                if image_result.IsIncomplete():
                    print('Image incomplete with image status %d ...' %
                          image_result.GetImageStatus())
                    image_result.Release()

                else:

                    #  Print image information; height and width recorded in pixels
                    #
                    #  *** NOTES ***
                    #  Images have quite a bit of available metadata including
                    #  things such as CRC, image status, and offset values, to
                    #  name a few.
                    width = image_result.GetWidth()
                    height = image_result.GetHeight()
                    # print('Grabbed Image %d, width = %d, height = %d' % (i, width, height))

                    #  Convert image to mono 8
                    #
                    #  *** NOTES ***
                    #  Images can be converted between pixel formats by using
                    #  the appropriate enumeration value. Unlike the original
                    #  image, the converted one does not need to be released as
                    #  it does not affect the camera buffer.
                    #
                    #  When converting images, color processing algorithm is an
                    #  optional parameter.
                    image_converted = processor.Convert(
                        image_result, PySpin.PixelFormat_Mono8)  # change format?

                    # Create a unique filename
                    import time
                    if device_serial_number:
                        filename = 'Acquisition-%s.jpg' % time.strftime(
                            "%H-%M-%S")
                    else:  # if serial number is empty
                        filename = 'Acquisition-%d.jpg' % i

                    #  Save image
                    #
                    #  *** NOTES ***
                    #  The standard practice of the examples is to use device
                    #  serial numbers to keep images of one device from
                    #  overwriting those of another.
                    image_converted.Save(filename)
                    print('Image saved at %s' % filename)

                    #  Release image
                    #
                    #  *** NOTES ***
                    #  Images retrieved directly from the camera (i.e. non-converted
                    #  images) need to be released in order to keep from filling the
                    #  buffer.
                    image_result.Release()
                    print('')

            except PySpin.SpinnakerException as ex:
                print('Error: %s' % ex)
                return False

        #  End acquisition
        #
        #  *** NOTES ***
        #  Ending acquisition appropriately helps ensure that devices clean up
        #  properly and do not need to be power-cycled to maintain integrity.
        cam.EndAcquisition()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return result, filename


def print_device_info(nodemap):
    """
    This function prints the device information of the camera from the transport
    layer; please see NodeMapInfo example for more in-depth comments on printing
    device information from the nodemap.

    :param nodemap: Transport layer device nodemap.
    :type nodemap: INodeMap
    :returns: True if successful, False otherwise.
    :rtype: bool
    """

    print('*** DEVICE INFORMATION ***\n')

    try:
        result = True
        node_device_information = PySpin.CCategoryPtr(
            nodemap.GetNode('DeviceInformation'))

        if PySpin.IsReadable(node_device_information):
            features = node_device_information.GetFeatures()
            for feature in features:
                node_feature = PySpin.CValuePtr(feature)
                print('%s: %s' % (node_feature.GetName(),
                                  node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'))

        else:
            print('Device control information not readable.')

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return result


def run_single_camera(cam):
    """
    This function acts as the body of the example; please see NodeMapInfo example
    for more in-depth comments on setting up cameras.

    :param cam: Camera to run on.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True

        # Retrieve TL device nodemap and print device information
        nodemap_tldevice = cam.GetTLDeviceNodeMap()
        # result &= print_device_info(nodemap_tldevice)

        # Initialize camera
        cam.Init()
        cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)

        # Retrieve GenICam nodemap
        nodemap = cam.GetNodeMap()

        # Set Stream Modes
        result &= set_stream_mode(cam)

        # ADDED SECTION: print camera setting info (node map info)

        # report automatic settings
        # print('Exposure time: ', end='')
        # print_node_info(cam.ExposureTime)
        # print('Gain: ', end='')
        # print_node_info(cam.Gain)
        # print('Flat Field Correction Enable: ', end='')
        # print_node_info(cam.FlatFieldCorrectionEnable)

        # disable automatic settings (also allows us to write new settings)
        cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
        # print('Automatic exposure disabled...')
        cam.GainAuto.SetValue(PySpin.GainAuto_Off)
        # print('Automatic gain disabled...')
        cam.Width.SetValue(cam.Width.GetMax())
        cam.Height.SetValue(cam.Height.GetMax())
        cam.OffsetX.SetValue(0)
        cam.OffsetY.SetValue(0)
        # print('\n')

        # set manual settings
        newExposure = 7372.0
        newGain = 4.48
        newExposure = min(cam.ExposureTime.GetMax(), newExposure)
        cam.ExposureTime.SetValue(newExposure)
        cam.Gain.SetValue(newGain)

        # report manual settings
        # print('New Exposure time: ', end='')
        # print_node_info(cam.ExposureTime)
        # print('New Gain: ', end='')
        # print_node_info(cam.Gain)

        # Grab dummy frame so auto can settle
        cam.BeginAcquisition()
        _ = cam.GetNextImage(15000)
        cam.EndAcquisition()

        # END OF ADDED SECTION

        # Acquire images
        new_result, filename = acquire_images(cam, nodemap, nodemap_tldevice)
        result &= new_result

        # Deinitialize camera
        cam.DeInit()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result, filename

    # PRINT NODE INFO EDIT


def print_node_info(node):
    """
    Prints node information if applicable

    *** NOTES ***
    Notice that each node is checked for availablility and readability prior
    to value retrieval. Checking for availability and readability (or writability
    when applicable) whenever a node is accessed is important in terms of error
    handling. If a node retrieval error occurs but remains unhandled, an exception
    is thrown.

    :param node: Node to get information from.
    :type node: INode
    """
    if node is not None and PySpin.IsReadable(node):
        print(PySpin.CValuePtr(node).ToString())
    else:
        print('unavailable')


def main(capture_setting):
    """
    Example entry point; please see Enumeration example for more in-depth
    comments on preparing and cleaning up the system.

    :return: True if successful, False otherwise.
    :rtype: bool
    """

    # Since this application saves images in the current folder
    # we must ensure that we have permission to write to this folder.
    # If we do not have permission, fail right away.
    try:
        test_file = open('test.txt', 'w+')
    except IOError:
        print('Unable to write to current directory. Please check permissions.')
        input('Press Enter to exit...')
        return False

    test_file.close()
    os.remove(test_file.name)

    result = True

    # Retrieve singleton reference to system object
    system = PySpin.System.GetInstance()

    # Get current library version
    version = system.GetLibraryVersion()
    # print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

    # Retrieve list of cameras from the system
    cam_list = system.GetCameras()

    num_cameras = cam_list.GetSize()

    # print('Number of cameras detected: %d' % num_cameras)

    # Finish if there are no cameras
    if num_cameras == 0:

        # Clear camera list before releasing system
        cam_list.Clear()

        # Release system instance
        system.ReleaseInstance()

        print('Not enough cameras!')
        input('Done! Press Enter to exit...')
        return False

    # Run example on each camera
    for i, cam in enumerate(cam_list):
        if capture_setting == 'auto':
            result, filename = run_single_camera_auto(cam)
            result &= new_result
        elif capture_setting == 'manual':
            new_result, filename = run_single_camera(cam)
            result &= new_result
        # print('Camera %d example complete... \n' % i)

    del cam

    # Clear camera list before releasing system
    cam_list.Clear()

    # Release system instance
    system.ReleaseInstance()

    # input('Done! Press Enter to exit...')
    return result, filename


if __name__ == '__main__':
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
