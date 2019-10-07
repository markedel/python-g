# Python-g main module
import tkinter as tk
import icon
from PIL import Image, ImageDraw, ImageTk, ImageWin

windowBgColor = (128, 128, 128, 255)

class Window:
    def __init__(self, master):
        self.top = tk.Toplevel(master)
        self.top.bind("<Destroy>", self.destroyCb)
        self.top.title("Python-G")
        self.frame = tk.Frame(self.top)
        self.menubar = tk.Menu(self.frame)
        menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=menu)
        menu.add_command(label="New", command=self.newCb)
        menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=menu)
        menu.add_command(label="Cut")
        menu.add_command(label="Copy")
        menu.add_command(label="Paste")
        self.top.config(menu=self.menubar)
        width = 2400
        height = 1800
        self.imgFrame = tk.Frame(self.frame, bg="", width=width, height=height)
        self.winImg = WindowImage(self.imgFrame, width, height)
        self.imgFrame.pack()
        self.frame.grid()

    def newCb(self):
        appData.newWindow()

    def destroyCb(self, evt):
        if evt.widget == self.top:
            appData.removeWindow(self)


# Tkinter canvas can't handle individual images for each icon.  After about
# 4000 pixmaps, it breaks and dies.  Drawing directly to the screen is also
# problematic.  Here, we have a Windows-only solution, provided by some
# rather questionable calls to pillow.  While we have no direct access to the
# windows framebuffer, we do have the ability to create a compatible pixmap
# and copy it there.
#
# This class maintains an image of the same size as the window, as a
# framebuffer-equivalent (the .image member).  It provides a call to refresh
# a given rectangle from that image.
class WindowImage:
    def __init__(self, widget, width, height):
        self.image = Image.new('RGB', (width, height), color=windowBgColor)
        self.draw = ImageDraw.Draw(self.image)
        self.widget = widget
        self.widget.config(bg="") # may not be necessary
        self.dc = None
        self.dirty = False

    def refresh(self, region=None):
        if region == None:
            self.drawImage(self.image, (0, 0))
        else:
            self.drawImage(self.image, (region[0], region[1]), region)

    def drawImage(self, image, location, subImage=None):
        if subImage:
            x1, y1, x2, y2 = subImage
            width = x2 - x1
            height = y2 - y1
            image = image.crop(subImage)
        else:
            width = image.width
            height = image.height
        dib = ImageWin.Dib('RGB', (width, height))
        dib.paste(image)
        x, y = location
        # While the documentation says that Dib.draw can take a window handle,
        # it really can't.  If you pass the integer ID, it doesn't know that
        # it has a window handle.  And if you pass it the output from
        # ImageWin.HWND, it tries to use it as an integer and fails.  Here,
        # we're using an undocumented internal function to get the device
        # context from the window ID
        if self.dc is None:
            self.dc = dib.image.getdc(self.widget.winfo_id())
        dib.draw(self.dc, (x, y, x + width, y + height))

class App:
    def __init__(self):
        self.windows = []
        self.root = tk.Tk()
        self.root.iconbitmap("python-g.ico")
        self.root.withdraw()
        self.newWindow()
        self.frameCount = 0

    def mainLoop(self):
        self.icons = [icon.Icon("Icon %d" % (i % 150)) for i in range((40*90))]
        for x in range(40):
            for y in range(90):
                self.icons[y*4+x].drawIcon(self.windows[0].winImg,
                    x*60 + (self.frameCount % 100)*10, y*20, 42, (5, 10))
        self.root.after(1000, self.animate)
        self.root.mainloop()

    def animate(self):
        print(self.frameCount)
        self.frameCount += 1
        winImg = self.windows[0].winImg
        fc = appData.frameCount
        x = fc % (winImg.image.width - 500)
        y = fc % (winImg.image.height - 500)
        winImg.refresh((x, y, x + 500, y + 500))
        self.root.after(10, self.animate)

    def removeWindow(self, window):
        self.windows.remove(window)
        if len(self.windows) == 0:
            exit(1)

    def newWindow(self):
        self.windows.append(Window(self.root))

if __name__ == '__main__':
    appData = App()
    appData.mainLoop()
