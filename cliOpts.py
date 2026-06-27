#  CliOpts.py Copyright (c) 2025 Nikki Cooper
#
#  This program and the accompanying materials are made available under the
#  terms of the GNU Lesser General Public License, version 3.0 which is available at
#  https://www.gnu.org/licenses/gpl-3.0.html#license-text
#
import os
import argparse

def cliOptions(bcolors):
    Path = []
    ap = argparse.ArgumentParser(
        usage=f"%(prog)s [options]{bcolors.BOLD}{bcolors.OKBLUE} <DIR> <DIR> <DIR> ...{bcolors.RESET}"
    )

    ap.add_argument("paths", nargs='+', metavar='DIR',
        help=f"One or more image directories")

    ap.add_argument("--loop", action="store_true", dest="loopFlag", default=False,
        help=f"Do not exit.  Loop instead.")

    ap.add_argument("--shuffle", action="store_true", dest="shuffle_flag", default=False,
        help=f"Play media in random order. {bcolors.BOLD}{bcolors.WARNING}[incompatible with --sort]{bcolors.RESET}")
    ap.add_argument("--sort", action="store_true", dest="sortFlag", default=False,
        help=f"Sort supplied image directories. {bcolors.BOLD}{bcolors.WARNING}[incompatible with --shuffle]{bcolors.RESET}")

    ap.add_argument("--disableGIF", action="store_true", dest="disableGif_flag", default=False,
        help=f"Disable playing {bcolors.Magenta_f}.GIF {bcolors.RESET}files.")

    ap.add_argument("--noIgnore", action="store_true", dest="ignFlag", default=False,
        help=f"Do not honor {bcolors.Green_f}'.ignore' {bcolors.RESET} files.")
    ap.add_argument("--noRecurse", action="store_true", dest="norecurse_flag", default=False,
        help=f"Do not recurse into the specified {bcolors.OKBLUE}<DIR>{bcolors.RESET}")

    ap.add_argument("--omitPaths", action="store_true", dest="omitPathsFlag", default=False,
        help=f"Omit DIR-PATH from the image status info in the console")

    ap.add_argument("--quiet", action="store_true", dest="quietFlag", default=False,
                    help=f"Suppress console output.{bcolors.BOLD}{bcolors.WARNING} [incompatible with --verbose] {bcolors.RESET}")

    ap.add_argument("--verbose", action="store_true", dest="verboseFlag", default=False,
        help=f"{bcolors.OKBLUE}DEBUG:{bcolors.RESET}  Be verbose on errors and exceptions.{bcolors.BOLD}{bcolors.WARNING} [incompatible with --quiet] {bcolors.RESET}")

    ap.add_argument("--debugMouse", action="store_true", dest="debugMouseFlag", default=False,
        help=f"{bcolors.OKBLUE}DEBUG:{bcolors.RESET}  Print mouse event debug info to console.{bcolors.BOLD}{bcolors.WARNING} [incompatible with --quiet]{bcolors.RESET}")
    ap.add_argument("--debugKeys", action="store_true", dest="debugKeysFlag", default=False,
        help=f"{bcolors.OKBLUE}DEBUG:{bcolors.RESET}  Print keyboard event debug info to console.{bcolors.BOLD}{bcolors.WARNING} [incompatible with --quiet]{bcolors.RESET}")

    ap.add_argument("-g", action="store_true", dest="grayscaleFlag", default=False,
        help="Display images in grayscale (BT.709 luminance-weighted)")
    ap.add_argument("-G", action="store_true", dest="grayscalePlFlag", default=False,
        help="Display images in grayscale (flat channel average)")

    ap.add_argument("--landscape", action="store_true", dest="landscapeFlag", default=False,
        help="Display images that are landscape only (width>height)")
    ap.add_argument("--portrait", action="store_true", dest="portraitFlag", default=False,
        help="Display images that are portrait only (height>width)")

    ap.add_argument("--scaleToFill", action="store_true", dest="scaledToFillFlag", default=False,
        help=f"Scale media to your monitors display height.{bcolors.RESET}")
    ap.add_argument("--scaletofill-only", action="store_true", dest="scaleToFillOnlyFlag", default=False,
        help="If using --scaletofill, only display scale to fill images")
    ap.add_argument("--scaletofill-info", action="store_true", dest="scaleToFillInfoFlag", default=False,
        help="Display scale to fill info to console")

    ap.add_argument("--isplash", "-i", action="store_true", dest="isplash", default=False,
        help=f"Enable the image info overlay at startup (toggle with 'i').")
    ap.add_argument("--info-divisor", action="store", type=int, dest="infoDivisor", default=80,
        help="Info splash font size = display_height // N (default 80 → ~24px at 4K, ~13px at 1080p; smaller N = larger text)")


    ap.add_argument("--printmediaList", action="store_true", dest="printmediaList", default=False,
        help=f"Print a list of media found in {bcolors.OKBLUE}<DIR>{bcolors.RESET}")
    ap.add_argument("--printIgnoreList", action="store_true", dest="printIgnoreList", default=False,
        help=f"Search for {bcolors.Magenta_f}.ignore {bcolors.RESET} files in {bcolors.OKBLUE}<DIR>{bcolors.RESET}")

    ap.add_argument("--delay", action="store", type=int, dest="delayTime", default=3000,
        help="The delay in ms between slides")

    ap.add_argument("--udp-port", action="store", type=int, dest="udpPort", default=5005,
                        help=f"The UDP port to listen on for remote control commands {bcolors.Green_f} (1024-49151)\n{bcolors.Magenta_f}Default: 5005{bcolors.RESET}")

    ap.add_argument("--ir-keymap", action="store", type=str, dest="irKeymap", default=None,
                    help=f"The path to the IR keymap file.\n{bcolors.Magenta_f}Default: {bcolors.OKBLUE}~/.local/share/nikkislide2/ir_keymap.conf{bcolors.RESET}")

    ap.add_argument("--disable-IR", action="store_true", dest="disable_IR", default=False,
        help=f"Disable the IR remote control listener")

    ap.add_argument("--enableEXIF", action="store_true", dest="enableEXIF", default=False,
        help=f"Read EXIF DateTimeOriginal/DateTimeDigitized and display in InfoSplash (line 3)")

    ap.add_argument("--display", "-D", action="store", type=str, dest="displayNum", default=None,
        help=f"Enable output on display. One of: 0|1|2 ...")

    options = ap.parse_args()

    for _path in options.paths:
        tmpPath = os.path.expanduser(_path)
        if not os.path.isdir(tmpPath):
            print(f"{bcolors.BOLD}{bcolors.FAIL}The following given path is not a valid directory:  {bcolors.WARNING}{tmpPath}{bcolors.RESET}")
            exit(30)
        Path.append(tmpPath)

    if options.delayTime < 30:
        print("%sDelay times lower than 30 ms are not allowed.%s" % (bcolors.FAIL, bcolors.Default_f))
        exit()

    if options.grayscaleFlag and options.grayscalePlFlag:
        print("%sThe use of %s-g%s and %s-G%s are mutually exclusive.%s" % (bcolors.FAIL, bcolors.L_Blue_f,
                                                                            bcolors.FAIL, bcolors.L_Blue_f,
                                                                            bcolors.FAIL, bcolors.Default_f))
        exit()

    if options.udpPort < 1024 or  options.udpPort > 49151:
        print("%sThe UDP port must be between 1024 and 49151.%s" % (bcolors.FAIL, bcolors.Default_f))
        exit()

    if options.irKeymap is not None:
        if options.irKeymap and not os.path.isfile(options.irKeymap):
            print("%sThe IR keymap file does not exist.%s" % (bcolors.FAIL, bcolors.Default_f))
            exit()

    if options.landscapeFlag and options.portraitFlag:
        print("%sThe use of %s--landscape%s and %s--portrait%s are mutually exclusive.%s" % (
            bcolors.FAIL, bcolors.L_Blue_f,
            bcolors.FAIL, bcolors.L_Blue_f,
            bcolors.FAIL, bcolors.Default_f))
        exit()

    if options.sortFlag and options.shuffle_flag:
        print("%sThe use of %s--sort%s and %s--shuffle%s are mutually exclusive.%s" % (
            bcolors.FAIL, bcolors.L_Blue_f,
            bcolors.FAIL, bcolors.L_Blue_f,
            bcolors.FAIL, bcolors.Default_f))
        exit()

    if options.scaleToFillOnlyFlag and not options.scaledToFillFlag:
        print("%sThe use of %s--scaletofill-only%s also requires %s--scaleToFill.%s" % (
            bcolors.FAIL, bcolors.L_Blue_f,
            bcolors.FAIL, bcolors.L_Blue_f,
            bcolors.Default_f))
        exit()

    if options.quietFlag:
        if options.verboseFlag or options.debugKeysFlag or options.debugMouseFlag:
            print(f"{bcolors.FAIL}The use of {bcolors.L_Blue_f}--quiet{bcolors.FAIL} is incompatible with "
                  f"{bcolors.Magenta_f}--verbose{bcolors.FAIL}, "
                  f"{bcolors.Magenta_f}--debugKeys{bcolors.FAIL}, "
                  f"and {bcolors.Magenta_f}--debugMouse{bcolors.FAIL}.{bcolors.RESET}" )

            exit()

    return options, Path
