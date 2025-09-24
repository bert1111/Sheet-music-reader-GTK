#page_settings.py
import json
import os

class PageSettings:
    def __init__(self, filename='page_settings.json'):
        self.filename = filename
        self.settings = {}
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    self.settings = json.load(f)
            except Exception as e:
                print(f"Fout bij laden instellingen: {e}")
                self.settings = {}
        else:
            self.settings = {}

    def save(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Fout bij opslaan instellingen: {e}")

    def get(self, filepath, page_number):
        # Geef default waardes mét scrollposities terug
        return self.settings.get(filepath, {}).get(str(page_number), {
            "zoom": 1.0,
            "rotation": 0,
            "scroll_x": 0,
            "scroll_y": 0
        })

    def set(self, filepath, page_number, zoom, rotation, scroll_x=0, scroll_y=0):
        if filepath not in self.settings:
            self.settings[filepath] = {}
        existing = self.settings[filepath].get(str(page_number), {})
        existing.update({
            "zoom": zoom,
            "rotation": rotation,
            "scroll_x": scroll_x,
            "scroll_y": scroll_y
        })
        self.settings[filepath][str(page_number)] = existing
