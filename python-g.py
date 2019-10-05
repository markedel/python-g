# Python-g main module
import tkinter as tk

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
        self.canvas = tk.Canvas(self.frame, bg="white", width=500, height=500,
         bd=0, highlightthickness=0)
        self.canvas.pack()
        self.frame.grid()
    def newCb(self):
        appData.newWindow()

    def destroyCb(self, evt):
        if evt.widget == self.top:
            appData.removeWindow(self)

class App:
    def __init__(self):
        self.windows = []
        self.root = tk.Tk()
        self.root.iconbitmap("python-g.ico")
        self.root.withdraw()
        self.newWindow()

    def mainLoop(self):
        self.root.mainloop()

    def removeWindow(self, window):
        self.windows.remove(window)
        if len(self.windows) == 0:
            exit(1)

    def newWindow(self):
        self.windows.append(Window(self.root))

if __name__ == '__main__':
    appData = App()
    appData.mainLoop()
