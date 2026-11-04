"""EDIT ONLY THIS FILE to organize your Padrinhos Magicos show.

The functions below execute sequentially, like a SPIKE Prime program.
Playback continues while the choreography waits for a timer or a signal.
"""
from application import Application


def main(stage):

    stage.video("VIDEO_INICIAL.mp4", vezes=1, camada="background")
    stage.esperar_video("background")

    stage.video("fairy_colapso.mp4", vezes=None, camada="background")

    stage.esperar_ble(1)

    stage.video("fonte_magia.mp4", vezes=1, camada="background")
    stage.esperar_video("background")

    print("SIGNAL RECEIVED!")



if __name__ == "__main__":
    Application(choreography=main).run()
