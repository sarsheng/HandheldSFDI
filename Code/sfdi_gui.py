import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import logging 
import cv2
import PySpin
from Camera import auto_AcquireSingle_sarah
from RotationStage import elliptec_rotation_stage



logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class Camera(object):
    def __init__(self, cam):
        self.cam = cam
        self.cam.Init()

    def stop(self):
        logger.debug('Cleaning up')
        self.cam.DeInit()
        del self.cam
        self.cam = None

    def configure(self):
        self.cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
        self.cam.PixelFormat.SetValue(PySpin.PixelFormat_BayerRG8)
        self.cam.BinningHorizontal.SetValue(2)
        self.cam.BinningVertical.SetValue(2)
        self.cam.Width.SetValue(1920)
        self.cam.Height.SetValue(1080)
        self.cam.AcquisitionFrameRateEnable.SetValue(True)
        self.cam.AcquisitionFrameRate.SetValue(30)
        self.cam.TLStream.StreamBufferCountMode.SetValue(
            PySpin.StreamBufferCountMode_Manual)
        self.cam.TLStream.StreamBufferCountManual.SetValue(1)
        self.cam.TLStream.StreamBufferHandlingMode.SetValue(
            PySpin.StreamBufferHandlingMode_NewestOnly)

    def show_image(self, data):
        cv2.imshow('image', data)
        cv2.waitKey(1)

    def run(self):
        logger.debug('Starting')
        self.configure()
        self.cam.BeginAcquisition()
        try:
            logger.debug('Streaming')
            while True:
                img = self.cam.GetNextImage()
                if img.IsIncomplete():
                    logger.warning('Image incomplete (%d)',
                                   img.GetImageStatus())
                    continue

                img_conv = img.Convert(PySpin.PixelFormat_BGR8,
                                       PySpin.HQ_LINEAR)
                # or img.GetData().tobytes() for pushing into gstreamer buffers
                self.show_image(img_conv.GetNDArray())
                img.Release()

        except PySpin.SpinnakerException as e:
            logger.exception(e)
        finally:
            logger.debug('Ending')
            self.cam.EndAcquisition()

def update_cam(cam, newExposure, newGain):
    # disable automatic settings (also allows us to write new settings)
    cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
    # print('Automatic exposure disabled...')
    cam.GainAuto.SetValue(PySpin.GainAuto_Off)
    # print('Automatic gain disabled...')
    cam.Width.SetValue(cam.Width.GetMax())
    cam.Height.SetValue(cam.Height.GetMax())
    cam.OffsetX.SetValue(0)
    cam.OffsetY.SetValue(0)

    # set manual settings
    cam.ExposureTime.SetValue(newExposure)
    cam.Gain.SetValue(newGain)
    return "Settings Saved"

def get_auto_settings(cam):
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

        # Retrieve GenICam nodemap
        nodemap = cam.GetNodeMap()

        # Grab dummy frame so auto can settle
        cam.BeginAcquisition()
        _ = cam.GetNextImage(15000)
        cam.EndAcquisition()

        # Sarah - Print out Auto Settings (node map info)

        # EXPOSURE
        # Set to Auto
        exposure_auto = cam.ExposureTime.GetValue()
        gain_auto = cam.Gain.GetValue()
        gamma_auto =  cam.Gamma.GetValue()

        cam.DeInit()
    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False
    return result, exposure_auto, gain_auto, gamma_auto

