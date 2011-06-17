# -*- coding: utf-8 -*-
"""
User logic
"""


class IRCUser(object):
	def __init__(self, nick, parent):
		if "!" in nick:
			nick, self.__host = nick.split("!")
		self.__nick= nick
		self.__parent = parent # server
	
	def __eq__(self, other):
		if isinstance(other, basestring):
			return self.nick() == other
		return super(IRCUser, self).__eq__(other)
	
	def name(self):
		"""
		Alias for nick()
		"""
		return self.__nick
	
	def nick(self):
		"""
		Returns the user's nickname.
		"""
		return self.__nick
	
	def parent(self):
		"""
		Returns the IRCServer the user lives on.
		"""
		return self.__parent
	
	def write(self, message):
		"""
		Sends \a message to the user.
		"""
		self.parent().send("PRIVMSG %s :%s" % (self.name(), message))
