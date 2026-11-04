
"""On-screen command console for Extended Stage.

F2: Open or close the console.
Enter: Execute the typed command.
Escape: Cancel input.
Backspace: Delete a character.
"""

import pygame


class WindowConsole:
    def __init__(self, callback):
        self.callback = callback
        self.active = False
        self.text = ""
        self.message = "Press F2 to open command mode"
        self.font = None
        self.small_font = None

    def _fonts(self):
        if not pygame.font.get_init():
            pygame.font.init()

        if self.font is None:
            self.font = pygame.font.Font(None, 30)
            self.small_font = pygame.font.Font(None, 22)

    def toggle(self):
        self.active = not self.active

        if self.active:
            self.text = ""
            pygame.key.start_text_input()
            print("[CONSOLE] Command mode enabled")
        else:
            pygame.key.stop_text_input()
            print("[CONSOLE] Command mode disabled")

    def close(self):
        self.active = False
        self.text = ""
        pygame.key.stop_text_input()

    def handle(self, event):
        """Return True when an input event was consumed."""

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F2:
                self.toggle()
                return True

            if not self.active:
                return False

            if event.key == pygame.K_ESCAPE:
                self.close()
                return True

            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                return True

            if event.key in (
                pygame.K_RETURN,
                pygame.K_KP_ENTER
            ):
                command = self.text.strip()
                self.text = ""

                if command:
                    self.message = f"Sent: {command}"
                    self.callback(command)

                return True

            # Ignore other keydown events while typing.
            # Text characters are handled through TEXTINPUT.
            return True

        if event.type == pygame.TEXTINPUT and self.active:
            incoming = event.text.replace("\n", "")

            if len(self.text) + len(incoming) <= 160:
                self.text += incoming

            return True

        return False

    def draw(self):
        """Draw the command box over the current media frame."""

        if not self.active:
            return

        surface = pygame.display.get_surface()

        if surface is None:
            return

        self._fonts()

        screen_width, screen_height = surface.get_size()

        width = min(850, max(200, screen_width - 40))
        height = 95

        x = (screen_width - width) // 2
        y = max(0, screen_height - height - 25)

        overlay = pygame.Surface(
            (width, height),
            pygame.SRCALPHA
        )
        overlay.fill((8, 12, 20, 225))

        pygame.draw.rect(
            overlay,
            (80, 160, 220),
            overlay.get_rect(),
            width=2,
            border_radius=8
        )

        label = self.small_font.render(
            "COMMAND MODE | ENTER: SEND | ESC: CANCEL | F2: CLOSE",
            True,
            (110, 210, 160)
        )
        overlay.blit(label, (15, 10))

        prefix = "> "
        available = width - 45

        visible_text = self.text

        while (
            visible_text
            and self.font.size(prefix + visible_text + "_")[0]
            > available
        ):
            visible_text = visible_text[1:]

        content = self.font.render(
            prefix + visible_text + "_",
            True,
            (245, 245, 245)
        )

        overlay.blit(content, (15, 43))

        surface.blit(overlay, (x, y))

        pygame.display.flip()
