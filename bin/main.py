#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Python IRC test client
"""

from __future__ import print_function
import sys; sys.path.append("..")
from irc import IRCServer
from PySide.QtCore import QCoreApplication, QTimer


class IRCClient(QCoreApplication):
	def __init__(self, argv):
		super(IRCClient, self).__init__(argv)
		QTimer.singleShot(0, self.run)
	
	def watchChannel(self, channel):
		channel.receivedTopic.connect(lambda topic: print("Topic for %s is: %s" % (channel.name(), topic)))
	
	def run(self):
		self.irc = IRCServer("irc.freenode.net")
		self.irc.connectAs("Addybot")
		self.irc.online.connect(lambda: self.irc.join("#addybot"))
		self.irc.receivedNotice.connect(lambda sender, msg: print("NOTICE (%s): %s" % (sender, msg)))
		self.irc.receivedChannelMessage.connect(lambda sender, msg, channel: print("%s <%s> %s" % (channel, sender, msg)))
		self.irc.receivedPrivateMessage.connect(lambda sender, msg: print("<<< %s >>>: %s" % (sender, msg)))
		
		self.irc.joinedChannel.connect(self.watchChannel)
		
		# raw log
		self.irc.packetWritten.connect(lambda data: print(">>> %r" % (data)))
		self.irc.packetRead.connect(lambda data: print("<<< %r" % (data)))


def main():
	import signal
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	app = IRCClient(sys.argv)
	sys.exit(app.exec_())

if __name__ == "__main__":
	main()
