"""Render media directly with Pygame, without full-screen Pillow recomposition."""
import pygame
from PIL import Image


class DisplayManager:
    def __init__(self, monitor=0, fullscreen=True, fit="cover", scale_quality="fast"):
        pygame.display.init()
        sizes = pygame.display.get_desktop_sizes()
        if monitor < 0 or monitor >= len(sizes):
            raise ValueError(f"Monitor {monitor} not available. Available: {list(enumerate(sizes))}")
        self.width, self.height = sizes[monitor]
        self.fit = fit
        self.scale_quality = scale_quality
        if fit not in ("cover", "contain", "stretch"):
            raise ValueError("video_fit must be cover, contain or stretch")
        if scale_quality not in ("fast", "smooth"):
            raise ValueError("scale_quality must be fast or smooth")
        flags = pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE
        self.screen = pygame.display.set_mode((self.width, self.height), flags, display=monitor)
        pygame.display.set_caption("Extended Stage - Padrinhos Magicos")
        self._static_cache = {}

    @staticmethod
    def _surface(image):
        # OpenCV video frames are RGB numpy arrays; PIL images preserve PNG alpha.
        if isinstance(image, Image.Image):
            rgba = image.convert("RGBA")
            return pygame.image.fromstring(rgba.tobytes(), rgba.size, "RGBA")
        h, w = image.shape[:2]
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("Expected an RGB video frame")
        return pygame.image.fromstring(image.tobytes(), (w, h), "RGB")

    def _scaled(self, surface, size):
        if surface.get_size() == size:
            return surface
        if self.scale_quality == "smooth":
            return pygame.transform.smoothscale(surface, size)
        return pygame.transform.scale(surface, size)

    def _draw_fitted(self, surface):
        w, h = surface.get_size()
        sw, sh = self.screen.get_size()
        if self.fit == "stretch":
            output = self._scaled(surface, (sw, sh))
            self.screen.blit(output, (0, 0))
            return
        factor = max(sw / w, sh / h) if self.fit == "cover" else min(sw / w, sh / h)
        output_w, output_h = max(1, round(w * factor)), max(1, round(h * factor))
        if self.fit == "cover" and (output_w > sw or output_h > sh):
            # Crop BEFORE scaling to avoid constructing a huge offscreen surface.
            crop_w, crop_h = min(w, round(sw / factor)), min(h, round(sh / factor))
            crop = pygame.Rect((w - crop_w) // 2, (h - crop_h) // 2, crop_w, crop_h)
            surface = surface.subsurface(crop)
            output_w, output_h = sw, sh
        result = self._scaled(surface, (output_w, output_h))
        self.screen.blit(result, ((sw - output_w) // 2, (sh - output_h) // 2))

    def render_layers(self, layers):
        self.screen.fill((0, 0, 0))
        sw, sh = self.screen.get_size()
        for name, layer in sorted(layers.items(), key=lambda pair: pair[1].z):
            if not layer.visible or layer.image is None or layer.opacity <= 0:
                continue
            image = layer.image
            # The base movie/camera/image covers the chosen output area.
            if name == "__base__":
                self._draw_fitted(self._surface(image))
                continue
            cache_key = (id(image), getattr(image, "size", None))
            surface = self._static_cache.get(cache_key)
            if surface is None:
                surface = self._surface(image)
                self._static_cache = {cache_key: surface} if len(self._static_cache) >= 32 else self._static_cache
                self._static_cache[cache_key] = surface
            size = (max(1, round(layer.width * sw)), max(1, round(layer.height * sh)))
            rendered = self._scaled(surface, size)
            if layer.opacity < 1:
                rendered = rendered.copy()
                rendered.set_alpha(round(layer.opacity * 255))
            self.screen.blit(rendered, (round(layer.x * sw), round(layer.y * sh)))
        pygame.display.flip()

    def close(self):
        pygame.display.quit()
