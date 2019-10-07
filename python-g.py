# Python-g main module
import tkinter as tk
import icon
from PIL import Image, ImageDraw, ImageTk, ImageWin

windowBgColor = (128, 128, 128, 255)
defaultWindowSize = (800, 800)

# Notes on window drawing:
#
# Tkinter canvas can't handle individual images for each icon.  After about
# 4000 pixmaps, it breaks and dies.  Drawing directly to the screen is also
# problematic.  Here, we have a Windows-only solution, provided by ImageWin
# module of pillow.  This is a kind-of messed up module which gets very little
# use due to bugs and poor documentation.  While it doesn't give us direct
# access to the windows framebuffer, it does allow us to copy data there from
# a PIL image in a two-step process that is sufficiently fast for the purposes
# of this program.

class Window:
    def __init__(self, master, size=None):
        self.top = tk.Toplevel(master)
        self.top.bind("<Destroy>", self.destroyCb)
        self.top.title("Python-G")
        self.frame = tk.Frame(self.top)
        self.menubar = tk.Menu(self.frame)
        self.icons = []
        menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=menu)
        menu.add_command(label="New", command=self.newCb)
        menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=menu)
        menu.add_command(label="Cut")
        menu.add_command(label="Copy")
        menu.add_command(label="Paste")
        self.top.config(menu=self.menubar)
        if size is None:
            size = defaultWindowSize
        width, height = size
        self.imgFrame = tk.Frame(self.frame, bg="", width=width, height=height)
        self.imgFrame.bind("<Expose>", self.exposeCb)
        self.imgFrame.bind("<Configure>", self.configureCb)
        self.imgFrame.pack(fill=tk.BOTH, expand=True)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.image = Image.new('RGB', (width, height), color=windowBgColor)
        self.draw = ImageDraw.Draw(self.image)
        self.dc = None
        self.dirty = False

    def newCb(self):
        appData.newWindow()

    def configureCb(self, evt):
        "Called when window is initially displayed or resized"
        if evt.width != self.image.width or evt.height != self.image.height:
            print('resizing', evt.width, evt.height)
            self.resize(evt.width, evt.height)
        for ic in self.icons:
            ic.drawIcon()

    def exposeCb(self, evt):
        "Called when a new part of the window is exposed and needs to be redrawn"
        self.refresh()

    def destroyCb(self, evt):
        if evt.widget == self.top:
            appData.removeWindow(self)

    def resize(self, width, height):
        self.image = Image.new('RGB', (width, height), color=windowBgColor)
        self.draw = ImageDraw.Draw(self.image)

    def refresh(self, region=None):
        """Redraw any rectangle (region) of the window from the pseudo-framebuffer
           (self.image).  Redraw the whole window if region==None"""
        if region == None:
            self.drawImage(self.image, (0, 0))
        else:
            self.drawImage(self.image, (region[0], region[1]), region)

    def drawImage(self, image, location, subImage=None):
        "Draw an arbitrary image anywhere in the window"
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
            self.dc = dib.image.getdc(self.imgFrame.winfo_id())
        dib.draw(self.dc, (x, y, x + width, y + height))

class App:
    def __init__(self):
        self.windows = []
        self.root = tk.Tk()
        self.root.overrideredirect(1) # Stop vestigial root window from flashing up
        self.root.iconbitmap("python-g.ico")
        self.root.withdraw()
        self.newWindow()
        self.frameCount = 0

    def mainLoop(self):
        #self.root.after(2000, self.animate)
        self.root.mainloop()

    def animate(self):
        print(self.frameCount)
        self.frameCount += 1
        image = self.window[0].image
        fc = appData.frameCount
        x = fc % (image.width - 500)
        y = fc % (image.height - 500)
        #refresh((x, y, x + 500, y + 500))
        self.windows[0].refresh()
        self.root.after(10, self.animate)

    def removeWindow(self, window):
        self.windows.remove(window)
        if len(self.windows) == 0:
            exit(1)

    def newWindow(self):
        window = Window(self.root)
        self.windows.append(window)
        for x in range(8):
            for y in range(18):
                loc = (x*60, y*20)
                window.icons.append(icon.Icon("Icon %d" % (x), loc,
                 42, (5, 10), window))

if __name__ == '__main__':
    appData = App()
    appData.mainLoop()
