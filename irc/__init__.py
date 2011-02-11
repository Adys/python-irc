"""
Python IRC library
"""

from PySide.QtCore import QObject, Signal, SIGNAL
from PySide.QtNetwork import QTcpSocket


def stripcolon(s):
	if s.startswith(":"):
		return s[1:]
	return s


# OpCodes
RPL_WELCOME = 001
RPL_TOPIC   = 332

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
			
			if opcode == RPL_TOPIC:
				channel, _, msg = msg.partition(" ")
				self.channel(channel).receivedTopic.emit(stripcolon(msg))
			
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
	
	def __parse(self, line):
		if line.startswith(":"):
			# XXX We need to use partition() and check arg numbers
			line = line[1:] # strip the first colon already
			sender, opcode, recipient = line.split(" ")[:3]
			idx = len(" ".join((sender, opcode, recipient)))
			msg = line[idx:]
			if opcode.isdigit():
				opcode = int(opcode)
			return sender, opcode, recipient, stripcolon(msg.strip())
		
		elif line.startswith("PING"):
			server = ""
			recipient = ""
			opcode, msg = line.split()
			return "", opcode, "", stripcolon(msg)
		
		return None, None, None, "(unknown msg)"
	
	def channel(self, channel):
		"""
		Returns the channel \a channel.
		"""
		return self.__channels[channel]
	
	def connectAs(self, nick, user="", host="", serverName="", realName=""):
		"""
		Opens a connection to the server and instantly returns.
		If the connection is successful, the user's nickname will automatically be
		set to \a nick. \a user, \a host, \a serverName and \a realName al default
		to the user's nickname.
		"""
		self.connectToHost(self.__host, self.__port)
		self.__nick = nick
		
		def onConnect():
			self.write("NICK %s\r\n" % (nick))
			self.write("USER %s %s %s :%s\r\n" % (user or nick, host or nick, serverName or nick, realName or nick))
		
		self.connected.connect(onConnect)
	
	def join(self, channel):
		"""
		Joins the channel \a channel.
		"""
		self.write("JOIN %s\r\n" % (channel))
	
	def nick(self):
		"""
		Returns the user's nickname.
		"""
		return self.__nick
	
	def pong(self, msg):
		"""
		Sends a PONG packet to the server with the message \a msg.
		\sa receivedPing()
		"""
		msg = str(msg) # XXX
		self.write("PONG %s\r\n" % (msg))
	
	def quit(self):
		"""
		Quits the server and closes the TCP socket.
		"""
		self.write("QUIT\r\n")
		self.close()
	
	def write(self, data):
		"""
		Writes \a data to the server. The data is not modified, and must be properly
		terminated with CRLF.
		"""
		super(IRCServer, self).write(data)
		self.waitForBytesWritten()


class IRCChannel(QObject):
	"""
	A channel on an IRC server
	This should not be created outside an IRCServer object.
	"""
	
	receivedTopic = Signal(str) # Fired when the client receives the channel topic
	userJoined = Signal(str) # Fired when an user joins the channel
	
	def __init__(self, name, parent):
		super(IRCChannel, self).__init__(parent)
		self.__name = name
		self.__parent = parent # server
		self.__topic = ""
		self.receivedTopic.connect(lambda topic: setattr(self, "__topic", topic))
	
	def name(self):
		"""
		Returns the channel name.
		"""
		return self.__name
	
	def parent(self):
		"""
		Returns the IRCServer the channel lives on.
		"""
		return self.__parent
	
	def topic(self):
		"""
		Returns the topic for  the channel.
		If no topic has been set, or the channel topic has not been received yet,
		returns an empty string.
		\sa receivedTopic()
		"""
		return self.__topic
	
	def write(self, msg):
		"""
		Sends a message to the channel.
		"""
		self.parent().write("PRIVMSG %s :%s" % (self.name(), msg))


class IRCUser(object):
	def __init__(self, name, parent):
		self.__name = name
		self.__parent = parent # server
	
	def name(self):
		"""
		Alias for nick()
		"""
		return self.__name
	
	def nick(self):
		"""
		Returns the user's nickname.
		"""
		return self.__name
	
	def parent(self):
		"""
		Returns the IRCServer the user lives on.
		"""
		return self.__parent
	
	def write(self, msg):
		"""
		Sends a message to the user.
		"""
		self.parent().write("PRIVMSG %s :%s" % (self.name(), msg))
