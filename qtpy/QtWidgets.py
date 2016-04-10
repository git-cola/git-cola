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
    del (QItemSelection, QItemSelectionRange, QSortFilterProxyModel)
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
    del (QItemSelection, QItemSelectionRange, QSortFilterProxyModel)
else:
    raise PythonQtError('No Qt bindings could be found')
