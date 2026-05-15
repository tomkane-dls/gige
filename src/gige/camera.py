import logging
from time import sleep, time

from epics import PV, caget, caput

logger = logging.getLogger(__name__)


class Gige1Camera:
    """GigE camera controller for acquiring tiffs.

    Args:
        base_pv: EPICS PV prefix.
        folder_path: directory to save images to.
        file_no: number to start from when numbering output files.
        acquire_time: exposure time of the camera in seconds.
        num_images: number of images to acquire.
        width: image width in pixels.
        height: image height in pixels.
        x_start: image X offset.
        y_start: image Y offset.
        image_mode: 0 = single, 1 = multiple, 2 = continuous.
        data_type: bits-per-pixel setting.
        file_template: printf-style template for output filenames.
        poll_interval: Seconds between status polls during acquisition.
    """

    def __init__(self, base_pv: str, folder_path: str, file_no: int,
                 acquire_time: float, num_images: int,
                 width: int, height: int,
                 x_start: int, y_start: int,
                 image_mode: int, data_type: int,
                 file_template: str, poll_interval: float):
        self.base_pv = base_pv
        self.cam_pv = base_pv + ":CAM:"
        self.tiff_pv = base_pv + ":TIFF:"

        self.folder_path = folder_path
        self.file_no = file_no
        self.num_images = num_images
        self.acquire_time = acquire_time
        self.file_template = file_template
        self.poll_interval = poll_interval

        self.params = {
            self.cam_pv + "AcquireTime": acquire_time,
            self.cam_pv + "NumImages": num_images,
            self.cam_pv + "ImageMode": image_mode,
            self.cam_pv + "DataType": data_type,
            self.cam_pv + "SizeX": width,
            self.cam_pv + "SizeY": height,
            self.cam_pv + "MinX": x_start,
            self.cam_pv + "MinY": y_start,
            self.tiff_pv + "FilePath": folder_path,
            self.tiff_pv + "NumCapture": num_images,
            self.tiff_pv + "FileNumber": file_no,
        }

        self.configure()

    def check_connection(self, timeout: float) -> bool:
        """Verify the camera IOC is reachable by connecting to a key PV"""

        test_pv_name = self.cam_pv + "DetectorState_RBV"
        logger.info("Checking connection to %s ...", test_pv_name)
        pv = PV(test_pv_name, connection_timeout=timeout)
        connected = pv.wait_for_connection(timeout=timeout)
        if connected:
            logger.info("PV %s connected (value: %s)", test_pv_name, pv.get())
        else:
            logger.error("PV %s did not connect within %.1fs", test_pv_name, timeout)
        return connected

    def configure(self):
        """Apply all camera and TIFF writer settings"""

        logger.info("Configuring camera %s ...", self.base_pv)

        caput(self.tiff_pv + "FileName", "")
        caput(self.tiff_pv + "FileTemplate", self.file_template)
        caput(self.tiff_pv + "FileWriteMode", 2)
        caput(self.tiff_pv + "AutoIncrement", 1)
        caput(self.tiff_pv + "AutoSave", 0)
        caput(self.tiff_pv + "LazyOpen", 1)

        for param, value in self.params.items():
            logger.debug("  caput %s = %s", param, value)
            caput(param, value)

        logger.info("Configuration complete.")

    def acquire(self, timeout_margin: float = 10.0):
        """Run an acquisition and wait for all frames to be saved"""

        expected_duration = self.num_images * self.acquire_time
        timeout = expected_duration + timeout_margin

        logger.info("Starting acquisition: %d image(s), %.4fs exposure "
                     "(timeout: %.1fs)",
                     self.num_images, self.acquire_time, timeout)

        # Arm the TIFF writer
        caput(self.tiff_pv + "Capture", 1)
        deadline = time() + timeout
        while caget(self.tiff_pv + "Capture_RBV") != 1:
            if time() > deadline:
                logger.error(
                    "TIFF writer failed to arm within %.1fs — check "
                    "FilePathExists_RBV and EnableCallbacks in the "
                    "TIFF plugin.", timeout)
                return
            sleep(self.poll_interval)
        logger.debug("TIFF writer armed.")

        # Start acquisition
        caput(self.cam_pv + "Acquire", 1)
        logger.info("Acquisition started.")

        # Monitor the TIFF writer queue while detector is acquiring
        queue_max = caget(self.tiff_pv + "QueueSize")
        deadline = time() + timeout
        while caget(self.cam_pv + "DetectorState_RBV") == 1:
            if time() > deadline:
                logger.error(
                    "Detector still acquiring after %.1fs — aborting. "
                    "Check TriggerMode and ImageMode settings.", timeout)
                caput(self.cam_pv + "Acquire", 0)
                return
            queue_size = caget(self.tiff_pv + "QueueUse")
            if queue_size >= queue_max:
                logger.warning("TIFF writer queue full (%d/%d)! "
                               "Frames may be dropped.", queue_size, queue_max)
            sleep(self.poll_interval)

        logger.debug("Detector idle. Waiting for TIFF writer to flush...")

        # Wait for the TIFF writer to finish flushing
        deadline = time() + timeout
        while caget(self.tiff_pv + "Capture_RBV") != 0:
            if time() > deadline:
                logger.error(
                    "TIFF writer did not finish flushing within %.1fs.",
                    timeout)
                return
            sleep(self.poll_interval)

        # Check for write errors
        if caget(self.tiff_pv + "WriteStatus") != 0:
            msg = caget(self.tiff_pv + "WriteMessage", as_string=True)
            logger.error("TIFF write error: %s", msg)

        # Verify frame count
        captured = caget(self.tiff_pv + "NumCaptured_RBV")
        if captured != self.num_images:
            logger.warning("%d TIFF images written — expected %d",
                           captured, self.num_images)
        else:
            logger.info("Acquisition complete: %d image(s) saved to %s",
                         captured, self.folder_path)
