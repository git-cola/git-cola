# -*- coding: utf-8 -*-
#
# Copyright © 2014-2015 Colin Duquesnoy
# Copyright © 2009- The Spyder Development Team
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""
Provides QtGui classes and functions.
.. warning:: Only PyQt4/PySide QtGui classes compatible with PyQt5.QtGui are
    exposed here. Therefore, you need to treat/use this package as if it were
    the ``PyQt5.QtGui`` module.
"""

from . import PYQT5, PYQT4, PYSIDE, PythonQtError


if PYQT5:
    from PyQt5.QtGui import *
elif PYQT4:
    try:
        # Older versions of PyQt4 do not provide these
        from PyQt4.QtGui import (QGlyphRun, QMatrix2x2, QMatrix2x3,
                                 QMatrix2x4, QMatrix3x2, QMatrix3x3,
                                 QMatrix3x4, QMatrix4x2, QMatrix4x3,
                                 QMatrix4x4, QTouchEvent, QQuaternion,
                                 QRadialGradient, QRawFont, QStaticText,
                                 QVector2D, QVector3D, QVector4D,
                                 qFuzzyCompare)
    except ImportError:
        pass
    from PyQt4.Qt import QKeySequence, QTextCursor
    from PyQt4.QtGui import (QAbstractTextDocumentLayout, QActionEvent, QBitmap,
                             QBrush, QClipboard, QCloseEvent, QColor,
                             QConicalGradient, QContextMenuEvent, QCursor,
                             QDesktopServices, QDoubleValidator, QDrag,
                             QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent,
                             QDropEvent, QFileOpenEvent, QFocusEvent, QFont,
                             QFontDatabase, QFontInfo, QFontMetrics,
                             QFontMetricsF, QGradient, QHelpEvent,
                             QHideEvent, QHoverEvent, QIcon, QIconDragEvent,
                             QIconEngine, QImage, QImageIOHandler, QImageReader,
                             QImageWriter, QInputEvent, QInputMethodEvent,
                             QKeyEvent, QLinearGradient,
                             QMouseEvent, QMoveEvent, QMovie,
                             QPaintDevice, QPaintEngine, QPaintEngineState,
                             QPaintEvent, QPainter, QPainterPath,
                             QPainterPathStroker, QPalette, QPen, QPicture,
                             QPictureIO, QPixmap, QPixmapCache, QPolygon,
                             QPolygonF, QRegExpValidator, QRegion, QResizeEvent,
                             QSessionManager, QShortcutEvent, QShowEvent,
                             QStandardItem, QStandardItemModel,
                             QStatusTipEvent, QSyntaxHighlighter, QTabletEvent,
                             QTextBlock, QTextBlockFormat, QTextBlockGroup,
                             QTextBlockUserData, QTextCharFormat,
                             QTextDocument, QTextDocumentFragment,
                             QTextDocumentWriter, QTextFormat, QTextFragment,
                             QTextFrame, QTextFrameFormat, QTextImageFormat,
                             QTextInlineObject, QTextItem, QTextLayout,
                             QTextLength, QTextLine, QTextList, QTextListFormat,
                             QTextObject, QTextObjectInterface, QTextOption,
                             QTextTable, QTextTableCell, QTextTableCellFormat,
                             QTextTableFormat, QTransform,
                             QValidator, QWhatsThisClickedEvent, QWheelEvent,
                             QWindowStateChangeEvent, qAlpha, qBlue,
                             qGray, qGreen, qIsGray, qRed, qRgb,
                             qRgba, QIntValidator)
elif PYSIDE:
    from PySide.QtGui import (QAbstractTextDocumentLayout, QActionEvent, QBitmap,
                              QBrush, QClipboard, QCloseEvent, QColor,
                              QConicalGradient, QContextMenuEvent, QCursor,
                              QDesktopServices, QDoubleValidator, QDrag,
                              QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent,
                              QDropEvent, QFileOpenEvent, QFocusEvent, QFont,
                              QFontDatabase, QFontInfo, QFontMetrics,
                              QFontMetricsF, QGradient, QHelpEvent,
                              QHideEvent, QHoverEvent, QIcon, QIconDragEvent,
                              QIconEngine, QImage, QImageIOHandler, QImageReader,
                              QImageWriter, QInputEvent, QInputMethodEvent,
                              QKeyEvent, QKeySequence, QLinearGradient,
                              QMatrix2x2, QMatrix2x3, QMatrix2x4, QMatrix3x2,
                              QMatrix3x3, QMatrix3x4, QMatrix4x2, QMatrix4x3,
                              QMatrix4x4, QMouseEvent, QMoveEvent, QMovie,
                              QPaintDevice, QPaintEngine, QPaintEngineState,
                              QPaintEvent, QPainter, QPainterPath,
                              QPainterPathStroker, QPalette, QPen, QPicture,
                              QPictureIO, QPixmap, QPixmapCache, QPolygon,
                              QPolygonF, QQuaternion, QRadialGradient,
                              QRegExpValidator, QRegion, QResizeEvent,
                              QSessionManager, QShortcutEvent, QShowEvent,
                              QStandardItem, QStandardItemModel,
                              QStatusTipEvent, QSyntaxHighlighter, QTabletEvent,
                              QTextBlock, QTextBlockFormat, QTextBlockGroup,
                              QTextBlockUserData, QTextCharFormat, QTextCursor,
                              QTextDocument, QTextDocumentFragment,
                              QTextFormat, QTextFragment,
                              QTextFrame, QTextFrameFormat, QTextImageFormat,
                              QTextInlineObject, QTextItem, QTextLayout,
                              QTextLength, QTextLine, QTextList, QTextListFormat,
                              QTextObject, QTextObjectInterface, QTextOption,
                              QTextTable, QTextTableCell, QTextTableCellFormat,
                              QTextTableFormat, QTouchEvent, QTransform,
                              QValidator, QVector2D, QVector3D, QVector4D,
                              QWhatsThisClickedEvent, QWheelEvent,
                              QWindowStateChangeEvent, qAlpha, qBlue,
                              qGray, qGreen, qIsGray, qRed, qRgb, qRgba,
                              QIntValidator)
else:
    raise PythonQtError('No Qt bindings could be found')
