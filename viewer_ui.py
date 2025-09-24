import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import json
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

        self.longpress_source_id = None
        self.scroll_positions = {}

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        self.btn_box = Gtk.Box(spacing=6)
        vbox.pack_start(self.btn_box, False, False, 0)

        self.btn_open = Gtk.Button(label="Open PDF")
        self.btn_open.connect("clicked", self.open_pdf)
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

        self.btn_pencil = Gtk.ToggleButton(label="Potlood aan/uit")
        self.btn_pencil.connect("toggled", self.toggle_pencil)
        self.btn_box.pack_start(self.btn_pencil, True, True, 0)

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
        # Stel callback in om wijzigingen direct persistent te maken
        self.annotation_widget.on_annotation_changed = self.save_annotations

        self.overlay.add_overlay(self.annotation_widget)

        self._create_navigation_buttons()
        for btn in [self.btn_left, self.btn_right, self.btn_top, self.btn_bottom]:
            self.main_overlay.add_overlay(btn)

        self.overlay.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                                Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.overlay.connect("button-press-event", self.on_touch_down)
        self.overlay.connect("button-release-event", self.on_touch_up)

        self.connect("delete-event", self.on_quit)

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

    def save_scroll_position(self):
        hadjust = self.scrolled_window.get_hadjustment()
        vadjust = self.scrolled_window.get_vadjustment()
        self.scroll_positions[self.page_navigator.current_page] = (hadjust.get_value(), vadjust.get_value())

    def restore_scroll_position(self, page_number):
        if page_number in self.scroll_positions:
            hadjust = self.scrolled_window.get_hadjustment()
            vadjust = self.scrolled_window.get_vadjustment()
            h_val, v_val = self.scroll_positions[page_number]
            GLib.idle_add(hadjust.set_value, h_val)
            GLib.idle_add(vadjust.set_value, v_val)

    def save_scroll_positions_to_file(self):
        if not self.filepath:
            return
        filename = self.filepath + ".scroll.json"
        try:
            with open(filename, "w") as f:
                json.dump(self.scroll_positions, f)
        except Exception as e:
            print(f"Fout bij opslaan van scrollposities: {e}")

    def load_scroll_positions_from_file(self):
        if not self.filepath:
            return
        filename = self.filepath + ".scroll.json"
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    loaded = json.load(f)
                    self.scroll_positions = {int(k): tuple(v) for k, v in loaded.items()}
            except Exception as e:
                print(f"Fout bij laden van scrollposities: {e}")

    def open_pdf(self, button):
        open_pdf_filechooser(self.load_pdf)

    def load_pdf(self, filepath):
        self.filepath = filepath
        self.pdf_renderer.open_pdf(filepath)
        self.page_navigator.set_total_pages(self.pdf_renderer.get_page_count())
        self.load_scroll_positions_from_file()
        self.show_page(self.page_navigator.current_page)
        self.load_annotations()
        self.btn_open.set_visible(False)
        self.restore_scroll_position(self.page_navigator.current_page)

    def show_page(self, page_number):
        if self.filepath:
            settings = self.page_settings.get(self.filepath, page_number)
            self.current_zoom = settings.get("zoom", 1.0)
            self.current_rotation = settings.get("rotation", 0)
        res = self.pdf_renderer.render_page(
            page_number,
            zoom=self.current_zoom,
            rotation=self.current_rotation
        )
        if res:
            pixbuf, _ = res
            self.image.set_from_pixbuf(pixbuf)
            while Gtk.events_pending():
                Gtk.main_iteration()
        else:
            self.image.clear()
        self.annotation_widget.set_zoom_and_rotation(self.current_zoom, self.current_rotation)

    def zoom_in(self, button):
        self.save_scroll_position()
        self.current_zoom = min(3.0, self.current_zoom * 1.1)
        self.save_page_settings()
        self.annotation_widget.set_zoom_and_rotation(self.current_zoom, self.current_rotation)
        self.show_page(self.page_navigator.current_page)
        self.save_annotations()

    def zoom_out(self, button):
        self.save_scroll_position()
        self.current_zoom = max(0.1, self.current_zoom / 1.1)
        self.save_page_settings()
        self.annotation_widget.set_zoom_and_rotation(self.current_zoom, self.current_rotation)
        self.show_page(self.page_navigator.current_page)
        self.save_annotations()

    def rotate(self, button):
        self.save_scroll_position()
        self.current_rotation = (self.current_rotation + 90) % 360
        self.save_page_settings()
        self.annotation_widget.set_zoom_and_rotation(self.current_zoom, self.current_rotation)
        self.show_page(self.page_navigator.current_page)
        self.save_annotations()

    def next_page(self):
        self.save_scroll_position()
        page = self.page_navigator.next_page()
        self.show_page(page)
        self.load_annotations()
        self.annotation_widget.set_zoom_and_rotation(self.current_zoom, self.current_rotation)
        self.restore_scroll_position(page)

    def prev_page(self):
        self.save_scroll_position()
        page = self.page_navigator.prev_page()
        self.show_page(page)
        self.load_annotations()
        self.annotation_widget.set_zoom_and_rotation(self.current_zoom, self.current_rotation)
        self.restore_scroll_position(page)

    def save_page_settings(self):
        if self.filepath:
            hadjust = self.scrolled_window.get_hadjustment()
            vadjust = self.scrolled_window.get_vadjustment()
            self.page_settings.set(
                self.filepath,
                self.page_navigator.current_page,
                zoom=self.current_zoom,
                rotation=self.current_rotation,
                scroll_x=hadjust.get_value(),
                scroll_y=vadjust.get_value()
            )
            self.page_settings.save()

    def toggle_pencil(self, btn):
        active = btn.get_active()
        if active and self.btn_clear.get_active():
            self.btn_clear.set_active(False)
        self.annotation_widget.set_drawing_enabled(active)
        self.annotation_widget.set_visible(True)

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
        annotations = self.annotation_storage.get(self.filepath, self.page_navigator.current_page)
        self.annotation_widget.load_annotations(annotations)

    def save_annotations(self):
        if not self.filepath:
            return
        annotations = self.annotation_widget.get_serializable_annotations()
        self.annotation_storage.set(self.filepath, self.page_navigator.current_page, annotations)
        self.annotation_storage.save()
        self.save_scroll_positions_to_file()

    def save_and_quit(self, button=None):
        self.save_annotations()
        self.save_scroll_positions_to_file()
        Gtk.main_quit()

    def on_quit(self, *args):
        self.save_annotations()
        self.save_scroll_positions_to_file()
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

def main():
    win = PDFViewerUI()
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
