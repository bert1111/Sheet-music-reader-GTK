import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

def open_pdf_filechooser(on_file_selected_callback):
    dialog = Gtk.FileChooserDialog(title="Selecteer PDF-bestand",
                                   action=Gtk.FileChooserAction.OPEN)
    dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                       Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
    
    filter_pdf = Gtk.FileFilter()
    filter_pdf.set_name("PDF-bestanden")
    filter_pdf.add_pattern("*.pdf")
    dialog.add_filter(filter_pdf)

    response = dialog.run()
    if response == Gtk.ResponseType.OK:
        on_file_selected_callback(dialog.get_filename())
    dialog.destroy()
