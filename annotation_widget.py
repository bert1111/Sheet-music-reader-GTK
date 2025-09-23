import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

class AnnotationWidget(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.set_size_request(600, 800)
        self.lines = []
        self.current_line = []
        self.drawing = False
        self.drawing_enabled = False  # Nieuw: tekenen aan/uit
        self.line_color = Gdk.RGBA(1, 0, 0, 1)

        self.connect("draw", self.on_draw)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect("button-press-event", self.on_button_press)
        self.connect("button-release-event", self.on_button_release)
        self.connect("motion-notify-event", self.on_motion_notify)

    def on_button_press(self, widget, event):
        if not self.drawing_enabled:
            return False
        if event.button == 1:
            self.drawing = True
            self.current_line = [(event.x, event.y)]
            self.queue_draw()

    def on_button_release(self, widget, event):
        if not self.drawing_enabled:
            return False
        if event.button == 1 and self.drawing:
            self.drawing = False
            self.lines.append(self.current_line)
            self.current_line = []
            self.queue_draw()

    def on_motion_notify(self, widget, event):
        if not self.drawing_enabled:
            return False
        if self.drawing:
            self.current_line.append((event.x, event.y))
            self.queue_draw()

    def on_draw(self, widget, cr):
        cr.set_source_rgba(self.line_color.red,
                           self.line_color.green,
                           self.line_color.blue,
                           self.line_color.alpha)
        cr.set_line_width(2)
        for line in self.lines:
            if len(line) > 1:
                cr.move_to(*line[0])
                for p in line[1:]:
                    cr.line_to(*p)
                cr.stroke()
        if self.drawing and len(self.current_line) > 1:
            cr.move_to(*self.current_line[0])
            for p in self.current_line[1:]:
                cr.line_to(*p)
            cr.stroke()

    def clear(self):
        self.lines = []
        self.queue_draw()

    def load_lines(self, lines):
        self.lines = lines if lines else []
        self.queue_draw()

    def set_drawing_enabled(self, enabled: bool):
        self.drawing_enabled = enabled
        self.queue_draw()
