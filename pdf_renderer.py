#pdf_renderer.py
import gi
gi.require_version("Poppler", "0.18")
gi.require_version("Gtk", "3.0")
from gi.repository import Poppler, GdkPixbuf
import cairo
import io
import math

class PDFRenderer:
    def __init__(self):
        self.doc = None

    def open_pdf(self, filepath):
        from pathlib import Path
        from urllib.request import pathname2url
        from urllib.parse import urljoin

        path = Path(filepath).absolute()
        uri = urljoin('file:', pathname2url(str(path)))
        self.doc = Poppler.Document.new_from_file(uri, None)

    def get_page_count(self):
        if not self.doc:
            return 0
        return self.doc.get_n_pages()

    def render_page(self, page_number, zoom=1.0, rotation=0):
        if not self.doc or page_number < 0 or page_number >= self.get_page_count():
            return None

        page = self.doc.get_page(page_number)
        width, height = page.get_size()
        width, height = int(width * zoom), int(height * zoom)

        if rotation in [90, 270]:
            w, h = height, width
        else:
            w, h = width, height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr = cairo.Context(surface)

        if rotation == 90:
            cr.translate(w, 0)
            cr.rotate(math.radians(90))
        elif rotation == 180:
            cr.translate(w, h)
            cr.rotate(math.radians(180))
        elif rotation == 270:
            cr.translate(0, h)
            cr.rotate(math.radians(270))

        cr.scale(zoom, zoom)
        page.render(cr)

        buf = io.BytesIO()
        surface.write_to_png(buf)
        buf.seek(0)
        loader = GdkPixbuf.PixbufLoader.new_with_type('png')
        loader.write(buf.read())
        loader.close()
        pixbuf = loader.get_pixbuf()
        return pixbuf, (w, h)
