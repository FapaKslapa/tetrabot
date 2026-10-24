import numpy as np

from vision import Frame

try:
    import mss
except ImportError:
    mss = None


class Capture:
    def __init__(self):
        if mss is None:
            raise RuntimeError("the mss package is missing (run ./build.sh)")
        self.sct = mss.mss()

    def monitors(self):
        return list(self.sct.monitors[1:]) or [self.sct.monitors[0]]

    def grab_box(self, left, top, width, height):
        shot = self.sct.grab({"left": int(left), "top": int(top), "width": int(width), "height": int(height)})
        img = np.asarray(shot)[:, :, :3][:, :, ::-1]
        return Frame(img, img.shape[1] / float(width), (left, top))

    def grab_monitor(self, monitor):
        return self.grab_box(monitor["left"], monitor["top"], monitor["width"], monitor["height"])

    def grab_layout(self, layout):
        return self.grab_box(*layout.region())
