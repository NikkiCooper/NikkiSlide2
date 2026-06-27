#  InfoSplash.py Copyright (c) 2025 Nikki Cooper
#
#  This program and the accompanying materials are made available under the
#  terms of the GNU Lesser General Public License, version 3.0 which is available at
#  https://www.gnu.org/licenses/gpl-3.0.html#license-text
#
import os
import time
import pygame

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
_COLOR_REGULAR   = (190, 190, 190)   # subdued gray — doesn't compete with photo
_COLOR_BOLD      = (225, 225, 225)   # near-white for the filename (normal state)
_COLOR_BOLD_PAUSED = (255, 220,   0) # bold yellow for the filename when paused
_COLOR_EXIF      = (255, 220,   0)   # bold yellow for EXIF-sourced date/time
_COLOR_SHADOW    = (  0,   0,   0)   # 1-px drop shadow for legibility on bright images
_BOX_BG          = (  0,   0,   0, 155)   # SRCALPHA dark pill

# ---------------------------------------------------------------------------
# Font search paths
# ---------------------------------------------------------------------------
_FONTS_DIR = os.path.expanduser('~/.local/share/nikkislide2/fonts/')

_REGULAR_CANDIDATES = [
    os.path.join(_FONTS_DIR, 'Arial.ttf'),
    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',   # Debian/Pi
    '/usr/share/fonts/TTF/LiberationSans-Regular.ttf',                   # Arch
]
_BOLD_CANDIDATES = [
    os.path.join(_FONTS_DIR, 'Arial_Bold.ttf'),
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    '/usr/share/fonts/TTF/LiberationSans-Bold.ttf',
]


