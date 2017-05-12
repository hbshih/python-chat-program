 #!/usr/bin/python3

# Development platform: Mac OSx
# Python version: python 3.6.0
# Version: Aprl.5.2017


from tkinter import *
import sys
import socket
import threading
import time
import select

#
# Global variables
#

username = "" # For storing user's name
server_address = "" # For storing server address
server_port = 0 # For storing server port
my_port = 0 # For storing user port
my_address = "" # For storing user address
chatroom_name="" # For storing chatroom name
recv_buffer = 3000 # Recv buffer when calling recv in the socket library
userID = 0xffffffffffffffff #For storing HEX member id
forward = 0xffffffffffffffff #forward link
sockfd = socket.socket(socket.AF_INET,socket.SOCK_STREAM) # Socket setup
clientSock = socket.socket(socket.AF_INET,socket.SOCK_STREAM) 
clientSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
connection = [] #all forward and backward connection sockets
backward = [] #backward link
message_number = 0
user_message = dict()#largest user message number
forwardSock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
gList = dict() #group member list which the key is hash and the value is [username, IPaddr, Port]


#
# This is the hash function for generating a unique
# Hash ID for each peer.
# Source: http://www.cse.yorku.ca/~oz/hash.html
#
# Concatenate the peer's username, str(IP address), 
# and str(Port) to form the input to this hash function
#
def sdbm_hash(instr):
	hash = 0
	for c in instr:
		hash = int(ord(c)) + (hash << 6) + (hash << 16) - hash
	return hash & 0xffffffffffffffff


#
# Functions to handle user input
#

def do_User():

	global username # For storing user's name
	global userID # For storing user's id
	global chatroom_name
	global my_port
	userInput = userentry.get() # Get the input from user
	if userInput == "" and username == "":
		"""Ask the user to type in a name if the input is empty"""
		outstr = "\n->[User] : Please Type in a Username"
		CmdWin.insert(1.0,outstr)
	elif userInput != "" and username != "":
		"""If the user wanted to change his/her name"""
		if chatroom_name != "":
			#Can only change before joining a chatroom
			outstr = "\n->[User]: You have joined a chatroom, you can't change your username"
			CmdWin.insert(1.0,outstr)
		else:
			#If the user hasn't join any chatroom yet then the name is changed
			username = userInput
			outstr = "\n->[User] : You have changed your username to : " + username
			CmdWin.insert(1.0,outstr)
			userentry.delete(0,END)
	else:
		"""Otherwise clear the entry widget and stored the suername"""
		userentry.delete(0,END)
		if username == "":
			username = userInput
			outstr = "\n->[User] : Your username is : " + username
			userID = sdbm_hash(username+my_address+str(my_port))
			CmdWin.insert(1.0,outstr)
		if userInput == "":
			"""If empty input with no chatroom"""
			outstr = "\n->[User] : Please Type in a new name if you want to change"
			CmdWin.insert(1.0,outstr)



def do_List():
	global recv_buffer

	"""Communicate with server"""
	sockfd.sendall("L::\r\n".encode('ascii')) #Send request to the server
	server_msg=sockfd.recv(recv_buffer) #Get response from the server
	msg=server_msg.split(":".encode('ascii'))
	"""Reading the responses"""
	if msg[0] == b"G":
		#If no error
		if msg[1] == b'':
			#Pring warning message if no chatroom is there
			outstr = "\n->[List] : No chatroom is available right now"
			CmdWin.insert(1.0,outstr)
		else:
			#Else print out all the chatrooms
			i = 1
			while(msg[i]!=b''):
				outstr = "\n\t[ " + str(i) + " ] : " + msg[i].decode('utf-8')
				CmdWin.insert(1.0,outstr)
				i = i + 1
			outstr = "\n->[List] : These are the chatrooms that are available : "
			CmdWin.insert(1.0,outstr)
	else:
		#if encounter error
		outstr = ("\n->[List] : An error has occured, please try again later")
		CmdWin.insert(1.0,outstr)

