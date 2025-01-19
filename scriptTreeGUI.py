import os
import time
import platform as pf
import signal as sig
import tkinter as tk
from tkinter import ttk
import tkinter.filedialog
import pexpect

#GLOBAL
workSpace = os.environ['HOME'] + '/scriptTreeWorkSpace'
configFilePath = os.environ['HOME'] + '/scriptTreeWorkSpace/.conf'
saveDirPath = os.environ['HOME'] + '/scriptTreeWorkSpace/data'
fileListPath = os.environ['HOME'] + '/scriptTreeWorkSpace/data/fileList.txt'
folderListPath = os.environ['HOME'] + '/scriptTreeWorkSpace/data/folderList.txt'
scriptTree = None
nodeFileList = list()
nodeFolderList = list()

#callback
def sigintHandle(signum, r):
	print("handler")
	root.destroy()


def ctrlChandle(event):
	print("ctrlC")
	root.destroy()


#func
def checkAreaBorder(value,center,halfWidth):
	return (value > (center-halfWidth)) and value < (center+halfWidth)


def isInWeight(x,y,wight):
	return x > wight.winfo_x() and x < (wight.winfo_x()+ wight.winfo_width()) and y > wight.winfo_y() and y < (wight.winfo_y()+ wight.winfo_height())

def openFile(dir,ex):
	fTyp = [(dir, ex)]
	iDir = os.path.abspath(os.path.dirname(__file__))
	return tkinter.filedialog.askopenfilename(filetypes=fTyp, initialdir=iDir)

def openFolder(dir,ex):
	fTyp = [(dir, ex)]
	iDir = os.path.abspath(os.path.dirname(__file__))
	return tkinter.filedialog.askdirectory(filetypes=fTyp, initialdir=iDir)

def loadFile(path):
	l = list()

	with open(path) as f:
		for line in f:
			l.append(line.strip("\n").split(" "))

	return l



