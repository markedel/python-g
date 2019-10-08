from PIL import Image, ImageDraw, ImageFont
from python_g import msTime

globalFont = ImageFont.truetype('c:/Windows/fonts/arial.ttf', 11)

textMargin = 2
spineThickness = 4
outSiteWidth = 5
outlineColor = (230, 230, 230, 255)
iconBgColor = (255, 255, 255, 255)
#windowBgColor = (255, 255, 255, 255)

outSitePixmap = (
 "obbbo",
 ".obo.",
 "..o..")
inSitePixmap = (
 "oxxxo",
 "boxob",
 "bbobb")

renderCache = {}

def asciiToImage(asciiPixmap):
    asciiMap = {'.': (0, 0, 0, 0), 'o': outlineColor, 'b': iconBgColor, 'x': (0, 0, 0, 0)}
    height = len(asciiPixmap)
    width = len(asciiPixmap[0])
    pixels = "".join(asciiPixmap)
    colors = [asciiMap[pixel] for pixel in pixels]
    image = Image.new('RGBA', (width, height))
    image.putdata(colors)
    return image

outSiteImage = asciiToImage(outSitePixmap)
inSiteImage = asciiToImage(inSitePixmap)

class Icon:
    def __init__(self, text, location, outOffset, inOffsets=None, window=None):
        self.window = window
        self.text = text
        self.outOffset = outOffset
        self.inOffsets = inOffsets
        self.rect = self._calcRectangle(location)
        self.selected = False

    def _calcRectangle(self, location):
        width, height = globalFont.getsize(self.text)
        width += self._spineLength() + 2*textMargin + 1
        height += 2*textMargin + outSiteImage.height
        x, y = location
        return x, y, x + width, y + height

    def drawIcon(self, image=None, location=None):
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        if self.text not in renderCache:
            width, height = globalFont.getsize(self.text)
            txtImg = Image.new('RGBA', (width+2*textMargin, height+2*textMargin),
             color=(255, 255, 255, 255))
            draw = ImageDraw.Draw(txtImg)
            draw.text((textMargin, textMargin), self.text, font=globalFont,
             fill=(0, 0, 0, 255))
            draw.rectangle((0, 0, width+2*textMargin-1, height+2*textMargin-1),
             fill=None, outline=outlineColor)
            renderCache[self.text] = txtImg
        else:
            txtImg = renderCache[self.text]
        x, y = location
        image.paste(txtImg, (x, y, x+txtImg.width, y+txtImg.height))
        if self.selected:
            selImg = Image.new('RGBA', (txtImg.width, txtImg.height), color=(0, 0, 100, 50))
            image.paste(selImg, (x, y, x+txtImg.width, y+txtImg.height), mask=selImg)
        self._drawSpine(image, x, y+txtImg.height, txtImg.width-1, self.outOffset, self.inOffsets)

    def _spineLength(self):
        return max(self.inOffsets) + outSiteImage.width // 2 + 2

    def _drawSpine(self, image, x, y, baseIconWidth, outOffset, inOffsets=None):
        if inOffsets is not None:
            spineLength = self._spineLength()
            spineImage = Image.new('RGBA', (spineLength, spineThickness), iconBgColor)
            draw = ImageDraw.Draw(spineImage)
            draw.line((0, 0, spineLength, 0), fill=outlineColor)
            draw.line((0, spineThickness-1, spineLength, spineThickness-1), fill=outlineColor)
            draw.line((spineLength-1, 0, spineLength-1, spineThickness), fill=outlineColor)
            for inOff in inOffsets:
                spineImage.paste(inSiteImage, (inOff - inSiteImage.width // 2, 0))
            image.paste(spineImage, (x+baseIconWidth, y-spineThickness,
             x+baseIconWidth+spineLength, y), mask=spineImage)
        image.paste(outSiteImage, (x+outOffset-outSiteImage.width//2, y-1),
         mask=outSiteImage)