class InfoSplash:
    """
    Per-image information overlay — lower-left corner of the display.

    Layout (two visible lines):
      Line 1:  (N/TOTAL) [1:~R]  <filename in bold>
      Line 2:  W × H  —  MM/DD/YYYY  HH:MM:SS AM/PM  —  X.X MiB
      Line 3:  (placeholder for future EXIF date / comment — not rendered)

    All text surfaces are pre-rendered once per image in prepare() and
    composited onto a single SRCALPHA surface.  draw() only blits that
    surface — no display.update() call is made here; the caller is
    responsible for the single display.update() that composites everything.

    Font size = max(13, display_height // divisor).  Default divisor=65 gives
    16 px at 1080p and 33 px at 4K.  Pass a different divisor to tune per machine.
    """

    def __init__(self, win: pygame.Surface, enabled: bool = False,
                 divisor: int = 80) -> None:
        """
        :param win:      The pygame display surface.
        :param enabled:  Whether to show the overlay (toggled by 'i' key or --isplash).
        :param divisor:  font_size = display_height // divisor.
                         Smaller divisor = larger text.  Tune with --info-divisor.
                         Default 80 gives ~13px at 1080p, ~27px at 4K, ~24px at 1920-tall portrait.
        """
        self.win       = win
        self.enabled   = enabled
        self.paused    = False      # set by EventHandler._toggle_pause()
        self._divisor  = divisor

        self._display_w = win.get_width()
        self._display_h = win.get_height()

        self._font_regular = self._load_font(_REGULAR_CANDIDATES, 'liberationsans')
        self._font_bold    = self._load_font(_BOLD_CANDIDATES,    'liberationsans:bold')

        # Normal state surface (white filename)
        self._info_surf:        pygame.Surface | None = None
        # Paused state surface (yellow filename) — same geometry, different colour
        self._info_surf_paused: pygame.Surface | None = None
        self._box_pos:          tuple[int, int]       = (0, 0)
        self._box_rect:         pygame.Rect | None    = None

    # ------------------------------------------------------------------
    # Font loading
    # ------------------------------------------------------------------

    def _load_font(self, candidates: list, match_name: str) -> pygame.font.Font:
        size = max(12, self._display_h // self._divisor)
        for path in candidates:
            if os.path.isfile(path):
                #print(f"[InfoSplash]    Font loaded   : {path}")
                #print(f"[InfoSplash]    Font size     : {size}px"
                #     f"  (height {self._display_h} // divisor {self._divisor})")
                return pygame.font.Font(path, size)
        match = pygame.font.match_font(match_name)
        if match:
            #print(f"[InfoSplash]    Font loaded   : {match}  (system match)")
            #print(f"[InfoSplash]    Font size     : {size}px"
            #     f"  (height {self._display_h} // divisor {self._divisor})")
            return pygame.font.Font(match, size)
        print(
            "[InfoSplash]    Arial / LiberationSans not found — falling back to system sans.\n"
            "  Copy Arial.ttf and Arial_Bold.ttf to  ~/.local/share/nikkislide2/fonts/"
        )
        return pygame.font.SysFont('sans', size)

    # ------------------------------------------------------------------
    # Per-image data preparation
    # ------------------------------------------------------------------

    def prepare(self, imageFile: str, currImgIndx: int, mediaListLen: int,
                imgWidth: int, imgHeight: int,
                bg_rect: pygame.Rect | None = None,
                exif_datetime: str | None = None) -> None:
        """
        Compute all display strings for the current image and pre-render them
        onto a single cached SRCALPHA surface.

        Always called on every image change (even when disabled) so that
        toggling 'i' on mid-slideshow shows correct data immediately.

        :param imageFile:     Full path to the current image.
        :param currImgIndx:   0-based index in the media list.
        :param mediaListLen:  Total number of images in the media list.
        :param imgWidth:      Image width in pixels.
        :param imgHeight:     Image height in pixels.
        :param bg_rect:       Rect of the scaled image on the display.  When
                              provided the box is anchored to bg_rect.bottom so
                              it stays within the image content area and clear of
                              any black bars (e.g. portrait mode).
        :param exif_datetime: Pre-formatted EXIF date/time string, or None to
                              omit line 3 (falls back to filesystem mtime on line 2).
        """
        try:
            stat = os.stat(imageFile)
        except OSError as e:
            print(f"[InfoSplash] os.stat failed for '{imageFile}': {e}")
            self._info_surf = None
            return

        # --- fit-to-screen scale ratio ---
        # scale < 1 means image is larger than display; show as [1:~N] (zoom-out ratio)
        # scale ≥ 1 means image fits or is smaller; show as [~N:1] (zoom-in ratio)
        scale = min(self._display_w / imgWidth, self._display_h / imgHeight)
        if scale >= 1.0:
            ratio_str = f"[~{scale:.2f}:1]"
        else:
            ratio_str = f"[1:~{1.0 / scale:.2f}]"

        # --- line 1 strings ---
        prefix_line1 = f"({currImgIndx + 1}/{mediaListLen}) {ratio_str} "
        filename     = os.path.basename(imageFile)

        # --- file size ---
        size_bytes = stat.st_size
        if size_bytes >= 1024 * 1024:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MiB"
        elif size_bytes >= 1024:
            size_str = f"{size_bytes / 1024:.1f} KiB"
        else:
            size_str = f"{size_bytes} B"

        # --- date / time ---
        mtime_str = time.strftime(
            "%m/%d/%Y  %I:%M:%S %p",
            time.localtime(stat.st_mtime)
        )

        # --- line 2 ---
        line2 = f"{imgWidth} \u00d7 {imgHeight}  \u2014  {mtime_str}  \u2014  {size_str}"

        # --- line 3: EXIF date/time (bold yellow) when available ---
        # exif_datetime is pre-formatted by _read_exif_datetime() in PlayMedia.
        # None means --enableEXIF was not set, or no valid tag was found.
        exif_label = "EXIF: "
        exif_str   = exif_datetime   # None → line 3 not rendered

        # --- layout constants (all derived from display height) ---
        padding      = max(6, self._display_h // 90)
        line_spacing = max(2, self._display_h // 400)
        shadow_off   = 1
        corner_r     = max(4, self._display_h // 120)

        # --- render text surfaces ---
        pfx_shd        = self._font_regular.render(prefix_line1, True, _COLOR_SHADOW)
        pfx_surf       = self._font_regular.render(prefix_line1, True, _COLOR_REGULAR)
        fn_shd         = self._font_bold.render(filename, True, _COLOR_SHADOW)
        fn_surf_normal = self._font_bold.render(filename, True, _COLOR_BOLD)
        fn_surf_paused = self._font_bold.render(filename, True, _COLOR_BOLD_PAUSED)
        l2_shd         = self._font_regular.render(line2, True, _COLOR_SHADOW)
        l2_surf        = self._font_regular.render(line2, True, _COLOR_REGULAR)

        if exif_str is not None:
            l3_label_shd  = self._font_regular.render(exif_label, True, _COLOR_SHADOW)
            l3_label_surf = self._font_regular.render(exif_label, True, _COLOR_REGULAR)
            l3_val_shd    = self._font_bold.render(exif_str, True, _COLOR_SHADOW)
            l3_val_surf   = self._font_bold.render(exif_str, True, _COLOR_EXIF)
            line3_w       = l3_label_surf.get_width() + l3_val_surf.get_width()
            line3_h       = max(l3_label_surf.get_height(), l3_val_surf.get_height())
        else:
            l3_label_shd = l3_label_surf = l3_val_shd = l3_val_surf = None
            line3_w = line3_h = 0

        # --- geometry ---
        line1_w = pfx_surf.get_width() + fn_surf_normal.get_width()
        line1_h = max(pfx_surf.get_height(), fn_surf_normal.get_height())
        line2_w = l2_surf.get_width()
        line2_h = l2_surf.get_height()

        content_w = max(line1_w, line2_w, line3_w)
        content_h = line1_h + line_spacing + line2_h
        if exif_str is not None:
            content_h += line_spacing + line3_h

        box_w = content_w + padding * 2
        box_h = content_h + padding * 2

        left_margin   = max(8,  self._display_h // 120)
        bottom_margin = max(8,  self._display_h // 120)
        # Anchor to the bottom of the rendered image, not the display edge.
        # This keeps the box inside the image content area and clear of any
        # black bars (letterbox / pillarbox from unscaled images).
        if bg_rect is not None:
            anchor_bottom = bg_rect.bottom
            anchor_left   = bg_rect.left
        else:
            anchor_bottom = self._display_h
            anchor_left   = 0
        box_x = anchor_left + left_margin
        box_y = anchor_bottom - box_h - bottom_margin
        self._box_pos  = (box_x, box_y)
        self._box_rect = pygame.Rect(box_x, box_y, box_w, box_h)

        # --- helper: build one composite surface with given filename colour ---
        def _build(fn_surf: pygame.Surface) -> pygame.Surface:
            s = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            pygame.draw.rect(s, _BOX_BG, s.get_rect(), border_radius=corner_r)
            px, py = padding, padding
            s.blit(pfx_shd,  (px + shadow_off, py + shadow_off))
            s.blit(pfx_surf, (px, py))
            fx = px + pfx_surf.get_width()
            s.blit(fn_shd,   (fx + shadow_off, py + shadow_off))
            s.blit(fn_surf,  (fx, py))
            ly = padding + line1_h + line_spacing
            s.blit(l2_shd,   (padding + shadow_off, ly + shadow_off))
            s.blit(l2_surf,  (padding, ly))
            if exif_str is not None:
                ly += line2_h + line_spacing
                s.blit(l3_label_shd,  (padding + shadow_off, ly + shadow_off))
                s.blit(l3_label_surf, (padding, ly))
                lx = padding + l3_label_surf.get_width()
                s.blit(l3_val_shd,  (lx + shadow_off, ly + shadow_off))
                s.blit(l3_val_surf, (lx, ly))
            return s

        self._info_surf        = _build(fn_surf_normal)
        self._info_surf_paused = _build(fn_surf_paused)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def draw(self) -> None:
        """
        Blit the pre-rendered info surface onto the display surface.

        Does NOT call pygame.display.update() — the caller composites all
        overlays and issues a single display.update() to avoid flicker.
        Picks the paused (yellow filename) variant when self.paused is True.
        """
        if not self.enabled or self._info_surf is None:
            return
        surf = self._info_surf_paused if self.paused else self._info_surf
        self.win.blit(surf, self._box_pos)

    def redraw_paused(self, status) -> None:
        """
        Partially update the info splash region to reflect a pause state change,
        using pygame.display.update(rect) so only the box region is pushed to screen.

        Patches status._saved_bg so StatusDisplay._clear() restores the correct
        pixels if it clears a PAUSED flash message that was shown over this box.

        :param status: The StatusDisplay instance.
        """
        if not self.enabled or self._info_surf is None or self._box_rect is None:
            return
        surf = self._info_surf_paused if self.paused else self._info_surf
        self.win.blit(surf, self._box_pos)
        pygame.display.update()
        status.patch_background(self.win, self._box_rect)
