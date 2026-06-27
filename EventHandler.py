#   EventHandler.py Copyright (c) 2025 Nikki Cooper
#
#  This program and the accompanying materials are made available under the
#  terms of the GNU Lesser General Public License, version 3.0 which is available at
#  https://www.gnu.org/licenses/gpl-3.0.html#license-text
#
import os
import pygame
from StatusDisplay import StatusDisplay
from InfoSplash import InfoSplash
from IRRemoteControl import IRRemoteControl

# Mouse button index constants for pygame.mouse.get_pressed(3)
LEFT   = 0
MIDDLE = 1
RIGHT  = 2

# Mousewheel direction constants (event.y values)
WHEEL_DOWN = -1
WHEEL_UP   =  1

class EventHandler:
    def __init__(self, _IMAGE):
        """
        :param _IMAGE: The PlayMedia instance.
        """
        self.Img = _IMAGE
        self.timer_event: int           = pygame.USEREVENT + 1
        self.display_event_timeout: int = pygame.USEREVENT + 2
        self.timer_interval: int = self.Img.opts.delayTime
        #print(f"self.timer_interval: {self.timer_interval}")
        pygame.time.set_timer(self.timer_event, self.timer_interval)
        self.status = StatusDisplay(self.Img.Win, self.Img.bcolors,
                                    self.display_event_timeout,
                                    divisor=max(1, self.Img.opts.infoDivisor // 2))
        self.info_splash = InfoSplash(self.Img.Win,
                                      enabled=self.Img.opts.isplash,
                                      divisor=self.Img.opts.infoDivisor)
        # Initialize IR Remote Control (set debug=True to troubleshoot IR codes)
        # Use --disable-IR on the command line to skip the UDP listener entirely.
        if not self.Img.opts.disable_IR:
            self.ir_remote = IRRemoteControl(self.Img.opts.irKeymap, self.Img.opts.udpPort, debug=False)
            self._setup_ir_callbacks()
            self.ir_remote.start()

        else:
            self.ir_remote = None
            print("IR Remote: disabled via --disable-IR")

    # ------------------------------------------------------------------
    # Debug helpers
    # ------------------------------------------------------------------

    def _debug_mouse(self, msg: str) -> None:
        """Print a mouse debug line when --debugMouse is active."""
        if self.Img.opts.debugMouseFlag:
            bc = self.Img.bcolors
            print(f"{bc.Cyan_f}{bc.BOLD}[MOUSE]{bc.RESET} {msg}{bc.RESET}")

    def _debug_key(self, msg: str) -> None:
        """Print a keyboard debug line when --debugKeys is active."""
        if self.Img.opts.debugKeysFlag:
            bc = self.Img.bcolors
            print(f"{bc.Yellow_f}{bc.BOLD}[KEY]{bc.RESET}   {msg}{bc.RESET}")

    # ------------------------------------------------------------------
    # IR Remote
    # ------------------------------------------------------------------
    def _setup_ir_callbacks(self):
        """
        Registers callback functions for handling IR remote control signals. Each callback
        is associated with a specific button on the remote and posts a corresponding
        Pygame event when triggered. These events simulate keyboard key presses to
        control the application, such as playback, volume, and other functionalities.

        Raises:
            pygame.event.Event: Posts a specific Pygame event for each registered
            callback function.

        Parameters:
            None

        Returns:
            None
        """
        # PWR - Quit program using the built-in pygame event pygame.QUIT
        self.ir_remote.register_callback('PWR', lambda: pygame.event.post(pygame.event.Event(pygame.QUIT)), False)

        # PLAY_NEXT - Next video pygame.K_n
        self.ir_remote.register_callback('PLAY_NEXT', lambda: pygame.event.post(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0)), False)

        # PLAY_PREV - Previous video pygame.K_BACKSPACE
        self.ir_remote.register_callback('PLAY_PREV', lambda: pygame.event.post(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, mod=0)), False)

        # PLAY_PAUSE
        # button name is loaded last.  Register both so either name fires K_p.
        self.ir_remote.register_callback('PLAY_PAUSE', lambda: pygame.event.post(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p, mod=0)), False)
        # OK button
        self.ir_remote.register_callback('OK', lambda: pygame.event.post(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p, mod=0)), False)

        # SPEED+ - Increase playback speed
        self.ir_remote.register_callback('SPEED+', lambda: pygame.event.post(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_KP_PLUS, mod=0)), False)

        # SPEED- - Decrease playback speed
        self.ir_remote.register_callback('SPEED-', lambda: pygame.event.post(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_KP_MINUS, mod=0)), False)

        # LOOP - Toggle single video loop pygame.K_l
        #self.ir_remote.register_callback('LOOP', lambda: pygame.event.post(
        #    pygame.event.Event(pygame.KEYDOWN, key=pygame.K_l, mod=0)), False)

        # RESTART - Restart video to beginning pygame.K_r
        #self.ir_remote.register_callback('RESTART', lambda: pygame.event.post(
        #    pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r, mod=0)), False)

        # MENU - Open goto-image dialog
        self.ir_remote.register_callback('MENU', lambda: pygame.event.post(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m, mod=0)), False)

        # REW - Backspace in goto dialog (also mapped to K_BACKSPACE globally)
        self.ir_remote.register_callback('REW', lambda: pygame.event.post(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, mod=0)), False)

        # Number buttons 0-9
        _digit_keys = {
            '0': pygame.K_0, '1': pygame.K_1, '2': pygame.K_2, '3': pygame.K_3,
            '4': pygame.K_4, '5': pygame.K_5, '6': pygame.K_6, '7': pygame.K_7,
            '8': pygame.K_8, '9': pygame.K_9,
        }
        for btn, key in _digit_keys.items():
            self.ir_remote.register_callback(btn,
                (lambda k: lambda: pygame.event.post(
                    pygame.event.Event(pygame.KEYDOWN, key=k, mod=0)))(key), False)

    # ------------------------------------------------------------------
    # Main event loop
    # ------------------------------------------------------------------

    def wait_for_advance(self) -> str:
        """
        Block the calling thread using pygame.event.wait() until it is time
        to advance to the next or previous image.  Because the thread is truly
        sleeping between events, CPU usage is ~0% during both the normal
        inter-slide delay and while the slideshow is paused.

        The slideshow timer fires every opts.delayTime ms and triggers a normal
        forward advance.  Mouse/keyboard input can trigger an early forward or
        backward advance.  When paused the timer is stopped, so only user input
        wakes the thread.

        Returns 'forward' or 'backward'.
        """
        # Restart the timer from zero so this image always gets its full configured
        # delay, regardless of how quickly the previous image was navigated away from.
        # Then clear any stale timer events that fired during image load/scale.
        if not self.Img.paused:
            pygame.time.set_timer(self.timer_event, self.timer_interval)
        pygame.event.clear([self.timer_event])
        while True:
            event = pygame.event.wait()
            if event.type == pygame.QUIT:
                self.Img.quit()
            elif event.type == self.timer_event:
                return 'forward'
            elif event.type == pygame.KEYDOWN:
                result = self.handle_keydown(event)
                if result is not None:
                    return result
            elif event.type == pygame.MOUSEBUTTONDOWN:
                result = self.handle_mousebutton(event)
                if result is not None:
                    return result
            elif event.type == pygame.MOUSEWHEEL:
                result = self.handle_mousewheel(event)
                if result is not None:
                    return result
            elif event.type == self.display_event_timeout:
                self.status.on_timeout()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def handle_timerEvent(self) -> None:
        """Placeholder — rendering is now done directly in PlayMedia.play()."""
        pass

    def handle_keydown(self, event) -> None:
        """Handle pygame keypress events."""
        key = pygame.key.name(event.key)
        if key == "q" or event.key == pygame.K_ESCAPE:
            self._debug_key(f"key='{key}'  →  QUIT")
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif event.key == pygame.K_g and pygame.key.get_mods() & pygame.KMOD_SHIFT:
            # Shift+G: flat average grayscale (no luminance weighting)
            self.Img.opts.grayscaleFlag = False
            self.Img.opts.grayscalePlFlag = not self.Img.opts.grayscalePlFlag
            self.Img.refresh_display(self)
            self.status.show_message(f"Grayscale Flat {'Enabled' if self.Img.opts.grayscalePlFlag else 'Disabled'}", tag='GrayscaleFlat', duration=2000)
        elif event.key == pygame.K_g:
            # G: BT.709 luminance-weighted grayscale
            self.Img.opts.grayscalePlFlag = False
            self.Img.opts.grayscaleFlag = not self.Img.opts.grayscaleFlag
            self.Img.refresh_display(self)
            self.status.show_message(f"Grayscale {'Enabled' if self.Img.opts.grayscaleFlag else 'Disabled'}", tag='Grayscale', duration=2000)
        elif event.key == pygame.K_KP_PLUS:
            current = self.Img.opts.delayTime
            # If below the step size (i.e. at the 30ms floor), snap up to 500ms
            # rather than 30 + 500 = 530.
            if current < 500:
                new_delay = 500
            else:
                new_delay = min(current + 500, 60000)
            self.Img.opts.delayTime = new_delay
            self.timer_interval = new_delay
            if not self.Img.paused:
                pygame.time.set_timer(self.timer_event, self.timer_interval)
            self._debug_key(f"key='KP+'  →  delay +500ms = {new_delay}ms")
            self.status.show_message(f"Delay: {new_delay} ms", tag='delay', duration=2000)
        elif event.key == pygame.K_KP_MINUS:
            current = self.Img.opts.delayTime
            # If at or below one step, drop to the hard floor of 30ms.
            if current <= 500:
                new_delay = 30
            else:
                new_delay = current - 500
            self.Img.opts.delayTime = new_delay
            self.timer_interval = new_delay
            if not self.Img.paused:
                pygame.time.set_timer(self.timer_event, self.timer_interval)
            self._debug_key(f"key='KP-'  →  delay -500ms = {new_delay}ms")
            self.status.show_message(f"Delay: {new_delay} ms", tag='delay', duration=2000)
        elif event.key == pygame.K_i:
            self.info_splash.enabled = not self.info_splash.enabled
            self._debug_key(f"key='i'  →  info splash {'on' if self.info_splash.enabled else 'off'}")
            self._redraw_current_frame()
        elif event.key == pygame.K_p:
            new_state = not self.Img.paused
            self._toggle_pause()
            return None
        elif event.key == pygame.K_m:
            return self._show_goto_dialog()
        elif event.key == pygame.K_SPACE:
            self.status.show_nav('next')
            return 'forward'
        elif event.key == pygame.K_BACKSPACE:
            self.status.show_nav('prev')
            return 'backward'
        else:
            self._debug_key(f"key='{key}'  →  unhandled")

    def handle_mousebutton(self, event) -> str | None:
        """
        Handle pygame mouse button events.

        Button priority order:
          L + R simultaneously  →  quit
          Middle (button 2)     →  pause / unpause toggle
          Left   (button 1)     →  next image
          Right  (button 3)     →  previous image

        event.button is used for single-button detection because it is captured
        at event-fire time.  pygame.mouse.get_pressed() is used only for the
        L+R combo since that requires knowing the live state of both buttons.

        Returns 'forward', 'backward', or None (no advance needed).
        """
        # L+R simultaneously: check live button state (both must be held)
        mouseButton = pygame.mouse.get_pressed(3)
        if mouseButton[LEFT] and mouseButton[RIGHT]:
            self._debug_mouse(f"MOUSEBUTTONDOWN  button=L+R  pos={event.pos}  →  QUIT")
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            return None
        # Single-button cases: use event.button (1=left, 2=middle, 3=right)
        if event.button == 2:
            new_state = not self.Img.paused
            self._debug_mouse(
                f"MOUSEBUTTONDOWN  button=2 (middle)  pos={event.pos}"
                f"  →  pause toggle  (paused={new_state})")
            self._toggle_pause()
            return None
        elif event.button == 1:
            self._debug_mouse(f"MOUSEBUTTONDOWN  button=1 (left)   pos={event.pos}  →  forward (next)")
            self.status.show_nav('next')
            return 'forward'
        elif event.button == 3:
            self._debug_mouse(f"MOUSEBUTTONDOWN  button=3 (right)  pos={event.pos}  →  backward (prev)")
            self.status.show_nav('prev')
            return 'backward'
        self._debug_mouse(f"MOUSEBUTTONDOWN  button={event.button}  pos={event.pos}  →  unhandled")
        return None

    def handle_mousewheel(self, event) -> str | None:
        """
        Handle pygame mousewheel events.

          Wheel up   (event.y > 0)  →  next image
          Wheel down (event.y < 0)  →  previous image

        event.y is compared with > / < 0 rather than == ±1 because fast
        scrolling can produce values of 2, 3, etc.

        Returns 'forward', 'backward', or None.
        """
        if event.y > 0:
            self._debug_mouse(f"MOUSEWHEEL  x={event.x}  y={event.y}  →  forward (next)")
            self.status.show_nav('next')
            return 'forward'
        elif event.y < 0:
            self._debug_mouse(f"MOUSEWHEEL  x={event.x}  y={event.y}  →  backward (prev)")
            self.status.show_nav('prev')
            return 'backward'
        self._debug_mouse(f"MOUSEWHEEL  x={event.x}  y={event.y}  →  unhandled")
        return None

    # ------------------------------------------------------------------
    # Goto-image dialog
    # ------------------------------------------------------------------

    def _show_goto_dialog(self) -> str | None:
        """
        Modal digit-entry dialog for jumping to an image by number.

        MENU (K_m)         — open/cancel
        0-9                — append digit (clamped to max digits needed)
        BACKSPACE / REW    — delete last digit
        RETURN / KP_ENTER  — confirm and jump

        Returns 'goto' if a valid jump was made, None if cancelled.
        The caller (handle_keydown) propagates the return value so that
        wait_for_advance() re-enters the slideshow loop at the new index.
        """
        total       = len(self.Img.mediaList)
        max_digits  = len(str(total))
        digits      = []

        # Stop the slideshow timer while dialog is open
        pygame.time.set_timer(self.timer_event, 0)
        pygame.event.clear([self.timer_event])

        # Render constants derived from display size
        win         = self.Img.Win
        dw, dh      = win.get_size()
        font        = self.status._font          # reuse StatusDisplay's already-loaded font
        padding     = max(10, dh // 70)
        shadow_off  = 1
        corner_r    = max(4, dh // 80)
        BOX_BG      = (0, 0, 0, 180)
        C_LABEL     = (190, 190, 190)
        C_INPUT     = (255, 255, 255)
        C_HINT      = (120, 120, 120)
        C_SHADOW    = (0, 0, 0)

        def _draw():
            input_str = ''.join(digits) if digits else '_'
            hint_str  = f"(1 – {total})"
            label_str = "Go to image:"

            label_s  = font.render(label_str, True, C_LABEL)
            input_s  = font.render(input_str, True, C_INPUT)
            hint_s   = font.render(hint_str,  True, C_HINT)

            content_w = max(label_s.get_width(), input_s.get_width() + hint_s.get_width() + padding)
            content_h = label_s.get_height() + padding // 2 + input_s.get_height()
            box_w     = content_w + padding * 2
            box_h     = content_h + padding * 2
            box_x     = (dw - box_w) // 2
            box_y     = int(dh * 0.40)

            # Restore clean background before drawing dialog
            if self.status._saved_bg is not None:
                win.blit(self.status._saved_bg, (0, 0))
            else:
                win.fill((0, 0, 0))

            bg_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            pygame.draw.rect(bg_surf, BOX_BG, bg_surf.get_rect(), border_radius=corner_r)
            win.blit(bg_surf, (box_x, box_y))

            # Label row
            lx, ly = box_x + padding, box_y + padding
            shd = font.render(label_str, True, C_SHADOW)
            win.blit(shd,     (lx + shadow_off, ly + shadow_off))
            win.blit(label_s, (lx, ly))

            # Input + hint on same row below label
            iy = ly + label_s.get_height() + padding // 2
            shd = font.render(input_str, True, C_SHADOW)
            win.blit(shd,     (lx + shadow_off, iy + shadow_off))
            win.blit(input_s, (lx, iy))
            hx = lx + input_s.get_width() + padding
            win.blit(hint_s,  (hx, iy + (input_s.get_height() - hint_s.get_height()) // 2))

            pygame.display.update()

        _draw()

        # Dialog event loop
        while True:
            event = pygame.event.wait()

            if event.type == pygame.QUIT:
                self.Img.quit()

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_p):
                    # K_p = OK button on remote (shares code with PLAY_PAUSE)
                    if digits:
                        n = int(''.join(digits))
                        n = max(1, min(n, total))          # clamp to valid range
                        self.Img.currImgIndx = n - 2       # play() increments before loading
                        self.Img.backwardsFlag = False
                        # Restart timer for the new image
                        if not self.Img.paused:
                            pygame.time.set_timer(self.timer_event, self.timer_interval)
                        return 'forward'
                    # Empty input — treat as cancel
                    break

                elif event.key == pygame.K_m:              # MENU cancels
                    break

                elif event.key == pygame.K_BACKSPACE:
                    if digits:
                        digits.pop()
                    _draw()

                elif pygame.K_0 <= event.key <= pygame.K_9:
                    if len(digits) < max_digits:
                        digits.append(chr(event.key))
                    _draw()

            elif event.type == self.display_event_timeout:
                self.status.on_timeout()

        # Cancelled — restore display and restart timer
        if self.Img.scaled_bg is not None:
            win.fill((0, 0, 0))
            win.blit(self.Img.scaled_bg, self.Img.bg_rect)
            self.info_splash.draw()
            pygame.display.update()
            self.status.update_background()
        if not self.Img.paused:
            pygame.time.set_timer(self.timer_event, self.timer_interval)
        return None

    # ------------------------------------------------------------------
    # Full-frame composite redraw
    # ------------------------------------------------------------------

    def _redraw_current_frame(self) -> None:
        """
        Re-composite the current image with all active overlays and push it
        to the display in one shot.  Used by toggle operations (info splash,
        future toggles) so the change is visible immediately without waiting
        for the next image advance.
        """
        if self.Img.scaled_bg is None:
            return
        self.Img.Win.fill((0, 0, 0))
        self.Img.Win.blit(self.Img.scaled_bg, self.Img.bg_rect)
        self.info_splash.draw()
        pygame.display.update()
        self.status.update_background()

    # ------------------------------------------------------------------
    # Pause
    # ------------------------------------------------------------------

    def _toggle_pause(self) -> None:
        """
        Toggle the paused state of the slideshow.

        Pausing stops the pygame timer entirely so wait_for_advance() sleeps
        with ~0% CPU until the user interacts.  Unpausing restarts the timer
        with the original interval so the slide advances after the full delay.

        A brief "PAUSED" / "PLAYING" flash is shown via StatusDisplay.
        If InfoSplash is visible the filename colour changes to yellow (paused)
        or white (playing) immediately via a partial display.update().
        """
        self.Img.paused = not self.Img.paused
        if self.Img.paused:
            pygame.time.set_timer(self.timer_event, 0)   # stop timer → no wakeups
            self.status.show_message('PAUSED', tag='pause', duration=1500)
        else:
            pygame.time.set_timer(self.timer_event, self.timer_interval)
            self.status.show_message('PLAYING', tag='pause', duration=1000)
        # Update the info splash filename colour immediately (partial redraw).
        self.info_splash.paused = self.Img.paused
        self.info_splash.redraw_paused(self.status)
