# Copyright (c) 2018 David Aguilar <davvid@gmail.com>
#
# Git Cola is GPL licensed, but this file has a more permissive license.
# This file is dual-licensed Git Cola GPL + pyqimageview MIT.
# imageview.py was originally based on the pyqimageview:
# https://github.com/nevion/pyqimageview/
#
# The MIT License (MIT)
#
# Copyright (c) 2014 Jason Newton <nevion@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from __future__ import absolute_import, division, print_function, unicode_literals
import argparse
import os
import sys

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

try:
    import numpy as np

    have_numpy = True
except ImportError:
    have_numpy = False

from .. import qtcompat

main_loop_type = 'qt'


def clamp(x, lo, hi):
    return max(min(x, hi), lo)


class ImageView(QtWidgets.QGraphicsView):
    image_changed = Signal()

    def __init__(self, parent=None):
        super(ImageView, self).__init__(parent)

        scene = QtWidgets.QGraphicsScene(self)
        self.graphics_pixmap = QtWidgets.QGraphicsPixmapItem()
        scene.addItem(self.graphics_pixmap)
        self.setScene(scene)

        self.zoom_factor = 1.125
        self.rubberband = None
        self.panning = False
        self.first_show_occured = False
        self.last_scene_roi = None
        self.start_drag = QtCore.QPoint()
        self.checkerboard = None

        CHECK_MEDIUM = 8
        CHECK_GRAY = 0x80
        CHECK_LIGHT = 0xCC
        check_pattern = QtGui.QImage(
            CHECK_MEDIUM * 2, CHECK_MEDIUM * 2, QtGui.QImage.Format_RGB888
        )
        color_gray = QtGui.QColor(CHECK_GRAY, CHECK_GRAY, CHECK_GRAY)
        color_light = QtGui.QColor(CHECK_LIGHT, CHECK_LIGHT, CHECK_LIGHT)
        painter = QtGui.QPainter(check_pattern)
        painter.fillRect(0, 0, CHECK_MEDIUM, CHECK_MEDIUM, color_gray)
        painter.fillRect(
            CHECK_MEDIUM, CHECK_MEDIUM, CHECK_MEDIUM, CHECK_MEDIUM, color_gray
        )
        painter.fillRect(0, CHECK_MEDIUM, CHECK_MEDIUM, CHECK_MEDIUM, color_light)
        painter.fillRect(CHECK_MEDIUM, 0, CHECK_MEDIUM, CHECK_MEDIUM, color_light)
        self.check_pattern = check_pattern
        self.check_brush = QtGui.QBrush(check_pattern)

    def load(self, filename):
        image = QtGui.QImage()
        image.load(filename)
        ok = not image.isNull()
        if ok:
            self.pixmap = image
        return ok

    @property
    def pixmap(self):
        return self.graphics_pixmap.pixmap()

    @pixmap.setter
    def pixmap(self, image, image_format=None):
        pixmap = None
        if have_numpy and isinstance(image, np.ndarray):
            if image.ndim == 3:
                if image.shape[2] == 3:
                    if image_format is None:
                        image_format = QtGui.QImage.Format_RGB888
                    q_image = QtGui.QImage(
                        image.data, image.shape[1], image.shape[0], image_format
                    )
                    pixmap = QtGui.QPixmap.fromImage(q_image)
                elif image.shape[2] == 4:
                    if image_format is None:
                        image_format = QtGui.QImage.Format_RGB32
                    q_image = QtGui.QImage(
                        image.data, image.shape[1], image.shape[0], image_format
                    )
                    pixmap = QtGui.QPixmap.fromImage(q_image)
                else:
                    raise TypeError(image)
            elif image.ndim == 2:
                if image_format is None:
                    image_format = QtGui.QImage.Format_RGB888
                q_image = QtGui.QImage(
                    image.data, image.shape[1], image.shape[0], image_format
                )
                pixmap = QtGui.QPixmap.fromImage(q_image)
            else:
                raise ValueError(image)

        elif isinstance(image, QtGui.QImage):
            pixmap = QtGui.QPixmap.fromImage(image)
        elif isinstance(image, QtGui.QPixmap):
            pixmap = image
        else:
            raise TypeError(image)

        if pixmap.hasAlpha():
            checkerboard = QtGui.QImage(
                pixmap.width(), pixmap.height(), QtGui.QImage.Format_ARGB32
            )
            self.checkerboard = checkerboard
            painter = QtGui.QPainter(checkerboard)
            painter.fillRect(checkerboard.rect(), self.check_brush)
            painter.drawPixmap(0, 0, pixmap)
            pixmap = QtGui.QPixmap.fromImage(checkerboard)

        self.graphics_pixmap.setPixmap(pixmap)
        self.update_scene_rect()
        self.fitInView(self.image_scene_rect, flags=Qt.KeepAspectRatio)
        self.graphics_pixmap.update()
        self.image_changed.emit()

    # image property alias
    @property
    def image(self):
        return self.pixmap

    @image.setter
    def image(self, image):
        self.pixmap = image

    def update_scene_rect(self):
        pixmap = self.pixmap
        self.setSceneRect(
            QtCore.QRectF(
                QtCore.QPointF(0, 0), QtCore.QPointF(pixmap.width(), pixmap.height())
            )
        )

    @property
    def image_scene_rect(self):
        return QtCore.QRectF(
            self.graphics_pixmap.pos(), QtCore.QSizeF(self.pixmap.size())
        )

    def resizeEvent(self, event):
        super(ImageView, self).resizeEvent(event)
        self.update_scene_rect()
        event.accept()
        self.fitInView(self.last_scene_roi, Qt.KeepAspectRatio)
        self.update()

    def zoomROICentered(self, p, zoom_level_delta):
        roi = self.current_scene_ROI
        if not roi:
            return
        roi_dims = QtCore.QPointF(roi.width(), roi.height())
        roi_scalef = 1

        if zoom_level_delta > 0:
            roi_scalef = 1.0 / self.zoom_factor
        elif zoom_level_delta < 0:
            roi_scalef = self.zoom_factor

        nroi_dims = roi_dims * roi_scalef
        nroi_dims.setX(max(nroi_dims.x(), 1))
        nroi_dims.setY(max(nroi_dims.y(), 1))

        nroi_center = p
        nroi_dimsh = nroi_dims / 2.0
        nroi_topleft = nroi_center - nroi_dimsh
        nroi = QtCore.QRectF(
            nroi_topleft.x(), nroi_topleft.y(), nroi_dims.x(), nroi_dims.y()
        )
        self.fitInView(nroi, Qt.KeepAspectRatio)
        self.update()

    def zoomROITo(self, p, zoom_level_delta):
        roi = self.current_scene_ROI
        if not roi:
            return
        roi_dims = QtCore.QPointF(roi.width(), roi.height())
        roi_topleft = roi.topLeft()
        roi_scalef = 1.0

        if zoom_level_delta > 0:
            roi_scalef = 1.0 / self.zoom_factor
        elif zoom_level_delta < 0:
            roi_scalef = self.zoom_factor

        nroi_dims = roi_dims * roi_scalef
        nroi_dims.setX(max(nroi_dims.x(), 1.0))
        nroi_dims.setY(max(nroi_dims.y(), 1.0))

        prel_scaled_x = (p.x() - roi_topleft.x()) / roi_dims.x()
        prel_scaled_y = (p.y() - roi_topleft.y()) / roi_dims.y()
        nroi_topleft_x = p.x() - prel_scaled_x * nroi_dims.x()
        nroi_topleft_y = p.y() - prel_scaled_y * nroi_dims.y()

        nroi = QtCore.QRectF(
            nroi_topleft_x, nroi_topleft_y, nroi_dims.x(), nroi_dims.y()
        )
        self.fitInView(nroi, Qt.KeepAspectRatio)
        self.update()

    def _scene_ROI(self, geometry):
        return QtCore.QRectF(
            self.mapToScene(geometry.topLeft()), self.mapToScene(geometry.bottomRight())
        )

    @property
    def current_scene_ROI(self):
        return self.last_scene_roi

    def mousePressEvent(self, event):
        super(ImageView, self).mousePressEvent(event)
        button = event.button()
        modifier = event.modifiers()

        # pan
        if modifier == Qt.ControlModifier and button == Qt.LeftButton:
            self.start_drag = event.pos()
            self.panning = True

        # initiate/show ROI selection
        if modifier == Qt.ShiftModifier and button == Qt.LeftButton:
            self.start_drag = event.pos()
            if self.rubberband is None:
                self.rubberband = QtWidgets.QRubberBand(
                    QtWidgets.QRubberBand.Rectangle, self.viewport()
                )
            self.rubberband.setGeometry(QtCore.QRect(self.start_drag, QtCore.QSize()))
            self.rubberband.show()

    def mouseMoveEvent(self, event):
        super(ImageView, self).mouseMoveEvent(event)
        # update selection display
        if self.rubberband is not None:
            self.rubberband.setGeometry(
                QtCore.QRect(self.start_drag, event.pos()).normalized()
            )

        if self.panning:
            end_drag = event.pos()
            pan_vector = end_drag - self.start_drag
            scene2view = self.transform()
            # skip shear
            sx = scene2view.m11()
            sy = scene2view.m22()
            scene_pan_x = pan_vector.x() / sx
            scene_pan_y = pan_vector.y() / sy
            scene_pan_vector = QtCore.QPointF(scene_pan_x, scene_pan_y)
            roi = self.current_scene_ROI
            top_left = roi.topLeft()
            new_top_left = top_left - scene_pan_vector
            scene_rect = self.sceneRect()
            new_top_left.setX(
                clamp(new_top_left.x(), scene_rect.left(), scene_rect.right())
            )
            new_top_left.setY(
                clamp(new_top_left.y(), scene_rect.top(), scene_rect.bottom())
            )
            nroi = QtCore.QRectF(new_top_left, roi.size())
            self.fitInView(nroi, Qt.KeepAspectRatio)
            self.start_drag = end_drag
        self.update()

    def mouseReleaseEvent(self, event):
        super(ImageView, self).mouseReleaseEvent(event)
        # consume rubber band selection
        if self.rubberband is not None:
            self.rubberband.hide()

            # set view to ROI
            rect = self.rubberband.geometry().normalized()

            if rect.width() > 5 and rect.height() > 5:
                roi = QtCore.QRectF(
                    self.mapToScene(rect.topLeft()), self.mapToScene(rect.bottomRight())
                )
                self.fitInView(roi, Qt.KeepAspectRatio)

            self.rubberband = None

        if self.panning:
            self.panning = False
        self.update()

    def wheelEvent(self, event):
        delta = qtcompat.wheel_delta(event)
        # adjust zoom
        if abs(delta) > 0:
            scene_pos = self.mapToScene(event.pos())
            if delta >= 0:
                sign = 1
            else:
                sign = -1
            self.zoomROITo(scene_pos, sign)

    def reset(self):
        self.update_scene_rect()
        self.fitInView(self.image_scene_rect, flags=Qt.KeepAspectRatio)
        self.update()

    # override arbitrary and unwanted margins:
    # https://bugreports.qt.io/browse/QTBUG-42331 - based on QT sources
    def fitInView(self, rect, flags=Qt.IgnoreAspectRatio):
        if self.scene() is None or not rect or rect.isNull():
            return
        self.last_scene_roi = rect
        unity = self.transform().mapRect(QtCore.QRectF(0.0, 0.0, 1.0, 1.0))
        self.scale(1.0 / unity.width(), 1.0 / unity.height())
        viewrect = self.viewport().rect()
        scene_rect = self.transform().mapRect(rect)
        xratio = viewrect.width() / scene_rect.width()
        yratio = viewrect.height() / scene_rect.height()
        if flags == Qt.KeepAspectRatio:
            xratio = yratio = min(xratio, yratio)
        elif flags == Qt.KeepAspectRatioByExpanding:
            xratio = yratio = max(xratio, yratio)
        self.scale(xratio, yratio)
        self.centerOn(rect.center())


