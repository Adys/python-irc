# -*- coding: utf-8 -*-
"""
Channel logic
"""

from PySide.QtCore import QObject, Signal
from . import opcodes
from .user import IRCUser


class IRCChannel(QObject):
	"""
	A channel on an IRC server
	This should not be created outside an IRCServer object.
	"""
	
	receivedMessage = Signal(IRCUser, str) # Fired when the client receives a channel privmsg packet
	receivedReply = Signal(int, str) # Fired when the client receives the channel topic
	topicUpdated = Signal(IRCUser, str) # Fired when the channel topic is received or updated. If user is None, it's an on-join reception.
	userJoined = Signal(IRCUser) # Fired when an user joins the channel
	userKicked = Signal(str, str, str) # Fired when an user is kicked from the channel
	
	def __init__(self, name, parent):
		super(IRCChannel, self).__init__(parent)
		self.__modes = ""
		self.__name = name
		self.__parent = parent # server
		self.__timestamp = 0
		self.__topic = ""
		self.receivedReply.connect(self.__handleReply)
		self.topicUpdated.connect(lambda user, topic: setattr(self, "__topic", topic))
	
	def __handleReply(self, opcode, reply):
		if opcode == opcodes.RPL_TOPIC:
			self.__topic = ""
		
		elif opcode == opcodes.RPL_CREATIONTIME:
			self.__timestamp = int(reply)
		
		elif opcode == opcodes.RPL_CHANNELMODEIS:
			self.__modes = reply
	
	def kick(self, user, reason=""):
		"""
		Kicks \a user from the channel, with optional \a reason.
		"""
		if reason:
			self.parent().send("KICK %s %s :%s" % (self.name(), user, reason))
		else:
			self.parent().send("KICK %s %s" % (self.name(), user))
	
	def mode(self):
		"""
		Returns the channel mode.
		\sa queryMode()
		"""
		return self.__modes
	
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
	
	def queryMode(self):
		"""
		Queries the channel mode.
		\sa mode()
		"""
		self.parent()
	
	def setTopic(self, topic):
		"""
		Sets channel topic to \a topic.
		\sa receivedTopic() topic()
		"""
		self.parent().send("TOPIC %s :%s" % (self.name(), topic))
	
	def send(self, message):
		"""
		Sends \a message to the channel.
		"""
		self.parent().send("PRIVMSG %s :%s" % (self.name(), message))
	
	def timestamp(self):
		"""
		Returns the channel's timestamp.
		See http://www.irchelp.org/irchelp/ircd/ts0.html
		"""
		return self.__timestamp
	
	def topic(self):
		"""
		Returns the topic for  the channel.
		If no topic has been set, or the channel topic has not been received yet,
		returns an empty string.
		\sa receivedTopic() setTopic()
		"""
		return self.__topic
