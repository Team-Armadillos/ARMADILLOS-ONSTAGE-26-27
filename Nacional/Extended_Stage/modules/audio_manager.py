"""Concurrent sound effects and music through pygame mixer."""
import pygame
class AudioManager:
    def __init__(self,device=None):
        self.ready=False
        try:
            pygame.mixer.init(devicename=device) if device else pygame.mixer.init()
            pygame.mixer.set_num_channels(16);self.ready=True
        except Exception as exc: print(f"Audio unavailable: {exc}")
    def play(self,path,volume=1,loop=False):
        if not self.ready:return
        sound=pygame.mixer.Sound(str(path));sound.set_volume(float(volume));sound.play(loops=-1 if loop else 0)
    def music(self,path,volume=1,loop=False):
        if not self.ready:return
        pygame.mixer.music.load(str(path));pygame.mixer.music.set_volume(float(volume));pygame.mixer.music.play(-1 if loop else 0)
    def stop(self):
        if self.ready:pygame.mixer.stop();pygame.mixer.music.stop()
    def close(self):
        if self.ready:pygame.mixer.quit()