class Application(tk.Frame):
	def __init__(self, master=None):
		super().__init__(master)

		#各種変数の生成
		self.nodeAreaRatio = 0.7
		self.mouseGrip = 0,"None"

		#ウィンドウの生成
		self.master.title("scriptTreeGUI")
		self.master.geometry("400x300")	
		self.master.bind("<Configure>", self.resizeWindowHandller)

		#メニューの作成
		self.menubar = tk.Menu(self.master)
		self.master.config(menu=self.menubar)
		filemenu = tk.Menu(self.menubar, tearoff=0)
		filemenu.add_command(label="Open Node File", command=self.openNodeFile)
		filemenu.add_command(label="Open Node Folder")
		self.menubar.add_cascade(label="File",menu=filemenu)
		self.menubar.add_separator()

		#フレームを生成
		self.mainFlame = tk.Frame(self.master, relief='groove', borderwidth=1)
		self.subFlame = tk.Frame(self.master, relief='groove', borderwidth=1)
		self.flameBorder = tk.Frame(self.master, relief='groove', borderwidth=1, cursor="sb_h_double_arrow", width=3)
		self.mainFlame.grid(row = 1, column = 0,sticky = tk.NSEW)
		self.flameBorder.grid(row = 1, column = 1,sticky = tk.NSEW)
		self.subFlame.grid(row = 1, column = 2,sticky = tk.NSEW)
		self.master.grid_rowconfigure(1, weight=1)
		self.flameBorder.bind("<Button-1>",self.flameBorderGrap)
		self.flameBorder.bind("<ButtonRelease-1>",self.flameBorderRelease)
		self.flameBorder.bind("<Motion>",self.flameBorderMotion)

		#Canvas生成
		self.nodeArea = tk.Canvas(self.mainFlame, relief='groove')
		self.nodeArea.pack(side='left', fill="both", expand=True)

		#Notebook生成
		self.subWindow= ttk.Notebook(self.subFlame)
		self.subWindow.pack(side='left', fill="both", expand=True)
		self.library = tk.Frame(self.subWindow)
		self.subWindow.add(self.library, text=' library ')
		self.nodeList = tk.Listbox(self.library, selectmode="single", height=6)
		scrollbar = ttk.Scrollbar(self.library, orient='vertical', command=self.nodeList.yview)
		self.nodeList['yscrollcommand'] = scrollbar.set
		self.nodeList.pack(side='left', fill="both", expand=True)
		self.info = tk.Frame(self.subWindow)
		self.subWindow.add(self.info, text=' info ')

	############################CallBacks##############################

	def resizeWindowHandller(self,event):
		self.resizeChildWeight()

	def flameBorderGrap(self,event):
		#グラップチェック
		if self.mouseGrip[0] == 0:
			self.mouseGrip = 1,"flameBorder"
	
	def flameBorderRelease(self,event):
		#リリース
		if self.mouseGrip[0] == 1:
			self.mouseGrip = 0,"None"

	def flameBorderMotion(self,event):
		if self.mouseGrip[0] == 1 and isInWeight(event.x_root,event.y_root,self.master):
			self.nodeAreaRatio = (event.x_root - self.master.winfo_x()) / self.master.winfo_width() 
			self.resizeChildWeight()
	
	def openNodeFile(self):
		fileName = openFile("すべてのファイル","*")
		scriptTree.expect(">>>")
		scriptTree.sendline("check "+fileName)
		scriptTree.expect("\n")
		scriptTree.expect("\n")
		if scriptTree.before.decode(encoding='utf-8').split(' ')[2] != 'not':
			if fileName not in nodeFileList:
				nodeFileList.append(fileName)
	
	def openNodeFolder(self):
		fileName = openFolder(" ","*")
		scriptTree.expect(">>>")
		scriptTree.sendline("check "+fileName)
		scriptTree.expect("\n")
		scriptTree.expect("\n")
		if scriptTree.before.decode(encoding='utf-8').split(' ')[2] != 'not':
			if fileName not in nodeFileList:
				nodeFileList.append(fileName)

	#####################################################################

	###############################Func##################################

	def resizeChildWeight(self):
		#エラー回避
		self.nodeAreaRatio = min(self.nodeAreaRatio,0.9)
		self.nodeAreaRatio = max(self.nodeAreaRatio,0.1)

		self.nodeArea.configure(width=self.master.winfo_width() * self.nodeAreaRatio)
		self.subFlame.configure(width=max(0.0,self.master.winfo_width() * (1.0 - self.nodeAreaRatio) - 7))

	#####################################################################

	

		


if __name__ == "__main__" and pf.system() == "Linux":
	#make dir and File
	if not os.path.isdir(workSpace):
		os.mkdir(workSpace)
	if not os.path.isdir(saveDirPath):
		os.mkdir(saveDirPath)
	if not os.path.isfile(fileListPath):
		open(fileListPath,"w").close()
	if not os.path.isfile(folderListPath):
		open(folderListPath,"w").close()
	os.chdir(workSpace)

	# lunch
	if os.path.isfile('./scriptTree'):
		scriptTree = pexpect.spawn('./scriptTree lunch')
	else:
		scriptTree = pexpect.spawn('scriptTree lunch')

	# load data
	nodeFileList = loadFile(fileListPath)
	nodeFolderList = loadFile(folderListPath)

	# lunch
	root = tk.Tk()
	app = Application(master=root)

	# sighandller
	sig.signal(sig.SIGINT, sigintHandle)
	root.bind('<Control-c>', ctrlChandle) 

	print(nodeFileList)
	print(nodeFolderList)

	# loop
	app.mainloop()

	# save data
	# fFileList = open(fileListPath,"w")
	# fFolderList = open(folderListPath,"w")

	# pickle.dump(nodeFileList,fFileList)
	# pickle.dump(nodeFolderList,fFolderList)

	# fFileList.close()
	# fFolderList.close()

	#quit
	scriptTree.expect(">>>")
	scriptTree.sendline("quit")
	time.sleep(1)
	if scriptTree.isalive():
		scriptTree.kill(sig.SIGINT)
		time.sleep(1)
		if scriptTree.isalive():
			scriptTree.terminate(True)
