#  PlayMedia.py Copyright (c) 2025 Nikki Cooper
#
#  This program and the accompanying materials are made available under the
#  terms of the GNU Lesser General Public License, version 3.0 which is available at
#  https://www.gnu.org/licenses/gpl-3.0.html#license-text
#
import os
import platform

# This must be called BEFORE importing pygame
# else set it in ~/.bashrc
# Or run it from the command line:
# PYGAME_HIDE_SUPPORT_PROMPT=1 pyvid [options] (more trouble than what its worth)
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import sys
import time
import random
import pygame
from pygame.locals import *
from fractions import Fraction
import numpy as np
from PIL import Image as pImage
from datetime import datetime as _datetime


def _read_exif_datetime(path: str) -> str | None:
	"""
	Read EXIF DateTimeOriginal (0x9003) or DateTimeDigitized (0x9004) from a JPEG.
	Returns the date/time formatted as MM/DD/YYYY  HH:MM:SS AM/PM, or None if
	the tag is absent, corrupt, or the camera clock was clearly bogus.

	Note: these tags live in the ExifIFD sub-IFD (0x8769), not IFD0.
	img.getexif() only returns IFD0; get_ifd(0x8769) is required.
	"""
	try:
		with pImage.open(path) as img:
			exif_ifd = img.getexif().get_ifd(0x8769)
		for tag_id in (0x9003, 0x9004):
			raw = exif_ifd.get(tag_id)
			if raw is None:
				continue
			try:
				dt = _datetime.strptime(str(raw).strip(), "%Y:%m:%d %H:%M:%S")
				if not (1970 <= dt.year <= _datetime.now().year + 1):
					continue   # clock was never set or tag is garbage
				return dt.strftime("%m/%d/%Y  %I:%M:%S %p")
			except ValueError:
				continue       # malformed value — try next tag
	except Exception:
		pass                   # unreadable file or no EXIF — silent fallback
	return None


