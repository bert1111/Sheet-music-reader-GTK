#main.py
from viewer_ui import PDFViewerUI
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

def main():
    win = PDFViewerUI()
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
