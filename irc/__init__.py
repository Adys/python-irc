# -*- coding: utf-8 -*-
"""
Python IRC library
"""

from PySide.QtCore import Signal, SIGNAL, QObject
from PySide.QtNetwork import QTcpSocket, QSslSocket
from . import opcodes
from .channel import IRCChannel
from .user import IRCUser


def stripcolon(s):
	if s.startswith(":"):
		return s[1:]
	return s

class IRCServer(QObject):
	"""
	A socket to an IRC server.
	Initialize it with the host and port (default 6667)
	Connect with server.connectAs(nick), and connect to the online() signal.
	"""
	
	joinedChannel = Signal(IRCChannel) # fired when the client joins a channel
	kicked = Signal(str, IRCChannel, str) # fired when the client gets kicked from a channel
	online = Signal() # fired when a connection to the IRC server has been successfully established.
	packetRead = Signal(str) # fired when a full packet is read from the server
	packetWritten = Signal(str) # fired when a full packet is written to the server
	receivedPing = Signal(str) # fired when the client receives a Ping packet
	receivedNotice = Signal(str, str) # fired when the client receives a Notice packet
	receivedPrivateMessage = Signal(str, str) # fired when the client receives a personal privmsg packet
	
	def __init__(self, host, port=6667, ssl=False):
		super(IRCServer, self).__init__()
		if ssl:
			self.socket = QSslSocket()
		else:
			self.socket = QTcpSocket()
		
		self.__host = host
		self.__port = port
		self.__linebuf = ""
		self.__channels = {}
		self.socket.readyRead.connect(self.__handleRead)
		self.receivedPing.connect(self.pong)
	
	def __handleRead(self):
		while True:
			line = str(self.socket.readLine())
			if not line:
				break
			
			if self.__linebuf:
				line = self.__linebuf + line
				self.__linebuf = ""
			
			if not line.endswith("\r\n"):
				self.__linebuf = line
				continue
			
			sender, opcode, recipient, msg = self._parse(line.strip())
			
			if opcode == opcodes.RPL_WELCOME:
				self.online.emit()
			
			elif opcode == opcodes.RPL_TOPIC:
				channel, _, topic = msg.partition(" ")
				topic = stripcolon(topic)
				channel = self.channel(channel)
				channel.topicUpdated.emit(None, topic)
				channel.receivedReply.emit(opcode, stripcolon(topic))
			
			elif opcode == opcodes.RPL_CREATIONTIME:
				channel, timestamp = msg.split(" ")
				self.channel(channel).receivedReply.emit(opcode, timestamp)
			
			elif opcode == opcodes.RPL_CHANNELMODEIS:
				channel, mode = msg.partition(" ")
				self.channel(channel).receivedReply.emit(opcode, mode)
			
			elif opcode == "JOIN":
				user = IRCUser(sender, self)
				channel = stripcolon(recipient)
				if user.nick() == self.nick():
					self.__channels[channel] = IRCChannel(channel, self)
					self.joinedChannel.emit(self.__channels[channel])
				else:
					self.channel(channel).userJoined.emit(user)
			
			elif opcode == "KICK":
				channel = self.channel(recipient)
				user, _, reason = msg.partition(" ")
				reason = stripcolon(reason)
				
				if user == self.nick():
					# If we get kicked, emit IRCServer.kicked(sender, channel, reason)
					# TODO also emit IRCChannel.kicked(sender, reason)
					self.kicked.emit(sender, channel, reason)
					del self.__channels[recipient] # remove from channel list
				
				else:
					# Otherwise, emit IRCChannel.userKicked(sender, user, reason)
					self.channel(channel).userKicked.emit(sender, user, reason)
			
			elif opcode == "NOTICE":
				self.receivedNotice.emit(sender, msg)
			
			elif opcode == "PING":
				self.receivedPing.emit(msg)
			
			elif opcode == "PRIVMSG":
				sender = IRCUser(sender, self)
				if recipient == self.nick():
					self.receivedPrivateMessage.emit(sender, msg)
				else:
					self.channel(recipient).receivedMessage.emit(sender, msg)
			
			elif opcode == "TOPIC":
				sender = IRCUser(sender, self)
				IRCChannel(recipient).topicUpdated.emit(sender, msg)
			
			self.packetRead.emit(line)
	
	def _parse(self, line):
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
		if self.isSsl():
			self.socket.connectToHostEncrypted(self.__host, self.__port)
		else:
			self.socket.connectToHost(self.__host, self.__port)
		self.__nick = nick
		
		def onConnect():
			self.send("NICK %s" % (nick))
			self.send("USER %s %s %s :%s" % (user or nick, host or nick, serverName or nick, realName or nick))
		
		self.socket.connected.connect(onConnect)
	
	def isSsl(self):
		return isinstance(self.socket, QSslSocket)
	
	def join(self, channel):
		"""
		Joins the channel \a channel.
		"""
		self.send("JOIN %s" % (channel))
	
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
		self.send("PONG :%s" % (msg))
	
	def quit(self, reason=""):
		"""
		Quits the server and closes the TCP socket.
		"""
		if reason:
			self.send("QUIT :%s" % (reason))
		else:
			self.send("QUIT")
		self.close()
	
	def send(self, message):
		"""
		Sends \a message to the server, terminating it with CRLF if necessary.
		\sa write()
		"""
		if not message.endswith("\r\n"):
			message += "\r\n"
		self.write(message)
	
	def write(self, data):
		"""
		Writes \a data to the server. The data is not modified, and must be properly
		terminated with CRLF.
		\sa send() packetWritten()
		"""
		data = str(data)
		self.socket.write(data)
		self.socket.waitForBytesWritten()
		self.packetWritten.emit(data)