def do_Join():
	global chatroom_name, username,userlist

	userInput = userentry.get() # Get the user input
	userentry.delete(0, END) # clear the entry widget
	"""Handling user actions"""
	if userInput != "" and chatroom_name == "" and username != "":
		#If everything is entered correctly
		chatroom_name = userInput # store the input
		outstr = "\n->[Join] : You are connected to a chatroom named : " + chatroom_name
		CmdWin.insert(1.0,outstr)
		server_msg = join_Request() # send a request to the server
		"""Displaying the members in the chatroom"""
		i = 2 # start from 2 according to server message
		while (server_msg[i] != b'') :
			outstr = "\n\t\t" + server_msg[i].decode('utf-8')
			CmdWin.insert(1.0,outstr)
			userlist = server_msg[i].decode('utf-8')
			#count = count + 1
			i = i + 3 # increase the msg by 3 to find the next username
		outstr = "\n->[Join] : The following members are in this chatroom : "
		CmdWin.insert(1.0,outstr)
		threadControl = ThreadingHandler() # run the threading class
		# start the threading
		thread = threading.Thread(target= threadControl.keep_alive,daemon = True)
		thread.start()
		#establish forward link
		thread = threading.Thread(target=establishedforward)
		thread.start()
		#start client thread
		thread = threading.Thread(target=clientThread)
		thread.start()
        

	else:
		#If already joined a chatroom
		if chatroom_name != "":
			outstr = "\n->[Join] : Joined chatroom failed, you are already in a chatroom named : " + chatroom_name
			CmdWin.insert(1.0,outstr)
		# if there's no username
		elif username == "":
			outstr = "\n->[Join] : Please create an username first!"
			CmdWin.insert(1.0,outstr)
		# if it's empty			
		else:
			outstr = "\n->[Join] : Please type in a chatroom name to create or join a chatroom"
			CmdWin.insert(1.0,outstr)

def do_Send():
	global connection,chatroom_name,userId,username,message_number

	#Get the input from the user
	userInput = userentry.get()

	#if the input is empty
	if not userInput:
		outstr = "\n->[Send] : Please type in a message to send"
		CmdWin.insert(1.0,outstr)
	else:
		#if the chatroom name is empty (not connected to chatroom)
		if not chatroom_name:
			outstr = "\n->[Send] : Please connect to a chatroom first"
			CmdWin.insert(1.0,outstr)
		else:
		#increase the messagenumber and send information to the server	
			message_number = message_number + 1
			outmsg = "T:" + chatroom_name + ":" + str(userID) + ":" + username + ":" + str(message_number) + ":"+ str(len(userInput)) + ":"+userInput+"::\r\n"

			for s in connection:
					s.sendall(outmsg.encode('ascii'))
			Winmsg = "\n-> [" + username + "] :" + userInput
			MsgWin.insert(1.0,Winmsg)
	userentry.delete(0, END)


def do_Quit():
	CmdWin.insert(1.0, "\nPress Quit")
	sockfd.close()
	clientSock.close()
	for s in connection:
		s.close()	
	threadControl = ThreadingHandler()
	threadControl.terminate() # Terminating the threads
	sys.exit(0)

"""Function handling join request"""
def join_Request():
	global username, sockfd, my_address, my_port, chatroom_name,recv_buffer,userlist
	"""communicating with server, sending infos"""
	join_message = "J:"+chatroom_name+":"+username+":"+my_address+":"+str(my_port)+"::\r\n" 
	sockfd.sendall(join_message.encode('ascii'))
	server_msg=sockfd.recv(recv_buffer) # get response from server
	msg = server_msg.split(":".encode('ascii'))
	groupList(msg[2:])
	return msg

"""Function handling gList"""
def groupList(msg):
	global gList,user_message
	username = []
	IPaddr = []
	port = []

	#Store the new member to the temporary list
	i = 0
	if msg[i] != (b''):
		username.append(msg[i].decode('utf-8'))
		IPaddr.append(msg[i+1].decode('utf-8'))
		port.append(msg[i+2].decode('utf-8'))
		i = i + 3 
	#calculate hash function and store in dict:gList
	i=0
	while(i < len(username)):
		hash = sdbm_hash(username[i]+IPaddr[i]+port[i])
		gList[hash]=[username[i], IPaddr[i], port[i]]
		i = i + 1

	#delete users not in the room anymore	
	temp = list(gList)

	for key in temp:
		if gList[key][0] not in username:
			try:
				del gList[key]
				del user_message[key]
			except KeyError as e:
				print("\n[DEBUG]:Message got some error, check grouplist update function")
				print(e)

def sortMember():
	global gList,userID
	#members with hashkey smaller than user

	upper_half = []
	lower_half = []

	for element in gList:
		if element < userID:
			lower_half.append(element)
	lower_half.sort()

	for element in gList:
		if element > userID:
			upper_half.append(element)
	upper_half.sort()

	#group members with hashkey larger than user
	return lower_half+upper_half

