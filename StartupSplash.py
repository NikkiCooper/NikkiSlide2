#  StartupSplash.py Copyright (c) 2025 Nikki Cooper
#
#  This program and the accompanying materials are made available under the
#  terms of the GNU Lesser General Public License, version 3.0 which is available at
#  https://www.gnu.org/licenses/gpl-3.0.html#license-text
#
import os
import sys
import pygame

# ---------------------------------------------------------------------------
# Colours — same palette as StatusDisplay / InfoSplash
# ---------------------------------------------------------------------------
_TITLE_COLOR = ( 30, 144, 255)      # dodger blue
_TEXT_COLOR  = (200, 200, 200)      # light gray
_SHADOW      = (  0,   0,  40)      # text shadow
_BOX_BG      = (  0,   0,   0, 180) # SRCALPHA dark box
_LOGO_BG     = ( 28,  28,  36)      # slightly lighter background inside logo area
_LOGO_BORDER = ( 72,  72,  96)      # subtle border when placeholder is shown

# Use USEREVENT + 10 — well clear of timer_event (+1) and display_event_timeout (+2)
_SPLASH_EVENT = pygame.USEREVENT + 10

# ---------------------------------------------------------------------------
# Font and logo search paths
# ---------------------------------------------------------------------------
_FONTS_DIR = os.path.expanduser('~/.local/share/nikkislide2/fonts/')

_FONT_CANDIDATES = [
    os.path.join(_FONTS_DIR, 'Roboto-Bold.ttf'),
    '/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf',   # Debian / Pi
    '/usr/share/fonts/TTF/Roboto-Bold.ttf',               # Arch
]

_LOGO_CANDIDATES = [
    os.path.join(_FONTS_DIR, '..', 'logo.png'),
    os.path.join(_FONTS_DIR, '..', 'logo.jpg'),
    os.path.join(_FONTS_DIR, '..', 'logo.jpeg'),
    os.path.join(_FONTS_DIR, '..', 'logo.webp'),
]


