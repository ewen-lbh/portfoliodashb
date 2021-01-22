import sys

class ProgressBar:
    total: int
    progress: int
    text: str
    width: int

    def __init__(self, total: int, width: int = 200, text: str = ""):
        self.progress = 0
        self.width = width
        self.total = total
        self.text = text
        print("")
        self._render()
    
    def advance(self, by: int = 1):
        self.progress += by
        self._render()
    
    def reset(self):
        self.progress = 0
        self._render()

    def _render(self):
        cells_filled = int(self.progress/self.total * self.width)
        cells_empty = int((self.total - self.progress)/self.total * self.width)
        print(f"\33[2K\r{self.progress/self.total*100:>3.0f}% [{'#' * cells_filled}{' ' * cells_empty}] {self.text}", end="")
    
    def print(self, text: str, *args, **kwargs):
        print("\33[2K\r" + text, end=kwargs.get("end", "") + "\n", *args, **kwargs)
        self._render()