def forwardLink():
	global userID, gList,backward,gList,chatroom_name,username,my_address,my_port,message_number,connection, user_message, forward, forwardSock
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	found = False	
	#sort the membership list according to the hash IDs
	sorted_memberList = sortMember()
	for x in sorted_memberList:
		print ("Try forward link for " + str(x))
		#check if socket has backward link
		#if not
		if x not in backward:
			try:
				#connect to server
				sock.connect((gList[x][1], int(gList[x][2])))
				sendmsg = "P:"+chatroom_name+":"+username+":"+my_address+":"+str(my_port)+":"+str(message_number)+"::\r\n"
				sock.sendall(sendmsg.encode('ascii'))
				RList = [sock]
				#listen for response
				Rready, Wready, Eready=select.select(RList, [], [], 2)
				if Rready:
					for s in Rready:
						rawmsg=s.recv(1024)
						msg = rawmsg.split(":".encode('ascii'))
						if msg[0] == b"S":
							#update forward link 
							forward = x
							forwardSock = s
							#update msg number 
							user_message[x] = int(msg[1])
							#put the connection to socket
							connection.append(s)
							outstr = "\n#####->[CONNECTION]Forward link established: to "+gList[x][0]
							CmdWin.insert(1.0, outstr)
							found = True
							break
					#stop finding if found
					if found:
						break
					#close the connection
					else:
						sock.close()
				else:
					print("idling")

			except select.error as emsg:
				sock.close()
				print ("At select, caught an exception : " , emsg)

"""forward the connection"""
def establishedforward():
	global forward
	join_Request() 
	while forward == 0xffffffffffffffff:
		join_Request()
		forwardLink()

"""For controlling all listening thread"""
def clientThread():
	global chatroom_name,clientSock,connection,message_number,forward,sockfd,user_message,forwardSock, backward, my_port

	#create socket and bind
	try:
		clientSock.bind(('', my_port))
		clientSock.listen(5)#set socket listening queue
	except socket.error as emsg:
		print("Socket bind error : ", emsg)
		outmsg = "\n->[ERROR]Port is used by other users, please try another one"
		CmdWin.insert(1.0,outmsg)
		sockfd.close()
		for s in connection:
			s.close()
		return
	#start the main loop
	while True:
		#Use select to wait for any incoming connection connection requests or incoming messages or 2 seconds
		RList = [clientSock] + connection
		try:
			Rready, Wready, Eready=select.select(RList, [], [], 2)
		except select.error as emsg:
			print("Error occurs at select",emsg)
		#if has incoming activities
		if Rready:
			#for each socket in the READ ready lsit
			for s in Rready:
				#if the listening socket is ready
				#means a new connection request, accept that request and add it to the connection list and backward list.
				if s == clientSock:
					try:
						newfd, caddr = s.accept()
						rawmsg=newfd.recv(1024)
						msg = rawmsg.decode("ascii").split(":")
						hk=sdbm_hash(msg[2]+msg[3]+msg[4])
						outmsg="S:"+str(message_number)+"::\r\n"
						newfd.sendall(outmsg.encode('ascii'))
						CmdWin.insert(1.0, "\n#####->[CONNECTION]Backward link is established")
						#save the connections
						connection.append(newfd)
						backward.append(hk)
						#update the message number
						user_message[hk] = int(msg[5])
					except IOError as e:
						print(e)
					#else is a client socket being ready that means a message is waiting or a connection is brokem, 
					#if a new message arrived, send to everybody except the sender, if broken connection, 
					#remove that socket from connection list
				else:
					rawmsg=s.recv(1024)
					#the server sends back nothing (broken connection)
					if rawmsg == b"":
						#remove it from the connection list
						connection.remove(s)
						forwardSock.close()
						forward = 0xffffffffffffffff
						CmdWin.insert(1.0, "\n#####->[CONNECTION]Forward link has broked")
						#update group list
						join_Request()
						thread = threading.Thread(target=establishedforward)
						thread.start()					
					#a new message has arrived
					else:
						msg = rawmsg.split(":".encode('ascii'))		
						#Check if the incoming message has any error
						if check_message(msg,chatroom_name):
							#myself
							if int(msg[2].decode('utf-8')) == userID:
								continue
							#create temporary log
							if int(msg[2].decode('utf-8')) not in user_message.keys():
								user_message[int(msg[2].decode('utf-8'))]=0
						
							#perform if receiving new messages
							if user_message[int(msg[2].decode('utf-8'))] < int(msg[4].decode('utf-8')):

								#forward to others
								for out in connection:
									if out.getpeername() != s.getpeername():
										print ("Forward message to " + str(out.getpeername()))
										out.sendall(rawmsg)

								#add the content, including the colon in the text 
								outmsg="\n["+msg[3].decode('utf-8')+"] : "
								i=6
								while msg[i+1]!=b"\r\n":
									outmsg=outmsg+msg[i].decode('utf-8')
									outmsg=outmsg+":"
									i=i+1
								#remove last colon
								outmsg = outmsg[:len(outmsg)-1]
								#output the content
								MsgWin.insert(1.0, outmsg)
								#update msgID
								user_message[int(msg[2])] = int(msg[4])
						else:
							outstr = "\n->[MESSAGE] : A problem has occured while someone is sending you a message"
							CmdWin.insert(1.0,outstr)

