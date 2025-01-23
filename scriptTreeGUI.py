import os
import time
import platform as pf
import signal as sig
import tkinter as tk
from tkinter import ttk
import tkinter.filedialog
import pexpect
from dataclasses import dataclass

#GLOBAL
workSpace = os.environ['HOME'] + '/scriptTreeWorkSpace'
configFilePath = os.environ['HOME'] + '/scriptTreeWorkSpace/.conf'
saveDirPath = os.environ['HOME'] + '/scriptTreeWorkSpace/data'
fileListPath = os.environ['HOME'] + '/scriptTreeWorkSpace/data/fileList.txt'
folderListPath = os.environ['HOME'] + '/scriptTreeWorkSpace/data/folderList.txt'
scriptTree = None
nodeFileList = list()
nodeFolderList = list()
nodeIdlate = 0

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


def isInWidget(x,y,wight):
	return x > wight.winfo_x() and x < (wight.winfo_x()+ wight.winfo_width()) and y > wight.winfo_y() and y < (wight.winfo_y()+ wight.winfo_height())

def openFile(dir,ex):
	fTyp = [(dir, ex)]
	iDir = os.path.abspath(os.path.dirname(__file__))
	return tkinter.filedialog.askopenfilename(filetypes=fTyp, initialdir=iDir)

def openFolder():
	iDir = os.path.abspath(os.path.dirname(__file__))
	return tkinter.filedialog.askdirectory(initialdir=iDir)

def loadFile(path):
	l = list()

	with open(path) as f:
		for line in f:
			l.append(line.strip("\n").split(" "))

	return l


def saveFile(path,data):
	with open(path,"w") as f:
		sList = list()
		for e in data:
			sList.append(e[0])
		
		f.write("\n".join(sList))

def scanFolder(folder):
	fList = list()
	for fileName in os.listdir(folder):
		filePath = os.path.join(folder,fileName)
		if os.path.isfile(filePath):
			if os.path.splitext(fileName)[1] == '.node':
				fList.append(fileName)

	return fList

@dataclass	
class NodeType:
	path : str
	name : str
	id : str
	width : int
	height : int
	x : int
	y : int

