import os
import time
import platform as pf
import signal as sig
import tkinter as tk
from tkinter import ttk
import tkinter.filedialog
import tkinter.simpledialog as simpledialog
import pexpect
from dataclasses import dataclass
from enum import Enum

@dataclass	
class NodeType:
	path : str
	name : str
	id : str
	width : int
	height : int
	x : int
	y : int

class GrabType(Enum):
	No = 0
	Dummy = 1
	Flame = 2
	List = 3
	Node = 4
	NodeArea = 5
	NodeArrow = 6

class FoucusObj(Enum):
	No = 0
	NodeArrow = 1
	Node = 2

#GLOBAL
workSpace = os.environ['HOME'] + '/scriptTreeWorkSpace'
configFilePath = os.environ['HOME'] + '/scriptTreeWorkSpace/.conf'
saveDirPath = os.environ['HOME'] + '/scriptTreeWorkSpace/data'
fileListPath = os.environ['HOME'] + '/scriptTreeWorkSpace/data/fileList.txt'
folderListPath = os.environ['HOME'] + '/scriptTreeWorkSpace/data/folderList.txt'
logFolder = ''
scriptTree = None
nodeFileList = list()
nodeFolderList = list()
nodeIdlate = 0
scriptTreeTimerValue = 1000

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

def getLatestFolder(folder):
	dirList = list()

	for f in os.listdir(folder):
		path = os.path.join(folder,f)
		if os.path.isdir(path):
			dirList.append(path)

	if len(dirList) == 0:
		return ''

	dirList.sort(key=os.path.getmtime,reverse=True)
	return dirList[0]


