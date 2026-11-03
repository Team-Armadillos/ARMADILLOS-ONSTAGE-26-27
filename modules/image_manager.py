"""RGBA image loading."""
from PIL import Image
class ImageManager:
    def load(self,path):
        with Image.open(path) as image: return image.convert("RGBA")
