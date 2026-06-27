#!/usr/bin/env python3
"""
test_status_display.py  —  NikkiSlide2 StatusDisplay tuning tool
Copyright (c) 2025 Nikki Cooper  (same licence as the project)

Standalone, single-file.  Only external dependency: pygame.

Purpose
-------
Run this on each target machine (dev / Pi4 / Pi5) to tune the font-size
divisor and verify the overlay renders correctly.  Report back the divisor
value that looks best on each display.

Usage
-----
    python test_status_display.py [options]

    --display  N      Monitor index (default 0)
    --divisor  N      font_size = display_height // N  (default 22)
    --duration N      Timed message duration in ms     (default 2000)
    --bg-color R G B  Solid background colour          (default 80 80 80)
    --image    PATH   Use an image file instead of solid colour

Interactive controls
--------------------
    1           Show a generic timed message
    2           Toggle PAUSED on/off
    3           Show timed message while PAUSED (watch PAUSED resume after timeout)
    +  / KP_+   Fake delay +500 ms  (tests smart-update while paused)
    -  / KP_-   Fake delay -500 ms
    B           Cycle background colour  (dark-gray → light-gray → black → white)
    Q / Escape  Quit
"""

import os
import sys
import argparse
import pygame

# ===========================================================================
# StatusDisplay  (inlined so this file has no project dependencies)
# ===========================================================================

_STATE_IDLE    = 'idle'
_STATE_SHOWING = 'showing'
_STATE_PAUSED  = 'paused'

_DODGER_BLUE  = ( 30, 144, 255)
_SHADOW_COLOR = (  0,   0,  40)
_BOX_BG       = (  0,   0,   0, 160)

_FONT_CANDIDATES = [
    os.path.expanduser('~/.local/share/nikkislide2/fonts/Roboto-Bold.ttf'),
    '/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf',
    '/usr/share/fonts/TTF/Roboto-Bold.ttf',
]


