#  StatusDisplay.py Copyright (c) 2025 Nikki Cooper
#
#  This program and the accompanying materials are made available under the
#  terms of the GNU Lesser General Public License, version 3.0 which is available at
#  https://www.gnu.org/licenses/gpl-3.0.html#license-text
#
import os
import pygame

# ---------------------------------------------------------------------------
# State constants
# ---------------------------------------------------------------------------
_STATE_IDLE    = 'idle'
_STATE_SHOWING = 'showing'

# ---------------------------------------------------------------------------
# Rendering constants  (only the alpha channel is hardcoded)
# ---------------------------------------------------------------------------
_DODGER_BLUE  = (30,  144, 255)      # main text colour
_SHADOW_COLOR = ( 0,    0,  40)      # text shadow
_BOX_BG       = ( 0,    0,   0, 160) # SRCALPHA dark pill background

# Ordered list of paths to try for Roboto-Bold.ttf
_FONT_CANDIDATES = [
    os.path.expanduser('~/.local/share/nikkislide2/fonts/Roboto-Bold.ttf'),
    '/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf',   # Debian / Ubuntu / Pi
    '/usr/share/fonts/TTF/Roboto-Bold.ttf',               # Arch
]


class StatusDisplay:
    """
    On-screen overlay messages for the slideshow.

    Handles brief timed notifications (pause flash, delay change, etc.).
    All pixel values derive from display_height so the layout scales
    correctly across 1080p, 4K, and portrait monitors.

    States
    ------
    IDLE    : nothing shown
    SHOWING : timed message on screen; display_event fires once to clear
    """

    def __init__(self, win: pygame.Surface, bcolors,
                 display_event: int, divisor: int = 22) -> None:
        """
        :param win:           The pygame display surface.
        :param bcolors:       Bcolors instance (stored; not used internally).
        :param display_event: Custom event ID for message timeout (USEREVENT + 2).
        :param divisor:       font_size = display_height // divisor.  Default 22.
        """
        self.win           = win
        self.bcolors       = bcolors
        self.display_event = display_event
        self._divisor      = divisor


        self._state    = _STATE_IDLE
        self._saved_bg = None   # pygame.Surface snapshot of the clean display
        self._box_rect = None   # pygame.Rect of the currently drawn box

        self._display_w = win.get_width()
        self._display_h = win.get_height()

        self._font = self._load_font()

    # ------------------------------------------------------------------
    # Font
    # ------------------------------------------------------------------

    def _load_font(self) -> pygame.font.Font:
        size = max(28, self._display_h // self._divisor)

        for path in _FONT_CANDIDATES:
            if os.path.isfile(path):
                #print(f"[StatusDisplay] Font loaded   : {path}")
                #print(f"[StatusDisplay] Font size     : {size}px"
                #     f"  (height {self._display_h} // divisor {self._divisor})")
                return pygame.font.Font(path, size)

        system_match = pygame.font.match_font('roboto')
        if system_match:
            #print(f"[StatusDisplay] Font loaded   : {system_match}  (system match)")
            #print(f"[StatusDisplay] Font size     : {size}px"
            #     f"  (height {self._display_h} // divisor {self._divisor})")
            return pygame.font.Font(system_match, size)

        print(
            "[StatusDisplay] Roboto-Bold.ttf not found — falling back to system sans.\n"
            "  For best results install Roboto:\n"
            "    sudo pacman -S ttf-roboto          # Arch\n"
            "    sudo apt install fonts-roboto      # Debian / Raspberry Pi\n"
            "  or copy Roboto-Bold.ttf to  ~/.local/share/nikkislide2/fonts/"
        )
        #print(f"[StatusDisplay] Font size     : {size}px"
        #     f"  (height {self._display_h} // divisor {self._divisor})")
        return pygame.font.SysFont('sans', size)

    def set_divisor(self, divisor: int) -> None:
        """Change the font-size divisor and reload the font immediately."""
        self._divisor = divisor
        self._font    = self._load_font()

    # ------------------------------------------------------------------
    # Background snapshot
    # ------------------------------------------------------------------

    def update_background(self) -> None:
        """
        Snapshot the current display surface.

        Call this immediately after every pygame.display.update() in play()
        so that _clear() always restores to the most recently shown image.
        """
        self._saved_bg = self.win.copy()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def show_message(self, text: str, tag: str, duration: int) -> None:
        """
        Display a timed overlay message.

        :param text:     Text to display.
        :param tag:      Logical identifier (reserved for future per-tag formatting).
        :param duration: Display duration in milliseconds.
        """
        pygame.time.set_timer(self.display_event, 0)   # cancel any running timer
        self._clear()
        self._draw_box(text)
        pygame.time.set_timer(self.display_event, duration, 1)   # loops=1: fires once
        self._state = _STATE_SHOWING

    def show_nav(self, direction: str) -> None:
        """Visual feedback for next/prev navigation.  Stub — slide change is the feedback."""
        pass

    def on_timeout(self) -> None:
        """Called by EventHandler when display_event fires.  Clears the current message."""
        self._clear()
        self._state = _STATE_IDLE

    def patch_background(self, surf: pygame.Surface, rect: pygame.Rect) -> None:
        """
        Update a region of the saved background snapshot after a partial display
        update.  Call this after any direct blit+display.update(rect) that changes
        the display without going through the full play() render pipeline — e.g.
        InfoSplash.redraw_paused().  Without this, the next _clear() would restore
        stale pixels under the cleared region.
        """
        if self._saved_bg is not None:
            self._saved_bg.blit(surf, rect, rect)

    # ------------------------------------------------------------------
    # Rendering internals
    # ------------------------------------------------------------------

    def _draw_box(self, text: str) -> None:
        """Render a message box centred horizontally at 75% of display height."""
        h = self._display_h
        w = self._display_w

        padding       = max(8, h // 60)    # space between text and box edge
        shadow_offset = max(1, h // 540)   # 2px @ 1080p, 4px @ 4K
        corner_radius = max(4, h // 80)    # rounded corners

        text_surf   = self._font.render(text, True, _DODGER_BLUE)
        shadow_surf = self._font.render(text, True, _SHADOW_COLOR)

        box_w = text_surf.get_width()  + padding * 2
        box_h = text_surf.get_height() + padding * 2
        box_x = (w - box_w) // 2
        box_y = int(h * 0.75)

        self._box_rect = pygame.Rect(box_x, box_y, box_w, box_h)

        # Semi-transparent dark pill — drawn on a temp SRCALPHA surface
        bg_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        pygame.draw.rect(bg_surf, _BOX_BG, bg_surf.get_rect(),
                         border_radius=corner_radius)
        self.win.blit(bg_surf, (box_x, box_y))

        # Shadow then main text
        self.win.blit(shadow_surf, (box_x + padding + shadow_offset,
                                    box_y + padding + shadow_offset))
        self.win.blit(text_surf,   (box_x + padding,
                                    box_y + padding))

        pygame.display.update()

    def _clear(self) -> None:
        """Restore the saved background pixels underneath the current box."""
        if self._box_rect is None or self._saved_bg is None:
            return
        # blit only the box-sized region of the snapshot back onto the display
        self.win.blit(self._saved_bg, self._box_rect, self._box_rect)
        pygame.display.update()
        self._box_rect = None