"""Check if the incoming message has any error"""
def check_message(msg,roomname):
	#unexpected message
	if msg[0] != b"T":
		print ("The message is lost or bad: ")
		print(msg)
		return False
	#chatroom_name inconsistent
	if msg[1].decode('utf-8') != roomname:
		print ("Chatroom name is lost")
		return False
	return True

"""Class to handle threads"""
class ThreadingHandler:
	def __init__(self):
		outstr = "\n->[KEEP] : Keep Alive Thread - Start Executing"
		CmdWin.insert(1.0,outstr)
		print("[DEBUG] : Start Threading")
		self._running = True
	def terminate(self):
		#stop threading
		self._running = False
	def keep_alive(self):
		time_interval = 20 # do join Rquest again every 20 seconds
		while self._running:
			time.sleep(time_interval)
			print ("\n[DEBUG] : Keep alive procedure")
			join_Request()	


	
#
# Set up of Basic UI
#
win = Tk()
win.title("MyP2PChat")

#Top Frame for Message display
topframe = Frame(win, relief=RAISED, borderwidth=1)
topframe.pack(fill=BOTH, expand=True)
topscroll = Scrollbar(topframe)
MsgWin = Text(topframe, height='15', padx=5, pady=5, fg="red", exportselection=0, insertofftime=0)
MsgWin.pack(side=LEFT, fill=BOTH, expand=True)
topscroll.pack(side=RIGHT, fill=Y, expand=True)
MsgWin.config(yscrollcommand=topscroll.set)
topscroll.config(command=MsgWin.yview)

#Top Middle Frame for buttons
topmidframe = Frame(win, relief=RAISED, borderwidth=1)
topmidframe.pack(fill=X, expand=True)
Butt01 = Button(topmidframe, width='8', relief=RAISED, text="User", command=do_User)
Butt01.pack(side=LEFT, padx=8, pady=8);
Butt02 = Button(topmidframe, width='8', relief=RAISED, text="List", command=do_List)
Butt02.pack(side=LEFT, padx=8, pady=8);
Butt03 = Button(topmidframe, width='8', relief=RAISED, text="Join", command=do_Join)
Butt03.pack(side=LEFT, padx=8, pady=8);
Butt04 = Button(topmidframe, width='8', relief=RAISED, text="Send", command=do_Send)
Butt04.pack(side=LEFT, padx=8, pady=8);
Butt05 = Button(topmidframe, width='8', relief=RAISED, text="Quit", command=do_Quit)
Butt05.pack(side=LEFT, padx=8, pady=8);

#Lower Middle Frame for User input
lowmidframe = Frame(win, relief=RAISED, borderwidth=1)
lowmidframe.pack(fill=X, expand=True)
userentry = Entry(lowmidframe, fg="blue")
userentry.pack(fill=X, padx=4, pady=4, expand=True)

#Bottom Frame for displaying action info
bottframe = Frame(win, relief=RAISED, borderwidth=1)
bottframe.pack(fill=BOTH, expand=True)
bottscroll = Scrollbar(bottframe)
CmdWin = Text(bottframe, height='15', padx=5, pady=5, exportselection=0, insertofftime=0)
CmdWin.pack(side=LEFT, fill=BOTH, expand=True)
bottscroll.pack(side=RIGHT, fill=Y, expand=True)
CmdWin.config(yscrollcommand=bottscroll.set)
bottscroll.config(command=CmdWin.yview)

def main():
	if len(sys.argv) != 4:
		print("P2PChat.py <server address> <server port no.> <my port no.>")
		sys.exit(2)
	else:
		global server_address,server_port,my_port,my_address
		"""Getting arguments from user"""
		server_address = sys.argv[1]
		server_port = int(sys.argv[2])
		my_port = int(sys.argv[3])
		ipname = socket.getfqdn(socket.gethostname())
		my_address = socket.gethostbyname(ipname)

	try:
		# Try connecting to the server
		global sockfd
		sockfd.connect((server_address,server_port)) 
		print ("The connection with ", sockfd.getpeername(), " has been established.")
	except IOError:
		# Print error if couldn't connect
		print("connection error")
		sys.exit(1)

	outstr = "\nYou have connected to "+server_address+" with port number #"+str(server_port)
	CmdWin.insert(1.0, outstr)
	outstr = "\nYour local address is "+my_address+" with port number #"+str(my_port)
	CmdWin.insert(1.0, outstr)
	outstr = "\n\n#The connection is succesful, you can start using this program now#\n\n"
	CmdWin.insert(1.0, outstr)
	
	win.mainloop()

if __name__ == "__main__":
	main()

