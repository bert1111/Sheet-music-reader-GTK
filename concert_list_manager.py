#concert_list_manager.py
import json
import os

class ConcertListManager:
    def __init__(self, storage_file='concert_list.json'):
        self.storage_file = storage_file
        self.concert_list = []
        self.load()

    def load(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    self.concert_list = json.load(f)
            except Exception as e:
                print(f"Error loading concert list: {e}")
                self.concert_list = []
        else:
            self.concert_list = []

    def save(self):
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.concert_list, f, indent=4)
        except Exception as e:
            print(f"Error saving concert list: {e}")

    def set_list(self, pdf_paths):
        self.concert_list = pdf_paths

    def get_list(self):
        return self.concert_list

    def move_item(self, old_index, new_index):
        if 0 <= old_index < len(self.concert_list) and 0 <= new_index < len(self.concert_list):
            item = self.concert_list.pop(old_index)
            self.concert_list.insert(new_index, item)
            self.save()

    def remove_item(self, index):
        if 0 <= index < len(self.concert_list):
            self.concert_list.pop(index)
            self.save()
