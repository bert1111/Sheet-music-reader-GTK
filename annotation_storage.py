import json
import os

class AnnotationStorage:
    def __init__(self, filename='annotations.json'):
        self.filename = filename
        self.data = {}
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"Error loading annotations: {e}")
                self.data = {}
        else:
            self.data = {}

    def save(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving annotations: {e}")

    def get(self, filepath, page_number):
        key = f"{filepath}:{page_number}"
        return self.data.get(key, [])

    def set(self, filepath, page_number, annotations):
        key = f"{filepath}:{page_number}"
        self.data[key] = annotations
