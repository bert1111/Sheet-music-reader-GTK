class PageNavigator:
    def __init__(self):
        self.current_page = 0
        self.total_pages = 0

    def set_total_pages(self, total):
        self.total_pages = total
        self.current_page = 0

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
        return self.current_page

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
        return self.current_page
