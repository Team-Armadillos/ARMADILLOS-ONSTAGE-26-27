"""EDIT THIS FILE to customize the Padrinhos Magicos show.

The source documents do not define the final timeline. The sample scenes below
are manually selectable; no narrative order is assumed.
"""

MEDIA = {
    "initial": "videos/VIDEO_INICIAL.mp4",
    "collapse": "videos/fairy_colapso.mp4",
    "magic_fountain": "videos/fonte_magia.mp4",
    "fairy_off": "videos/fairy_apagada.mp4",
    "suspended": "videos/padrinhos_suspensos.mp4",
    "returned": "videos/padrinhos_devolvidos.mp4",
    "big_fairy": "videos/big_fairy.mp4",
    "fairy_saved": "images/fairy_salvo.png",
}

# Edit/add scene names and media keys here.
SCENES = {
    "initial": {"video":"initial"},
    "collapse": {"video":"collapse"},
    "magic_fountain": {"video":"magic_fountain"},
    "fairy_off": {"video":"fairy_off"},
    "suspended": {"video":"suspended"},
    "returned": {"video":"returned"},
    "big_fairy": {"video":"big_fairy"},
    "fairy_saved": {"image":"fairy_saved"},
    "camera": {"camera":True,"ai":False},
    "recognition": {"camera":True,"ai":True},
    "black": {},
}

# Each trigger is evaluated against event name, optional data and current state.
# Actions: scene, image, video, audio, music, stop_audio, signal,
#          state, camera, recognition, layer, clear_layers, delay_event.
TRIGGERS = [
    # Example: receiving SIGNAL:1 selects the initial scene.
    {"event":"signal", "data":{"value":1}, "actions":[{"type":"scene","name":"initial"}]},
    # Example conditional trigger (uncomment and adapt when the choreography is known):
    # {"event":"wand_detected", "when":{"scene":"fairy_off","godparents_off":True},
    #  "actions":[{"type":"scene","name":"fairy_saved"}]},
]

# Map your trained model's exact label names to presentation events here.
AI_LABEL_EVENTS = {
    # "magic_wand": "wand_detected",
}

INITIAL_SCENE = "black"  # Change to "initial" to start the video immediately.