class PlayMedia:
	def __init__(self, opts, mediaList, bcolors):
		"""
		A class which plays videos
		:param opts: Contains all of our command line argument flags
		:type opts:
		:param mediaList: A list which has all the path/filenames of the vids to be played
		:type mediaList:
		:param bcolors:   Class object to give colors in the python console
		:type bcolors:
		"""
		# A list containing the path/filenames of each video to be played
		self.mediaList = mediaList
		self.opts = opts
		self.bcolors = bcolors
		self.image = None
		self.imageFile = ""
		self.img = True
		self.errHdr = None
		self.scaled_bg = None
		self.bg_rect = None
		self.errCnt = 0
		self.refresh = False
		self.imageCount = 0
		self.imgWidth = 0
		self.imgHeight = 0
		self.doScaledToFill = False
		self.imgAspectRatio = 0
		self.targetImgAspectRatio = 0
		self.deltaRatio = 0
		self.imageBPP = 0
		self.scaledToFillLimit: float = 0.125
		#self.scaledToFillLimit: float = 0.280
		self.smoothscaleBackend = ""

		# index to access the video elements in self.vidoeList
		self.currImgIndx = -1
		self.lastImgIndx = -1
		# Flag that denotes we are wanting to play a previously played video.
		self.backwardsFlag = False
		# Flag that denotes we are wanting to play the next video
		self.forwardsFlag = False
		self.paused = False
		# Set some environment variables BEFORE initializing pygame
		self.__setEnvironment()
		# Initialize pygame

		pygame.init()
		pygame.transform.set_smoothscale_backend(self.smoothscaleBackend)
		#self.bcolors.clear()
		self.dFlags = pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.NOFRAME
		self.Win = pygame.display.set_mode((0, 0), self.dFlags, 24)
		self.clock = pygame.time.Clock()
		self.displayWidth = self.Win.get_width()
		self.displayHeight = self.Win.get_height()

		''' 
		Setup some fonts to be used by the status bar.
		ToDo:  Setup some default backup fonts incase my choice of fonts are not installed.
		'''
		#self.font = pygame.font.SysFont("Roboto-Condensed-RegularItalic", 26)
		'''
		self.font_italic = pygame.font.Font('/usr/share/fonts/truetype/roboto/unhinted/RobotoCondensed-Italic.ttf', 18)
		self.font_regular = pygame.font.Font('/usr/share/fonts/truetype/roboto/unhinted/RobotoCondensed-Regular.ttf', 18)
		'''

	@staticmethod
	def quit():
		"""
		Method to quit pygame and then exit the application.
		:return:
		:rtype:
		"""
		pygame.quit()
		exit()

	def __setEnvironment(self):
		"""
		Method to set necessary environment variables.

		PYGAME_DISPLAY priority:
		  1. --display / -D CLI option (if provided)
		  2. PYGAME_DISPLAY already set in the environment
		  3. Not set — SDL uses the display the program was launched from
		"""
		# Display selection
		if self.opts.displayNum is not None:
			os.environ["PYGAME_DISPLAY"] = str(self.opts.displayNum)
		# else: honour existing PYGAME_DISPLAY or let SDL choose

		# For multi-monitor setups, prevent the window minimising on focus loss.
		os.environ["SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS"] = "0"

		# Smoothscale backend — SSE/MMX are x86-only; ARM (Raspberry Pi) needs GENERIC.
		if "SMOOTHSCALE_BACKEND" in os.environ:
			# Explicit override always wins.
			self.smoothscaleBackend = os.environ["SMOOTHSCALE_BACKEND"]
		elif platform.machine().lower().startswith(('arm', 'aarch')):
			self.smoothscaleBackend = 'GENERIC'
		else:
			self.smoothscaleBackend = 'SSE'

	@staticmethod
	def update():
		"""
		Helper method to update the pygame screen
		:return:
		:rtype:
		"""
		pygame.display.update()

	def printError(self):
		iFile = f"{os.path.basename(self.imageFile)}"
		print(
			f"{self.bcolors.DESC}Image: {self.bcolors.L_Blue_f}{iFile}{self.bcolors.DESC} "
			f"[{self.bcolors.FAIL}{self.errHdr}{self.bcolors.DESC}]{self.bcolors.Default_f}"
		)

		del self.mediaList[self.currImgIndx]
		if self.currImgIndx == 0:
			self.currImgIndx = -1
		else:
			self.currImgIndx -= 1
		self.imageCount = len(self.mediaList)

	def __getBPP(self,imageF):
		"""
		Gets the Bits Per Pixel of an image.  This is a measure of the color or intensity information
		stored for each pixel in an image.  It represents the depth of color or grayscale levels that
		can be displayed in the image. Also retrieves the image width and height.

		:param str imageF: The path/filename of the image.
		:return:
		:rtype: int
		"""
		try:
			mode2bpp = {"1": 1, "L": 8, "LA": 8, "P": 8, "RGB": 24, "RGBA": 32,
						"CMYK": 32, "YCbCr": 24, "LAB": 24, "HSV": 24, "I": 32, "F": 32}

			with pImage.open(imageF) as im:
				im.verify()  # Check the image integrity
				return mode2bpp[im.mode]
		except KeyError:
			return 0     # Handle unsupported modes
		except Exception as e:
			print(f"Error: {e}")
			return 0      # Handle general errors
		finally:
			if im is not None:
				im.close()

	def __to_grayscale(self, img, preserve_luminance=True):
		"""
		Convert a pygame Surface to grayscale.
		:param Surface img: Source image surface.
		:param bool preserve_luminance: True → BT.709 weighted (perceptually correct).
		                                False → flat channel average.
		:return: Grayscale pygame Surface, or None on error.
		"""
		try:
			arr = pygame.surfarray.array3d(img)
			if preserve_luminance:
				mean_arr = np.dot(arr, [0.2126, 0.7152, 0.0722])
			else:
				mean_arr = np.mean(arr, axis=2)
			new_arr = np.repeat(mean_arr[..., np.newaxis], 3, axis=2)
			return pygame.surfarray.make_surface(new_arr)
		except:
			return None

	def __check_aspect_ratio(self, img_aspect_ratio, target_aspect_ratio):
		return abs(round((img_aspect_ratio - target_aspect_ratio), 3)) <= round(self.scaledToFillLimit, 3)

	def __scaledToFill(self, _img, size):
		"""
		Resizes a surface object to fill the entire display without clipping.
		:param Surface _img: A pygame surface object.
		:param tuple size:  A tuple containing the image width & height.
		:return: tuple[Surface, tuple[int, int]]
		:rtype: tuple[Surface, tuple[int, int]]
		"""
		scaled_image = pygame.transform.scale(_img, size)
		image_rect = (0, 0)
		return scaled_image, image_rect

	def __getScale(self, _image, sWidth, sHeight):
		"""
		Returns the scaled size of an image given a desired Width and a desired Height.
		:param object _image: A pygame image object.
		:param int sWidth:    Desired width to scale to in pixels.
		:param int sHeight:   Desired height to scale to in pixels.
		:return: tuple[Scaled_Width, Scaled_Height]
		:rtype: tuple[int,int]
		"""
		iwidth, iheight = _image.get_size()
		scale = min((sWidth / iwidth), (sHeight / iheight))
		new_size = (round(iwidth * scale), round(iheight * scale))
		return new_size




	def transformScaleKeepRatio(self, img, size, bpp):
		"""
		A function that scales an  image object from one size to another keeping its aspect ratio.
		:param Surface img: An image object containing the image to be scaled
		:param tuple size: List containing the display width & height.
		:param int bpp: The BPP of the image.
		:return:  tuple[Surface, Rect] | None
		:raises FileNotFoundError: Returns None if img doesn't exist.
		"""
		dispWidth = size[0]
		dispHeight = size[1]
		try:
			new_size = self.__getScale(img, dispWidth, dispHeight)
			if bpp < 24:
				scaled_image = pygame.transform.scale(img, new_size)
			else:
				scaled_image = pygame.transform.smoothscale(img, new_size)
			image_rect = scaled_image.get_rect(center=((dispWidth // 2), (dispHeight // 2)))
			return scaled_image, image_rect
		except FileNotFoundError:
			return None

	def playImage(self, _Image):
		self.ImageFile = _Image
		"""
		Method that creates a pygame image object. Called by self.play()
		:param media:   Path/Filename of media to play
		:type media: str
		:return: An instance of a  image object
		:rtype: object
		"""

		try:
			self.img = False
			self.image = pygame.image.load_extended(self.ImageFile).convert()
			self.img = True
			return self.image
		except pygame.error:
			self.img = False
			self.errHdr = "BAD FILE!"
			self.errCnt += 1
			self.printError()
			return None

	def refresh_display(self, eventHandler):
		"""Re-render the current image with the current filter state.
		Call after toggling grayscale (or any other filter) mid-slide so the
		change is visible immediately without waiting for the next advance.
		Must be called before status.show_message() so update_background()
		captures the clean image before the status overlay is drawn on top.
		"""
		if self.image is None:
			return
		if self.doScaledToFill and self.opts.scaledToFillFlag:
			if self.opts.grayscaleFlag:
				self.scaled_bg, self.bg_rect = self.__scaledToFill(self.__to_grayscale(self.image, preserve_luminance=True), self.Win.get_size())
			elif self.opts.grayscalePlFlag:
				self.scaled_bg, self.bg_rect = self.__scaledToFill(self.__to_grayscale(self.image, preserve_luminance=False), self.Win.get_size())
			else:
				self.scaled_bg, self.bg_rect = self.__scaledToFill(self.image, self.Win.get_size())
		else:
			if self.opts.grayscaleFlag:
				self.scaled_bg, self.bg_rect = self.transformScaleKeepRatio(self.__to_grayscale(self.image, preserve_luminance=True), self.Win.get_size(), self.imageBPP)
			elif self.opts.grayscalePlFlag:
				self.scaled_bg, self.bg_rect = self.transformScaleKeepRatio(self.__to_grayscale(self.image, preserve_luminance=False), self.Win.get_size(), self.imageBPP)
			else:
				self.scaled_bg, self.bg_rect = self.transformScaleKeepRatio(self.image, self.Win.get_size(), self.imageBPP)
		self.Win.fill((0, 0, 0))
		self.Win.blit(self.scaled_bg, self.bg_rect)
		eventHandler.info_splash.draw()
		pygame.display.update()
		eventHandler.status.update_background()

	def play(self, eventHandler):
		"""
		Method to play the slideshow images that are listed in self.mediaList.
		The method will exit once all the videos in self.mediaList are played
		unless the commandline argument --loop is given.
		:param eventHandler:
		:type eventHandler:
		:return:
		:rtype:
		"""
		while True:
			self.currImgIndx = -1
			while self.currImgIndx < len(self.mediaList) - 1:
				self.refresh = True
				self.forwardsFlag = False
				if not self.backwardsFlag:
					self.lastImgIndx = self.currImgIndx
					self.currImgIndx += 1
				else:
					if self.currImgIndx < 0:
						self.currImgIndx = 0
					self.backwardsFlag = False
					if self.currImgIndx > 0:
						self.currImgIndx -= 1
				if self.currImgIndx == len(self.mediaList):
					break
				self.imageFile = self.mediaList[self.currImgIndx]

				self.image = self.playImage(self.imageFile)
				if self.image is None:
					continue

				#eventHandler.handle_events()

				self.imageBPP = self.__getBPP(self.ImageFile)
				self.imgWidth, self.imgHeight = self.image.get_size()

				if self.opts.landscapeFlag or self.opts.portraitFlag:
					if self.opts.landscapeFlag:
						if self.imgWidth < self.imgHeight:
							del self.mediaList[self.currImgIndx]
							if self.currImgIndx == 0:
								self.currImgIndx = -1
							else:
								self.currImgIndx -=1
							self.imageCount = len(self.mediaList)
							#print(f"[LS] self.imageCount: {self.imageCount}")
							continue
					elif self.opts.portraitFlag:
						if self.imgHeight < self.imgWidth:
							#print(f"self.currImgIndx: {self.currImgIndx}")
							del self.mediaList[self.currImgIndx]
							if self.currImgIndx == 0:
								self.currImgIndx = -1
							else:
								self.currImgIndx -= 1
							self.imageCount = len(self.mediaList)
							#print(f"[PS] self.imageCount: {self.imageCount}")
							continue

				self.imgAspectRatio = round(self.imgWidth / self.imgHeight, 3)
				self.targetImgAspectRatio = round(self.Win.get_width() / self.Win.get_height(), 3)
				self.deltaRatio = abs(round(self.imgAspectRatio - self.targetImgAspectRatio,3))
				#print(f"imageFile: {self.imageFile}, imgAspectRatio: {self.imgAspectRatio}, targetImgAspectRatio: {self.targetImgAspectRatio}, deltaRatio: {self.deltaRatio}")

				self.doScaledToFill = self.__check_aspect_ratio(self.imgAspectRatio, self.targetImgAspectRatio)
				if self.opts.scaledToFillFlag:
					if self.opts.scaleToFillOnlyFlag:
						if not self.doScaledToFill:
							del self.mediaList[self.currImgIndx]
							if self.currImgIndx == 0:
								self.currImgIndx = -1
							else:
								self.currImgIndx -= 1
							self.imageCount = len(self.mediaList)
							continue
				iFile = ("%s" % self.imageFile) if not self.opts.omitPathsFlag else "%s" % (os.path.basename(self.imageFile))
				errHdr = "BAD FILE!" if self.imageBPP == 0 else "8-BPP!"
				if self.opts.grayscaleFlag or self.opts.grayscalePlFlag or self.imageBPP == 0:
					if self.imageBPP < 24:
						self.errCnt += 1
						print(
							"%sImage: %s%s%s (%s%s%s)%s"
							% (
								self.bcolors.DESC
								, self.bcolors.L_Blue_f
								, iFile
								, self.bcolors.DESC
								, self.bcolors.FAIL
								, errHdr
								, self.bcolors.DESC
								, self.bcolors.Default_f
							)
						)
						del self.mediaList[self.currImgIndx]
						if self.currImgIndx == 0:
							self.currImgIndx = -1
						else:
							self.currImgIndx -= 1
						self.imageCount = len(self.mediaList)
						continue

				if self.doScaledToFill and self.opts.scaledToFillFlag:
					if self.opts.grayscaleFlag:
						self.scaled_bg, self.bg_rect = self.__scaledToFill(self.__to_grayscale(self.image, preserve_luminance=True), self.Win.get_size())
					elif self.opts.grayscalePlFlag:
						self.scaled_bg, self.bg_rect = self.__scaledToFill(self.__to_grayscale(self.image, preserve_luminance=False), self.Win.get_size())
					else:
						self.scaled_bg, self.bg_rect = self.__scaledToFill(self.image, self.Win.get_size())
				else:
					if self.opts.grayscaleFlag:
						self.scaled_bg, self.bg_rect = self.transformScaleKeepRatio(self.__to_grayscale(self.image, preserve_luminance=True), self.Win.get_size(), self.imageBPP)
					elif self.opts.grayscalePlFlag:
						self.scaled_bg, self.bg_rect = self.transformScaleKeepRatio(self.__to_grayscale(self.image, preserve_luminance=False), self.Win.get_size(), self.imageBPP)
					else:
						self.scaled_bg, self.bg_rect = self.transformScaleKeepRatio(self.image, self.Win.get_size(), self.imageBPP)
				# Pre-render the info splash for this image (always, even if disabled,
				# so toggling 'i' on mid-slideshow shows correct data immediately).
				exif_dt = _read_exif_datetime(self.imageFile) if self.opts.enableEXIF else None
				eventHandler.info_splash.prepare(
					self.imageFile,
					self.currImgIndx,
					len(self.mediaList),
					self.imgWidth,
					self.imgHeight,
					self.bg_rect if isinstance(self.bg_rect, pygame.Rect) else None,
					exif_datetime=exif_dt
				)
				# Display the image immediately — don't wait for the timer.
				# The timer in wait_for_advance() only controls when to *advance*,
				# not when to *show* the current image.
				if not self.opts.quietFlag:
					print(iFile)
				if self.opts.scaleToFillInfoFlag:
					print(
						"{}{}[ {} ]  "
						"{}Image aspect ratio: {}[ {:.3f} ]  "
						"{}Target aspect ratio: {}[ {:.1f} ]  "
						"{}delta: {}[ {:.3f} ]{}"
						.format(
							self.bcolors.White_f
							, (self.bcolors.Red_b + self.bcolors.BOLD + self.bcolors.White_f
							   if self.doScaledToFill is not True
							   else self.bcolors.BOLD + self.bcolors.BOOL_TRUE)
							, 'scaledToFill()' if self.doScaledToFill is True else 'scaledToFit()'
							, self.bcolors.RESET + self.bcolors.White_f
							, self.bcolors.BOLD + self.bcolors.Yellow_f
							, self.imgAspectRatio
							, self.bcolors.RESET + self.bcolors.White_f
							, self.bcolors.BOLD + self.bcolors.L_Blue_f
							, self.targetImgAspectRatio
							, self.bcolors.RESET + self.bcolors.White_f
							, (self.bcolors.Red_b + self.bcolors.White_f
							   if (self.deltaRatio > self.scaledToFillLimit) else
							   self.bcolors.Magenta_b + self.bcolors.BOLD + self.bcolors.White_f
							   if (self.deltaRatio <= 0.1250) else
							   self.bcolors.BOLD + self.bcolors.HEADER
							   if (0.1250 < self.deltaRatio <= 0.250) else
							   self.bcolors.BOLD + self.bcolors.Yellow_f
							   if (0.250 < self.deltaRatio <= self.scaledToFillLimit) else
							   self.bcolors.Red_b + self.bcolors.White_f)
							, self.deltaRatio
							, self.bcolors.RESET)
					)
				self.Win.fill((0, 0, 0))
				self.Win.blit(self.scaled_bg, self.bg_rect)
				eventHandler.info_splash.draw()   # blit only — no display.update() here
				pygame.display.update()           # one call composites everything
				# Snapshot the composite frame (image + info splash) so StatusDisplay
				# restores to the correct background when clearing its overlays.
				eventHandler.status.update_background()
				# Block until the delay timer fires or the user navigates.
				# Uses pygame.event.wait() so CPU usage is ~0% while waiting.
				direction = eventHandler.wait_for_advance()
				if direction == 'backward':
					self.backwardsFlag = True
			# End of mediaList playback loop
			if not self.opts.loopFlag:
				break
		# End of main loop
		self.quit()
