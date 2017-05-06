# -*- coding: utf-8 -*-
#
# Copyright © The Spyder Development Team
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

def introduce_renamed_methods_qheaderview(QHeaderView):

    _isClickable = QHeaderView.isClickable
    def sectionsClickable(self):
        """
        QHeaderView.sectionsClickable() -> bool
        """
        return _isClickable(self)
    QHeaderView.sectionsClickable = sectionsClickable
    def isClickable(self):
        raise Exception('isClickable is only available in Qt4. Use '
                        'sectionsClickable instead.')
    QHeaderView.isClickable = isClickable


    _isMovable = QHeaderView.isMovable
    def sectionsMovable(self):
        """
        QHeaderView.sectionsMovable() -> bool
        """
        return _isMovable(self)
    QHeaderView.sectionsMovable = sectionsMovable
    def isMovable(self):
        raise Exception('isMovable is only available in Qt4. Use '
                        'sectionsMovable instead.')
    QHeaderView.isMovable = isMovable


    _resizeMode = QHeaderView.resizeMode
    def sectionResizeMode(self, logicalIndex):
        """
        QHeaderView.sectionResizeMode(int) -> QHeaderView.ResizeMode
        """
        return _resizeMode(self, logicalIndex)
    QHeaderView.sectionResizeMode = sectionResizeMode
    def resizeMode(self, logicalIndex):
        raise Exception('resizeMode is only available in Qt4. Use '
                        'sectionResizeMode instead.')
    QHeaderView.resizeMode = resizeMode

    _setClickable = QHeaderView.setClickable
    def setSectionsClickable(self, clickable):
        """
        QHeaderView.setSectionsClickable(bool)
        """
        return _setClickable(self, clickable)
    QHeaderView.setSectionsClickable = setSectionsClickable
    def setClickable(self, clickable):
        raise Exception('setClickable is only available in Qt4. Use '
                        'setSectionsClickable instead.')
    QHeaderView.setClickable = setClickable


    _setMovable = QHeaderView.setMovable
    def setSectionsMovable(self, movable):
        """
        QHeaderView.setSectionsMovable(bool)
        """
        return _setMovable(self, movable)
    QHeaderView.setSectionsMovable = setSectionsMovable
    def setMovable(self, movable):
        raise Exception('setMovable is only available in Qt4. Use '
                        'setSectionsMovable instead.')
    QHeaderView.setMovable = setMovable


    _setResizeMode = QHeaderView.setResizeMode
    def setSectionResizeMode(self, *args):
        """
        QHeaderView.setSectionResizeMode(QHeaderView.ResizeMode)
        QHeaderView.setSectionResizeMode(int, QHeaderView.ResizeMode)
        """
        _setResizeMode(self, *args)
    QHeaderView.setSectionResizeMode = setSectionResizeMode
    def setResizeMode(self, *args):
        raise Exception('setResizeMode is only available in Qt4. Use '
                        'setSectionResizeMode instead.')
    QHeaderView.setResizeMode = setResizeMode




