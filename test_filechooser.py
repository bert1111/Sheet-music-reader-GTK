import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

class PDFTestWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="PDF Selector Test")
        self.set_default_size(300, 100)

        button = Gtk.Button(label="Open PDF")
        button.connect("clicked", self.open_pdf_dialog)

        box = Gtk.Box(spacing=6)
        box.pack_start(button, True, True, 0)

        self.add(box)

    def open_pdf_dialog(self, widget):
        dialog = Gtk.FileChooserDialog(title="Selecteer PDF-bestand",
                                       parent=self,
                                       action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        filter_pdf = Gtk.FileFilter()
        filter_pdf.set_name("PDF-bestanden")
        filter_pdf.add_pattern("*.pdf")
        dialog.add_filter(filter_pdf)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("Gekozen bestand:", dialog.get_filename())
        dialog.destroy()

win = PDFTestWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
