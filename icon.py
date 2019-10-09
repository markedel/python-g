from PIL import Image, ImageDraw, ImageFont
from python_g import msTime

globalFont = ImageFont.truetype('c:/Windows/fonts/arial.ttf', 11)

textMargin = 2
spineThickness = 4
outSiteWidth = 5
iconOutlineColor = (230, 230, 230, 255)
iconBgColor = (255, 255, 255, 255)
selectModColor = (0, 0, 80, 50)

outSitePixmap = (
 "obbbo",
 ".obo.",
 "..o..")
inSitePixmap = (
 "oxxxo",
 "boxob",
 "bbobb")

renderCache = {}

def overlayColor(c1, c2):
    r1, g1, b1, a1 = c1
    r2, g2, b2, a2 = c2
    w1 = (255 - a2) / 255.0
    w2 = a2 / 255.0
    return int(r1*w1 + r2*w2), int(g1*w1 + g2*w2), int(b1*w1+b2*w2), a1

iconOutlineSelColor = overlayColor(iconOutlineColor, selectModColor)
iconBgSelColor = overlayColor(iconBgColor, selectModColor)

def asciiToImage(asciiPixmap, selected=False):
    if selected:
        outLineColor = iconOutlineSelColor
        bgColor = iconBgSelColor
    else:
        outLineColor = iconOutlineColor
        bgColor = iconBgColor
    print('bgcolor', bgColor)
    asciiMap = {'.': (0, 0, 0, 0), 'o': outLineColor, 'b': bgColor, 'x': (0, 0, 0, 0)}
    height = len(asciiPixmap)
    width = len(asciiPixmap[0])
    pixels = "".join(asciiPixmap)
    colors = [asciiMap[pixel] for pixel in pixels]
    image = Image.new('RGBA', (width, height))
    image.putdata(colors)
    return image

outSiteImage = asciiToImage(outSitePixmap)
outSiteSelImage = asciiToImage(outSitePixmap, selected=True)
inSiteImage = asciiToImage(inSitePixmap)
inSiteSelImage = asciiToImage(inSitePixmap, selected=True)

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
             fill=None, outline=iconOutlineColor)
            renderCache[self.text] = txtImg
        else:
            txtImg = renderCache[self.text]
        x, y = location
        textDrawRect = (x, y, x+txtImg.width, y+txtImg.height)
        image.paste(txtImg, textDrawRect)
        if self.selected:
            selImg = Image.new('RGBA', (txtImg.width, txtImg.height), color=(0, 0, 80, 50))
            image.paste(selImg, textDrawRect, mask=selImg)
        self._drawSpine(image, x, y+txtImg.height, txtImg.width-1, self.outOffset, self.inOffsets)

    def _spineLength(self):
        return max(self.inOffsets) + outSiteImage.width // 2 + 2

    def _drawSpine(self, image, x, y, baseIconWidth, outOffset, inOffsets=None):
        if inOffsets is not None:
            spineLength = self._spineLength()
            if self.selected:
                bgColor = iconBgSelColor
                outlineColor = iconOutlineSelColor
                inImg = inSiteSelImage
                outImg = outSiteSelImage
            else:
                bgColor = iconBgColor
                outlineColor = iconOutlineColor
                inImg = inSiteImage
                outImg = outSiteImage
            spineImage = Image.new('RGBA', (spineLength, spineThickness), bgColor)
            draw = ImageDraw.Draw(spineImage)
            draw.line((0, 0, spineLength, 0), fill=outlineColor)
            draw.line((0, spineThickness-1, spineLength, spineThickness-1), fill=outlineColor)
            draw.line((spineLength-1, 0, spineLength-1, spineThickness), fill=outlineColor)
            for inOff in inOffsets:
                spineImage.paste(inImg, (inOff - inImg.width // 2, 0))
            image.paste(spineImage, (x+baseIconWidth, y-spineThickness,
             x+baseIconWidth+spineLength, y), mask=spineImage)
        image.paste(outImg, (x+outOffset-outImg.width//2, y-1), mask=outImg)
