#   ns.py Copyright (c) 2025 Nikki Cooper
#
#  This program and the accompanying materials are made available under the
#  terms of the GNU Lesser General Public License, version 3.0 which is available at
#  https://www.gnu.org/licenses/gpl-3.0.html#license-text
#
import os
from _version import __version__
import warnings
warnings.filterwarnings('ignore',
						category=UserWarning,
						message='pkg_resources is deprecated as an API.*')
warnings.filterwarnings('ignore',
						category=RuntimeWarning,
						message='Your system is avx2 capable but pygame was not built with support for it.*')
from Bcolors import Bcolors
from cliOpts import cliOptions
from PlayMedia import PlayMedia
from EventHandler import EventHandler
from FindMedia import FindMedia
from StartupSplash import StartupSplash

def main():
	# Create a Bcolors instance to give us colors in the console.
	bcolors = Bcolors()
	#bcolors.clear()
	program_path = __file__
	program_name = os.path.basename(program_path)
	# Retrieve all command line arguments and default variables, as well as user specified directories
	print(
		f"{bcolors.RESET}\n{bcolors.Green_f}NikkiSlide "
		f"version {bcolors.Cyan_f}{__version__}{bcolors.RESET}"
		f" An image slideshow for Linux by Nikki Cooper.{bcolors.RESET}")


	opts, pathList = cliOptions(bcolors)
	# Create a FindVideos instance, populate Videos.videoList with the path/filename of all found playable media.
	images = FindMedia(opts, pathList)
	# Create a Play instance, pass our cli arguments and variables to it, also pass our mediaList created
	# by FindMedia().  Finally, pass a bcolors object to it so we can have some colors in the console.
	playImage = PlayMedia(opts, images.mediaList, bcolors)
	# Clear the console screen
	bcolors.clear()
	# Create an instance of a pygame EventHandler and run it.
	eventHandler = EventHandler(playImage)
	# Show the startup splash (auto-dismisses after 3.5 s).
	StartupSplash(playImage.Win, opts).show(__version__)
	# Finally, play all the images that are specified in playImage.mediaList
	playImage.play(eventHandler)

if __name__ == "__main__":
	main()

