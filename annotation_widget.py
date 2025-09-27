#annotation_widget.py
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk
import math

class Annotation:
    def __init__(self, points, color):
        self.points = points  # lijst van (x,y) in PDF-coördinaten
        self.color = color    # Gdk.RGBA kleur

    def get_bounding_box(self):
        if not self.points:
            return (0, 0, 0, 0)
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

        self.dragging_enabled = False  # Sleepmodus aan/uit
        self.dragging_annotation = False
        self.drag_start_pdf = None

        self.current_color = Gdk.RGBA(1, 0, 0, 1)
        self.current_zoom = 1.0
        self.current_rotation = 0

        # PDF & widget afmetingen
        self.pdf_width = 0
        self.pdf_height = 0
        self.widget_width = 0
        self.widget_height = 0

        self.on_annotation_changed = None

        self.connect("draw", self.on_draw)
        self.connect("size-allocate", self.on_size_allocate)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect("button-press-event", self.on_button_press)
        self.connect("button-release-event", self.on_button_release)
        self.connect("motion-notify-event", self.on_motion_notify)

    def set_line_color(self, rgba: Gdk.RGBA):
        self.current_color = rgba
        self.queue_draw()

    def set_drawing_enabled(self, enabled: bool):
        self.drawing_enabled = enabled
        if enabled:
            self.wis_modus = False
        self.queue_draw()

    def set_pdf_dimensions(self, pdf_width, pdf_height):
        self.pdf_width = pdf_width
        self.pdf_height = pdf_height
        self.queue_draw()

    def set_zoom_and_rotation(self, zoom, rotation):
        self.current_zoom = zoom
        self.current_rotation = rotation
        self.queue_draw()

    def on_size_allocate(self, widget, allocation):
        self.widget_width = allocation.width
        self.widget_height = allocation.height

    def _mouse_to_pdf_coords(self, mouse_x, mouse_y):
        if self.pdf_width == 0 or self.pdf_height == 0:
            return mouse_x, mouse_y

        scale_x = self.pdf_width / self.widget_width if self.widget_width > 0 else 1.0
        scale_y = self.pdf_height / self.widget_height if self.widget_height > 0 else 1.0

        pdf_x = mouse_x * scale_x
        pdf_y = mouse_y * scale_y

        pdf_x /= self.current_zoom
        pdf_y /= self.current_zoom

        center_x = self.pdf_width / (2 * self.current_zoom)
        center_y = self.pdf_height / (2 * self.current_zoom)

        rel_x = pdf_x - center_x
        rel_y = pdf_y - center_y

        angle = -math.radians(self.current_rotation)
        rotated_x = rel_x * math.cos(angle) - rel_y * math.sin(angle)
        rotated_y = rel_x * math.sin(angle) + rel_y * math.cos(angle)

        return rotated_x + center_x, rotated_y + center_y

    def _pdf_to_widget_coords(self, pdf_x, pdf_y):
        if self.pdf_width == 0 or self.pdf_height == 0:
            return pdf_x, pdf_y

        center_x = self.pdf_width / (2 * self.current_zoom)
        center_y = self.pdf_height / (2 * self.current_zoom)

        rel_x = pdf_x - center_x
        rel_y = pdf_y - center_y

        angle = math.radians(self.current_rotation)
        rotated_x = rel_x * math.cos(angle) - rel_y * math.sin(angle)
        rotated_y = rel_x * math.sin(angle) + rel_y * math.cos(angle)

        rotated_x += center_x
        rotated_y += center_y

        zoomed_x = rotated_x * self.current_zoom
        zoomed_y = rotated_y * self.current_zoom

        scale_x = self.widget_width / self.pdf_width if self.pdf_width > 0 else 1.0
        scale_y = self.widget_height / self.pdf_height if self.pdf_height > 0 else 1.0

        widget_x = zoomed_x * scale_x
        widget_y = zoomed_y * scale_y

        return widget_x, widget_y

    def on_button_press(self, widget, event):
        x, y = self._mouse_to_pdf_coords(event.x, event.y)
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
                if self.dragging_enabled:
                    self.selected_annotation = None
                    for ann in reversed(self.annotations):
                        if ann.contains_point(x, y):
                            self.selected_annotation = ann
                            self.dragging_annotation = True
                            self.drag_start_pdf = (x, y)
                            break
                    self.queue_draw()
                else:
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
        elif self.dragging_enabled and self.dragging_annotation:
            self.dragging_annotation = False
            self.drag_start_pdf = None
            if self.on_annotation_changed:
                self.on_annotation_changed()

    def on_motion_notify(self, widget, event):
        if self.drawing_enabled and self.drawing:
            x, y = self._mouse_to_pdf_coords(event.x, event.y)
            self.current_line.append((x, y))
            self.queue_draw()
        elif self.dragging_enabled and self.dragging_annotation and self.selected_annotation:
            x, y = self._mouse_to_pdf_coords(event.x, event.y)
            dx = x - self.drag_start_pdf[0]
            dy = y - self.drag_start_pdf[1]
            moved_points = [(px + dx, py + dy) for (px, py) in self.selected_annotation.points]
            self.selected_annotation.points = moved_points
            self.drag_start_pdf = (x, y)
            self.queue_draw()

    def on_draw(self, widget, cr):
        cr.set_line_width(2)

        for ann in self.annotations:
            cr.set_source_rgba(ann.color.red, ann.color.green, ann.color.blue, ann.color.alpha)
            pts = ann.points
            if len(pts) > 1:
                wx, wy = self._pdf_to_widget_coords(*pts[0])
                cr.move_to(wx, wy)
                for p in pts[1:]:
                    wx, wy = self._pdf_to_widget_coords(*p)
                    cr.line_to(wx, wy)
                cr.stroke()

        if self.drawing and len(self.current_line) > 1:
            cr.set_source_rgba(self.current_color.red, self.current_color.green,
                               self.current_color.blue, self.current_color.alpha)
            wx, wy = self._pdf_to_widget_coords(*self.current_line[0])
            cr.move_to(wx, wy)
            for p in self.current_line[1:]:
                wx, wy = self._pdf_to_widget_coords(*p)
                cr.line_to(wx, wy)
            cr.stroke()

        if self.selected_annotation:
            bbox = self.selected_annotation.get_bounding_box()
            if bbox[2] > 0 and bbox[3] > 0:
                x1, y1 = self._pdf_to_widget_coords(bbox[0], bbox[1])
                x2, y2 = self._pdf_to_widget_coords(bbox[0] + bbox[2], bbox[1] + bbox[3])

                cr.set_source_rgba(0, 0, 1, 0.5)
                cr.set_line_width(3)
                cr.rectangle(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
                cr.stroke()

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
            color_dict = ann.get("color", {"red": 1, "green": 0, "blue": 0, "alpha": 1})
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