class Application(tk.Frame):
	def __init__(self, master=None):
		super().__init__(master)

		#各種変数の生成
		self.nodeAreaRatio = 0.7
		self.mouseGrip = 0,None
		self.opendFolder = list()
		self.paintNodes = list()

		#ウィンドウの生成
		self.master.title("scriptTreeGUI")
		self.master.geometry("400x300")	
		self.master.bind("<Configure>", self.resizeWindowHandller)
		self.master.bind("<Button-1>",self.MouseGrap)
		self.master.bind("<ButtonRelease-1>",self.MouseRelease)
		self.master.bind("<Motion>",self.MouseMotion)
		
		#メニューの作成
		self.menubar = tk.Menu(self.master)
		self.master.config(menu=self.menubar)
		filemenu = tk.Menu(self.menubar, tearoff=0)
		filemenu.add_command(label="Open Node File", command=self.openNodeFile)
		filemenu.add_command(label="Open Node Folder", command=self.openNodeFolder)
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
		self.flameBorder.bind("<Motion>",self.flameBorderMotion)

		#Canvas生成
		self.nodeArea = tk.Canvas(self.mainFlame, relief='groove', background="white")
		self.nodeArea.pack(side='left', fill="both", expand=True)
		self.nodeArea.bind("<Button-1>",self.NodeGrap)

		#Notebook生成
		self.subWindow= ttk.Notebook(self.subFlame)
		self.subWindow.pack(side='left', fill="both", expand=True)
		self.library = tk.Frame(self.subWindow)
		self.subWindow.add(self.library, text=' library ')
		self.nodeList = tk.Listbox(self.library, selectmode="single", height=6)
		self.initList()
		self.nodeList.bind('<<ListboxSelect>>', self.nodeListSelectHandller)
		scrollbar = ttk.Scrollbar(self.library, orient='vertical', command=self.nodeList.yview)
		self.nodeList['yscrollcommand'] = scrollbar.set
		scrollbar.pack(side='right',fill="y")
		self.nodeList.pack(side='left', fill="both", expand=True)
		self.info = tk.Frame(self.subWindow)
		self.subWindow.add(self.info, text=' info ')

		self.master.after(20,self.nodeAreaDraw)

	############################CallBacks##############################

	def resizeWindowHandller(self,event):
		self.resizeChildWeight()

	def flameBorderGrap(self,event):
		#グラップチェック
		if self.mouseGrip[0] == 0:
			self.mouseGrip = 2,"flameBorder"

	def flameBorderMotion(self,event):
		if self.mouseGrip[0] == 2 and isInWidget(event.x_root,event.y_root,self.master):
			self.nodeAreaRatio = (event.x_root - self.master.winfo_x()) / self.master.winfo_width() 
			self.resizeChildWeight()

	def NodeGrap(self,event):
		#グラップチェック
		if self.mouseGrip[0] == 0:
			self.mouseGrip = 1,None
			x = self.master.winfo_pointerx() - self.master.winfo_rootx()
			y = self.master.winfo_pointery() -self.master.winfo_rooty()
			for (index,(node,pipes)) in enumerate(reversed(self.paintNodes)):
				if x > node.x and y > node.y and x < (x + node.width) and y < (y + node.height):
					self.paintNodes[len(self.paintNodes) - index - 1],self.paintNodes[-1] = self.paintNodes[-1],self.paintNodes[len(self.paintNodes) - index - 1]
					self.mouseGrip = 4,(-1,x - node.x,y - node.y)
					break

	def MouseGrap(self,event):
		#グラップチェック
		if self.mouseGrip[0] == 0:
			self.mouseGrip = 1,None
		

	def MouseRelease(self,event):
		#リリース
		if self.mouseGrip[0] == 2:
			self.mouseGrip = 0,None
		elif self.mouseGrip[0] == 3:
			if self.mouseGrip[1] != None:
				if event.y > 0 and self.nodeArea.winfo_containing(event.x_root-1,event.y_root-1) == self.nodeArea:
					#座標計算
					x = self.master.winfo_pointerx() - self.master.winfo_rootx()
					y = self.master.winfo_pointery() -self.master.winfo_rooty()

					#NodeDataの生成
					global nodeIdlate
					fileName = os.path.splitext(os.path.basename(self.mouseGrip[1].cget("text")))[0]
					node = NodeType(x=x,y=y,width=100,height=100,path = self.mouseGrip[1].cget("text"),name=fileName ,id=str(nodeIdlate))
					nodeIdlate+=1

					#Nodeの生成
					scriptTree.expect(">>>")
					scriptTree.sendline("run "+node.path+" -name "+node.id)

					scriptTree.expect("\n")
					scriptTree.expect("\n")
					
					if scriptTree.before.decode(encoding='utf-8').split(" ")[2] != 'success\r':
						print("run node failed")
					else:
						scriptTree.expect(">>>")
						scriptTree.sendline("list")

						pipeList = list()
						scriptTree.expect("\n")
						line = scriptTree.before.decode(encoding='utf-8')
						while not '--------------------------------------------------------' in line:
							scriptTree.expect("\n")
							line = scriptTree.before.decode(encoding='utf-8')
							if "name: "+node.id+"\r" in line:
								scriptTree.expect("\n")
								scriptTree.expect("\n")
								scriptTree.expect("\n")
								line = scriptTree.before.decode(encoding='utf-8')
								while not '------------------------------------------' in line:
									pipeName = line[:-1].split(":")[1]
									scriptTree.expect("\n")
									line = scriptTree.before.decode(encoding='utf-8')
									pipeType = line[:-1].split(":")[1]
									scriptTree.expect("\n")
									line = scriptTree.before.decode(encoding='utf-8')
									pipeUnit = line[:-1].split(":")[1]
									scriptTree.expect("\n")
									line = scriptTree.before.decode(encoding='utf-8')
									pipeLength = line[:-1].split(":")[1]
									scriptTree.expect("\n")
									scriptTree.expect("\n")
									if pipeType == 'IN':
										scriptTree.expect("\n")
									line = scriptTree.before.decode(encoding='utf-8')
									pipeList.append((pipeName,pipeType,pipeUnit,pipeLength))

						
						self.paintNodes.append((node,pipeList))


								
				self.mouseGrip[1].destroy()
			self.mouseGrip = 0,None
		else:
			self.mouseGrip = 0,None
	
	def MouseMotion(self,event):
		if self.mouseGrip[0] == 3:
			if self.mouseGrip[1] == None:
				self.mouseGrip = 3,(tk.Label(self.master, text=self.mouseGrip[2]))
			
			# 座標計算
			x = self.master.winfo_pointerx() - self.master.winfo_rootx()
			y = self.master.winfo_pointery() -self.master.winfo_rooty()

			self.mouseGrip[1].place(x=x, y=y)
		elif self.mouseGrip[0] == 4 and event.y > 0 and self.nodeArea.winfo_containing(event.x_root-1,event.y_root-1) == self.nodeArea:
			#座標計算
			x = self.master.winfo_pointerx() - self.master.winfo_rootx()
			y = self.master.winfo_pointery() -self.master.winfo_rooty()
			#反映
			self.paintNodes[self.mouseGrip[1][0]][0].x = x - self.mouseGrip[1][1]
			self.paintNodes[self.mouseGrip[1][0]][0].y = y - self.mouseGrip[1][2]

	
	def nodeListSelectHandller(self,event):
		#get index
		selectIndex = self.nodeList.curselection()[0]

		filePath = None
		if selectIndex >= len(nodeFileList):
			iter = len(nodeFileList)
			isFile = True
			folderName = nodeFolderList[0][0]
			for folder in nodeFolderList:
				#if folder name select
				if iter == selectIndex:
					isFile = False

					if folder[0] in self.opendFolder:
						#open
						self.opendFolder.remove(folder[0])
						self.nodeList.delete(iter)
						self.nodeList.insert(iter,folder[0] + " ▶ ") 
						for file in folder[1:]:
							self.nodeList.delete(iter+1)
					else:
						#close
						self.opendFolder.append(folder[0])
						self.nodeList.delete(iter)
						self.nodeList.insert(iter,folder[0] + " ▼ ")
						for file in folder[1:]:
							iter+=1
							self.nodeList.insert(iter,"    " + file)

					break
				elif iter > selectIndex:
					break

				#inclement
				if folder[0] in self.opendFolder:
					folderName = folder[0]
					iter += len(folder)
				else:
					iter += 1
				
			if isFile:
				filePath = folderName + "/" + self.nodeList.get(selectIndex)[4:]
		else:
			filePath = nodeFileList[selectIndex]

		#グラップチェック
		if self.mouseGrip[0] == 0 and filePath != None:
			self.mouseGrip = 3,None ,filePath
					

	#####################################################################

	###############################Func##################################

	def nodeAreaDraw(self):
		self.nodeArea.delete("all")
		for (node,pipes) in self.paintNodes:
			self.nodeArea.create_rectangle(node.x,node.y,node.x+node.width,node.y+node.height,fill="gray")
			self.nodeArea.create_text(node.x+ node.width/2,node.y-8,text=node.name)
		self.master.after(20,self.nodeAreaDraw)

	def resizeChildWeight(self):
		#エラー回避
		self.nodeAreaRatio = min(self.nodeAreaRatio,0.9)
		self.nodeAreaRatio = max(self.nodeAreaRatio,0.1)

		self.nodeArea.configure(width=self.master.winfo_width() * self.nodeAreaRatio)
		self.subFlame.configure(width=max(0.0,self.master.winfo_width() * (1.0 - self.nodeAreaRatio) - 7))
	
	def openNodeFile(self):
		fileName = openFile("nodeファイル","*.node")
		if len(fileName) != 0:
			isInclude = False
			for e in nodeFileList:
				if e[0] == fileName:
					isInclude = True
					break

			if not isInclude:
				files = list()
				files.append(fileName)
				self.insertFile(files)
	
	def openNodeFolder(self):
		folderNmae = openFolder()
		if len(folderNmae) != 0:
			isInclude = False
			for e in nodeFolderList:
				if e[0] == folderNmae:
					isInclude = True
					break

			if not isInclude:
				folderList = list()
				folderList.append(folderNmae)
				folderList += scanFolder(folderNmae)
				self.insertFolder(folderList)
	
	def initList(self):
		for file in nodeFileList:
			self.nodeList.insert(tkinter.END,file[0])
		
		for folder in nodeFolderList:
			self.nodeList.insert(tkinter.END,folder[0] + " ▶ ")

	def insertFile(self,fileList):
		self.nodeList.insert(len(nodeFileList),fileList[0])
		nodeFileList.append(fileList)

	def insertFolder(self,folderList):
		self.nodeList.insert(tkinter.END,folderList[0] + " ▶ ")
		nodeFolderList.append(folderList)

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
	for folder in nodeFolderList:
		folder += scanFolder(folder[0])

	# lunch
	root = tk.Tk()
	app = Application(master=root)

	# sighandller
	sig.signal(sig.SIGINT, sigintHandle)
	root.bind('<Control-c>', ctrlChandle) 

	# loop
	app.mainloop()

	# save data
	saveFile(fileListPath,nodeFileList)
	saveFile(folderListPath,nodeFolderList)

	#quit
	scriptTree.expect(">>>")
	scriptTree.sendline("quit")
	time.sleep(1)
	if scriptTree.isalive():
		scriptTree.kill(sig.SIGINT)
		time.sleep(1)
		if scriptTree.isalive():
			scriptTree.terminate(True)
