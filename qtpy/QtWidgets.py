# -*- coding: utf-8 -*-
#
# Copyright © 2014-2015 Colin Duquesnoy
# Copyright © 2009- The Spyder Developmet Team
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""
Provides widget classes and functions.
.. warning:: Only PyQt4/PySide QtGui classes compatible with PyQt5.QtWidgets
    are exposed here. Therefore, you need to treat/use this package as if it
    were the ``PyQt5.QtWidgets`` module.
"""

import os

from qtpy import QT_API
from qtpy import PYQT5_API
from qtpy import PYQT4_API
from qtpy import PYSIDE_API
from qtpy import PythonQtError


def patch_qcombobox():
    """
    In PySide, using Python objects as userData in QComboBox causes
    Segmentation faults under certain conditions. Even in cases where it
    doesn't, findData does not work correctly. Likewise, findData also does not
    work correctly with Python objects when using PyQt4. On the other hand,
    PyQt5 deals with this case correctly. We therefore patch QComboBox when
    using PyQt4 and PySide to avoid issues.
    """

    from qtpy.QtGui import QIcon
    from qtpy.QtCore import Qt, QObject

    class userDataWrapper(QObject):
        """
        This class is used to wrap any userData object inside a QObject which
        is then supported by all Python Qt wrappers.
        """
        def __init__(self, data, parent=None):
            super(userDataWrapper, self).__init__(parent)
            self.data = data

    _addItem = QComboBox.addItem

    def addItem(self, *args, **kwargs):
        if len(args) == 3 or (not isinstance(args[0], QIcon)
                              and len(args) == 2):
            args, kwargs['userData'] = args[:-1], args[-1]
        if 'userData' in kwargs:
            kwargs['userData'] = userDataWrapper(kwargs['userData'],
                                                 parent=self)
        _addItem(self, *args, **kwargs)

    _insertItem = QComboBox.insertItem

    def insertItem(self, *args, **kwargs):
        if len(args) == 4 or (not isinstance(args[1], QIcon)
                              and len(args) == 3):
            args, kwargs['userData'] = args[:-1], args[-1]
        if 'userData' in kwargs:
            kwargs['userData'] = userDataWrapper(kwargs['userData'],
                                                 parent=self)
        _insertItem(self, *args, **kwargs)

    _setItemData = QComboBox.setItemData

    def setItemData(self, index, value, role=Qt.UserRole):
        value = userDataWrapper(value, parent=self)
        _setItemData(self, index, value, role=role)

    _itemData = QComboBox.itemData

    def itemData(self, index, role=Qt.UserRole):
        userData = _itemData(self, index, role=role)
        if isinstance(userData, userDataWrapper):
            userData = userData.data
        return userData

    def findData(self, value):
        for i in range(self.count()):
            if self.itemData(i) == value:
                return i
        return -1

    QComboBox.addItem = addItem
    QComboBox.insertItem = insertItem
    QComboBox.setItemData = setItemData
    QComboBox.itemData = itemData
    QComboBox.findData = findData


if os.environ[QT_API] in PYQT5_API:
    from PyQt5.QtWidgets import *
elif os.environ[QT_API] in PYQT4_API:
    from PyQt4.QtGui import *
    QStyleOptionViewItem = QStyleOptionViewItemV4

    # These objects belong to QtGui
    del (QAbstractTextDocumentLayout, QActionEvent, QBitmap, QBrush, QClipboard,
         QCloseEvent, QColor, QConicalGradient, QContextMenuEvent, QCursor,
         QDesktopServices, QDoubleValidator, QDrag, QDragEnterEvent,
         QDragLeaveEvent, QDragMoveEvent, QDropEvent, QFileOpenEvent,
         QFocusEvent, QFont, QFontDatabase, QFontInfo, QFontMetrics,
         QFontMetricsF, QGlyphRun, QGradient, QHelpEvent, QHideEvent,
         QHoverEvent, QIcon, QIconDragEvent, QIconEngine, QImage,
         QImageIOHandler, QImageReader, QImageWriter, QInputEvent,
         QInputMethodEvent, QKeyEvent, QKeySequence, QLinearGradient,
         QMatrix2x2, QMatrix2x3, QMatrix2x4, QMatrix3x2, QMatrix3x3,
         QMatrix3x4, QMatrix4x2, QMatrix4x3, QMatrix4x4, QMouseEvent,
         QMoveEvent, QMovie, QPaintDevice, QPaintEngine, QPaintEngineState,
         QPaintEvent, QPainter, QPainterPath, QPainterPathStroker, QPalette,
         QPen, QPicture, QPictureIO, QPixmap, QPixmapCache, QPolygon,
         QPolygonF, QQuaternion, QRadialGradient, QRawFont, QRegExpValidator,
         QRegion, QResizeEvent, QSessionManager, QShortcutEvent, QShowEvent,
         QStandardItem, QStandardItemModel, QStaticText, QStatusTipEvent,
         QSyntaxHighlighter, QTabletEvent, QTextBlock, QTextBlockFormat,
         QTextBlockGroup, QTextBlockUserData, QTextCharFormat, QTextCursor,
         QTextDocument, QTextDocumentFragment, QTextDocumentWriter,
         QTextFormat, QTextFragment, QTextFrame, QTextFrameFormat,
         QTextImageFormat, QTextInlineObject, QTextItem, QTextLayout,
         QTextLength, QTextLine, QTextList, QTextListFormat, QTextObject,
         QTextObjectInterface, QTextOption, QTextTable, QTextTableCell,
         QTextTableCellFormat, QTextTableFormat, QTouchEvent, QTransform,
         QValidator, QVector2D, QVector3D, QVector4D, QWhatsThisClickedEvent,
         QWheelEvent, QWindowStateChangeEvent, qAlpha, qBlue, qFuzzyCompare,
         qGray, qGreen, qIsGray, qRed, qRgb, qRgba, QIntValidator)

    # These objects belong to QtPrintSupport
    del (QAbstractPrintDialog, QPageSetupDialog, QPrintDialog, QPrintEngine,
         QPrintPreviewDialog, QPrintPreviewWidget, QPrinter, QPrinterInfo)

    # These objects belong to QtCore
    del (QItemSelection, QItemSelectionModel, QItemSelectionRange,
         QSortFilterProxyModel)

    # Patch QComboBox
    patch_qcombobox()

elif os.environ[QT_API] in PYSIDE_API:
    from PySide.QtGui import *
    QStyleOptionViewItem = QStyleOptionViewItemV4

    # These objects belong to QtGui
    del (QAbstractTextDocumentLayout, QActionEvent, QBitmap, QBrush, QClipboard,
         QCloseEvent, QColor, QConicalGradient, QContextMenuEvent, QCursor,
         QDesktopServices, QDoubleValidator, QDrag, QDragEnterEvent,
         QDragLeaveEvent, QDragMoveEvent, QDropEvent, QFileOpenEvent,
         QFocusEvent, QFont, QFontDatabase, QFontInfo, QFontMetrics,
         QFontMetricsF, QGradient, QHelpEvent, QHideEvent,
         QHoverEvent, QIcon, QIconDragEvent, QIconEngine, QImage,
         QImageIOHandler, QImageReader, QImageWriter, QInputEvent,
         QInputMethodEvent, QKeyEvent, QKeySequence, QLinearGradient,
         QMatrix2x2, QMatrix2x3, QMatrix2x4, QMatrix3x2, QMatrix3x3,
         QMatrix3x4, QMatrix4x2, QMatrix4x3, QMatrix4x4, QMouseEvent,
         QMoveEvent, QMovie, QPaintDevice, QPaintEngine, QPaintEngineState,
         QPaintEvent, QPainter, QPainterPath, QPainterPathStroker, QPalette,
         QPen, QPicture, QPictureIO, QPixmap, QPixmapCache, QPolygon,
         QPolygonF, QQuaternion, QRadialGradient, QRegExpValidator,
         QRegion, QResizeEvent, QSessionManager, QShortcutEvent, QShowEvent,
         QStandardItem, QStandardItemModel, QStatusTipEvent,
         QSyntaxHighlighter, QTabletEvent, QTextBlock, QTextBlockFormat,
         QTextBlockGroup, QTextBlockUserData, QTextCharFormat, QTextCursor,
         QTextDocument, QTextDocumentFragment,
         QTextFormat, QTextFragment, QTextFrame, QTextFrameFormat,
         QTextImageFormat, QTextInlineObject, QTextItem, QTextLayout,
         QTextLength, QTextLine, QTextList, QTextListFormat, QTextObject,
         QTextObjectInterface, QTextOption, QTextTable, QTextTableCell,
         QTextTableCellFormat, QTextTableFormat, QTouchEvent, QTransform,
         QValidator, QVector2D, QVector3D, QVector4D, QWhatsThisClickedEvent,
         QWheelEvent, QWindowStateChangeEvent, qAlpha, qBlue, qGray, qGreen,
         qIsGray, qRed, qRgb, qRgba, QIntValidator)

    # These objects belong to QtPrintSupport
    del (QAbstractPrintDialog, QPageSetupDialog, QPrintDialog, QPrintEngine,
         QPrintPreviewDialog, QPrintPreviewWidget, QPrinter, QPrinterInfo)

    # These objects belong to QtCore
    del (QItemSelection, QItemSelectionModel, QItemSelectionRange,
         QSortFilterProxyModel)

    # Patch QComboBox
    patch_qcombobox()

else:
    raise PythonQtError('No Qt bindings could be found')
