#  Bcolors.py Copyright (c) 2025 Nikki Cooper
#
#  This program and the accompanying materials are made available under the
#  terms of the GNU Lesser General Public License, version 3.0 which is available at
#  https://www.gnu.org/licenses/gpl-3.0.html#license-text
#
"""
Ansi console escape sequences
-----------------------------

Console colors for Kinney
You bastards can't kill Kinney

"""
import os
class Bcolors(object):
    def __init__(self):
        # Foreground Colors
        self.Default_f = '\x1B[39m'
        self.Black_f = '\x1B[30m'
        self.Red_f = '\x1B[31m'
        self.Green_f = '\x1B[32m'
        self.Yellow_f = '\x1B[33m'
        self.Blue_f = '\x1B[34m'
        self.Magenta_f = '\x1B[35m'
        self.Cyan_f = '\x1B[36m'
        self.L_Gray_f = '\x1B[37m'
        self.Dark_Gray_f  = '\x1B[90m'
        self.L_Red_f = '\x1B[91m'
        self.L_Green_f = '\x1B[92m'
        self.L_Yellow_f = '\x1B[93m'
        self.L_Blue_f = '\x1B[94m'
        self.L_Magenta_f = '\x1B[95m'
        self.L_Cyan_f = '\x1B[96m'
        self.White_f = '\x1B[97m'

        # Background Colors
        self.Default_b = '\x1B[49m'
        self.Black_b = '\x1B[40m'
        self.Red_b = '\x1B[41m'
        self.Green_b = '\x1B[42m'
        self.Yellow_b = '\x1B[43m'
        self.Blue_b = '\x1B[44m'
        self.Magenta_b = '\x1B[45m'
        self.Cyan_b = '\x1B[46m'
        self.L_Gray_b = '\x1B[47m'
        self.Dark_Gray_b = '\x1B[100m'
        self.L_Red_b = '\x1B[101m'
        self.L_Green_b = '\x1B[102m'
        self.L_Yellow_b = '\x1B[103m'
        self.L_Blue_b = '\x1B[104m'
        self.L_Magenta_b = '\x1B[105m'
        self.L_Cyan_b = '\x1B[106m'
        self.White_b = '\x1B[107m'

        self.HEADER = self.Magenta_f
        self.OKBLUE = self.L_Blue_f
        self.OKGREEN = self.L_Green_f
        self.WARNING = self.L_Yellow_f
        self.FAIL = self.Red_f

        self.DESC = self.Magenta_f
        self.DESC_VALUE = self.L_Cyan_f
        self.BOOL_TRUE = self.Green_f
        self.BOOL_FALSE = self.L_Yellow_f

        # Attributes
        self.ENDC = '\x1B[0m'
        self.BOLD = '\x1B[1m'
        self.DIM = '\x1B[2m'
        self.UNDERLINE = '\x1B[4m'
        self.BLINK = '\x1B[5m'
        self.INVERTED = '\x1B[7m'

        # Reset Attributes
        self.RESET = '\x1B[0m'
        self.RESET_BOLD = '\x1B[21m'
        self.RESET_DIM = '\x1B[22m'
        self.RESET_UNDERLINED = '\x1B[24m'
        self.RESET_BLINK = '\x1B[25m'
        self.RESET_REVERSE = '\x1B[27m'

    @staticmethod
    def clear():
        os.system('cls' if os.name == 'nt' else 'clear')
