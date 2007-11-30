#!/usr/bin/env python
import sys
from PyQt4 import QtCore, QtGui

from ugitmainwindow import ugitMainWindow
from ugitdata import ugitData

def main():
	app = QtGui.QApplication(sys.argv)
	ugitWindow = ugitMainWindow(app.activeWindow())

	ugitdata = ugitData()
	ugitWindow.setup_notifications(ugitdata)

	ugitWindow.show()
	sys.exit(app.exec_())

if __name__ == "__main__": main()
