import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import os

from pdf_renderer import PDFRenderer
from page_navigator import PageNavigator
from annotation_widget import AnnotationWidget
from annotation_storage import AnnotationStorage
from page_settings import PageSettings
from file_selector import open_pdf_filechooser

class PDFViewerUI(Gtk.Window):
    LONGPRESS_TIME = 1000

    def __init__(self):
        super().__init__(title="PDF Viewer")

        screen = Gdk.Screen.get_default()
        screen_width = screen.get_width()
        screen_height = screen.get_height()
        print(f"Detecteerde schermresolutie: {screen_width} x {screen_height}")

        self.set_default_size(screen_width, screen_height)
        self.fullscreen()

        self.pdf_renderer = PDFRenderer()
        self.page_navigator = PageNavigator()
        self.page_settings = PageSettings()
        self.annotation_storage = AnnotationStorage()

        self.filepath = None
        self.current_zoom = 1.0
        self.current_rotation = 0

        # Concert-navigatie attributen
        self.concert_order = []
        self.concert_piece_index = 0
        self.concert_folder = None
        self.total_pages_current_pdf = 0
        self.current_page_in_piece = 0

        self.longpress_source_id = None

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        self.btn_box = Gtk.Box(spacing=6)
        vbox.pack_start(self.btn_box, False, False, 0)

        self.btn_open = Gtk.Button(label="Open PDF")
        self.btn_open.connect("clicked", self.open_orkest_map)
        self.btn_box.pack_start(self.btn_open, True, True, 0)

        self.btn_zoom_in = Gtk.Button(label="Zoom +")
        self.btn_zoom_in.connect("clicked", self.zoom_in)
        self.btn_box.pack_start(self.btn_zoom_in, True, True, 0)

        self.btn_zoom_out = Gtk.Button(label="Zoom -")
        self.btn_zoom_out.connect("clicked", self.zoom_out)
        self.btn_box.pack_start(self.btn_zoom_out, True, True, 0)

        self.btn_rotate = Gtk.Button(label="Draai 90°")
        self.btn_rotate.connect("clicked", self.rotate)
        self.btn_box.pack_start(self.btn_rotate, True, True, 0)

        self.btn_pencil = Gtk.ToggleButton(label="Tekenen")
        self.btn_pencil.connect("toggled", self.toggle_pencil)
        self.btn_box.pack_start(self.btn_pencil, True, True, 0)

        self.btn_drag = Gtk.ToggleButton(label="Annotatie slepen")
        self.btn_drag.set_tooltip_text("Annotatie slepen aan/uit")
        self.btn_drag.connect("toggled", self.toggle_drag_mode)
        self.btn_box.pack_start(self.btn_drag, True, True, 0)

        self.btn_choose_color = Gtk.Button(label="Kies kleur")
        self.btn_choose_color.connect("clicked", self.choose_color)
        self.btn_box.pack_start(self.btn_choose_color, True, True, 0)

        self.btn_clear = Gtk.ToggleButton(label="Wis geselecteerde annotatie")
        self.btn_clear.connect("toggled", self.on_clear_toggled)
        self.btn_box.pack_start(self.btn_clear, True, True, 0)

        self.btn_save_quit = Gtk.Button(label="Opslaan & Afsluiten")
        self.btn_save_quit.connect("clicked", self.save_and_quit)
        self.btn_box.pack_start(self.btn_save_quit, True, True, 0)

        self.main_overlay = Gtk.Overlay()
        vbox.pack_start(self.main_overlay, True, True, 0)

        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_hexpand(True)
        self.scrolled_window.set_vexpand(True)
        self.main_overlay.add(self.scrolled_window)

        self.overlay = Gtk.Overlay()
        self.scrolled_window.add(self.overlay)

        self.image = Gtk.Image()
        self.overlay.add(self.image)

        self.annotation_widget = AnnotationWidget()
        self.annotation_widget.set_visible(True)
        self.annotation_widget.set_zoom_and_rotation(self.current_zoom, self.current_rotation)
        self.annotation_widget.on_annotation_changed = self.save_annotations
        self.overlay.add_overlay(self.annotation_widget)

        self._create_navigation_buttons()
        for btn in [self.btn_left, self.btn_right, self.btn_top, self.btn_bottom]:
            self.main_overlay.add_overlay(btn)

        self.overlay.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.overlay.connect("button-press-event", self.on_touch_down)
        self.overlay.connect("button-release-event", self.on_touch_up)

        self.connect("delete-event", self.on_quit)

        self.muziek_basispad = self.page_settings.get_basispad()
        if not self.muziek_basispad or not os.path.isdir(self.muziek_basispad):
            self.muziek_basispad = self.kies_muziek_basispad()
        if self.muziek_basispad:
            self.page_settings.set_basispad(self.muziek_basispad)
            self.page_settings.save()
            print(f"Geselecteerd basis pad voor bladmuziek: {self.muziek_basispad}")

    def kies_muziek_basispad(self):
        dialog = Gtk.FileChooserDialog(
            title="Selecteer basis map bladmuziek",
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                     "Kies", Gtk.ResponseType.OK)
        )
        response = dialog.run()
        pad = None
        if response == Gtk.ResponseType.OK:
            pad = dialog.get_filename()
        dialog.destroy()
        return pad

    def lijst_orkesten(self):
        try:
            return sorted([d for d in os.listdir(self.muziek_basispad)
                           if os.path.isdir(os.path.join(self.muziek_basispad, d))])
        except Exception as e:
            print(f"Fout bij lezen orkestmappen: {e}")
            return []

    def open_orkest_map(self, button):
        orkesten = self.lijst_orkesten()
        if not orkesten:
            dlg = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK,
                                    "Geen orkestmappen gevonden in basismap.")
            dlg.run()
            dlg.destroy()
            return

        dialog = Gtk.Dialog("Selecteer orkest", self, 0,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                             Gtk.STOCK_OK, Gtk.ResponseType.OK))

        box = dialog.get_content_area()
        label = Gtk.Label(label="Kies het orkest:")
        box.add(label)

        combo = Gtk.ComboBoxText()
        for orkest in orkesten:
            combo.append_text(orkest)
        combo.set_active(0)
        box.add(combo)

        dialog.show_all()

        resp = dialog.run()
        pad_or_kest = None
        if resp == Gtk.ResponseType.OK:
            actieve_index = combo.get_active()
            if actieve_index >= 0:
                geselecteerd_orkest = orkesten[actieve_index]
                pad_or_kest = os.path.join(self.muziek_basispad, geselecteerd_orkest)
        dialog.destroy()

        if pad_or_kest:
            open_pdf_filechooser(self.load_pdf_or_concert, start_folder=pad_or_kest)

    def _create_navigation_buttons(self):
        def make_invisible_button():
            btn = Gtk.Button()
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.set_can_focus(False)
            btn.set_focus_on_click(False)
            btn.set_opacity(0)
            return btn

        self.btn_left = make_invisible_button()
        self.btn_right = make_invisible_button()
        self.btn_top = make_invisible_button()
        self.btn_bottom = make_invisible_button()

        self.btn_left.connect("clicked", lambda w: self.prev_page())
        self.btn_right.connect("clicked", lambda w: self.next_page())
        self.btn_top.connect("clicked", lambda w: self.prev_page())
        self.btn_bottom.connect("clicked", lambda w: self.next_page())

        self.btn_left.set_halign(Gtk.Align.START)
        self.btn_left.set_valign(Gtk.Align.FILL)
        self.btn_left.set_size_request(100, -1)

        self.btn_right.set_halign(Gtk.Align.END)
        self.btn_right.set_valign(Gtk.Align.FILL)
        self.btn_right.set_size_request(100, -1)

        self.btn_top.set_halign(Gtk.Align.FILL)
        self.btn_top.set_valign(Gtk.Align.START)
        self.btn_top.set_size_request(-1, 100)

        self.btn_bottom.set_halign(Gtk.Align.FILL)
        self.btn_bottom.set_valign(Gtk.Align.END)
        self.btn_bottom.set_size_request(-1, 100)

    def load_pdf_or_concert(self, filepath):
        base_dir = os.path.dirname(filepath)
        concert_map = os.path.join(base_dir, "Concert")
        if os.path.isdir(concert_map):
            concert_txt = os.path.join(concert_map, "Concert.txt")
            if os.path.isfile(concert_txt):
                self.concert_order = self.get_concert_order(concert_map)
                self.concert_piece_index = 0
                self.concert_folder = concert_map
                self.load_pdf_direct(self._get_pdf_path_for_current_piece())
                return

        self.concert_order = []
        self.filepath = filepath
        self.pdf_renderer.open_pdf(filepath)
        self.total_pages_current_pdf = self.pdf_renderer.get_page_count()
        self.current_page_in_piece = 0
        self.page_navigator.set_total_pages(self.total_pages_current_pdf)
        self.show_page(self.current_page_in_piece)
        self.load_annotations()

    def _get_pdf_path_for_current_piece(self):
        bovenliggende_map = os.path.dirname(self.concert_folder)
        stuk_naam = self.concert_order[self.concert_piece_index]
        return os.path.join(bovenliggende_map, stuk_naam + ".pdf")

    def get_concert_order(self, concert_folder):
        txt_path = os.path.join(concert_folder, "Concert.txt")
        if not os.path.isfile(txt_path):
            return []
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return [title.strip() for title in content.split(",") if title.strip()]

    def load_pdf_direct(self, filepath):
        self.filepath = filepath
        self.pdf_renderer.open_pdf(filepath)
        self.total_pages_current_pdf = self.pdf_renderer.get_page_count()
        self.current_page_in_piece = 0
        self.page_navigator.set_total_pages(self.total_pages_current_pdf)
        self.show_page(self.current_page_in_piece)
        self.load_annotations()

    def next_page(self, button=None):
        if self.concert_order:
            if self.current_page_in_piece < self.total_pages_current_pdf - 1:
                self.current_page_in_piece += 1
                self.show_page(self.current_page_in_piece)
            else:
                if self.concert_piece_index < len(self.concert_order) - 1:
                    self.concert_piece_index += 1
                    next_pdf = self._get_pdf_path_for_current_piece()
                    if os.path.isfile(next_pdf):
                        self.load_pdf_direct(next_pdf)
                    else:
                        print(f"PDF bestand niet gevonden: {next_pdf}")
        else:
            self.save_page_settings()
            page = self.page_navigator.next_page()
            self.show_page(page)
            self.load_annotations()

    def prev_page(self, button=None):
        if self.concert_order:
            if self.current_page_in_piece > 0:
                self.current_page_in_piece -= 1
                self.show_page(self.current_page_in_piece)
            else:
                if self.concert_piece_index > 0:
                    self.concert_piece_index -= 1
                    prev_pdf = self._get_pdf_path_for_current_piece()
                    if os.path.isfile(prev_pdf):
                        self.load_pdf_direct(prev_pdf)
                        self.current_page_in_piece = self.total_pages_current_pdf - 1
                        self.show_page(self.current_page_in_piece)
                    else:
                        print(f"PDF bestand niet gevonden: {prev_pdf}")
        else:
            self.save_page_settings()
            page = self.page_navigator.prev_page()
            self.show_page(page)
            self.load_annotations()

    def show_page(self, page_number):
        if self.filepath:
            settings = self.page_settings.get(self.filepath, page_number)
            self.current_zoom = settings.get("zoom", 1.0)
            self.current_rotation = settings.get("rotation", 0)
            scroll_x = settings.get("scroll_x", 0)
            scroll_y = settings.get("scroll_y", 0)

        res = self.pdf_renderer.render_page(
            page_number,
            zoom=self.current_zoom,
            rotation=self.current_rotation
        )
        if res:
            pixbuf, pdf_size = res
            self.image.set_from_pixbuf(pixbuf)

            if pdf_size:
                self.annotation_widget.set_pdf_dimensions(pdf_size[0], pdf_size[1])

            while Gtk.events_pending():
                Gtk.main_iteration()
        else:
            self.image.clear()

        self.annotation_widget.set_zoom_and_rotation(self.current_zoom, self.current_rotation)

        hadjust = self.scrolled_window.get_hadjustment()
        vadjust = self.scrolled_window.get_vadjustment()
        hadjust.set_value(scroll_x)
        vadjust.set_value(scroll_y)

    def save_page_settings(self):
        if self.filepath:
            hadjust = self.scrolled_window.get_hadjustment()
            vadjust = self.scrolled_window.get_vadjustment()
            self.page_settings.set(
                self.filepath,
                self.current_page_in_piece if self.concert_order else self.page_navigator.current_page,
                zoom=self.current_zoom,
                rotation=self.current_rotation,
                scroll_x=hadjust.get_value(),
                scroll_y=vadjust.get_value()
            )
            self.page_settings.save()

    def zoom_in(self, button):
        self.current_zoom = min(3.0, self.current_zoom * 1.1)
        self.save_page_settings()
        self.show_page(self.current_page_in_piece if self.concert_order else self.page_navigator.current_page)
        self.save_annotations()

    def zoom_out(self, button):
        self.current_zoom = max(0.1, self.current_zoom / 1.1)
        self.save_page_settings()
        self.show_page(self.current_page_in_piece if self.concert_order else self.page_navigator.current_page)
        self.save_annotations()

    def rotate(self, button):
        self.current_rotation = (self.current_rotation + 90) % 360
        self.save_page_settings()
        self.show_page(self.current_page_in_piece if self.concert_order else self.page_navigator.current_page)
        self.save_annotations()

    def toggle_pencil(self, btn):
        active = btn.get_active()
        if active and self.btn_clear.get_active():
            self.btn_clear.set_active(False)
        if active and self.btn_drag.get_active():
            self.btn_drag.set_active(False)
        self.annotation_widget.set_drawing_enabled(active)
        self.annotation_widget.dragging_enabled = False
        self.annotation_widget.wis_modus = False
        self.annotation_widget.set_visible(True)

    def toggle_drag_mode(self, btn):
        active = btn.get_active()
        if active:
            if self.btn_pencil.get_active():
                self.btn_pencil.set_active(False)
            if self.btn_clear.get_active():
                self.btn_clear.set_active(False)
            self.annotation_widget.dragging_enabled = True
            self.annotation_widget.set_drawing_enabled(False)
            self.annotation_widget.wis_modus = False
        else:
            self.annotation_widget.dragging_enabled = False
            if self.btn_pencil.get_active():
                self.annotation_widget.set_drawing_enabled(True)

    def choose_color(self, button):
        dialog = Gtk.ColorChooserDialog(title="Kies annotatiekleur", parent=self)
        dialog.set_rgba(self.annotation_widget.current_color)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            color = dialog.get_rgba()
            self.annotation_widget.set_line_color(color)
        dialog.destroy()

    def on_clear_toggled(self, togglebutton):
        active = togglebutton.get_active()
        if active:
            if self.btn_pencil.get_active():
                self.btn_pencil.set_active(False)
            self.annotation_widget.wis_modus = True
            self.annotation_widget.set_drawing_enabled(False)
        else:
            self.annotation_widget.wis_modus = False
            self.annotation_widget.set_drawing_enabled(self.btn_pencil.get_active())

    def clear_selected_annotation(self, button):
        self.annotation_widget.clear_selected_annotation()
        self.save_annotations()

    def load_annotations(self):
        if not self.filepath:
            return
        annotations = self.annotation_storage.get(self.filepath, self.current_page_in_piece if self.concert_order else self.page_navigator.current_page)
        self.annotation_widget.load_annotations(annotations)

    def save_annotations(self):
        if not self.filepath:
            return
        annotations = self.annotation_widget.get_serializable_annotations()
        self.annotation_storage.set(self.filepath, self.current_page_in_piece if self.concert_order else self.page_navigator.current_page, annotations)
        self.annotation_storage.save()

    def save_and_quit(self, button=None):
        self.save_page_settings()
        self.save_annotations()
        Gtk.main_quit()

    def on_quit(self, *args):
        self.save_page_settings()
        self.save_annotations()
        Gtk.main_quit()

    def on_touch_down(self, widget, event):
        if not self.filepath:
            return False
        alloc = self.image.get_allocation()
        x, y = event.x, event.y

        if alloc.width * 0.4 < x < alloc.width * 0.6 and alloc.height * 0.4 < y < alloc.height * 0.6:
            self.cancel_longpress()
            self.longpress_source_id = GLib.timeout_add(self.LONGPRESS_TIME, self.toggle_button_bar_visibility)
            return True
        return True

    def on_touch_up(self, widget, event):
        self.cancel_longpress()
        if not self.filepath:
            return False

        alloc = self.overlay.get_allocation()
        x, y = event.x, event.y

        zone_size_x = alloc.width * 0.15
        zone_size_y = alloc.height * 0.15

        if x < zone_size_x or y < zone_size_y:
            self.prev_page()
            return True
        if x > (alloc.width - zone_size_x) or y > (alloc.height - zone_size_y):
            self.next_page()
            return True
        return False

    def cancel_longpress(self):
        if self.longpress_source_id is not None:
            GLib.source_remove(self.longpress_source_id)
            self.longpress_source_id = None

    def toggle_button_bar_visibility(self):
        visible = self.btn_box.get_visible()
        self.btn_box.set_visible(not visible)
        self.longpress_source_id = None
        return False

def open_pdf_filechooser(callback, start_folder=None):
    dialog = Gtk.FileChooserDialog(
        title="Selecteer PDF-bestand",
        action=Gtk.FileChooserAction.OPEN)
    dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                       Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

    filter_pdf = Gtk.FileFilter()
    filter_pdf.set_name("PDF-bestanden")
    filter_pdf.add_pattern("*.pdf")
    dialog.add_filter(filter_pdf)

    if start_folder:
        try:
            dialog.set_current_folder(start_folder)
        except Exception as e:
            print(f"Fout bij instellen startmap filechooser: {e}")

    response = dialog.run()
    if response == Gtk.ResponseType.OK:
        callback(dialog.get_filename())
    dialog.destroy()

def main():
    win = PDFViewerUI()
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
