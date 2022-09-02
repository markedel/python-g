# Copyright Mark Edel  All rights reserved
# Constants and low-level utility functions used across modules
from PIL import Image

# Number of pixels to indent a code block
BLOCK_INDENT = 24

# Outline color is currently set to white with a minimal non-zero alpha to allow
# a rendering trick to make outlines appear on demand.  This is sub-optimal because it
# does not allow any sort of variable coloring or shading in outlines.
OUTLINE_COLOR = (255, 255, 255, 1)

ICON_BG_COLOR = (255, 255, 255, 255)

def asciiToImage(asciiPixmap):
    if asciiToImage.asciiMap is None:
        asciiToImage.asciiMap = {'.':(0, 0, 0, 0), 'o': OUTLINE_COLOR,
                ' ': ICON_BG_COLOR, '%':(0, 0, 0, 255), 'R':(255, 0, 0, 255),
                'r':(255, 128, 128, 255)}
        for i in range(1, 10):
            pixel = int(int(i) * 255 * 0.1)
            asciiToImage.asciiMap[str(i)] = (pixel, pixel, pixel, 255)
    height = len(asciiPixmap)
    width = len(asciiPixmap[0])
    pixels = "".join(asciiPixmap)
    colors = [asciiToImage.asciiMap[pixel] for pixel in pixels]
    image = Image.new('RGBA', (width, height))
    image.putdata(colors)
    return image
asciiToImage.asciiMap = None

def rectWidth(rect):
    return rect[2] - rect[0]

def rectHeight(rect):
    return rect[3] - rect[1]

def rectsTouch(rect1, rect2):
    """Returns true if rectangles rect1 and rect2 overlap"""
    l1, t1, r1, b1 = rect1
    l2, t2, r2, b2 = rect2
    # One is to the right side of the other
    if l1 > r2 or l2 > r1:
        return False
    # One is above the other
    if t1 > b2 or t2 > b1:
        return False
    return True

def offsetRect(rect, xOff, yOff):
    l, t, r, b = rect
    return l+xOff, t+yOff, r+xOff, b+yOff

def combineRects(rect1, rect2):
    """Find the minimum rectangle enclosing rect1 and rect2"""
    l1, t1, r1, b1 = rect1
    l2, t2, r2, b2 = rect2
    return min(l1, l2), min(t1, t2), max(r1, r2), max(b1, b2)

class AccumRects:
    """Make one big rectangle out of all rectangles added."""
    def __init__(self, initRect=None):
        self.rect = initRect

    def add(self, rect):
        if rect is None:
            return
        if self.rect is None:
            self.rect = rect
        else:
            self.rect = combineRects(rect, self.rect)

    def get(self):
        """Return the enclosing rectangle.  Returns None if no rectangles were added"""
        return self.rect

    def clear(self):
        self.rect = None
