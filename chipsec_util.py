#!/usr/bin/env python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2019, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



"""
Standalone utility
"""

import re
import os
import sys
import time
import importlib
import imp
import argparse

from chipsec import defines
from chipsec.logger  import logger
from chipsec.chipset import UnknownChipsetError
from chipsec.testcase import ExitCode
from chipsec import chipset

logger().UTIL_TRACE = True

#CMD_OPTS_WIDTH = [ 'byte', 'word', 'dword', 'qword' ]
CMD_OPTS_WIDTH = [ 'byte', 'word', 'dword' ]
def is_option_valid_width( width_op ):
    return (width_op.lower() in CMD_OPTS_WIDTH)

def get_option_width( width_op ):
    width_op = width_op.lower()
    if   'byte'  == width_op: return 0x1
    elif 'word'  == width_op: return 0x2
    elif 'dword' == width_op: return 0x4
    #elif 'qword' == width_op: return 0x8
    else:               return 0x0


commands = {}

class ChipsecUtil:

    def __init__(self, argv):
        self.global_usage = "CHIPSEC UTILITIES\n\n" + \
                   "All numeric values are in hex\n" + \
                   "<width> is in {1, byte, 2, word, 4, dword}\n\n"
        self.commands = {}
        # determine if CHIPSEC is loaded as chipsec_*.exe or in python
        self.CHIPSEC_LOADED_AS_EXE = True if (hasattr(sys, "frozen") or hasattr(sys, "importers")) else False

        self.argv = argv
        self.print_banner()
        self.parse_args()

    def init_cs(self):
        self._cs = chipset.cs()


    def chipsec_util_help(self, command=None):
        """
        Shows the list of available command line extensions
        """
        if command is None or command not in self.commands:
            for cmd in sorted(list(self.commands.keys()) + ['help']):
                logger().log( '    {}'.format(cmd) )
        else:
            logger().log("\nhelp for '{}' <command>:".format(command))
            logger().log(self.commands[command].__doc__)

    def f_mod_zip(self, x):
        ZIP_UTILCMD_RE = re.compile(r"^chipsec\/utilcmd\/\w+\.pyc$", re.IGNORECASE)
        return ( x.find('__init__') == -1 and ZIP_UTILCMD_RE.match(x) )
        
    def map_modname_zip(self, x):
        return ((x.split('/', 2)[2]).rpartition('.')[0]).replace('/','.')

    def f_mod(self, x):
        MODFILE_RE = re.compile(r"^\w+\.py$")
        return ( x.lower().find('__init__') == -1 and MODFILE_RE.match(x.lower()) )
    def map_modname(self, x):
        return x.split('.')[0]

    def parse_args(self):
        parser = argparse.ArgumentParser(usage='%(prog)s [options] <command>',add_help=False)
        options = parser.add_argument_group('Options')
        options.add_argument('-h', '--help',dest='show_help', help="show this message and exit",action='store_true')
        options.add_argument('-v','--verbose', help='verbose mode', action='store_true')
        options.add_argument('--hal', help='HAL mode', action='store_true')
        options.add_argument('-d','--debug', help='debug mode', action='store_true')
        options.add_argument('-l','--log', help='output to log file')
        options.add_argument('-p','--platform',dest='_platform', help='explicitly specify platform code',choices=chipset.Chipset_Code, type=str.upper)
        options.add_argument('--pch',dest='_pch', help='explicitly specify PCH code',choices=chipset.pch_codes, type=str.upper)
        options.add_argument('-n', '--no_driver',dest='_no_driver', help="chipsec won't need kernel mode functions so don't load chipsec driver", action='store_true')
        options.add_argument('-i', '--ignore_platform',dest='_unkownPlatform', help='run chipsec even if the platform is not recognized', action='store_false')
        options.add_argument('_cmd_args',metavar='Command',nargs=argparse.REMAINDER,help="All numeric values are in hex. <width> can be one of {1, byte, 2, word, 4, dword}")

        parser.parse_args(self.argv,namespace=ChipsecUtil)
        if self.show_help or self._cmd_args == []:
            parser.print_help()
        if self.verbose:
            logger().VERBOSE = True
        if self.hal:
            logger().HAL     = True
        if self.debug:
            logger().DEBUG   = True
        if self.log:
            logger().set_log_file( self.log )
        if self._cmd_args:
            self.help_cmd = self._cmd_args[0]


    ##################################################################################
    # Entry point
    ##################################################################################


    def main(self):
        """
        Receives and executes the commands
        """

        if self.CHIPSEC_LOADED_AS_EXE:
            import zipfile
            myzip = zipfile.ZipFile("library.zip")
            cmds = map( self.map_modname_zip, filter(self.f_mod_zip, myzip.namelist()) )
        else:
            #traceback.print_stack()
            mydir = imp.find_module('chipsec')[1]
            cmds_dir = os.path.join(mydir,os.path.join("utilcmd"))
            cmds = map( self.map_modname, filter(self.f_mod, os.listdir(cmds_dir)) )

        if logger().DEBUG:
            logger().log( '[CHIPSEC] Loaded command-line extensions:' )
            logger().log( '   {}'.format(cmds) )
        module = None
        for cmd in cmds:
            try:
                cmd_path = 'chipsec.utilcmd.' + cmd
                module = importlib.import_module( cmd_path )
                cu = getattr(module, 'commands')
                self.commands.update(cu)
            except ImportError as msg:
                # Display the import error and continue to import commands
                logger().error("Exception occurred during import of {}: '{}'".format(cmd, str(msg)))
                continue

        if self.show_help:
            return ExitCode.OK

        self.init_cs()

        # @TODO: change later
        # all util cmds assume 'chipsec_util.py' as the first arg so adding dummy first arg
        if self._cmd_args:
            cmd = self._cmd_args[0]
            self.argv = ['dummy'] + self._cmd_args
        else:
            cmd = 'help'
            self.argv = ['dummy']

        if cmd in self.commands:
            comm = self.commands[cmd](self.argv, cs = self._cs)

            try:
                self._cs.init( self._platform, self._pch, comm.requires_driver() and not self._no_driver)
            except UnknownChipsetError as msg:
                logger().warn("*******************************************************************")
                logger().warn("* Unknown platform!")
                logger().warn("* Platform dependent functionality will likely be incorrect")
                logger().warn("* Error Message: \"{}\"".format(str(msg)))
                logger().warn("*******************************************************************")
            except Exception as msg:
                logger().error(str(msg))
                sys.exit(ExitCode.EXCEPTION)
            except None as msg:
                logger().error(str(msg))
                sys.exit(ExitCode.EXCEPTION)

            logger().log( "[CHIPSEC] Executing command '{}' with args {}\n".format(cmd,self.argv[2:]) )
            comm.run()
            if comm.requires_driver():
                self._cs.destroy(True)
            return comm.ExitCode

        elif cmd == 'help':
            if len(self.argv) <= 2:
                self.chipsec_util_help()
            else:
                self.chipsec_util_help(self.argv[2])
            return ExitCode.OK
        else:
            logger().error( "Unknown command '{:.32s}'".format(cmd) )
        return ExitCode.WARNING

    def set_logfile(self, logfile):
        """
        Calls logger's set_log_file function
        """
        logger().set_log_file(logfile)

    def print_banner(self):
        """
        Prints chipsec banner
        """
        logger().log( '' )
        logger().log( "################################################################\n"
                      "##                                                            ##\n"
                      "##  CHIPSEC: Platform Hardware Security Assessment Framework  ##\n"
                      "##                                                            ##\n"
                      "################################################################" )
        logger().log( "[CHIPSEC] Version {}".format(defines.get_version()) )

def main(argv=None):
    chipsecUtil = ChipsecUtil(argv if argv else sys.argv[1:])
    return chipsecUtil.main()

       
if __name__ == "__main__":
    sys.exit( main() )

