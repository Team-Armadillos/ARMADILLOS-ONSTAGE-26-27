"""Thread-safe, sequential show scripting API.

The choreography runs in a worker thread. Multimedia changes are marshalled
onto the Pygame application thread, so delays never freeze the display.
"""
import logging
import queue
import threading


class ShowStopped(Exception):
    """Raised when the operator closes the show."""


class ScriptController:
    def __init__(self):
        self.requests = queue.Queue()
        self.stopping = threading.Event()
        self._lock = threading.Lock()
        self._video_done = {}
        self._signals = queue.Queue()
        self._thread = None

    def start(self, choreography):
        if choreography is None:
            return
        if self._thread and self._thread.is_alive():
            raise RuntimeError("The show script is already running")

        def worker():
            try:
                choreography(self)
                if not self.stopping.is_set():
                    print("[SCRIPT] Choreography completed")
            except ShowStopped:
                pass
            except Exception:
                logging.exception("Show script failed")
                print("[SCRIPT ERROR] See logs/extended_stage.log")

        self._thread = threading.Thread(target=worker, daemon=True, name="ShowScript")
        self._thread.start()

    def _request(self, command, **params):
        if self.stopping.is_set():
            raise ShowStopped()
        done = threading.Event()
        response = {}
        self.requests.put((command, params, done, response))
        while not done.wait(0.05):
            if self.stopping.is_set():
                raise ShowStopped()
        if "error" in response:
            raise response["error"]
        return response.get("result")

    def process_requests(self, handler, limit=30):
        """Run on the Pygame/main thread."""
        for _ in range(limit):
            try:
                command, args, done, response = self.requests.get_nowait()
            except queue.Empty:
                break
            try:
                response["result"] = handler(command, **args)
            except Exception as exc:
                response["error"] = exc
                logging.exception("Script command failed: %s", command)
            finally:
                done.set()

    def video(self, file, vezes=1, camada="background", som=True,
              x=0, y=0, largura=1, altura=1, z=0, opacidade=1):
        """Play MP4 (vezes=None means infinite loop). Nonblocking."""
        if vezes is not None and (not isinstance(vezes, int) or vezes < 1):
            raise ValueError("vezes must be a positive integer or None")
        return self._request(
            "video", file=file, vezes=vezes, camada=camada, som=som,
            x=x, y=y, largura=largura, altura=altura, z=z, opacidade=opacidade
        )

    def imagem(self, file, camada="background", x=0, y=0,
               largura=1, altura=1, z=0, opacidade=1):
        """Show a PNG/JPEG on a selected layer."""
        return self._request(
            "image", file=file, camada=camada, x=x, y=y,
            largura=largura, altura=altura, z=z, opacidade=opacidade
        )

    def remover(self, camada="background"):
        return self._request("remove", camada=camada)

    def limpar(self):
        return self._request("clear")

    def cena(self, nome):
        return self._request("scene", nome=nome)

    def esperar_video(self, camada="background"):
        with self._lock:
            finished = self._video_done.get(camada)
        if finished is None:
            raise RuntimeError(f"No video has been started on layer {camada!r}")
        while not finished.wait(0.05):
            if self.stopping.is_set():
                raise ShowStopped()

    def wait(self, milissegundos):
        if self.stopping.wait(max(0, milissegundos) / 1000.0):
            raise ShowStopped()

    def esperar_ble(self, sinal):
        """Wait for the next matching BLE/serial/terminal signal."""
        print(f"[SCRIPT] Waiting for signal {sinal}")
        while not self.stopping.is_set():
            try:
                incoming = self._signals.get(timeout=0.1)
            except queue.Empty:
                continue
            if incoming == int(sinal):
                return
        raise ShowStopped()

    def enviar_ble(self, sinal):
        """Use the application's configured outgoing transport."""
        return self._request("signal", sinal=int(sinal))

    def notify_signal(self, signal):
        try:
            self._signals.put_nowait(int(signal))
        except (ValueError, TypeError):
            pass

    def new_video(self, layer):
        with self._lock:
            old = self._video_done.get(layer)
            if old:
                old.set()
            finished = threading.Event()
            self._video_done[layer] = finished
            return finished

    def finish_video(self, layer):
        with self._lock:
            finished = self._video_done.get(layer)
            if finished:
                finished.set()

    def stop(self):
        self.stopping.set()
        with self._lock:
            for finished in self._video_done.values():
                finished.set()
