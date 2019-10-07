from PIL import Image, ImageDraw, ImageFont

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
    def __init__(self, text):
        self.text = text

    def drawIcon(self, windowImage, x, y, outOffset, inOffsets=None):
        if self.text not in renderCache:
            width, height = globalFont.getsize(self.text)
            image = Image.new('RGBA', (width+2*textMargin, height+2*textMargin),
             color=(255, 255, 255, 255))
            draw = ImageDraw.Draw(image)
            draw.text((textMargin, textMargin), self.text, font=globalFont,
             fill=(0, 0, 0, 255))
            draw.rectangle((0, 0, width+2*textMargin-1, height+2*textMargin-1),
             fill=None, outline=outlineColor)
            renderCache[self.text] = image
        else:
            image = renderCache[self.text]
        windowImage.image.paste(image, (x, y, x+image.width, y+image.height))
        self.drawSpine(windowImage, x, y+image.height, image.width-1, outOffset, inOffsets)

    def drawSpine(self, windowImage, x, y, baseIconWidth, outOffset, inOffsets=None):
        if inOffsets is not None:
            spineLength = max(inOffsets) + outSiteImage.width // 2 + 2
            spineImage = Image.new('RGBA', (spineLength, spineThickness), iconBgColor)
            draw = ImageDraw.Draw(spineImage)
            draw.line((0, 0, spineLength, 0), fill=outlineColor)
            draw.line((0, spineThickness-1, spineLength, spineThickness-1), fill=outlineColor)
            draw.line((spineLength-1, 0, spineLength-1, spineThickness), fill=outlineColor)
            for inOff in inOffsets:
                spineImage.paste(inSiteImage, (inOff - inSiteImage.width // 2, 0))
            windowImage.image.paste(spineImage, (x+baseIconWidth, y-spineThickness,
             x+baseIconWidth+spineLength, y), mask=spineImage)
        windowImage.image.paste(outSiteImage, (x+outOffset-outSiteImage.width//2, y-1),
         mask=outSiteImage)