class StatusDisplay:
    def __init__(self, win: pygame.Surface, display_event: int,
                 divisor: int = 22) -> None:
        self.win           = win
        self.display_event = display_event
        self._divisor      = divisor

        self._state            = _STATE_IDLE
        self._resume_to_paused = False
        self._saved_bg         = None
        self._box_rect         = None

        self._display_w = win.get_width()
        self._display_h = win.get_height()

        self._font = self._load_font()

    def _load_font(self) -> pygame.font.Font:
        size = max(28, self._display_h // self._divisor)
        for path in _FONT_CANDIDATES:
            if os.path.isfile(path):
                print(f"[StatusDisplay] Font loaded   : {path}")
                print(f"[StatusDisplay] Font size     : {size}px"
                      f"  (height {self._display_h} // divisor {self._divisor})")
                return pygame.font.Font(path, size)
        system_match = pygame.font.match_font('roboto')
        if system_match:
            print(f"[StatusDisplay] Font loaded   : {system_match}  (system match)")
            print(f"[StatusDisplay] Font size     : {size}px"
                  f"  (height {self._display_h} // divisor {self._divisor})")
            return pygame.font.Font(system_match, size)
        print(
            "[StatusDisplay] Roboto-Bold.ttf not found — falling back to system sans.\n"
            "  For best results install Roboto:\n"
            "    sudo pacman -S ttf-roboto          # Arch\n"
            "    sudo apt install fonts-roboto      # Debian / Raspberry Pi\n"
            "  or copy Roboto-Bold.ttf to  ~/.local/share/nikkislide2/fonts/"
        )
        print(f"[StatusDisplay] Font size     : {size}px"
              f"  (height {self._display_h} // divisor {self._divisor})")
        return pygame.font.SysFont('sans', size)

    def set_divisor(self, divisor: int) -> None:
        self._divisor = divisor
        self._font    = self._load_font()

    def update_background(self) -> None:
        self._saved_bg = self.win.copy()

    def show_message(self, text: str, tag: str, duration: int) -> None:
        pygame.time.set_timer(self.display_event, 0)
        if self._state == _STATE_PAUSED:
            self._resume_to_paused = True
        elif self._state == _STATE_IDLE:
            self._resume_to_paused = False
        self._clear()
        self._draw_box(text)
        pygame.time.set_timer(self.display_event, duration, 1)
        self._state = _STATE_SHOWING

    def show_paused(self) -> None:
        pygame.time.set_timer(self.display_event, 0)
        self._resume_to_paused = False
        self._clear()
        self._draw_box('PAUSED')
        self._state = _STATE_PAUSED

    def hide_paused(self) -> None:
        if self._state == _STATE_PAUSED:
            self._clear()
            self._state = _STATE_IDLE

    def on_timeout(self) -> None:
        self._clear()
        if self._resume_to_paused:
            self._resume_to_paused = False
            self.show_paused()
        else:
            self._state = _STATE_IDLE

    def _draw_box(self, text: str) -> None:
        h = self._display_h
        w = self._display_w
        padding       = max(8, h // 60)
        shadow_offset = max(1, h // 540)
        corner_radius = max(4, h // 80)
        text_surf   = self._font.render(text, True, _DODGER_BLUE)
        shadow_surf = self._font.render(text, True, _SHADOW_COLOR)
        box_w = text_surf.get_width()  + padding * 2
        box_h = text_surf.get_height() + padding * 2
        box_x = (w - box_w) // 2
        box_y = int(h * 0.75)
        self._box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
        bg_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        pygame.draw.rect(bg_surf, _BOX_BG, bg_surf.get_rect(),
                         border_radius=corner_radius)
        self.win.blit(bg_surf, (box_x, box_y))
        self.win.blit(shadow_surf, (box_x + padding + shadow_offset,
                                    box_y + padding + shadow_offset))
        self.win.blit(text_surf,   (box_x + padding, box_y + padding))
        pygame.display.update(self._box_rect)

    def _clear(self) -> None:
        if self._box_rect is None or self._saved_bg is None:
            return
        self.win.blit(self._saved_bg, self._box_rect, self._box_rect)
        pygame.display.update(self._box_rect)
        self._box_rect = None


# ===========================================================================
# Test harness
# ===========================================================================

# Background colours to cycle through with the B key
_BG_CYCLE = [
    ( 80,  80,  80),   # mid-gray (default)
    (160, 160, 160),   # light-gray
    (  0,   0,   0),   # black
    (255, 255, 255),   # white
    ( 20,  40,  80),   # dark blue  (close to image content)
]

DISPLAY_EVENT = pygame.USEREVENT + 2


def _draw_background(win: pygame.Surface, image_path: str | None,
                     bg_color: tuple) -> None:
    if image_path:
        try:
            img = pygame.image.load(image_path).convert()
            img = pygame.transform.scale(img, win.get_size())
            win.blit(img, (0, 0))
            pygame.display.update()
            return
        except Exception as exc:
            print(f"[test] Could not load image '{image_path}': {exc}")
            print("[test] Falling back to solid colour.")
    win.fill(bg_color)
    pygame.display.update()


def _print_controls() -> None:
    print()
    print("Controls")
    print("--------")
    print("  1           Show timed message")
    print("  2           Toggle PAUSED")
    print("  3           Show timed message while PAUSED  (watch PAUSED resume)")
    print("  + / KP_+    Fake delay +500 ms")
    print("  - / KP_-    Fake delay -500 ms")
    print("  B           Cycle background colour")
    print("  Q / Escape  Quit")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="NikkiSlide2 StatusDisplay tuning tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    ap.add_argument('--display',  type=int, default=0,
                    metavar='N',   help='Monitor index')
    ap.add_argument('--divisor',  type=int, default=22,
                    metavar='N',   help='font_size = display_height // N')
    ap.add_argument('--duration', type=int, default=2000,
                    metavar='MS',  help='Timed message duration in ms')
    ap.add_argument('--bg-color', type=int, nargs=3, default=[80, 80, 80],
                    metavar=('R', 'G', 'B'), help='Background colour')
    ap.add_argument('--image',    type=str, default=None,
                    metavar='PATH', help='Background image (overrides --bg-color)')
    args = ap.parse_args()

    os.environ['PYGAME_DISPLAY']               = str(args.display)
    os.environ['SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS'] = '0'
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT']   = '1'

    pygame.init()
    flags = pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.NOFRAME
    win   = pygame.display.set_mode((0, 0), flags, 24)
    w, h  = win.get_size()

    print()
    print(f"Display resolution : {w} x {h}")
    print(f"Divisor            : {args.divisor}")
    print(f"Message duration   : {args.duration} ms")
    print()

    status = StatusDisplay(win, DISPLAY_EVENT, divisor=args.divisor)

    bg_color   = tuple(args.bg_color)
    bg_index   = 0
    fake_delay = 3000
    paused     = False

    _draw_background(win, args.image, bg_color)
    status.update_background()

    _print_controls()

    running = True
    while running:
        event = pygame.event.wait()

        if event.type == pygame.QUIT:
            running = False

        elif event.type == DISPLAY_EVENT:
            status.on_timeout()

        elif event.type == pygame.KEYDOWN:
            key = event.key

            if key in (pygame.K_q, pygame.K_ESCAPE):
                running = False

            elif key == pygame.K_1:
                status.show_message(
                    "NikkiSlide2 — test message", tag='test',
                    duration=args.duration)

            elif key == pygame.K_2:
                paused = not paused
                if paused:
                    print("[test] → show_paused()")
                    status.show_paused()
                else:
                    print("[test] → hide_paused()")
                    status.hide_paused()

            elif key == pygame.K_3:
                print("[test] → show_message() while paused — watch PAUSED resume")
                status.show_message(
                    "Timed msg while paused", tag='test2',
                    duration=args.duration)

            elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                fake_delay = min(fake_delay + 500, 60000)
                print(f"[test] fake delay → {fake_delay} ms")
                status.show_message(
                    f"Delay: {fake_delay} ms", tag='delay',
                    duration=args.duration)

            elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                fake_delay = max(fake_delay - 500, 30)
                print(f"[test] fake delay → {fake_delay} ms")
                status.show_message(
                    f"Delay: {fake_delay} ms", tag='delay',
                    duration=args.duration)

            elif key == pygame.K_b:
                bg_index = (bg_index + 1) % len(_BG_CYCLE)
                bg_color  = _BG_CYCLE[bg_index]
                print(f"[test] background → {bg_color}")
                # Must clear any visible box before overwriting the background
                # so _saved_bg doesn't capture a box baked into the image.
                status._clear()
                status._state = _STATE_IDLE
                _draw_background(win, None, bg_color)
                status.update_background()
                # Restore paused indicator if it was showing
                if paused:
                    status.show_paused()

    pygame.quit()
    sys.exit(0)


if __name__ == '__main__':
    main()