def main():

    def cancel_btn_cmd():
        choice = messagebox.askyesno("Verify Close", "Are you sure you want "
                                                     "to exit.")
        if choice == tk.YES:
            root.destroy()

    def update_btn_cmd():
        # Get data from the GUI
        exposure_input = exposure_data.get()
        gain_input = gain_data.get()
    
    def cam_preview_cmd():
        # start the camera preview
        print("camera preview is starting...")

    # Create root window
    root = tk.Tk()
    root.title("Handheld SFDI GUI")
    root.geometry("1000x800")

    # Create title, name and id widgets
    title_label = ttk.Label(root, text="Spatial Frequency Domain Imaging Handheld GUI")
    title_label.grid(column = 0, row = 0, columnspan = 10, sticky = 'n', pady =20, padx = 350)

    # Camera Settings
    # framerate_label = ttk.Label(root, text="Frame Rate:")
    # framerate_label.grid(column=0, row=1, sticky=tk.E, pady=5)
    # framerate_data = tk.StringVar(value = "170.21")
    # framerate_entry = ttk.Entry(root, textvariable=framerate_data)
    # framerate_entry.grid(column=1, row=1,  columnspan =3, sticky=tk.W, pady=5)

    # result, exposure_auto, gain_auto, gamma_auto = auto_AcquireSingle_sarah.main("auto")

    exp_label = ttk.Label(root, text="Exposure:")
    exp_label.grid(column=0, row=2, sticky=tk.E, pady=5)
    exp_data = tk.StringVar()
    exp_entry = ttk.Entry(root, textvariable=exp_data)
    exp_entry.grid(column=1, row=2,  columnspan =3, sticky=tk.W, pady=5)

    gain_label = ttk.Label(root, text="Gain:")
    gain_label.grid(column=0, row=3, sticky=tk.E, pady=5)
    gain_data = tk.StringVar()
    gain_entry = ttk.Entry(root, textvariable=gain_data)
    gain_entry.grid(column=1, row=3,  columnspan =3, sticky=tk.W, pady=5)

    # gamma_label = ttk.Label(root, text="Gain:")
    # gamma_label.grid(column=0, row=4, sticky=tk.E, pady=5)
    # gamma_data = tk.StringVar()
    # gamma_entry = ttk.Entry(root, textvariable=gamma_data)
    # gamma_entry.grid(column=1, row=4,  columnspan =3, sticky=tk.W, pady=5)

    export_label = ttk.Label(root, text="Export Path:")
    export_label.grid(column=0, row=10, sticky=tk.E, pady=5)
    export_data = tk.StringVar(value="sarahsheng@10.193.47.130:/Users/sarahsheng/Desktop/SFDI_spiral_handheld/code/code_scripts")
    export_entry = ttk.Entry(root, textvariable=export_data, width = 55)
    export_entry.grid(column=1, row=10, columnspan = 60, sticky=tk.W, pady=5)

    preview_label = ttk.Label(root, text="Camera preview", relief="solid", padding=(50, 50))
    preview_label.grid(column=8, row=0, sticky="e", rowspan = 25)

    status_var = tk.StringVar(value="Not connected")
    status_label = ttk.Label(root, textvariable=status_var)
    status_label.grid(column=6, row=4, padx = 18, sticky="e")

    # --- Camera state ---
    system = None
    cam = None
    running = False
    preview_job = None
    tk_img_ref = None 

    def connect_camera():
        nonlocal system, cam
        if cam is not None and system is not None:
            return True

        system = PySpin.System.GetInstance()
        cam_list = system.GetCameras()
        if cam_list.GetSize() == 0:
            cam_list.Clear()
            system.ReleaseInstance()
            system = None
            status_var.set("No cameras found")
            return False

        cam = cam_list[0]
        cam_list.Clear()

        try:
            cam.Init()
            status_var.set("Connected")
            return True
        except Exception as e:
            status_var.set(f"Init failed: {e}")
            cam = None
            system.ReleaseInstance()
            system = None
            return False

    def configure_camera():
        """Apply your settings safely."""
        nonlocal cam
        if cam is None:
            return

        # Turn off autos so manual writes work
        if cam.ExposureAuto.GetAccessMode() == PySpin.RW:
            cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
        if cam.GainAuto.GetAccessMode() == PySpin.RW:
            cam.GainAuto.SetValue(PySpin.GainAuto_Off)

        cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
        cam.PixelFormat.SetValue(PySpin.PixelFormat_BayerRG8)

        # binning
        if cam.BinningHorizontal.GetAccessMode() == PySpin.RW:
            cam.BinningHorizontal.SetValue(2)
        if cam.BinningVertical.GetAccessMode() == PySpin.RW:
            cam.BinningVertical.SetValue(2)

        # ROI: safest is max
        cam.Width.SetValue(cam.Width.GetMax())
        cam.Height.SetValue(cam.Height.GetMax())
        cam.OffsetX.SetValue(0)
        cam.OffsetY.SetValue(0)

        # frame rate (only if supported)
        if cam.AcquisitionFrameRateEnable.GetAccessMode() == PySpin.RW:
            cam.AcquisitionFrameRateEnable.SetValue(True)
            try:
                cam.AcquisitionFrameRate.SetValue(float(framerate_data.get()))
            except Exception:
                cam.AcquisitionFrameRate.SetValue(30)

        # buffer handling
        cam.TLStream.StreamBufferCountMode.SetValue(PySpin.StreamBufferCountMode_Manual)
        cam.TLStream.StreamBufferCountManual.SetValue(1)
        cam.TLStream.StreamBufferHandlingMode.SetValue(PySpin.StreamBufferHandlingMode_NewestOnly)

    def apply_settings_from_gui():
        """Apply exposure/gain from entries."""
        nonlocal cam
        if cam is None:
            return
        try:
            exp = float(exp_data.get()) if exp_data.get() else None
            gain = float(gain_data.get()) if gain_data.get() else None

            if exp is not None and cam.ExposureTime.GetAccessMode() == PySpin.RW:
                cam.ExposureTime.SetValue(exp)
            if gain is not None and cam.Gain.GetAccessMode() == PySpin.RW:
                cam.Gain.SetValue(gain)

            status_var.set("Settings updated")
        except Exception as e:
            status_var.set(f"Settings error: {e}")

    def grab_and_update_frame():
        """Called repeatedly by Tkinter to update preview."""
        nonlocal preview_job, tk_img_ref, running, cam
        if not running or cam is None:
            return

        try:
            img = cam.GetNextImage(1000)  # timeout ms
            if img.IsIncomplete():
                img.Release()
                preview_job = root.after(10, grab_and_update_frame)
                return

            # Convert Bayer -> RGB for PIL/Tk
            img_conv = img.Convert(PySpin.PixelFormat_RGB8, PySpin.HQ_LINEAR)
            frame = img_conv.GetNDArray()
            img.Release()

            pil = Image.fromarray(frame)

            # Resize to something reasonable for your GUI
            pil = pil.resize((480, 270))

            tk_img_ref = ImageTk.PhotoImage(pil)
            preview_label.configure(image=tk_img_ref, text="")

        except Exception as e:
            status_var.set(f"Preview error: {e}")
            stop_preview()
            return

        # schedule next frame (~30 fps)
        preview_job = root.after(33, grab_and_update_frame)

    def start_preview():
        nonlocal running
        if running:
            return
        if not connect_camera():
            return

        try:
            configure_camera()
            apply_settings_from_gui()
            cam.BeginAcquisition()
            running = True
            status_var.set("Preview running")
            grab_and_update_frame()
        except Exception as e:
            status_var.set(f"Start failed: {e}")
            running = False

    def stop_preview():
        nonlocal running, preview_job
        running = False
        if preview_job is not None:
            root.after_cancel(preview_job)
            preview_job = None
        if cam is not None:
            try:
                cam.EndAcquisition()
            except Exception:
                pass
        status_var.set("Preview stopped")

    def cleanup_camera():
        nonlocal cam, system
        stop_preview()
        if cam is not None:
            try:
                cam.DeInit()
            except Exception:
                pass
            cam = None
        if system is not None:
            try:
                system.ReleaseInstance()
            except Exception:
                pass
            system = None

        # --- Buttons ---
    
    start_button = ttk.Button(root, text="Start Preview", command = start_preview)
    start_button.grid(column=6, row=2, padx=20, sticky="e")
    stop_button = ttk.Button(root, text="Stop Preview",  command = stop_preview)
    stop_button.grid(column=6, row=3, padx=20, sticky="e")
    ok_btn = ttk.Button(root, text="Update", command=update_btn_cmd)
    ok_btn.grid(column=1, row=4)
    accquire_btn = ttk.Button(root, text="Accquire")
    accquire_btn.grid(column=1, row=5)
    export_btn = ttk.Button(root, text = "Export")
    export_btn.grid(column = 5, row = 10, padx =25, sticky = 'w')
    cancel_btn = ttk.Button(root, text="Close", command=cancel_btn_cmd)
    cancel_btn.grid(column=4, row=12, padx=10, pady=10, sticky="s")
    root.mainloop()

    # # --- camera preview --- 
    # logging.basicConfig(level=logging.DEBUG)
    # system = PySpin.System.GetInstance()
    # version = system.GetLibraryVersion()
    # logger.debug('Library version: %d.%d.%d.%d',
    #              version.major, version.minor, version.type, version.build)
    # cam_list = system.GetCameras()
    # if not cam_list.GetSize():
    #     logger.error('No cameras found')
    #     return
    # cam = cam_list[0]
    # del cam_list
    # camera = Camera(cam)
    # try:
    #     camera.run()
    # except KeyboardInterrupt:
    #     pass
    # finally:
    #     camera.stop()
    #     system.ReleaseInstance()
    print("Finished")

if __name__ == "__main__":
    main()