class Application(tk.Frame):
	def __init__(self, master=None):
		super().__init__(master)

		#各種変数の生成
		self.nodeAreaRatio = 0.7
		self.mouseGrip = GrabType.No,None
		self.opendFolder = list()
		self.paintNodes = list()
		self.connectList = list()
		self.underCursor = None
		self.focuseObject = FoucusObj.No,None
		self.displayNode = None
		self.editConst = None

		#ウィンドウの生成
		self.master.title("scriptTreeGUI")
		self.master.geometry("1280x720")	
		self.master.bind("<Configure>", self.resizeWindowHandller)
		self.master.bind("<Button-1>",self.MouseGrap)
		self.master.bind("<ButtonRelease-1>",self.MouseRelease)
		self.master.bind("<Motion>",self.MouseMotion)
		
		#メニューの作成
		self.menubar = tk.Menu(self.master)
		self.master.config(menu=self.menubar)
		fileMenu = tk.Menu(self.menubar, tearoff=0)
		fileMenu.add_command(label="Open Node File", command=self.openNodeFile)
		fileMenu.add_command(label="Open Node Folder", command=self.openNodeFolder)
		self.menubar.add_cascade(label="File",menu=fileMenu)
		self.menubar.add_separator()
		timerMenu = tk.Menu(self.menubar, tearoff=0)
		timerMenu.add_command(label="Timer Run", command=self.nodeSystemTimerRun)
		timerMenu.add_command(label="Timer Stop", command=self.nodeSystemTimerStop)
		timerMenu.add_command(label="Timer Set", command=self.nodeSystemTimerSet)
		self.menubar.add_cascade(label="Timer",menu=timerMenu)
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
		self.master.bind("<KeyPress>",self.nodeDeleateHandler)

		#Notebook生成
		self.subWindow= ttk.Notebook(self.subFlame)
		self.subWindow.pack(side='left', fill="both", expand=True)
		# lib
		self.library = tk.Frame(self.subWindow)
		self.subWindow.add(self.library, text=' library ')
		self.nodeList = tk.Listbox(self.library, selectmode="single", height=6)
		self.initList()
		self.nodeList.bind('<<ListboxSelect>>', self.nodeListSelectHandller)
		scrollbar = ttk.Scrollbar(self.library, orient='vertical', command=self.nodeList.yview)
		self.nodeList['yscrollcommand'] = scrollbar.set
		scrollbar.pack(side='right',fill="y")
		self.nodeList.pack(side='left', fill="both", expand=True)
		# info
		self.info = tk.Frame(self.subWindow)
		self.info_nodeName = tk.Label(self.info,text="",background='white',relief='solid',anchor='w')
		self.info_nodeName.place(relx = 0.05,y = 20,relwidth= 0.9)
		self.info_nodeId = tk.Label(self.info,text="id:1")
		self.info_nodeId.place(relx = 0.95,y = 56,anchor='e')
		self.info_nodePipes = ttk.Treeview(self.info)
		self.info_nodePipes['columns'] = ('Name','Type','Unit','Length')
		self.info_nodePipes.column('#0',width=0, stretch='no')
		self.info_nodePipes.column('Name',anchor='center',width=40)
		self.info_nodePipes.column('Type',anchor='center',width=40)
		self.info_nodePipes.column('Unit',anchor='center',width=40)
		self.info_nodePipes.column('Length',anchor='center',width=40)
		self.info_nodePipes.heading('Name',text='Name')
		self.info_nodePipes.heading('Type',text='Type')
		self.info_nodePipes.heading('Unit',text='Unit')
		self.info_nodePipes.heading('Length',text='Length')
		self.info_nodePipes.place(relx = 0.05,y = 70,relwidth=0.90,height=220)
		self.info_nodePipes.bind("<<TreeviewSelect>>",self.pipeTreeSelected)
		tk.Label(self.info,text="const value").place(relx = 0.05,y = 300,relwidth=0.90)
		self.info_constValue = tk.Entry(self.info,state='disabled')
		self.info_constValue.place(relx=0.05,y = 320,relwidth=0.9)
		self.info_logArea = ttk.Notebook(self.info)
		self.info_logArea.place(relx=0.05,y = 360,relwidth=0.9,height=300)
		self.info_logPage = tk.Frame(self.info_logArea)
		self.info_graphPage = tk.Frame(self.info_logArea)
		self.info_logArea.add(self.info_logPage, text=' log ')
		self.info_debugLog = tk.Text(self.info_logPage,state='disabled')
		scrollbar = ttk.Scrollbar(self.info_logPage, orient='vertical', command=self.info_debugLog.yview)
		self.info_debugLog['yscrollcommand'] = scrollbar.set
		scrollbar.pack(side='right',fill="y")
		self.info_debugLog.pack(side='left',fill='both',expand=True) 
		self.info_logArea.add(self.info_graphPage, text=' graph ')
		self.subWindow.add(self.info, text=' info ')

		self.master.after(20,self.nodeAreaDraw)

	############################CallBacks##############################

	def nodeSystemTimerRun(self):
		scriptTree.expect(">>>")
		scriptTree.sendline("timer run")
		scriptTree.expect("\n")
		scriptTree.expect("\n")
		
	def nodeSystemTimerStop(self):
		scriptTree.expect(">>>")
		scriptTree.sendline("timer stop")
		scriptTree.expect("\n")
		scriptTree.expect("\n")

	def nodeSystemTimerSet(self):
		global scriptTreeTimerValue
		scriptTreeTimerValue = simpledialog.askfloat("Input Box", "Wakeup timer period[ms]",initialvalue=float(scriptTreeTimerValue))
		
		if scriptTreeTimerValue != None:
			scriptTree.expect(">>>")
			scriptTree.sendline("timer set " + str(scriptTreeTimerValue))
			scriptTree.expect("\n")
			scriptTree.expect("\n")

		
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

	def resizeWindowHandller(self,event):
		self.resizeChildWeight()

	def flameBorderGrap(self,event):
		#グラップチェック
		if self.mouseGrip[0] == GrabType.No:
			self.mouseGrip = GrabType.Flame,"flameBorder"
	
	def nodeDeleateHandler(self,event):
		if event.keysym == 'Delete':
			if self.focuseObject[0] == FoucusObj.NodeArrow:
				#deleate connect

				#find target
				deleateIndexList = list()
				for i in range(len(self.connectList)):
					((leftPipe,leftPos),(rightPipe,rightPos)) = self.connectList[i]

					if leftPipe == self.focuseObject[1] or rightPipe == self.focuseObject[1]:
						deleateIndexList.append(i - len(deleateIndexList))

				#deleate
				for i in deleateIndexList:
					((leftPipe,leftPos),(rightPipe,rightPos)) = self.connectList[i]
					scriptTree.expect(">>>")
					scriptTree.sendline("disconnect "+leftPipe[0]+' '+leftPipe[1])
					self.connectList.pop(i)
			elif self.focuseObject[0] == FoucusObj.Node:
				#パイプ探査
				deleateIndexList = list()
				for i in range(len(self.connectList)):
					((leftPipe,leftPos),(rightPipe,rightPos)) = self.connectList[i]

					if leftPipe[0] == self.focuseObject[1] or rightPipe[0] == self.focuseObject[1]:
						deleateIndexList.append(i - len(deleateIndexList))
				
				#パイプ削除
				for i in deleateIndexList:
					((leftPipe,leftPos),(rightPipe,rightPos)) = self.connectList[i]
					self.connectList.pop(i)

				#ノード削除

				scriptTree.expect(">>>")
				scriptTree.sendline("kill "+self.focuseObject[1])

				deleateIndex = -1
				for index,(node,pipes) in enumerate(self.paintNodes):
					if node.id == self.focuseObject[1]:
						deleateIndex = index

				if deleateIndex != -1:
					self.paintNodes.pop(deleateIndex)
				self.mouseGrip = GrabType.No,None
				self.focuseObject = FoucusObj.No,None
		elif event.keysym == 'Return':
			if self.info_constValue.focus_get() == self.info_constValue:
				self.info_nodePipes.focus_set()
				scriptTree.expect(">>>")
				scriptTree.sendline('const set '+self.displayNode[0].id+' '+self.editConst[0]+' '+self.info_constValue.get().replace(',',' '))
				scriptTree.expect("\n")
				scriptTree.expect("\n")

				if scriptTree.before.decode(encoding='utf-8').split(' ')[2] != 'success\r':
					self.updateInfo()

			
				

	def flameBorderMotion(self,event):
		if self.mouseGrip[0] == GrabType.Flame and isInWidget(event.x_root,event.y_root,self.master):
			self.nodeAreaRatio = (event.x_root - self.master.winfo_x()) / self.master.winfo_width() 
			self.resizeChildWeight()

	def MouseGrap(self,event):
		self.focuseObject = FoucusObj.No,None

		#NodeArea
		if event.y > 0 and self.nodeArea.winfo_containing(event.x_root-1,event.y_root-1) == self.nodeArea:
			#グラップチェック
			if self.mouseGrip[0] == GrabType.No:

				if self.underCursor != None:
					self.focuseObject = FoucusObj.NodeArrow,self.underCursor
					self.mouseGrip = GrabType.NodeArrow,self.underCursor
					return

				#座標計算
				x = self.master.winfo_pointerx() - self.master.winfo_rootx()
				y = self.master.winfo_pointery() -self.master.winfo_rooty()

				self.mouseGrip = GrabType.NodeArea,(x,y)

				for (index,(node,pipes)) in enumerate(reversed(self.paintNodes)):
					if x > node.x and y > node.y and x < (node.x + node.width) and y < (node.y + node.height):
						self.paintNodes[len(self.paintNodes) - index - 1],self.paintNodes[-1] = self.paintNodes[-1],self.paintNodes[len(self.paintNodes) - index - 1]
						self.focuseObject = FoucusObj.Node,node.id
						self.mouseGrip = GrabType.Node,(-1,x - node.x,y - node.y)
						self.displayNode = (node,pipes)
						self.updateInfo()

						return

		#グラップチェック
		if self.mouseGrip[0] == GrabType.No:
			self.mouseGrip = GrabType.Dummy,None
		

	def MouseRelease(self,event):
		#リリース
		if self.mouseGrip[0] == GrabType.NodeArrow:
			if self.underCursor != None:

				#すでに接続済みor自己接続
				if self.mouseGrip[1] == self.underCursor:
					self.mouseGrip = GrabType.No,None
					return
				for  ((leftPipe,leftPos),(rightPipe,rightPos)) in self.connectList:
					if leftPipe == self.underCursor and rightPipe == self.mouseGrip[1]:
						self.mouseGrip = GrabType.No,None
						return
					if rightPipe == self.underCursor and leftPipe == self.mouseGrip[1]:
						self.mouseGrip = GrabType.No,None
						return
					
				leftPipe = None
				rightPipe = None
				
				for (node,pipes) in self.paintNodes:
					if node.id == self.mouseGrip[1][0]:
						inputCount = 0
						outputCount = 0

						for pipe in pipes:							
							if pipe[1] == 'OUT':
								if pipe[0] == self.mouseGrip[1][1]:
									leftPipe = (pipe,(node.x + node.width +7,(node.y+8) + outputCount * 16))
								outputCount += 1
							else:
								if pipe[0] == self.mouseGrip[1][1]:
									leftPipe = (pipe,(node.x,(node.y+8) + inputCount * 16))
								inputCount += 1

					if node.id == self.underCursor[0]:
						inputCount = 0
						outputCount = 0

						for pipe in pipes:							
							if pipe[1] == 'OUT':
								if pipe[0] == self.underCursor[1]:
									rightPipe = (pipe,(node.x + node.width +7,(node.y+8) + outputCount * 16))
								outputCount += 1
							else:
								if pipe[0] == self.underCursor[1]:
									rightPipe = (pipe,(node.x,(node.y+8) + inputCount * 16))
								inputCount += 1

				if leftPipe[0][2] == rightPipe[0][2] and leftPipe[0][3] == rightPipe[0][3] and leftPipe[0][1] != rightPipe[0][1] and leftPipe[0][1] != 'CONST' and rightPipe[0][1] != 'CONST':
					scriptTree.expect(">>>")
					if leftPipe[0][1] != 'IN':
						self.connectList.append((((self.underCursor[0],rightPipe[0][0]),rightPipe[1]),((self.mouseGrip[1][0],leftPipe[0][0]),leftPipe[1])))
						scriptTree.sendline("connect "+self.underCursor[0]+' '+rightPipe[0][0]+' '+self.mouseGrip[1][0]+' '+leftPipe[0][0])
					else:
						self.connectList.append((((self.mouseGrip[1][0],leftPipe[0][0]),leftPipe[1]),((self.underCursor[0],rightPipe[0][0]),rightPipe[1])))
						scriptTree.sendline("connect "+self.mouseGrip[1][0]+' '+leftPipe[0][0]+' '+self.underCursor[0]+' '+rightPipe[0][0])
					
					
				else:
					print("pipe is Invalid")
					print("Must be IN and OUT with the same data type and same array length")

		elif self.mouseGrip[0] == GrabType.List:
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
						inputCount = 0
						outputCount = 0
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

									if pipeType == 'OUT':
										outputCount+= 1
									else:
										inputCount += 1 
						
						node.height = max(outputCount,inputCount) * 16

						
						self.paintNodes.append((node,pipeList))


								
				self.mouseGrip[1].destroy()
			
		self.mouseGrip = GrabType.No,None
	
	def MouseMotion(self,event):
		if self.mouseGrip[0] == GrabType.List:
			if self.mouseGrip[1] == None:
				self.mouseGrip = GrabType.List,(tk.Label(self.master, text=self.mouseGrip[2]))
			
			# 座標計算
			x = self.master.winfo_pointerx() - self.master.winfo_rootx()
			y = self.master.winfo_pointery() -self.master.winfo_rooty()

			self.mouseGrip[1].place(x=x, y=y)
		elif event.y > 0 and self.nodeArea.winfo_containing(event.x_root-1,event.y_root-1) == self.nodeArea:
			#座標計算
			x = self.master.winfo_pointerx() - self.master.winfo_rootx()
			y = self.master.winfo_pointery() -self.master.winfo_rooty()
			
			if self.mouseGrip[0] == GrabType.Node:
				moveX = x - self.mouseGrip[1][1] - self.paintNodes[self.mouseGrip[1][0]][0].x 
				moveY = y - self.mouseGrip[1][2] - self.paintNodes[self.mouseGrip[1][0]][0].y

				for i in range(len(self.connectList)):
					((leftPipe,leftPos),(rightPipe,rightPos)) = self.connectList[i]
					if self.paintNodes[self.mouseGrip[1][0]][0].id == leftPipe[0]:
						leftPos = (leftPos[0] + moveX, leftPos[1] + moveY)
						self.connectList[i] = ((leftPipe,leftPos),(rightPipe,rightPos))
					if self.paintNodes[self.mouseGrip[1][0]][0].id == rightPipe[0]:
						rightPos = (rightPos[0] + moveX, rightPos[1] + moveY)
						self.connectList[i] = ((leftPipe,leftPos),(rightPipe,rightPos))

				#反映
				self.paintNodes[self.mouseGrip[1][0]][0].x += moveX
				self.paintNodes[self.mouseGrip[1][0]][0].y += moveY
			elif self.mouseGrip[0] == GrabType.NodeArea:

				moveX = x -self.mouseGrip[1][0]
				moveY = y -self.mouseGrip[1][1]

				for i in range(len(self.paintNodes)):
					self.paintNodes[i][0].x += moveX
					self.paintNodes[i][0].y += moveY
				
				for i in range(len(self.connectList)):
					((leftPipe,leftPos),(rightPipe,rightPos)) = self.connectList[i]
					leftPos = (leftPos[0] + moveX, leftPos[1] + moveY)
					rightPos = (rightPos[0] + moveX, rightPos[1] + moveY)
					self.connectList[i] = ((leftPipe,leftPos),(rightPipe,rightPos))

				self.mouseGrip = GrabType.NodeArea,(x,y)
			else:
				#矢印を光らせる
				self.underCursor = None
				for (node,pipes) in self.paintNodes:
					#矢印の範囲かチェック
					if node.y < y and (node.y+node.height) > y:

						if (node.x - 10) < x  and node.x > x:#IN側矢印
							inCount = int((y - node.y) / 16)
							for (pipeName,pipeType,pipeUnit,pipeLength) in pipes:
								if pipeType != 'OUT':
									if inCount == 0:
										self.underCursor = (node.id,pipeName)
										break
									else:
										inCount-=1

						elif (node.x + node.width) < x  and (node.x + node.width + 10) > x:#OUT側矢印
							outCount = int((y - node.y) / 16)
							for (pipeName,pipeType,pipeUnit,pipeLength) in pipes:
								if pipeType == 'OUT':
									if outCount == 0:
										self.underCursor = (node.id,pipeName)
										break
									else:
										outCount-=1


	
	def nodeListSelectHandller(self,event):
		#get index
		selection = self.nodeList.curselection()
		if selection == ():
			return

		selectIndex = selection[0]

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
		if self.mouseGrip[0] == GrabType.No and filePath != None:
			self.mouseGrip = GrabType.List,None ,filePath
					
	def pipeTreeSelected(self,event):
		id = self.info_nodePipes.focus()
		
		if id != '':
			pipeType = self.info_nodePipes.item(id,'values')
			if pipeType[1] == 'CONST':
				
				#store
				self.editConst = pipeType

				#get value
				scriptTree.expect(">>>")
				scriptTree.sendline('const get '+self.displayNode[0].id+' '+pipeType[0])
				scriptTree.expect("\n")
				scriptTree.expect("\n")
				
				arrayStr = ''

				#parse
				if scriptTree.before.decode(encoding='utf-8').split(' ')[2] == 'success:\r':
					length = int(pipeType[3])
					for i in range(length):
						scriptTree.expect("\n")
						num = float(scriptTree.before.decode(encoding='utf-8').split(':')[1])

						if i != 0:
							arrayStr += ','

						if num.is_integer():
							arrayStr += str(int(num))
						else:
							arrayStr += str(num)

				#display
				self.info_constValue.delete(0,'end')
				self.info_constValue['state'] = 'normal'
				self.info_constValue.insert(0,arrayStr)

	#####################################################################

	###############################Func##################################

	def nodeAreaDraw(self):
		self.nodeArea.delete("all")
		for (node,pipes) in self.paintNodes:
			if self.focuseObject[0] == FoucusObj.Node and self.focuseObject[1] == node.id: 
				self.nodeArea.create_rectangle(node.x,node.y,node.x+node.width,node.y+node.height,fill="deep sky blue",outline='blue',width=3)
			else:
				self.nodeArea.create_rectangle(node.x,node.y,node.x+node.width,node.y+node.height,fill="gray",outline='black')
			self.nodeArea.create_text(node.x+ node.width/2,node.y-8,text=node.name)
			inputCount = 0
			outputCount = 0
			for (pipeName,pipeType,pipeUnit,pipeLength) in pipes:
				c = 'black'
				w = 2
				if (self.underCursor != None and (node.id,pipeName) == self.underCursor) or \
					(self.focuseObject[0] == FoucusObj.NodeArrow and (node.id,pipeName) == self.focuseObject[1]):
					c = 'blue'
					w = 3
				
				if self.mouseGrip[0] == GrabType.NodeArrow and node.id == self.mouseGrip[1][0] and pipeName == self.mouseGrip[1][1]:
					#座標計算
					x = self.master.winfo_pointerx() - self.master.winfo_rootx()
					y = self.master.winfo_pointery() -self.master.winfo_rooty()

					if pipeType == 'OUT':
						self.nodeArea.create_line(node.x + node.width +7,(node.y+8) + outputCount * 16,x,y,width=w,fill = c)
					else:
						self.nodeArea.create_line(node.x,(node.y+8) + inputCount * 16,x,y,width=w,fill = c)


				if pipeType == 'OUT':
					self.nodeArea.create_text(node.x+ node.width - 3,(node.y+8) + outputCount * 16 ,text=pipeName,anchor='e')
					self.nodeArea.create_line(node.x+ node.width,(node.y+8) + outputCount * 16 - 6,node.x+node.width+7,(node.y+8) + outputCount * 16,width=w,fill = c)
					self.nodeArea.create_line(node.x+ node.width,(node.y+8) + outputCount * 16 + 6,node.x+node.width+7,(node.y+8) + outputCount * 16 ,width=w,fill = c)
					outputCount += 1
				else:
					self.nodeArea.create_text(node.x + 3,(node.y+8) + inputCount * 16 ,text=pipeName,anchor='w')
					self.nodeArea.create_line(node.x - 7,(node.y+8) + inputCount * 16 - 6,node.x-1,(node.y+8) + inputCount * 16,width=w,fill = c)
					self.nodeArea.create_line(node.x - 7,(node.y+8) + inputCount * 16 + 6,node.x-1,(node.y+8) + inputCount * 16 ,width=w,fill = c)
					inputCount += 1

		for ((leftPipe,leftPos),(rightPipe,rightPos)) in self.connectList:
			self.nodeArea.create_line(leftPos[0],leftPos[1],rightPos[0],rightPos[1],width=2)

		self.master.after(20,self.nodeAreaDraw)

	def updateInfo(self):	
		#update display
		(node,pipes) = self.displayNode
		for item in self.info_nodePipes.get_children():
			self.info_nodePipes.delete(item)
		for pipe in pipes:
			self.info_nodePipes.insert(parent='', index='end' ,values=pipe)
		self.info_nodeName['text'] = ' ' + node.name
		self.info_nodeId['text'] = 'id: ' + node.id
		self.info_constValue.delete(0,'end')
		self.info_constValue['state'] = 'disable'

	def resizeChildWeight(self):
		#エラー回避
		self.nodeAreaRatio = min(self.nodeAreaRatio,0.9)
		self.nodeAreaRatio = max(self.nodeAreaRatio,0.1)

		self.nodeArea.configure(width=self.master.winfo_width() * self.nodeAreaRatio)
		self.subFlame.configure(width=max(0.0,self.master.winfo_width() * (1.0 - self.nodeAreaRatio) - 7))
	
	
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
	scriptTree.expect("\n")
	if scriptTree.before.decode(encoding='utf-8') != 'lunch success.\r':
		print('Failed lunch scriptTree')
		exit(1)

	# load data
	nodeFileList = loadFile(fileListPath)
	nodeFolderList = loadFile(folderListPath)
	for folder in nodeFolderList:
		folder += scanFolder(folder[0])

	logFolder = getLatestFolder(workSpace + '/Logs')

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
