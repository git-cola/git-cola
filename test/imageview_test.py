"""Tests for crisp SVG rendering in the image diff viewer.

These exercise the pure module-level helpers only (no widget event flow), so
they stay deterministic in the full suite.
"""
import sys

import pytest

from cola.widgets import imageview
from cola.widgets.diff import Options
from cola.widgets.diff import comp_logical_size
from cola.widgets.diff import is_svg_source
from cola.widgets.diff import load_image_source
from cola.widgets.diff import render_comp_image
from cola.widgets.diff import source_logical_size
from qtpy import QtGui
from qtpy import QtSvg
from qtpy import QtWidgets

# A minimal SVG whose intrinsic size comes from viewBox alone (no width/height),
# reproducing the syncthing.svg case that rendered blurry.
SVG_BYTES = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 118 118">' b'<circle cx="59" cy="59" r="59" fill="#0891d1"/></svg>'


@pytest.fixture(scope='module')
def qapp():
    """Provide a QApplication for the QImage/QPixmap/QPainter helpers."""
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ['git-cola-test']
        )
    yield instance


@pytest.fixture
def svg_path(tmp_path):
    path = tmp_path / 'logo.svg'
    path.write_bytes(SVG_BYTES)
    return str(path)


@pytest.fixture
def png_path(tmp_path, qapp):
    path = tmp_path / 'logo.png'
    image = QtGui.QImage(32, 24, QtGui.QImage.Format_ARGB32)
    image.fill(0)
    image.save(str(path))
    return str(path)


def test_looks_like_svg_by_extension_and_content(svg_path, png_path, tmp_path):
    assert imageview.looks_like_svg(svg_path)
    assert not imageview.looks_like_svg(png_path)
    # Content sniff wins even without a .svg extension.
    disguised = tmp_path / 'logo.txt'
    disguised.write_bytes(SVG_BYTES)
    assert imageview.looks_like_svg(str(disguised))
    # An unreadable file with a non-SVG extension is not treated as SVG.
    assert not imageview.looks_like_svg(str(tmp_path / 'missing.png'))


def test_load_image_source_detects_svg_vs_raster(qapp, svg_path, png_path):
    svg_source = load_image_source(svg_path)
    assert is_svg_source(svg_source)
    assert isinstance(svg_source, QtSvg.QSvgRenderer)

    raster_source = load_image_source(png_path)
    assert not is_svg_source(raster_source)
    assert isinstance(raster_source, QtGui.QPixmap)


def test_load_image_source_returns_none_for_garbage(qapp, tmp_path):
    junk = tmp_path / 'junk.bin'
    junk.write_bytes(b'not an image')
    assert load_image_source(str(junk)) is None


def test_source_logical_size_uses_viewbox(qapp, svg_path):
    size = source_logical_size(load_image_source(svg_path))
    assert size.width() == 118
    assert size.height() == 118


def test_comp_logical_size(qapp, svg_path):
    source = load_image_source(svg_path)
    single = comp_logical_size([source], Options.SIDE_BY_SIDE)
    assert (single.width(), single.height()) == (118, 118)
    # Side-by-side lays two images out horizontally.
    pair = comp_logical_size([source, source], Options.SIDE_BY_SIDE)
    assert (pair.width(), pair.height()) == (236, 118)
    # Comp modes overlay, so the canvas is the max of each dimension.
    overlay = comp_logical_size([source, source], Options.DIFF)
    assert (overlay.width(), overlay.height()) == (118, 118)


@pytest.mark.parametrize(
    'mode',
    [Options.SIDE_BY_SIDE, Options.DIFF, Options.XOR, Options.PIXEL_XOR],
)
def test_render_comp_image_rasterises_at_scale(qapp, svg_path, mode):
    source = load_image_source(svg_path)
    pixmap = render_comp_image([source], mode, 4.0)
    assert not pixmap.isNull()
    # A 118-unit SVG rendered at 4x yields a 472px raster carrying dpr 4, so the
    # scene keeps its 118 logical units while painting at higher resolution.
    assert pixmap.devicePixelRatio() == 4.0
    assert pixmap.width() == 472
    assert pixmap.height() == 472


def test_render_svg_to_pixmap_scales(qapp, svg_path):
    renderer = load_image_source(svg_path)
    size = source_logical_size(renderer)
    pixmap = imageview.render_svg_to_pixmap(renderer, size, 3.0)
    assert not pixmap.isNull()
    assert pixmap.devicePixelRatio() == 3.0
    assert pixmap.width() == 354
    assert pixmap.height() == 354
