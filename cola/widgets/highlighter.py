from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtCore, QtGui

from cola.compat import ustr

have_pygments = True
try:
    from pygments.styles import get_style_by_name
    from pygments import lex
    from pygments.util import ClassNotFound
    from pygments.lexers import get_lexer_for_filename
except ImportError:
    have_pygments = False

def highlight_document(edit, filename):
    doc = edit.document()

    if not have_pygments:
        return

    try:
        lexer = get_lexer_for_filename(filename, stripnl=False)
    except ClassNotFound:
        return

    style = get_style_by_name("default")

    font = doc.defaultFont()
    base_format = QtGui.QTextCharFormat()
    base_format.setFont(font)
    token_formats = {}

    window = edit.window()
    if hasattr(window, "processEvents"):
        processEvents = window.processEvents
    else:
        processEvents = QtCore.QCoreApplication.processEvents

    def get_token_format(token):
        if token in token_formats:
            return token_formats[token]

        if token.parent:
            parent_format = get_token_format(token.parent)
        else:
            parent_format = base_format

        format = QtGui.QTextCharFormat(parent_format)
        font = format.font()
        if style.styles_token(token):
            tstyle = style.style_for_token(token)
            if tstyle['color']:
                format.setForeground (QtGui.QColor("#"+tstyle['color']))
            if tstyle['bold']: font.setWeight(QtGui.QFont.Bold)
            if tstyle['italic']: font.setItalic (True)
            if tstyle['underline']: format.setFontUnderline(True)
            if tstyle['bgcolor']: format.setBackground (QtGui.QColor("#"+tstyle['bgcolor']))
            # No way to set this for a QTextCharFormat
            #if tstyle['border']: format.
        token_formats[token] = format
        return format

    text = ustr(doc.toPlainText())

    block_count = 0
    block = doc.firstBlock()
    assert(isinstance(block, QtGui.QTextBlock))
    block_pos = 0
    block_len = block.length()
    block_formats = []

    for token, ttext in lex(text, lexer):
        format_len = len(ttext)
        format = get_token_format(token)
        while format_len > 0:
            format_range = QtGui.QTextLayout.FormatRange()
            format_range.start = block_pos
            format_range.length = min(format_len, block_len)
            format_range.format = format
            block_formats.append(format_range)
            block_len -= format_range.length
            format_len -= format_range.length
            block_pos += format_range.length
            if block_len == 0:
                block.layout().setAdditionalFormats(block_formats)
                doc.markContentsDirty(block.position(), block.length())
                block = block.next()
                block_pos = 0
                block_len = block.length()
                block_formats = []

                block_count += 1
                if block_count % 100 == 0:
                    processEvents()


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)

    python = QtGui.QPlainTextEdit()
    f = open(__file__, 'r')
    python.setPlainText(f.read())
    f.close()

    python.setWindowTitle('python')
    python.show()
    highlight_document(python, __file__)

    sys.exit(app.exec_())
