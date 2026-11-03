"""EDIT ONLY THIS FILE to organize your Padrinhos Magicos show.

The functions below execute sequentially, like a SPIKE Prime program.
Playback continues while the choreography waits for a timer or a signal.
"""
from application import Application


def main(stage):
    # ========================================================
    # INTRODUCTION
    # ========================================================
    stage.video("VIDEO_INICIAL.mp4", vezes=1, camada="background")
    stage.esperar_video("background")

    # ========================================================
    # FAIRY COLLAPSE
    # ========================================================
    stage.video("fairy_colapso.mp4", vezes=1, camada="background")
    stage.esperar_video("background")

    # ========================================================
    # EXAMPLE: OVERLAY + REPEATED VIDEO
    # ========================================================
    stage.video("fonte_magia.mp4", vezes=2, camada="background")
    stage.imagem("fairy_salvo.png", camada="overlay", x=0.65,
                 y=0.05, largura=0.3, altura=0.4, z=10)
    stage.esperar_video("background")
    stage.remover("overlay")

    # ========================================================
    # EXAMPLE: WAIT FOR A SIGNAL BEFORE CONTINUING
    # Uncomment after the robot communication is configured.
    # ========================================================
    # stage.esperar_ble(1)
    # stage.video("fairy_apagada.mp4", vezes=None, camada="background")
    # stage.wait(2000)
    # stage.remover("background")

    # ========================================================
    # FINAL IMAGE
    # ========================================================
    stage.imagem("fairy_salvo.png", camada="background")
    print("SHOW FINISHED")


if __name__ == "__main__":
    Application(choreography=main).run()
