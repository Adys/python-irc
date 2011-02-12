# -*- coding: utf-8 -*-
"""
Channel logic
"""

from PySide.QtCore import QObject, Signal


class IRCChannel(QObject):
	"""
	A channel on an IRC server
	This should not be created outside an IRCServer object.
	"""
	
	receivedMessage = Signal(str, str) # Fired when the client receives a channel privmsg packet
	receivedTopic = Signal(str) # Fired when the client receives the channel topic
	userJoined = Signal(str) # Fired when an user joins the channel
	userKicked = Signal(str, str, str) # Fired when an user is kicked from the channel
	
	def __init__(self, name, parent):
		super(IRCChannel, self).__init__(parent)
		self.__name = name
		self.__parent = parent # server
		self.__topic = ""
		self.receivedTopic.connect(lambda topic: setattr(self, "__topic", topic))
	
	def kick(self, user, reason=""):
		"""
		Kicks \a user from the channel, with optional \a reason.
		"""
		if reason:
			self.parent().write("KICK %s %s :%s" % (self.name(), user, reason))
		else:
			self.parent().write("KICK %s %s" % (self.name(), user))
	
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
