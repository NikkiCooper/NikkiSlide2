#  FindVideos.py Copyright (c) 2025 Nikki Cooper
#
#  This program and the accompanying materials are made available under the
#  terms of the GNU Lesser General Public License, version 3.0 which is available at
#  https://www.gnu.org/licenses/gpl-3.0.html#license-text
#
import os
import random

class FindMedia:
	def __init__(self, opts: object, pathList: list) -> None:
		"""
		Class with methods that will search for supported media
		in the user supplied directories given on the command line.
		All found media files are listed in self.mediaList
		:param opts: Contains our variable flags base on options given on the command line.
		:type opts:
		:param pathList:  A list which contains all user directories specified on the command line.
		:type pathList:
		"""
		self.opts = opts
		self.pathList = pathList
		self.mediaList  = []
		self.tmpList = []
		self.ignoreList = []
		self.numMedia = self.getMedia()
		'''
		There are no entries in self.mediaList,
		so no point in continuing.
		Just exit the program instead.
		'''
		if len(self.mediaList) == 0:
			print("No playable media files were found.  Exiting.")
			exit(128)

		if opts.shuffle_flag:
			self.shuffle()

		if opts.printIgnoreList or opts.printmediaList:
			if opts.printIgnoreList:
				self.print_ignores()
			if opts.printmediaList:
				self.mediaList_print()
			exit()

	def getMedia(self):
		"""
		Method that iterates through a list of user supplied paths
		looking for supported videos.  If any are found, they are appended
		to self.videoList.  This method is called by the class constructor.
		:return:
		:rtype:
		"""
		for mediaDir in self.pathList:
			# print(f"videoDirs: {videoDirs}")
			self.recursive(
						    mediaDir,
							recurse=False if self.opts.norecurse_flag is True else True,
			                disableGIF=True if self.opts.disableGif_flag is True else False,
			                ignore=True if self.opts.ignFlag is True else False
			              )
		return len(self.mediaList)

	def recursive(self, dpath: str, recurse: bool = False, ignore: bool = False, disableGIF: bool = False) -> None:
		"""
		A method that recurses into a directory structure looking for media files.
		If a supported media file is found, the path/filename of this file is appended to a
		list called 'self.videoList'. This list contains the master path/filenamess of
		all videos that will be played.

		:param str self, dpath:  Path containing the directory to recurse into.
		:param bool recurse:    Flag to tell the function whether it should recurse into 'dpath' (recurse=True).
		:param bool ignore:     Flag if set to True will ignore all directories containing .ignore files
		:param bool disableGIF: Flag if set to True, disables GIF support.
		:return:                None. However, it will append found and supported media path/filenames to self.videoList
		:rtype: None
		"""
		# Supported extensions.
		ext = ('.jpg', 'png', 'bmp', '.gif', '.jpeg', 'jpe')
		#ext = ['.vob', '.mp4', '.mkv', '.mov', '.avi', '.flv', '.wmv', '.webm', '.3gp', '.gif']

		# Remove '.gif' from the ext list if the opts['disableGif_flag'] is set
		if disableGIF:
			ext = [e for e in ext if e != '.gif']

		files = os.listdir(dpath)
		files.sort()
		for obj in files:
			if os.path.isfile(os.path.join(dpath, obj)):
				file = os.path.join(dpath, obj)
				file_lower = file.lower()
				# If directory has a file called '.ignore',
				# The contents of this directory are ignored.
				if not ignore:
					if '.ignore' in file_lower:
						if file_lower.endswith('.ignore'):
							self.ignoreList.append(file)
						break
				if file_lower.endswith(tuple(ext)):
					# Append our path/file to videoList
					self.mediaList.append(file)
			elif os.path.isdir(os.path.join(dpath, obj)):
				_dr = os.path.join(obj)
				# Ignore hidden directories
				if not _dr.startswith('.'):
					if recurse:
						self.recursive(os.path.join(dpath, obj), recurse, ignore, disableGIF)

	def shuffle (self):
		random.shuffle(self.mediaList)

	def sort(self):
		self.mediaList.sort()

	def mediaList_size(self):
		return len(self.mediaList)

	def mediaList_print(self):
		if self.mediaList_size() == 0:
			return
		else:
			print("\nContents of videoList:")
			for media in self.mediaList:
				print(media)
			print(f"Total number of entries in the mediaList: {len(self.mediaList)}\n\n")

	def print_ignores(self):
		if len(self.ignoreList) == 0:
			return
		else:
			print("\nContents of ignoreList:")
			for entry in self.ignoreList:
				print(entry)
			print(f"Total number of entries in the ignoreList: {len(self.ignoreList)}\n\n")

