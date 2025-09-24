import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk
import math

class Annotation:
    def __init__(self, points, color):
        self.points = points  # lijst van (x,y)
        self.color = color    # Gdk.RGBA kleur

    def get_bounding_box(self):
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        return (min_x, min_y, max_x - min_x, max_y - min_y)

    def contains_point(self, x, y, tolerance=5):
        for px, py in self.points:
            if abs(px - x) <= tolerance and abs(py - y) <= tolerance:
                return True
        return False

class AnnotationWidget(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.set_size_request(600, 800)

        self.annotations = []
        self.current_line = []

        self.drawing = False
        self.drawing_enabled = False
        self.wis_modus = False

        self.selected_annotation = None

        self.current_color = Gdk.RGBA(1,0,0,1)
        self.current_zoom = 1.0
        self.current_rotation = 0

        self.on_annotation_changed = None

        self.connect("draw", self.on_draw)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect("button-press-event", self.on_button_press)
        self.connect("button-release-event",self.on_button_release)
        self.connect("motion-notify-event",self.on_motion_notify)

    def set_line_color(self, rgba: Gdk.RGBA):
        self.current_color = rgba
        self.queue_draw()

    def set_drawing_enabled(self, enabled: bool):
        self.drawing_enabled = enabled
        if enabled:
            self.wis_modus = False
        self.queue_draw()

    def set_zoom_and_rotation(self, zoom, rotation):
        self.current_zoom = zoom
        self.current_rotation = rotation
        self.queue_draw()

    # Zet muis coördinaten terug naar pagina coördinaten dmv inverse transform
    def _inverse_transform(self, x, y):
        angle = -math.radians(self.current_rotation)
        zx, zy = x / self.current_zoom, y / self.current_zoom
        tx = zx * math.cos(angle) - zy * math.sin(angle)
        ty = zx * math.sin(angle) + zy * math.cos(angle)
        return tx, ty

    def on_button_press(self, widget, event):
        x, y = self._inverse_transform(event.x, event.y)
        if self.wis_modus and event.button == 1:
            for ann in reversed(self.annotations):
                if ann.contains_point(x, y):
                    self.annotations.remove(ann)
                    self.selected_annotation = None
                    self.queue_draw()
                    if self.on_annotation_changed:
                        self.on_annotation_changed()
                    break
        elif self.drawing_enabled and event.button == 1:
            self.drawing = True
            self.current_line = [(x, y)]
            self.selected_annotation = None
            self.queue_draw()
        else:
            if event.button == 1:
                self.selected_annotation = None
                for ann in reversed(self.annotations):
                    if ann.contains_point(x, y):
                        self.selected_annotation = ann
                        break
                self.queue_draw()

    def on_button_release(self, widget, event):
        if self.drawing_enabled and event.button == 1 and self.drawing:
            self.drawing = False
            if len(self.current_line) > 1:
                ann = Annotation(self.current_line, self.current_color)
                self.annotations.append(ann)
                if self.on_annotation_changed:
                    self.on_annotation_changed()
            self.current_line = []
            self.queue_draw()

    def on_motion_notify(self, widget, event):
        if self.drawing_enabled and self.drawing:
            x, y = self._inverse_transform(event.x, event.y)
            self.current_line.append((x, y))
            self.queue_draw()

    def on_draw(self, widget, cr):
        cr.set_line_width(2)

        cr.save()
        # Pas globale zoom en rotatie toe op de hele context
        cr.scale(self.current_zoom, self.current_zoom)
        if self.current_rotation != 0:
            cr.rotate(math.radians(self.current_rotation))

        # Teken annotaties
        for ann in self.annotations:
            cr.set_source_rgba(ann.color.red, ann.color.green, ann.color.blue, ann.color.alpha)
            pts = ann.points
            if len(pts) > 1:
                cr.move_to(*pts[0])
                for p in pts[1:]:
                    cr.line_to(*p)
                cr.stroke()

        # Tekenen van lopende lijn
        if self.drawing and len(self.current_line) > 1:
            cr.set_source_rgba(self.current_color.red,
                               self.current_color.green,
                               self.current_color.blue,
                               self.current_color.alpha)
            cr.move_to(*self.current_line[0])
            for p in self.current_line[1:]:
                cr.line_to(*p)
            cr.stroke()
        cr.restore()

        # Highlight geselecteerde annotatie ook met tranform
        if self.selected_annotation:
            cr.save()
            cr.scale(self.current_zoom, self.current_zoom)
            if self.current_rotation != 0:
                cr.rotate(math.radians(self.current_rotation))
            bbox = self.selected_annotation.get_bounding_box()
            cr.set_source_rgba(0, 0, 1, 0.5)
            cr.set_line_width(3)
            cr.rectangle(*bbox)
            cr.stroke()
            cr.restore()

    def clear_selected_annotation(self):
        if self.selected_annotation and self.selected_annotation in self.annotations:
            self.annotations.remove(self.selected_annotation)
            self.selected_annotation = None
            self.queue_draw()
            if self.on_annotation_changed:
                self.on_annotation_changed()

    def clear_all_annotations(self):
        self.annotations.clear()
        self.selected_annotation = None
        self.queue_draw()
        if self.on_annotation_changed:
            self.on_annotation_changed()

    def load_annotations(self, annotations_data):
        from gi.repository import Gdk
        self.annotations.clear()
        for ann in annotations_data or []:
            points = ann.get("points", [])
            color_dict = ann.get("color", {"red":1,"green":0,"blue":0,"alpha":1})
            color = Gdk.RGBA(color_dict["red"], color_dict["green"], color_dict["blue"], color_dict["alpha"])
            self.annotations.append(Annotation(points, color))
        self.queue_draw()

    def get_serializable_annotations(self):
        data = []
        for ann in self.annotations:
            data.append({
                "points": ann.points,
                "color": {
                    "red": ann.color.red,
                    "green": ann.color.green,
                    "blue": ann.color.blue,
                    "alpha": ann.color.alpha
                }
            })
        return data
