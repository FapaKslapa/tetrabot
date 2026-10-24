import layout as layout_mod
from vision import Reader

MIN_READABLE_PREVIEWS = 4


def find_layout(capture, palette, threshold):
    for monitor in capture.monitors():
        frame = capture.grab_monitor(monitor)
        boxes = layout_mod.detect_pixels(frame.img, palette)
        if boxes is None:
            continue
        found = layout_mod.to_points(boxes, frame.scale, *frame.origin)
        readable = [p for p in Reader(found, palette, threshold).previews(frame) if p]
        if len(readable) >= MIN_READABLE_PREVIEWS:
            return found
    return None
