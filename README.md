# Extended Stage — SESI Armadillos / Padrinhos Magicos

Python-based modular multimedia show controller. The application and source comments are in English.

## Setup (Windows / Python 3.10+)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

If using a trained YOLO model: `pip install ultralytics` and set `ai.model` in `config/settings.json` to a relative path such as `models/best.pt`.

## Media

Place these files under `assets/videos/`: `VIDEO_INICIAL.mp4`, `fairy_colapso.mp4`, `fonte_magia.mp4`, `fairy_apagada.mp4`, `padrinhos_suspensos.mp4`, `padrinhos_devolvidos.mp4`, `big_fairy.mp4`.

Place `fairy_salvo.png` under `assets/images/`. Media files are not bundled. The exact filenames are mapped in `presentation/my_project.py`.

## Edit the show

- Edit **`main.py`** to define the sequence of media, repetitions, layers, waits and signal triggers, using `def main(stage):`.
- `modules/script_controller.py` exposes `stage.video`, `stage.imagem`, `stage.esperar_video`, `stage.wait`, `stage.esperar_ble`, `stage.enviar_ble`, `stage.remover`, `stage.limpar` and `stage.cena`.
- `presentation/my_project.py` retains legacy scene aliases, events and triggers.
- Edit `config/settings.json`: monitor index (zero-based), fullscreen, camera, audio output, BLE, serial, AI model.
- Use `config/scenes.json` and `config/triggers.json` for optional overrides and additional rules.
- MP4 audio is automatically extracted and played with its video. There is no need to export soundtracks manually.

## Video performance and fullscreen sizing

- Video decoding runs on a separate worker thread, and Pygame scales frames directly.
- In `config/settings.json`, `"video_fit": "cover"` fills the screen **without stretching** and crops some edges when the source aspect ratio differs from the monitor. `"contain"` shows the entire video with black bars; `"stretch"` fills the screen but can distort the picture.
- Use `"scale_quality": "fast"` for higher FPS; `"smooth"` for better resizing quality on fast computers.
- `"monitor": 0` selects the first display and `"fullscreen": true` uses fullscreen mode.
- Videos must already be encoded at practical resolutions and rates (e.g. 1920x1080, 30 fps). 4K/60 may still be slow on low-powered computers. Audio is decoded separately using FFmpeg and played through pygame mixer.
- The source videos are not included. These improvements require testing with the actual MP4 files and performance hardware.

## Terminal controls

Run `python main.py`: the `main(stage)` choreography now starts automatically. You can also enter commands into the same terminal:

```text
help
scenes
scene initial
scene fairy_saved
play collapse
image fairy_saved
signal 1
event wand_detected
set godparents_off true
status
restart
pause
resume
stop
quit
```

Use `signal 1` to test the example trigger without any hardware. Terminal commands are processed on the render thread through the event queue. Press ESC in the output window to close.

## Layer example

Add a scene with a list of `layers` using `{ "name":"frame", "media":"fairy_saved", "x":0.1, "y":0.1, "width":0.8, "height":0.8, "opacity":0.7, "z":5 }`. Coordinates are normalized 0..1. PNG alpha is preserved.

## Communication

BLE scanning supports Pybricks-style manufacturer advertisements with company ID `0x0397`, channel `4`, bytes `[channel, 0x00, 0x61, signed_value]`. Enable BLE in settings. Signal events include a source/device address when supplied. Bluetooth scanning depends on host hardware and permissions.

The serial bridge reads newline-delimited `SIGNAL:3` or `EVENT:wand_detected`. Sending `SIGNAL:3` over serial is supported when a bridge is configured. **Direct BLE advertising/transmission and ESP-NOW are not implemented**: ESP-NOW requires a compatible intermediary; native BLE advertising on Windows needs a separate backend. Do not assume the serial bridge broadcasts BLE without bridge firmware.

## AI

The trained model and its class labels are not supplied. The optional YOLO adapter loads a user-provided model, runs inference asynchronously and emits `ai_detection` events. Map exact model labels in `AI_LABEL_EVENTS`. Use `event wand_detected` for a manual test. Camera preview is fullscreen in the `camera` and `recognition` scenes. AI load failures are logged and do not intentionally terminate the presentation.

## Logs and tests

Runtime logs: `logs/extended_stage.log`. Run `python -m unittest discover -s tests -v` for logic-only tests. Validate video codecs, monitor placement, sound output, BLE and camera on the actual performance PC. No hardware integration or live performance test has been performed here.

## Current limitations

This is a functional starter implementation, not a validated production deployment. MP4 embedded audio is extracted to OGG on first playback and starts together with video; precise frame-level lip-sync is not guaranteed. Direct BLE transmission, ESP-NOW and the real trained model require additional integration. High-resolution video decoding, audio/video synchronization, camera latency, fullscreen multi-monitor behavior and real devices require on-site testing.

## Embedded MP4 audio (enabled by default)

The video decoder uses OpenCV for frames and the `VideoAudioManager` uses FFmpeg (installed through `imageio-ffmpeg`) to extract an MP4's embedded audio on first playback. The OGG soundtrack is cached in `assets/audio/.video_cache/`, and the audio and video are started together. Subsequent playback reuses that cache, until the original MP4 file changes. This saves CPU during the performance. The first play of a long MP4 may take some time while the soundtrack is prepared; pre-run every scene before the show. MP4 files without an audio stream remain silent.

Settings in `config/settings.json`:

- `"video_audio_enabled": true`: enable/disable original MP4 sound.
- `"video_volume": 1.0`: volume from 0.0 to 1.0.
- `"audio_device": null`: use the Windows default playback device.

`pause`, `resume`, `stop`, and scene changes also control the video soundtrack. The original sound is played on pygame's music channel; independently scheduled `music` actions use that same channel and can replace MP4 audio, while ordinary sound effects (`audio` actions) play on separate mixer channels. For simultaneous background music and MP4 audio, a dedicated multi-track mixer must be added. This starter approximates A/V synchronization at start, but does not implement continuous clock drift correction.

Install the added audio extraction dependency when upgrading from the previous ZIP:

```powershell
python -m pip install -r requirements.txt
```

## Scripted show example

```python
def main(stage):
    stage.video("VIDEO_INICIAL.mp4", vezes=1, camada="background")
    stage.esperar_video("background")
    stage.video("fonte_magia.mp4", vezes=None, camada="background")
    stage.imagem("fairy_salvo.png", camada="overlay", x=0.6, y=0.1, largura=0.3, altura=0.5, z=10)
    stage.wait(2000)
    stage.remover("overlay")
```

A layer can have independent media, and multiple videos can be displayed, but the embedded MP4 audio system plays only one original soundtrack at a time. Signal tests can be simulated from the terminal (`signal 1`). BLE transmission requires an implemented/configured serial bridge. Source media assets are not bundled.
