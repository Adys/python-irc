"""
Python IRC library
"""

from PySide.QtCore import Signal, SIGNAL
from PySide.QtNetwork import QTcpSocket


def stripcolon(s):
	if s.startswith(":"):
		return s[1:]
	return s


# OpCodes
RPL_WELCOME = 001

class IRCServer(QTcpSocket):
	"""
	A socket to an IRC server.
	Initialize it with the host and port (default 6667)
	Connect with server.connectAs(nick), and connect to the online() signal.
	"""
	
	joinedChannel = Signal(str) # fired when the client joins a channel
	online = Signal() # fired when a connection to the IRC server has been successfully established.
	receivedPing = Signal(str) # fired when the client receives a Ping packet
	receivedChannelMessage = Signal(str, str, str) # fired when the client receives a channel privmsg packet
	receivedNotice = Signal(str, str) # fired when the client receives a Notice packet
	receivedPrivateMessage = Signal(str, str) # fired when the client receives a personal privmsg packet
	
	def __init__(self, host, port=6667):
		super(IRCServer, self).__init__()
		self.__host = host
		self.__port = port
		self.__linebuf = ""
		self.__channels = {}
		self.readyRead.connect(self.__handleRead)
		self.receivedPing.connect(self.pong)
	
	def __handleRead(self):
		while True:
			line = str(self.readLine())
			if not line:
				break
			
			if self.__linebuf:
				line = self.__linebuf + line
				self.__linebuf = ""
			
			if not line.endswith("\r\n"):
				self.__linebuf = line
				continue
			
			sender, opcode, recipient, msg = self.__parse(line.strip())
			
			if opcode == RPL_WELCOME:
				self.online.emit()
			
			elif opcode == "JOIN":
				nick, host = sender.split("!")
				channel = stripcolon(recipient)
				if nick == self.nick():
					self.__channels[channel] = IRCChannel(channel, self)
					self.joinedChannel.emit(self.__channels[channel])
				else:
					self.channel(channel).userJoined.emit(nick)
			
			elif opcode == "NOTICE":
				self.receivedNotice.emit(sender, msg)
			
			elif opcode == "PING":
				self.receivedPing.emit(msg)
			
			elif opcode == "PRIVMSG":
				if recipient == self.nick():
					self.receivedPrivateMessage.emit(sender, msg)
				else:
					recipient = IRCChannel(recipient, self)
					self.receivedChannelMessage.emit(sender, msg, recipient)
			
			else:
				print("<<< %r" % (line))
	
	def __parse(self, line):
		if line.startswith(":"):
			sender, opcode, recipient = line.split(" ")[:3]
			idx = len(" ".join((sender, opcode, recipient)))
			msg = line[idx:]
			if opcode.isdigit():
				opcode = int(opcode)
			return stripcolon(sender), opcode, recipient, stripcolon(msg)
		
		elif line.startswith("PING"):
			server = ""
			recipient = ""
			opcode, msg = line.split()
			return "", opcode, "", stripcolon(msg)
		
		return None, None, None, "(unknown msg)"
	
	def channel(self, name):
		return self.__channels[name]
	
	def connectAs(self, nick, user="", host="", serverName="", realName=""):
		self.connectToHost(self.__host, self.__port)
		self.__nick = nick
		
		def onConnect():
			self.write("NICK %s\r\n" % (nick))
			self.write("USER %s %s %s :%s\r\n" % (user or nick, host or nick, serverName or nick, realName or nick))
		
		self.connected.connect(onConnect)
	
	def join(self, channel):
		self.write("JOIN %s\r\n" % (channel))
	
	def nick(self):
		return self.__nick
	
	def pong(self, msg):
		msg = str(msg) # XXX
		self.write("PONG %s\r\n" % (msg))
	
	def quit(self):
		self.write("QUIT\r\n")
		self.close()
	
	def write(self, data):
		#print(">>> %r" % (data))
		super(IRCServer, self).write(data)
		self.waitForBytesWritten()

class IRCChannel(object):
	"""
	A channel on an IRC server
	This should not be created outside an IRCServer object.
	"""
	
	userJoined = Signal(str) # Fired when an user joins the channel
	
	def __init__(self, name, parent):
		self.__name = name
		self.__parent = parent # server
	
	def name(self):
		return self.__name
	
	def parent(self):
		return self.__parent
	
	def write(self, msg):
		self.parent().write("PRIVMSG %s :%s" % (self.name(), msg))

class IRCUser(object):
	def __init__(self, name, parent):
		self.__name = name
		self.__parent = parent # server
	
	def name(self):
		return self.__name
	
	def nick(self):
		"""
		Alias for name()
		"""
		return self.__name
	
	def parent(self):
		return self.__parent
	
	def write(self, msg):
		self.parent().write("PRIVMSG %s :%s" % (self.name(), msg))
