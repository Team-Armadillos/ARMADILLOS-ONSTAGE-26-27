"""Play an MP4's embedded audio alongside OpenCV-rendered video.

FFmpeg extracts the soundtrack once to a cached OGG file; pygame then plays
that audio without blocking the display loop. Source MP4s remain unchanged.
"""
import hashlib
import logging
from pathlib import Path
import subprocess

import imageio_ffmpeg
import pygame


class VideoAudioManager:
    def __init__(self, cache_dir, enabled=True, volume=1.0):
        self.cache_dir = Path(cache_dir)
        self.enabled = bool(enabled)
        self.volume = max(0.0, min(1.0, float(volume)))
        self.active = False

    def _cached_audio(self, video_path):
        video_path = Path(video_path).resolve()
        stat = video_path.stat()
        signature = f"{video_path}|{stat.st_size}|{stat.st_mtime_ns}"
        cache_key = hashlib.sha256(signature.encode('utf-8')).hexdigest()[:20]
        target = self.cache_dir / f"{video_path.stem}_{cache_key}.ogg"
        if target.is_file() and target.stat().st_size:
            return target

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix('.part.ogg')
        print(f"[VIDEO AUDIO] Extracting soundtrack (first playback): {video_path.name}")
        # An optional audio stream avoids a hard failure for silent MP4 files.
        args = [imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error',
                '-nostdin', '-y', '-i', str(video_path), '-map', '0:a:0?', '-vn',
                '-c:a', 'libvorbis', '-q:a', '5', str(partial)]
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=180)
            if result.returncode:
                logging.warning('FFmpeg audio extraction failed: %s', result.stderr.strip())
                return None
            if not partial.is_file() or not partial.stat().st_size:
                logging.info('No soundtrack in %s', video_path.name)
                return None
            partial.replace(target)
            return target
        except (OSError, subprocess.TimeoutExpired) as exc:
            logging.warning('MP4 audio extraction unavailable: %s', exc)
            print(f'[VIDEO AUDIO] Audio extraction failed: {exc}')
            return None
        finally:
            partial.unlink(missing_ok=True)

    def prepare(self, path):
        """Prepare a soundtrack before starting the video clock."""
        if not self.enabled:
            return None
        return self._cached_audio(path)

    def play_prepared(self, soundtrack):
        self.stop()
        if soundtrack is None:
            return
        if not pygame.mixer.get_init():
            print('[VIDEO AUDIO] Audio output unavailable; check Windows sound settings.')
            return
        try:
            pygame.mixer.music.load(str(soundtrack))
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()
            self.active = True
        except pygame.error as exc:
            logging.exception('Cannot play MP4 soundtrack')
            print(f'[VIDEO AUDIO] Playback error: {exc}')

    def pause(self):
        if self.active:
            pygame.mixer.music.pause()

    def resume(self):
        if self.active:
            pygame.mixer.music.unpause()

    def stop(self):
        if self.active and pygame.mixer.get_init():
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except pygame.error:
                pass
        self.active = False