class StartupSplash:
    """
    Startup splash screen — shown once at launch, auto-dismissed after `duration` ms.

    Layout: logo area (left) | text column (right)
      Text column: title (large dodger blue), version, author, tagline.

    All geometry is derived from display_height and --info-divisor so the
    splash scales correctly across all displays without manual tuning.

    The logo area accepts any image (portrait, landscape, square) — it is
    scaled to fit the square area while preserving the image's aspect ratio.
    Drop any image at  ~/.local/share/nikkislide2/logo.png  and it will
    just work.  If no logo file is found a placeholder rectangle is shown.
    """

    def __init__(self, win: pygame.Surface, opts) -> None:
        """
        :param win:  The pygame display surface (already initialised).
        :param opts: Parsed CLI options — reads infoDivisor.
        """
        self.win   = win
        self._dw   = win.get_width()
        self._dh   = win.get_height()

        # Base unit: same scale as StatusDisplay (infoDivisor // 2).
        # All geometry grows/shrinks with this.
        self._unit = max(18, self._dh // max(1, opts.infoDivisor // 2))

        self._title_font = self._load_font(self._unit)
        self._body_font  = self._load_font(max(12, self._unit * 2 // 3))
        self._logo_surf  = self._load_logo()

    # ------------------------------------------------------------------
    # Font / logo loading
    # ------------------------------------------------------------------

    def _load_font(self, size: int) -> pygame.font.Font:
        for path in _FONT_CANDIDATES:
            if os.path.isfile(path):
                return pygame.font.Font(path, size)
        match = pygame.font.match_font('roboto')
        if match:
            return pygame.font.Font(match, size)
        return pygame.font.SysFont('sans', size)

    def _load_logo(self) -> pygame.Surface | None:
        for path in _LOGO_CANDIDATES:
            p = os.path.normpath(path)
            if os.path.isfile(p):
                try:
                    return pygame.image.load(p).convert_alpha()
                except pygame.error:
                    pass
        return None

    def _fit_logo(self, surf: pygame.Surface, size: int) -> pygame.Surface:
        """Scale logo to fit within size×size, preserving aspect ratio, centred."""
        w, h = surf.get_size()
        scale = min(size / w, size / h)
        nw, nh = round(w * scale), round(h * scale)
        scaled = pygame.transform.smoothscale(surf, (nw, nh))
        result = pygame.Surface((size, size), pygame.SRCALPHA)
        result.blit(scaled, ((size - nw) // 2, (size - nh) // 2))
        return result

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def show(self,
             version:  str,
             author:   str = "Nikki Cooper",
             tagline:  str = "An Image Slideshow for Linux",
             duration: int = 7500) -> None:
        """
        Render the splash screen and block until the auto-dismiss timer fires.

        :param version:  Version string, e.g. "0.50".
        :param author:   Author name shown below the version line.
        :param tagline:  Short one-liner shown below the author line.
        :param duration: How long to display the splash, in milliseconds.
        """
        unit       = self._unit
        pad        = max(8, unit // 2)
        logo_size  = unit * 3
        line_gap   = max(3, unit // 5)
        shadow_off = max(1, unit // 24)
        corner_r   = max(4, unit // 8)

        # --- render text surfaces ---
        title_surf  = self._title_font.render("NikkiSlide2",       True, _TITLE_COLOR)
        title_shd   = self._title_font.render("NikkiSlide2",       True, _SHADOW)
        ver_surf    = self._body_font.render(f"Version {version}", True, _TEXT_COLOR)
        auth_surf   = self._body_font.render(f"by {author}",       True, _TEXT_COLOR)
        tag_surf    = self._body_font.render(tagline,              True, _TEXT_COLOR)

        text_w = max(title_surf.get_width(), ver_surf.get_width(),
                     auth_surf.get_width(),  tag_surf.get_width())
        text_h = (title_surf.get_height() + line_gap +
                  ver_surf.get_height()   + line_gap +
                  auth_surf.get_height()  + line_gap +
                  tag_surf.get_height())

        # --- box geometry ---
        inner_h = max(logo_size, text_h)
        box_w   = pad + logo_size + pad + text_w + pad
        box_h   = inner_h + pad * 2
        box_x   = (self._dw - box_w) // 2
        box_y   = (self._dh - box_h) // 2

        # --- draw to window ---
        self.win.fill((0, 0, 0))

        # dark semi-transparent box
        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        pygame.draw.rect(bg, _BOX_BG, bg.get_rect(), border_radius=corner_r)
        self.win.blit(bg, (box_x, box_y))

        # logo area (left column, vertically centred in box)
        logo_x = box_x + pad
        logo_y = box_y + (box_h - logo_size) // 2
        logo_rect_draw = pygame.Rect(logo_x, logo_y, logo_size, logo_size)

        if self._logo_surf is not None:
            self.win.blit(self._fit_logo(self._logo_surf, logo_size), (logo_x, logo_y))
        else:
            pygame.draw.rect(self.win, _LOGO_BG,     logo_rect_draw, border_radius=corner_r // 2)
            pygame.draw.rect(self.win, _LOGO_BORDER, logo_rect_draw, 1, border_radius=corner_r // 2)

        # text column (right of logo, vertically centred)
        text_x = box_x + pad + logo_size + pad
        text_y = box_y + (box_h - text_h) // 2

        def _blit(surf, shd, y):
            if shd is not None:
                self.win.blit(shd, (text_x + shadow_off, y + shadow_off))
            self.win.blit(surf, (text_x, y))
            return y + surf.get_height() + line_gap

        y = text_y
        y = _blit(title_surf, title_shd, y)
        y = _blit(ver_surf,   None,      y)
        y = _blit(auth_surf,  None,      y)
        _blit(tag_surf, None, y)

        pygame.display.update()

        # --- auto-dismiss ---
        pygame.time.set_timer(_SPLASH_EVENT, duration, 1)
        while True:
            event = pygame.event.wait()
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == _SPLASH_EVENT:
                break
        pygame.time.set_timer(_SPLASH_EVENT, 0)   # safety cancel
