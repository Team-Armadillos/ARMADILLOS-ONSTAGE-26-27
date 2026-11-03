"""Extended Stage runtime: scenes, layered video, audio and show scripting."""
import json
import logging
import threading
import time
from pathlib import Path

import pygame

from core.event_manager import EventManager
from core.state_manager import StateManager
from core.trigger_manager import TriggerManager
from core.scene_manager import SceneManager
from modules.image_manager import ImageManager
from modules.layer_manager import LayerManager
from modules.video_manager import VideoManager
from modules.audio_manager import AudioManager
from modules.video_audio_manager import VideoAudioManager
from modules.camera_manager import CameraManager
from modules.ai_manager import AIManager
from modules.display_manager import DisplayManager
from modules.led_manager import LEDManager
from modules.script_controller import ScriptController
from communication.ble_manager import BLEManager
from communication.serial_manager import SerialManager
from presentation import my_project as show
from modules.window_console import WindowConsole

ROOT = Path(__file__).resolve().parent


class Application:
    def __init__(self, choreography=None):
        self.settings = json.loads((ROOT / "config/settings.json").read_text(encoding="utf-8"))
        (ROOT / "logs").mkdir(exist_ok=True)
        logging.basicConfig(
            filename=ROOT / "logs/extended_stage.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )

        self.events = EventManager()
        self.state = StateManager()
        self.images = ImageManager()
        self.layers = LayerManager()
        self.video = VideoManager()  # Legacy scene video
        self.audio = AudioManager(self.settings.get("audio_device"))
        self.video_audio = VideoAudioManager(
            ROOT / "assets/audio/.video_cache",
            self.settings.get("video_audio_enabled", True),
            self.settings.get("video_volume", 1.0),
        )
        self.camera = CameraManager(self.settings["camera_index"])
        ai_settings = self.settings["ai"]
        model = ROOT / "assets" / ai_settings["model"] if ai_settings.get("model") else None
        self.ai = AIManager(model, ai_settings["confidence"])

        self.display = None
        self.ble = None
        self.serial = None
        self.running = True
        self.window_console = WindowConsole(self.command)
        self.camera_active = False
        self.recognition = False
        self.last_ai = 0
        self.current_image = None
        self.timers = []

        self.script = ScriptController()
        self.choreography = choreography
        self.script_videos = {}  # layer name -> playback metadata
        self.script_audio_layer = None  # One embedded MP4 soundtrack at a time

        self.trigger = TriggerManager(self.state, self.action)
        self.scene = SceneManager(self.state, self.apply_scene)
        self.scene.configure({
            **show.SCENES,
            **self._config("scenes.json").get("scenes", {}),
        })
        for rule in show.TRIGGERS + self._config("triggers.json").get("triggers", []):
            self.trigger.add(rule)
        self.events.subscribe(self.on_event)
        self.events.subscribe(self._terminal_event)
        self.led = LEDManager(self.send_signal)
        self._start_communications()

    def _config(self, filename):
        return json.loads((ROOT / "config" / filename).read_text(encoding="utf-8"))

    def media(self, name):
        """Accept a registered alias, relative asset name, or absolute file path."""
        relative = show.MEDIA.get(name, name)
        path = Path(relative)
        options = ([path] if path.is_absolute() else [
            ROOT / "assets" / path,
            ROOT / "assets/videos" / path,
            ROOT / "assets/images" / path,
            ROOT / "assets/audio" / path,
        ])
        for option in options:
            if option.is_file():
                return option
        raise FileNotFoundError(f"Media not found: {name} (searched: {options})")

    def _start_communications(self):
        cfg = self.settings["ble"]
        if cfg.get("enabled"):
            try:
                self.ble = BLEManager(self.events.emit, cfg["channel"], cfg["company_id"])
                self.ble.start()
                self.state.set("ble", True)
            except Exception:
                logging.exception("BLE initialization failed")
        cfg = self.settings["serial"]
        if cfg.get("enabled"):
            try:
                self.serial = SerialManager(cfg["port"], cfg["baudrate"], self.events.emit)
                self.serial.start()
                self.state.set("serial", True)
            except Exception:
                logging.exception("Serial initialization failed")

    def send_signal(self, value):
        """Existing outgoing serial bridge, not direct computer BLE broadcast."""
        if self.serial:
            self.serial.send(f"SIGNAL:{int(value)}")
        else:
            print(f"[COMM] Signal {value} not sent: configure serial bridge first")

    def on_event(self, event):
        logging.info("EVENT %s source=%s data=%s", event.name, event.source, event.data)
        if event.name != "terminal_command":
            print(f"[EVENT] {event.name} from {event.source}: {event.data}")
        if event.name == "signal":
            self.script.notify_signal(event.data.get("value"))
        self.trigger.handle(event)

    def play_video(self, key):
        """Legacy scene video with its original soundtrack."""
        path = self.media(key)
        soundtrack = self.video_audio.prepare(path)
        self.video_audio.stop()
        self.video.play(path)
        self.video_audio.play_prepared(soundtrack)
        self.script_audio_layer = None

    def _stop_script_video(self, layer, keep_frame=False):
        item = self.script_videos.pop(layer, None)
        if item is not None:
            item["player"].stop(keep_frame=keep_frame)
            self.script.finish_video(layer)
        if self.script_audio_layer == layer:
            self.video_audio.stop()
            self.script_audio_layer = None

    def _clear_script_media(self):
        for layer in list(self.script_videos):
            self._stop_script_video(layer)
        for name in list(self.layers.layers):
            if name.startswith("__script_") or name == "__base__":
                self.layers.remove(name)

    @staticmethod
    def _layer_name(name):
        return "__base__" if name == "background" else "__script_" + name

    def _set_script_layer(self, name, image, cfg):
        self.layers.set(
            self._layer_name(name), image,
            x=cfg["x"], y=cfg["y"],
            width=cfg["largura"], height=cfg["altura"],
            z=cfg["z"], opacity=cfg["opacidade"], visible=True,
        )

    def _script_action(self, command, **data):
        if command == "video":
            layer = data["camada"]
            path = self.media(data["file"])
            soundtrack = self.video_audio.prepare(path) if data["som"] else None
            self._stop_script_video(layer)
            self.video.stop()
            self.current_image = None
            self.script.new_video(layer)
            player = VideoManager()
            try:
                player.play(path)
            except Exception:
                self.script.finish_video(layer)
                raise
            self.script_videos[layer] = {
                "player": player, "file": path, "remaining": data["vezes"],
                "soundtrack": soundtrack, "sound": data["som"],
                "config": data,
            }
            self.layers.remove(self._layer_name(layer))
            if data["som"]:
                # Pygame mixer.music has one stream: the latest audible MP4 wins.
                self.video_audio.stop()
                self.video_audio.play_prepared(soundtrack)
                self.script_audio_layer = layer
            print(f"[SCRIPT] Video {path.name} on {layer}, repeats={data['vezes']}")
            return

        if command == "image":
            layer = data["camada"]
            self._stop_script_video(layer)
            image = self.images.load(self.media(data["file"]))
            self._set_script_layer(layer, image, data)
            print(f"[SCRIPT] Image {data['file']} on {layer}")
            return

        if command == "remove":
            self._stop_script_video(data["camada"])
            self.layers.remove(self._layer_name(data["camada"]))
            return

        if command == "clear":
            self._clear_script_media()
            self.layers.clear()
            return

        if command == "scene":
            self.scene.go(data["nome"])
            return

        if command == "signal":
            self.send_signal(data["sinal"])
            return

        raise ValueError(f"Unknown script command: {command}")

    def _update_script_videos(self):
        for layer, item in list(self.script_videos.items()):
            if self.script_videos.get(layer) is not item:
                continue
            player = item["player"]
            frame = player.update()
            if frame is not None:
                self._set_script_layer(layer, frame, item["config"])
            if not player.finished:
                continue
            left = item["remaining"]
            if left is None or left > 1:
                if left is not None:
                    item["remaining"] -= 1
                player.play(item["file"])
                if item["sound"] and self.script_audio_layer == layer:
                    self.video_audio.play_prepared(item["soundtrack"])
                continue
            # Keep the last frame onscreen until the next script command.
            self._stop_script_video(layer, keep_frame=True)
            print(f"[SCRIPT] Video finished on {layer}")

    def apply_scene(self, definition):
        self._clear_script_media()
        self.video_audio.stop()
        self.video.stop()
        self.layers.clear()
        self.current_image = None
        self.camera_active = bool(definition.get("camera", False))
        self.recognition = bool(definition.get("ai", False))
        if self.camera_active:
            try:
                self.camera.start()
                self.state.set("camera", True)
            except Exception as exc:
                logging.exception("Camera failed")
                print("[CAMERA ERROR]", exc)
                self.camera_active = False
        else:
            self.camera.stop()
            self.state.set("camera", False)
        self.state.set("ai", self.recognition)
        if self.recognition:
            try:
                if self.ai.model is None:
                    self.ai.load()
            except Exception as exc:
                logging.exception("AI unavailable")
                print("[AI ERROR]", exc)
                self.recognition = False
        if "image" in definition:
            try:
                self.current_image = self.images.load(self.media(definition["image"]))
            except Exception:
                logging.exception("Scene image failed")
        if "video" in definition:
            try:
                self.play_video(definition["video"])
            except Exception:
                logging.exception("Scene video failed")
        for layer in definition.get("layers", []):
            self.action({"type": "layer", **layer})
        for action in definition.get("on_enter", []):
            self.action(action)
        print("[SCENE]", self.state.get("scene"))

    def action(self, a):
        try:
            kind = a["type"]
            if kind == "scene":
                self.scene.go(a["name"])
            elif kind == "image":
                self.current_image = self.images.load(self.media(a["name"]))
                self.video_audio.stop()
                self.video.stop()
            elif kind == "video":
                self.play_video(a["name"])
                self.current_image = None
            elif kind == "audio":
                self.audio.play(self.media(a["name"]), a.get("volume", 1), a.get("loop", False))
            elif kind == "music":
                self.audio.music(self.media(a["name"]), a.get("volume", 1), a.get("loop", False))
            elif kind == "stop_audio":
                self.audio.stop()
            elif kind == "signal":
                self.led.effect(a["value"])
            elif kind == "state":
                self.state.set(a["key"], a["value"])
            elif kind == "camera":
                self.camera_active = bool(a["enabled"])
                self.camera.start() if self.camera_active else self.camera.stop()
                self.state.set("camera", self.camera_active)
            elif kind == "recognition":
                self.recognition = bool(a["enabled"])
                self.state.set("ai", self.recognition)
                if self.recognition and self.ai.model is None:
                    self.ai.load()
            elif kind == "layer":
                self.layers.set(
                    a["name"], self.images.load(self.media(a["media"])),
                    x=a.get("x", 0), y=a.get("y", 0),
                    width=a.get("width", 1), height=a.get("height", 1),
                    z=a.get("z", 0), opacity=a.get("opacity", 1),
                    visible=a.get("visible", True),
                )
            elif kind == "clear_layers":
                self.layers.clear()
            elif kind == "delay_event":
                self.timers.append((
                    time.monotonic() + float(a["seconds"]),
                    a["event"], a.get("data", {}),
                ))
            else:
                raise ValueError(f"Unknown action: {kind}")
        except Exception as exc:
            logging.exception("Action failed: %s", a)
            print("[ERROR]", exc)

    def command(self, line):
        parts = line.strip().split()
        if not parts:
            return
        cmd = parts[0].lower()
        try:
            if cmd == "help":
                print("help | scenes | scene NAME | restart | play KEY | image KEY | "
                      "signal N | event NAME | set KEY JSON | status | "
                      "pause | resume | stop | quit")
            elif cmd == "scenes":
                print(", ".join(self.scene.scenes))
            elif cmd == "scene":
                self.scene.go(parts[1])
            elif cmd == "restart":
                self.scene.restart()
            elif cmd == "play":
                self.action({"type": "video", "name": parts[1]})
            elif cmd == "image":
                self.action({"type": "image", "name": parts[1]})
            elif cmd == "signal":
                self.events.emit("signal", {"value": int(parts[1])}, "terminal")
            elif cmd == "event":
                self.events.emit(parts[1], {}, "terminal")
            elif cmd == "set":
                self.state.set(parts[1], json.loads(" ".join(parts[2:])))
            elif cmd == "status":
                print("STATE:", self.state.values, "SCRIPT VIDEOS:",
                      {k: v["file"].name for k, v in self.script_videos.items()},
                      "LAST EVENTS:", [(e.name, e.data) for e in self.events.history[-5:]])
            elif cmd == "pause":
                self.video.pause()
                for item in self.script_videos.values():
                    item["player"].pause()
                self.video_audio.pause()
            elif cmd == "resume":
                self.video.resume()
                for item in self.script_videos.values():
                    item["player"].resume()
                self.video_audio.resume()
            elif cmd == "stop":
                self._clear_script_media()
                self.video_audio.stop()
                self.video.stop()
                self.audio.stop()
            elif cmd == "quit":
                self.running = False
            else:
                print("Unknown command. Type help.")
        except Exception as exc:
            print("[COMMAND ERROR]", exc)

    def _terminal(self):
        while self.running:
            try:
                line = input()
            except (EOFError, OSError):
                break
            self.events.emit("terminal_command", {"line": line}, "terminal")

    def _terminal_event(self, event):
        if event.name == "terminal_command":
            self.command(event.data["line"])

    def run(self):
        try:
            self.display = DisplayManager(
                self.settings["monitor"], self.settings["fullscreen"],
                self.settings.get("video_fit", "cover"),
                self.settings.get("scale_quality", "fast"),
            )
            threading.Thread(target=self._terminal, daemon=True).start()
            self.scene.go(self.settings.get("start_scene") or show.INITIAL_SCENE)
            clock = pygame.time.Clock()
            print("Extended Stage running. Type help in terminal.")
            self.script.start(self.choreography)
            while self.running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        continue

                    # The on-screen console processes keyboard input first.
                    if self.window_console.handle(event):
                        continue

                    # Escape closes the application only when
                    # the command console is not active.
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.running = False

                now = time.monotonic()
                ready = [t for t in self.timers if t[0] <= now]
                self.timers = [t for t in self.timers if t[0] > now]
                for _, name, data in ready:
                    self.events.emit(name, data, "timer")
                self.events.drain()
                self.script.process_requests(self._script_action)

                # Update scene visuals, camera and inference.
                frame = None
                if self.camera_active:
                    frame = self.camera.frame()
                    if (self.recognition and frame is not None and
                            now - self.last_ai >= self.settings["ai"]["interval_seconds"]):
                        self.ai.submit(frame)
                        self.last_ai = now
                elif self.video.capture is not None:
                    frame = self.video.update()
                    if self.video.finished:
                        self.video.finished = False
                        self.events.emit("video_finished", {"scene": self.state.get("scene")})
                elif self.current_image is not None:
                    frame = self.current_image

                if self.recognition:
                    try:
                        results = self.ai.poll()
                        if results is not None:
                            for detection in results:
                                self.events.emit("ai_detection", detection, "ai")
                                event_name = show.AI_LABEL_EVENTS.get(detection["label"])
                                if event_name:
                                    self.events.emit(event_name, detection, "ai")
                    except Exception:
                        logging.exception("AI inference failed")

                if frame is not None:
                    self.layers.set("__base__", frame, z=-100)
                elif "background" not in self.script_videos and "__base__" not in [
                        self._layer_name(k) for k in self.script._video_done]:
                    # No legacy picture and no scripted background.
                    self.layers.remove("__base__")

                self._update_script_videos()
                self.display.render_layers(self.layers.layers)
                self.window_console.draw()
                clock.tick(self.settings["fps"])
        finally:
            self.close()

    def close(self):
        self.window_console.close()
        self.running = False
        self.script.stop()
        self._clear_script_media()
        if self.ble:
            self.ble.close()
        if self.serial:
            self.serial.close()
        self.camera.stop()
        self.video_audio.stop()
        self.video.stop()
        self.audio.close()
        self.ai.close()
        if self.display:
            self.display.close()