class AppImageView(ImageView):
    def __init__(self, parent=None):
        ImageView.__init__(self, parent=parent)
        self.main_widget = None

    def mousePressEvent(self, event):
        ImageView.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        ImageView.mouseMoveEvent(self, event)
        pos = event.pos()
        scene_pos = self.mapToScene(pos)
        msg = 'ui: %d, %d  image: %d, %d' % (
            pos.y(),
            pos.x(),
            int(scene_pos.y()),
            int(scene_pos.x()),
        )
        self.main_widget.statusBar().showMessage(msg)


class ImageViewerWindow(QtWidgets.QMainWindow):
    def __init__(self, image, input_path):
        QtWidgets.QMainWindow.__init__(self)
        self.image = image
        self.input_path = input_path
        self.image_view = AppImageView(parent=self)
        self.image_view.main_widget = self
        self.statusBar().showMessage('')

        padding = self.frameGeometry().size() - self.geometry().size()
        self.resize(image.size() + padding)

        central = QtWidgets.QWidget(self)
        self.vbox = QtWidgets.QVBoxLayout(central)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(central)
        self.layout().setContentsMargins(0, 0, 0, 0)

        Expanding = QtWidgets.QSizePolicy.Expanding
        height_for_width = self.image_view.sizePolicy().hasHeightForWidth()
        policy = QtWidgets.QSizePolicy(Expanding, Expanding)
        policy.setHorizontalStretch(1)
        policy.setVerticalStretch(1)
        policy.setHeightForWidth(height_for_width)
        self.image_view.setSizePolicy(policy)

        self.image_view.setMouseTracking(True)
        self.image_view.setFocusPolicy(Qt.NoFocus)
        self.image_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.image_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.vbox.addWidget(self.image_view)

        screen = QtWidgets.QDesktopWidget().screenGeometry(self)
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 4, (screen.height() - size.height()) // 4
        )

        self.update_view()
        self.image_view.reset()

    def hideEvent(self, _event):
        QtWidgets.QMainWindow.hide(self)

    def update_view(self):
        self.image_view.image = self.image
        self.setWindowTitle(self.make_window_title())

    def make_window_title(self):
        return os.path.basename(self.input_path)

    def keyPressEvent(self, event):
        key = event.key()
        global main_loop_type  # pylint: disable=global-statement
        if key == Qt.Key_Escape:
            if main_loop_type == 'qt':
                QtWidgets.QApplication.quit()
            elif main_loop_type == 'ipython':
                self.hide()
                # import IPython
                # IPython.get_ipython().ask_exit()


# pylint: disable=unused-argument
def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    QtWidgets.QApplication.quit()


def main():
    parser = argparse.ArgumentParser(description='image viewer')
    parser.add_argument('image', help='path to the image')
    opts = parser.parse_args()

    input_image = opts.image
    image = QtGui.QImage()
    image.load(input_image)

    app = QtWidgets.QApplication(sys.argv)
    try:
        import signal  # pylint: disable=all

        signal.signal(signal.SIGINT, sigint_handler)
    except ImportError:
        pass
    window = ImageViewerWindow(image, input_image)
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
