#!/usr/bin/python
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



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2019 Intel Corporation
#
# -------------------------------------------------------------------------------

"""
Contains platform identification functions
"""

import sys
import collections
import os
import fnmatch
import re

from chipsec.helper.oshelper import OsHelper, OsHelperError
from chipsec.hal import cpu, io, iobar, mmio, msgbus, msr, pci, physmem, ucode, igd
from chipsec.hal.pci import PCI_HDR_RID_OFF

from chipsec.cfg.common import Cfg
from chipsec.logger import logger

import chipsec.file

import importlib
import traceback
#_importlib = True
#try:                import importlib
#except ImportError: _importlib = False

# DEBUG Flags
QUIET_PCI_ENUM = True

class RegisterType:
    PCICFG    = 'pcicfg'
    MMCFG     = 'mmcfg'
    MMIO      = 'mmio'
    MSR       = 'msr'
    PORTIO    = 'io'
    IOBAR     = 'iobar'
    MSGBUS    = 'msgbus'
    MM_MSGBUS = 'mm_msgbus'


##################################################################################
# Functionality defining current chipset
##################################################################################
CHIPSET_ID_COMMON  = -1
CHIPSET_ID_UNKNOWN = 0

CHIPSET_ID_SNB     = 1
CHIPSET_ID_JKT     = 2
CHIPSET_ID_IVB     = 3
CHIPSET_ID_IVT     = 4
CHIPSET_ID_HSW     = 5
CHIPSET_ID_BYT     = 6
CHIPSET_ID_BDW     = 7
CHIPSET_ID_QRK     = 8
CHIPSET_ID_AVN     = 9
CHIPSET_ID_HSX     = 10
CHIPSET_ID_SKL     = 11
CHIPSET_ID_BSW     = 12
CHIPSET_ID_KBL     = 13
CHIPSET_ID_CHT     = 14
CHIPSET_ID_BDX     = 15
CHIPSET_ID_CFL     = 16
CHIPSET_ID_APL     = 17
CHIPSET_ID_DNV     = 18
CHIPSET_ID_WHL     = 19
CHIPSET_ID_SKX     = 20

CHIPSET_CODE_COMMON  = 'COMMON'
CHIPSET_CODE_UNKNOWN = ''

CHIPSET_CODE_SNB     = 'SNB'
CHIPSET_CODE_JKT     = 'JKT'
CHIPSET_CODE_IVB     = 'IVB'
CHIPSET_CODE_IVT     = 'IVT'
CHIPSET_CODE_HSW     = 'HSW'
CHIPSET_CODE_BYT     = 'BYT'
CHIPSET_CODE_BDW     = 'BDW'
CHIPSET_CODE_QRK     = 'QRK'
CHIPSET_CODE_AVN     = 'AVN'
CHIPSET_CODE_HSX     = 'HSX'
CHIPSET_CODE_SKL     = 'SKL'
CHIPSET_CODE_BSW     = 'BSW'
CHIPSET_CODE_KBL     = 'KBL'
CHIPSET_CODE_CHT     = 'CHT'
CHIPSET_CODE_BDX     = 'BDX'
CHIPSET_CODE_CFL     = 'CFL'
CHIPSET_CODE_APL     = 'APL'
CHIPSET_CODE_DNV     = 'DNV'
CHIPSET_CODE_WHL     = 'WHL'
CHIPSET_CODE_SKX     = 'SKX'

CHIPSET_FAMILY_XEON  = [CHIPSET_ID_JKT,CHIPSET_ID_IVT,CHIPSET_ID_HSX,CHIPSET_ID_BDX,CHIPSET_ID_SKX]
CHIPSET_FAMILY_CORE  = [CHIPSET_ID_SNB,CHIPSET_ID_IVB,CHIPSET_ID_HSW,CHIPSET_ID_BDW,CHIPSET_ID_SKL,CHIPSET_ID_KBL,CHIPSET_ID_CFL,CHIPSET_ID_WHL]
CHIPSET_FAMILY_ATOM  = [CHIPSET_ID_BYT,CHIPSET_ID_AVN,CHIPSET_ID_BSW,CHIPSET_ID_CHT,CHIPSET_ID_APL,CHIPSET_ID_DNV]
CHIPSET_FAMILY_QUARK = [CHIPSET_ID_QRK]


VID_INTEL = 0x8086

# PCI 0/0/0 Device IDs
Chipset_Dictionary = {
# DID  : Data Dictionary

# 2nd Generation Core Processor Family (Sandy Bridge)
0x0100 : {'name' : 'Sandy Bridge',   'id' : CHIPSET_ID_SNB , 'code' : CHIPSET_CODE_SNB,  'longname' : 'Desktop 2nd Generation Core Processor (Sandy Bridge CPU / Cougar Point PCH)' },
0x0104 : {'name' : 'Sandy Bridge',   'id' : CHIPSET_ID_SNB , 'code' : CHIPSET_CODE_SNB,  'longname' : 'Mobile 2nd Generation Core Processor (Sandy Bridge CPU / Cougar Point PCH)' },
0x0108 : {'name' : 'Sandy Bridge',   'id' : CHIPSET_ID_SNB , 'code' : CHIPSET_CODE_SNB,  'longname' : 'Intel Xeon Processor E3-1200 (Sandy Bridge CPU, C200 Series PCH)' },

# Xeon v1 Processor (Jaketown/Sandy Bridge - EP)
0x3C00 : {'name' : 'Jaketown',       'id' : CHIPSET_ID_JKT,  'code' : CHIPSET_CODE_JKT,  'longname' : 'Server 2nd Generation Core Processor (Jaketown CPU / Patsburg PCH)'},

# 3rd Generation Core Processor Family (Ivy Bridge)
0x0150 : {'name' : 'Ivy Bridge',     'id' : CHIPSET_ID_IVB , 'code' : CHIPSET_CODE_IVB,  'longname' : 'Desktop 3rd Generation Core Processor (Ivy Bridge CPU / Panther Point PCH)' },
0x0154 : {'name' : 'Ivy Bridge',     'id' : CHIPSET_ID_IVB , 'code' : CHIPSET_CODE_IVB,  'longname' : 'Mobile 3rd Generation Core Processor (Ivy Bridge CPU / Panther Point PCH)' },
0x0158 : {'name' : 'Ivy Bridge',     'id' : CHIPSET_ID_IVB , 'code' : CHIPSET_CODE_IVB,  'longname' : 'Intel Xeon Processor E3-1200 v2 (Ivy Bridge CPU, C200/C216 Series PCH)' },

# Xeon v2 Processor (Ivy Town/Ivy Bridge - EP)
0x0E00 : {'name' : 'Ivytown',        'id' : CHIPSET_ID_IVT,  'code' : CHIPSET_CODE_IVT,  'longname' : 'Server 3rd Generation Core Procesor (Ivytown CPU / Patsburg PCH)'},

# 4th Generation Core Processor Family (Haswell)
0x0C00 : {'name' : 'Haswell',        'id' : CHIPSET_ID_HSW , 'code' : CHIPSET_CODE_HSW,  'longname' : 'Desktop 4th Generation Core Processor (Haswell CPU / Lynx Point PCH)' },
0x0C04 : {'name' : 'Haswell',        'id' : CHIPSET_ID_HSW , 'code' : CHIPSET_CODE_HSW,  'longname' : 'Mobile 4th Generation Core Processor (Haswell M/H / Lynx Point PCH)' },
0x0C08 : {'name' : 'Haswell',        'id' : CHIPSET_ID_HSW , 'code' : CHIPSET_CODE_HSW,  'longname' : 'Intel Xeon Processor E3-1200 v3 (Haswell CPU, C220 Series PCH)' },
0x0D00 : {'name' : 'Haswell',        'id' : CHIPSET_ID_HSW , 'code' : CHIPSET_CODE_HSW,  'longname' : 'Desktop 4th Generation Core Processor (Haswell)' },
0x0D04 : {'name' : 'Haswell',        'id' : CHIPSET_ID_HSW , 'code' : CHIPSET_CODE_HSW,  'longname' : 'Mobile 4th Generation Core Processor (Haswell)' },
0x0D08 : {'name' : 'Haswell',        'id' : CHIPSET_ID_HSW , 'code' : CHIPSET_CODE_HSW,  'longname' : '4th Generation Core Processor (Haswell)' },
0x0A00 : {'name' : 'Haswell',        'id' : CHIPSET_ID_HSW , 'code' : CHIPSET_CODE_HSW,  'longname' : '4th Generation Core Processor (Haswell U/Y)' },
0x0A04 : {'name' : 'Haswell',        'id' : CHIPSET_ID_HSW , 'code' : CHIPSET_CODE_HSW,  'longname' : '4th Generation Core Processor (Haswell U/Y)' },
0x0A08 : {'name' : 'Haswell',        'id' : CHIPSET_ID_HSW , 'code' : CHIPSET_CODE_HSW,  'longname' : '4th Generation Core Processor (Haswell U/Y)' },

# 5th Generation Core Processor Family (Broadwell)
0x1600 : {'name' : 'Broadwell',      'id' : CHIPSET_ID_BDW , 'code' : CHIPSET_CODE_BDW,  'longname' : 'Desktop 5th Generation Core Processor (Broadwell CPU / Wildcat Point PCH)' },
0x1604 : {'name' : 'Broadwell',      'id' : CHIPSET_ID_BDW , 'code' : CHIPSET_CODE_BDW,  'longname' : 'Mobile 5th Generation Core Processor (Broadwell M/H / Wildcat Point PCH)' },
0x1610 : {'name' : 'Broadwell',      'id' : CHIPSET_ID_BDW , 'code' : CHIPSET_CODE_BDW,  'longname' : 'Desktop 5th Generation Core Processor (Broadwell H / Wildcat Point PCH)' },
0x1614 : {'name' : 'Broadwell',      'id' : CHIPSET_ID_BDW , 'code' : CHIPSET_CODE_BDW,  'longname' : 'Mobile 5th Generation Core Processor (Broadwell H / Wildcat Point PCH)' },

# 6th Generation Core Processor Family (Skylake)
0x1904 : {'name' : 'Skylake',        'id' : CHIPSET_ID_SKL , 'code' : CHIPSET_CODE_SKL,  'longname' : 'Mobile 6th Generation Core Processor (Skylake U)' },
0x190C : {'name' : 'Skylake',        'id' : CHIPSET_ID_SKL , 'code' : CHIPSET_CODE_SKL,  'longname' : 'Mobile 6th Generation Core Processor (Skylake Y)' },
0x1900 : {'name' : 'Skylake',        'id' : CHIPSET_ID_SKL , 'code' : CHIPSET_CODE_SKL,  'longname' : 'Mobile 6th Generation Core Processor Dual Core (Skylake H)' },
0x1910 : {'name' : 'Skylake',        'id' : CHIPSET_ID_SKL , 'code' : CHIPSET_CODE_SKL,  'longname' : 'Mobile 6th Generation Core Processor Quad Core (Skylake H)' },
0x190F : {'name' : 'Skylake',        'id' : CHIPSET_ID_SKL , 'code' : CHIPSET_CODE_SKL,  'longname' : 'Desktop 6th Generation Core Processor Dual Core (Skylake CPU / Sunrise Point PCH)' },
0x191F : {'name' : 'Skylake',        'id' : CHIPSET_ID_SKL , 'code' : CHIPSET_CODE_SKL,  'longname' : 'Desktop 6th Generation Core Processor Quad Core (Skylake CPU / Sunrise Point PCH)' },

# 7th Generation Core Processor Family (Kabylake)
0x5900 : {'name' : 'Kabylake',       'id' : CHIPSET_ID_KBL , 'code' : CHIPSET_CODE_KBL,  'longname' : 'Mobile 7th Generation Core Processor (Kabylake H)' },
0x5904 : {'name' : 'Kabylake',       'id' : CHIPSET_ID_KBL , 'code' : CHIPSET_CODE_KBL,  'longname' : 'Mobile 7th Generation Core Processor (Kabylake U)' },
0x590C : {'name' : 'Kabylake',       'id' : CHIPSET_ID_KBL , 'code' : CHIPSET_CODE_KBL,  'longname' : 'Mobile 7th Generation Core Processor (Kabylake Y)' },
0x590F : {'name' : 'Kabylake',       'id' : CHIPSET_ID_KBL , 'code' : CHIPSET_CODE_KBL,  'longname' : 'Desktop 7th Generation Core Processor (Kabylake S)' },
0x5910 : {'name' : 'Kabylake',       'id' : CHIPSET_ID_KBL , 'code' : CHIPSET_CODE_KBL,  'longname' : 'Mobile 7th Generation Core Processor (Kabylake H)' },
0x5914 : {'name' : 'Kabylake',       'id' : CHIPSET_ID_KBL , 'code' : CHIPSET_CODE_KBL,  'longname' : 'Mobile 8th Generation Core Processor (Kabylake U-Quad Core)' },
0x591F : {'name' : 'Kabylake',       'id' : CHIPSET_ID_KBL , 'code' : CHIPSET_CODE_KBL,  'longname' : 'Desktop 7th Generation Core Processor (Kabylake S)' },
0x5918 : {'name' : 'Kabylake',       'id' : CHIPSET_ID_KBL , 'code' : CHIPSET_CODE_KBL,  'longname' : 'Mobile 7th Generation Core Processor (Kabylake H)' },

# 8th Generation Core Processor Family (Coffeelake)
0x3E0F : {'name' : 'CoffeeLake',     'id' : CHIPSET_ID_CFL , 'code' : CHIPSET_CODE_CFL,  'longname' : 'Desktop 8th Generation Core Processor (CoffeeLake S 2 Cores)' },
0x3E1F : {'name' : 'CoffeeLake',     'id' : CHIPSET_ID_CFL , 'code' : CHIPSET_CODE_CFL,  'longname' : 'Desktop 8th Generation Core Processor (Coffeelake S 4 Cores)' },
0x3EC2 : {'name' : 'CoffeeLake',     'id' : CHIPSET_ID_CFL , 'code' : CHIPSET_CODE_CFL,  'longname' : 'Desktop 8th Generation Core Processor (Coffeelake S 6 Cores)' },
0x3E30 : {'name' : 'CoffeeLake',     'id' : CHIPSET_ID_CFL , 'code' : CHIPSET_CODE_CFL,  'longname' : 'Desktop 8th Generation Core Processor (CoffeeLake S 8 Cores)' },
0x3ECC : {'name' : 'CoffeeLake',     'id' : CHIPSET_ID_CFL , 'code' : CHIPSET_CODE_CFL,  'longname' : 'Desktop 8th Generation Core Processor (CoffeeLake U 2 Cores)' },
0x3ED0 : {'name' : 'CoffeeLake',     'id' : CHIPSET_ID_CFL , 'code' : CHIPSET_CODE_CFL,  'longname' : 'Desktop 8th Generation Core Processor (CoffeeLake U 4 Cores)' },
0x3E10 : {'name' : 'CoffeeLake',     'id' : CHIPSET_ID_CFL , 'code' : CHIPSET_CODE_CFL,  'longname' : 'Desktop 8th Generation Core Processor (CoffeeLake H 4 Cores)' },
0x3EC4 : {'name' : 'CoffeeLake',     'id' : CHIPSET_ID_CFL , 'code' : CHIPSET_CODE_CFL,  'longname' : 'Desktop 8th Generation Core Processor (CoffeeLake H 6 Cores)' },
0x3E18 : {'name' : 'CoffeeLake',     'id' : CHIPSET_ID_CFL , 'code' : CHIPSET_CODE_CFL,  'longname' : 'Desktop 8th Generation Core Processor (CoffeeLake Workstation 4 Cores)' },
0x3EC6 : {'name' : 'CoffeeLake',     'id' : CHIPSET_ID_CFL , 'code' : CHIPSET_CODE_CFL,  'longname' : 'Desktop 8th Generation Core Processor (CoffeeLake Workstation 6 Cores)' },
0x3E31 : {'name' : 'CoffeeLake',     'id' : CHIPSET_ID_CFL , 'code' : CHIPSET_CODE_CFL,  'longname' : 'Desktop 8th Generation Core Processor (CoffeeLake Workstation 8 Cores)' },
0x3E33 : {'name' : 'CoffeeLake',     'id' : CHIPSET_ID_CFL , 'code' : CHIPSET_CODE_CFL,  'longname' : 'Desktop 8th Generation Core Processor (CoffeeLake Server 4 Cores)' },
0x3ECA : {'name' : 'CoffeeLake',     'id' : CHIPSET_ID_CFL , 'code' : CHIPSET_CODE_CFL,  'longname' : 'Desktop 8th Generation Core Processor (CoffeeLake Server 6 Cores)' },
0x3E32 : {'name' : 'CoffeeLake',     'id' : CHIPSET_ID_CFL , 'code' : CHIPSET_CODE_CFL,  'longname' : 'Desktop 8th Generation Core Processor (CoffeeLake Server 8 Cores)' },

# 8th Generation Core Processor Family (Whiskey Lake)
0x3E34 : {'name': 'Whiskey Lake',    'id' : CHIPSET_ID_WHL , 'code' : CHIPSET_CODE_WHL,  'longname' : 'Mobile 8th Generation Core Processor (Whiskey Lake U 4 Cores)' },

# Xeon v3 Processor (Haswell Server)
0x2F00 : {'name' : 'Haswell Server', 'id' : CHIPSET_ID_HSX,  'code' : CHIPSET_CODE_HSX,  'longname' : 'Server 4th Generation Core Processor (Haswell Server CPU / Wellsburg PCH)'},

# Xeon v4 Processor (Broadwell Server)
0x1618 : {'name' : 'Broadwell Server', 'id' : CHIPSET_ID_BDW , 'code' : CHIPSET_CODE_BDW,  'longname' : 'Intel Xeon Processor E3 v4 (Broadwell CPU)' },
0x6F00 : {'name' : 'Broadwell Server', 'id' : CHIPSET_ID_BDX,  'code' : CHIPSET_CODE_BDX,  'longname' : 'Intel Xeon Processor E5/E7 v4 (Broadwell Server CPU / Wellsburg PCH)'},

# Xeon v5 Processor (Skylake Server)
0x1918 : {'name' : 'Skylake Server', 'id' : CHIPSET_ID_SKL,  'code' : CHIPSET_CODE_SKL,  'longname' : 'Intel Xeon Processor E3 v5 (Skylake CPU / Sunrise Point PCH)'},
0x2020 : {'name' : 'Skylake',        'id' : CHIPSET_ID_SKX , 'code' : CHIPSET_CODE_SKX,  'longname' : 'Intel Xeon Processor E5/E7 v5 (Skylake)' },

# Xeon v6 Processor (Kabylake Server)
0x5918 : {'name' : 'Kabylake','id' : CHIPSET_ID_KBL , 'code' : CHIPSET_CODE_KBL,  'longname' : 'Intel Xeon Processor E3 v6 (Kabylake CPU)' },

#
# Atom based SoC platforms
#

# Bay Trail SoC
0x0F00 : {'name' : 'Baytrail',       'id' : CHIPSET_ID_BYT , 'code' : CHIPSET_CODE_BYT,  'longname' : 'Bay Trail SoC' },

# Denverton
0x1980 : {'name' : 'Denverton',      'id' : CHIPSET_ID_DNV , 'code' : CHIPSET_CODE_DNV,  'longname' : 'Intel Atom Processor C3000 Product Family' },

# Atom C2000 Processor Family (Avoton)
0x1F00 : {'name' : 'Avoton  ',       'id' : CHIPSET_ID_AVN , 'code' : CHIPSET_CODE_AVN,  'longname' : 'Intel Avoton' },
0x1F01 : {'name' : 'Avoton  ',       'id' : CHIPSET_ID_AVN , 'code' : CHIPSET_CODE_AVN,  'longname' : 'Intel Avoton' },
0x1F02 : {'name' : 'Avoton  ',       'id' : CHIPSET_ID_AVN , 'code' : CHIPSET_CODE_AVN,  'longname' : 'Intel Avoton' },
0x1F03 : {'name' : 'Avoton  ',       'id' : CHIPSET_ID_AVN , 'code' : CHIPSET_CODE_AVN,  'longname' : 'Intel Avoton' },
0x1F04 : {'name' : 'Avoton  ',       'id' : CHIPSET_ID_AVN , 'code' : CHIPSET_CODE_AVN,  'longname' : 'Intel Avoton' },
0x1F05 : {'name' : 'Avoton  ',       'id' : CHIPSET_ID_AVN , 'code' : CHIPSET_CODE_AVN,  'longname' : 'Intel Avoton' },
0x1F06 : {'name' : 'Avoton  ',       'id' : CHIPSET_ID_AVN , 'code' : CHIPSET_CODE_AVN,  'longname' : 'Intel Avoton' },
0x1F07 : {'name' : 'Avoton  ',       'id' : CHIPSET_ID_AVN , 'code' : CHIPSET_CODE_AVN,  'longname' : 'Intel Avoton' },
0x1F08 : {'name' : 'Avoton  ',       'id' : CHIPSET_ID_AVN , 'code' : CHIPSET_CODE_AVN,  'longname' : 'Intel Avoton' },
0x1F09 : {'name' : 'Avoton  ',       'id' : CHIPSET_ID_AVN , 'code' : CHIPSET_CODE_AVN,  'longname' : 'Intel Avoton' },
0x1F0A : {'name' : 'Avoton  ',       'id' : CHIPSET_ID_AVN , 'code' : CHIPSET_CODE_AVN,  'longname' : 'Intel Avoton' },
0x1F0B : {'name' : 'Avoton  ',       'id' : CHIPSET_ID_AVN , 'code' : CHIPSET_CODE_AVN,  'longname' : 'Intel Avoton' },
0x1F0C : {'name' : 'Avoton  ',       'id' : CHIPSET_ID_AVN , 'code' : CHIPSET_CODE_AVN,  'longname' : 'Intel Avoton' },
0x1F0D : {'name' : 'Avoton  ',       'id' : CHIPSET_ID_AVN , 'code' : CHIPSET_CODE_AVN,  'longname' : 'Intel Avoton' },
0x1F0E : {'name' : 'Avoton  ',       'id' : CHIPSET_ID_AVN , 'code' : CHIPSET_CODE_AVN,  'longname' : 'Intel Avoton' },
0x1F0F : {'name' : 'Avoton  ',       'id' : CHIPSET_ID_AVN , 'code' : CHIPSET_CODE_AVN,  'longname' : 'Intel Avoton' },

# Cherry Trail SoC
0x2280 : {'name' : 'Braswell/Cherry Trail', 'id' : CHIPSET_ID_CHT, 'code' : CHIPSET_CODE_CHT,  'longname' : 'Braswell/Cherry Trail SoC' },

# Apollo Lake
0x5AF0 : {'name' : 'Apollo Lake','id' : CHIPSET_ID_APL , 'code' : CHIPSET_CODE_APL,  'longname' : 'Apollo Lake' },

#
# Quark based SoC platforms
#

# Galileo Board
0x0958 : {'name' : 'Galileo ',       'id' : CHIPSET_ID_QRK , 'code' : CHIPSET_CODE_QRK,  'longname' : 'Intel Quark SoC X1000' },

}

PCH_ID_1xx      = 10001
PCH_ID_2xx      = 10002
PCH_ID_C620     = 10003
PCH_ID_C60x     = 10004
PCH_ID_C61x     = 10005
PCH_ID_3xx      = 10006

PCH_CODE_PREFIX = 'PCH_'
PCH_CODE_1xx    = 'PCH_1XX'
PCH_CODE_2xx    = 'PCH_2XX'
PCH_CODE_3xx    = 'PCH_3XX'
PCH_CODE_C620   = 'PCH_C620'
PCH_CODE_C60x   = 'PCH_C60X'
PCH_CODE_C61x   = 'PCH_C61X'

pch_dictionary = {
# 100 series PCH
0xA143 : {'name' : 'H110',   'id' : PCH_ID_1xx, 'code' : PCH_CODE_1xx, 'longname' : 'Intel H110 (100 series) PCH'},
0xA144 : {'name' : 'H170',   'id' : PCH_ID_1xx, 'code' : PCH_CODE_1xx, 'longname' : 'Intel H170 (100 series) PCH'},
0xA145 : {'name' : 'Z170',   'id' : PCH_ID_1xx, 'code' : PCH_CODE_1xx, 'longname' : 'Intel Z170 (100 series) PCH'},
0xA146 : {'name' : 'Q170',   'id' : PCH_ID_1xx, 'code' : PCH_CODE_1xx, 'longname' : 'Intel Q170 (100 series) PCH'},
0xA147 : {'name' : 'Q150',   'id' : PCH_ID_1xx, 'code' : PCH_CODE_1xx, 'longname' : 'Intel Q150 (100 series) PCH'},
0xA148 : {'name' : 'B150',   'id' : PCH_ID_1xx, 'code' : PCH_CODE_1xx, 'longname' : 'Intel B150 (100 series) PCH'},
0xA14D : {'name' : 'CQM170', 'id' : PCH_ID_1xx, 'code' : PCH_CODE_1xx, 'longname' : 'Intel CQM170 (100 series) PCH'},
0xA14E : {'name' : 'HM170',  'id' : PCH_ID_1xx, 'code' : PCH_CODE_1xx, 'longname' : 'Intel HM170 (100 series) PCH'},
0xA150 : {'name' : 'CM236',  'id' : PCH_ID_1xx, 'code' : PCH_CODE_1xx, 'longname' : 'Intel CM236 (100 series) PCH'},

# 200 series and Z370 PCH
0xA2C4 : {'name' : 'H270', 'id' : PCH_ID_2xx, 'code' : PCH_CODE_2xx, 'longname' : 'Intel H270 (200 series) PCH'},
0xA2C5 : {'name' : 'Z270', 'id' : PCH_ID_2xx, 'code' : PCH_CODE_2xx, 'longname' : 'Intel Z270 (200 series) PCH'},
0xA2C6 : {'name' : 'Q270', 'id' : PCH_ID_2xx, 'code' : PCH_CODE_2xx, 'longname' : 'Intel Q270 (200 series) PCH'},
0xA2C7 : {'name' : 'Q250', 'id' : PCH_ID_2xx, 'code' : PCH_CODE_2xx, 'longname' : 'Intel Q250 (200 series) PCH'},
0xA2C8 : {'name' : 'B250', 'id' : PCH_ID_2xx, 'code' : PCH_CODE_2xx, 'longname' : 'Intel B250 (200 series) PCH'},
0xA2C9 : {'name' : 'Z370', 'id' : PCH_ID_2xx, 'code' : PCH_CODE_2xx, 'longname' : 'Intel Z370 (200 series) PCH'},
0xA2D2 : {'name' : 'X299', 'id' : PCH_ID_2xx, 'code' : PCH_CODE_2xx, 'longname' : 'Intel X299 (200 series) PCH'},

# 300 series and Z390 PCH
0xA306 : {'name' : 'Q370',   'id' : PCH_ID_3xx, 'code' : PCH_CODE_3xx, 'longname' : 'Intel Q370 (300 series) PCH'},
0xA304 : {'name' : 'H370',   'id' : PCH_ID_3xx, 'code' : PCH_CODE_3xx, 'longname' : 'Intel H370 (300 series) PCH'},
0xA305 : {'name' : 'Z390',   'id' : PCH_ID_3xx, 'code' : PCH_CODE_3xx, 'longname' : 'Intel Z390 (300 series) PCH'},
0xA308 : {'name' : 'B360',   'id' : PCH_ID_3xx, 'code' : PCH_CODE_3xx, 'longname' : 'Intel B360 (300 series) PCH'},
0xA303 : {'name' : 'H310',   'id' : PCH_ID_3xx, 'code' : PCH_CODE_3xx, 'longname' : 'Intel H310 (300 series) PCH'},
0xA30A : {'name' : 'C242',   'id' : PCH_ID_3xx, 'code' : PCH_CODE_3xx, 'longname' : 'Intel C242 (300 series) PCH'},
0xA309 : {'name' : 'C246',   'id' : PCH_ID_3xx, 'code' : PCH_CODE_3xx, 'longname' : 'Intel C246 (300 series) PCH'},
0xA30D : {'name' : 'HM370',  'id' : PCH_ID_3xx, 'code' : PCH_CODE_3xx, 'longname' : 'Intel HM370 (300 series) PCH'},
0xA30C : {'name' : 'QM370',  'id' : PCH_ID_3xx, 'code' : PCH_CODE_3xx, 'longname' : 'Intel QM370 (300 series) PCH'},
0xA30E : {'name' : 'CM246',  'id' : PCH_ID_3xx, 'code' : PCH_CODE_3xx, 'longname' : 'Intel CM246 (300 series) PCH'},
0x9D84 : {'name' : 'PCH-U',  'id' : PCH_ID_3xx, 'code' : PCH_CODE_3xx, 'longname' : 'Intel 300 series On-Package PCH'},

# C600 and X79 series PCH
0x1D41 : {'name' : 'C600', 'id' : PCH_ID_C60x, 'code' : PCH_CODE_C60x, 'longname' : 'Intel C600/X79 series PCH'},

# C610 and X99 series PCH
0x8D40 : {'name' : 'C610',   'id' : PCH_ID_C61x, 'code' : PCH_CODE_C61x, 'longname' : 'Intel Wellsburg (C610/X99 series) PCH'},
0x8D44 : {'name' : 'C610-G', 'id' : PCH_ID_C61x, 'code' : PCH_CODE_C61x, 'longname' : 'Intel Wellsburg-G (C610/X99 series) PCH'},
0x8D47 : {'name' : 'C610-X', 'id' : PCH_ID_C61x, 'code' : PCH_CODE_C61x, 'longname' : 'Intel Wellsburg-X (C610/X99 series) PCH'},

# C620 series PCH
0xA1C1 : {'name' : 'C621', 'id' : PCH_ID_C620, 'code' : PCH_CODE_C620, 'longname' : 'Intel C621 (C620 series) PCH'},
0xA1C2 : {'name' : 'C622', 'id' : PCH_ID_C620, 'code' : PCH_CODE_C620, 'longname' : 'Intel C622 (C620 series) PCH'},
0xA1C3 : {'name' : 'C624', 'id' : PCH_ID_C620, 'code' : PCH_CODE_C620, 'longname' : 'Intel C624 (C620 series) PCH'},
0xA1C4 : {'name' : 'C625', 'id' : PCH_ID_C620, 'code' : PCH_CODE_C620, 'longname' : 'Intel C625 (C620 series) PCH'},
0xA1C5 : {'name' : 'C626', 'id' : PCH_ID_C620, 'code' : PCH_CODE_C620, 'longname' : 'Intel C626 (C620 series) PCH'},
0xA1C6 : {'name' : 'C627', 'id' : PCH_ID_C620, 'code' : PCH_CODE_C620, 'longname' : 'Intel C627 (C620 series) PCH'},
0xA1C7 : {'name' : 'C628', 'id' : PCH_ID_C620, 'code' : PCH_CODE_C620, 'longname' : 'Intel C628 (C620 series) PCH'},
0xA242 : {'name' : 'C624', 'id' : PCH_ID_C620, 'code' : PCH_CODE_C620, 'longname' : 'Intel C624 (C620 series) PCH'},
0xA243 : {'name' : 'C627', 'id' : PCH_ID_C620, 'code' : PCH_CODE_C620, 'longname' : 'Intel C627 (C620 series) PCH'},
0xA244 : {'name' : 'C621', 'id' : PCH_ID_C620, 'code' : PCH_CODE_C620, 'longname' : 'Intel C621 (C620 series) PCH'},
0xA245 : {'name' : 'C627', 'id' : PCH_ID_C620, 'code' : PCH_CODE_C620, 'longname' : 'Intel C627 (C620 series) PCH'},
0xA246 : {'name' : 'C628', 'id' : PCH_ID_C620, 'code' : PCH_CODE_C620, 'longname' : 'Intel C628 (C620 series) PCH'}
}

try:
    from custom_chipsets import *
except :
    pass

Chipset_Code = dict( [(Chipset_Dictionary[ _did ]['code'], _did) for _did in Chipset_Dictionary] )
pch_codes = dict([(pch_dictionary[_did]['code'], _did) for _did in pch_dictionary])

def print_supported_chipsets():
    codes_dict = collections.defaultdict(list)
    for _did in Chipset_Dictionary: codes_dict[ Chipset_Dictionary[ _did ]['code'] ].append( _did )
    logger().log( "\nSupported platforms:\n" )
    logger().log( "DID     | Name           | Code   | Long Name" )
    logger().log( "-------------------------------------------------------------------------------------" )
    for _code in sorted(codes_dict):
        for _did in codes_dict[_code]:
            logger().log( " {:-#6x} | {:14} | {:6} | {:40}".format(_did, Chipset_Dictionary[_did]['name'], _code.lower(), Chipset_Dictionary[_did]['longname']) )


def f_xml(self, x):
    XMLFILE_RE = re.compile("^\w+\.xml")
    return ( x.find('common') == -1 and XMLFILE_RE.match(x) )
def map_xmlname(self, x):
    return x.split('.')[0]


class UnknownChipsetError(RuntimeError):
    pass

class DeviceNotFoundError(RuntimeError):
    pass

class RegisterNotFoundError(RuntimeError):
    pass

class RegisterTypeNotFoundError(RuntimeError):
    pass

class Chipset:

    def __init__(self, helper=None):
        if helper is None:
            self.helper = OsHelper()
        else:
            self.helper = helper

        self.vid            = 0xFFFF
        self.did            = 0xFFFF
        self.rid            = 0xFF
        self.code           = CHIPSET_CODE_UNKNOWN
        self.longname       = "Unrecognized Platform"
        self.id             = CHIPSET_ID_UNKNOWN
        self.pch_vid        = 0xFFFF
        self.pch_did        = 0xFFFF
        self.pch_rid        = 0xFF
        self.pch_code       = CHIPSET_CODE_UNKNOWN
        self.pch_longname   = 'Unrecognized PCH'
        self.pch_id         = CHIPSET_ID_UNKNOWN
        self.Cfg        = Cfg()

        #
        # Initializing 'basic primitive' HAL components
        # (HAL components directly using native OS helper functionality)
        #
        self.pci        = pci.Pci(self)
        self.mem        = physmem.Memory(self)
        self.msr        = msr.Msr(self)
        self.ucode      = ucode.Ucode(self)
        self.io         = io.PortIO(self)
        self.cpu        = cpu.CPU(self)
        self.msgbus     = msgbus.MsgBus(self)
        self.mmio       = mmio.MMIO(self)
        self.iobar      = iobar.IOBAR(self)
        self.igd        = igd.IGD(self)
        #
        # All HAL components which use above 'basic primitive' HAL components
        # should be instantiated in modules/utilcmd with an instance of chipset
        # Examples:
        # - initializing SPI HAL component in a module or util extension:
        #   self.spi = SPI( self.cs )
        #

    ##################################################################################
    #
    # Iitialization
    #
    ##################################################################################
    def detect_platform( self ):
        vid = 0xFFFF
        did = 0xFFFF
        rid = 0xFF
        pch_vid = 0xFFFF
        pch_did = 0xFFFF
        pch_rid = 0xFF
        try:
            vid_did = self.pci.read_dword(0, 0, 0, 0)
            vid = vid_did & 0xFFFF
            did = (vid_did >> 16) & 0xFFFF
            rid = self.pci.read_byte(0, 0, 0, PCI_HDR_RID_OFF)
        except:
            if logger().DEBUG: logger().error("pci.read_dword couldn't read platform VID/DID")
        try:
            vid_did = self.pci.read_dword(0, 31, 0, 0)
            pch_vid = vid_did & 0xFFFF
            pch_did = (vid_did >> 16) & 0xFFFF
            pch_rid = self.pci.read_byte(0, 31, 0, PCI_HDR_RID_OFF)
        except:
            if logger().DEBUG: logger().error("pci.read_dword couldn't read PCH VID/DID")
        return (vid, did, rid, pch_vid, pch_did, pch_rid)

    def init( self, platform_code, req_pch_code, start_driver, driver_exists=None, to_file=None, from_file=None ):

        _unknown_platform = False
        self.helper.start(start_driver, driver_exists, to_file, from_file)
        logger().log( '[CHIPSEC] API mode: {}'.format('using OS native API (not using CHIPSEC kernel module)' if self.use_native_api() else 'using CHIPSEC kernel module API') )

        self.vid, self.did, self.rid, self.pch_vid, self.pch_did, self.pch_rid = self.detect_platform()
        if platform_code is None:
            if VID_INTEL != self.vid:
                _unknown_platform = True
        else:
            self.vid = VID_INTEL
            if platform_code in Chipset_Code:
                self.did = Chipset_Code[ platform_code ]
                self.rid = 0x00
            else:
                _unknown_platform = True
                self.vid = 0xFFFF
                self.did = 0xFFFF
                self.rid = 0xFF

        if self.did in Chipset_Dictionary:
            data_dict       = Chipset_Dictionary[ self.did ]
            self.code       = data_dict['code'].lower()
            self.longname   = data_dict['longname']
            self.id         = data_dict['id']
        else:
            _unknown_platform = True
            self.longname   = 'UnknownPlatform'

        if req_pch_code is not None:
            self.pch_vid = VID_INTEL
            if req_pch_code in pch_codes:
                self.pch_did = pch_codes[req_pch_code]
                self.pch_rid = 0x00
            else:
                self.pch_vid = 0xFFFF
                self.pch_did = 0xFFFF
                self.pch_rid = 0xFF

        if self.pch_vid == VID_INTEL and self.pch_did in pch_dictionary:
            data_dict           = pch_dictionary[self.pch_did]
            self.pch_code       = data_dict['code'].lower()
            self.pch_longname   = data_dict['longname']
            self.pch_id         = data_dict['id']
        else:
            self.pch_longname = 'Default PCH'

        self.init_cfg()
        if _unknown_platform and start_driver:
            msg = 'Unsupported Platform: VID = 0x{:04X}, DID = 0x{:04X}, RID = 0x{:02X}'.format(self.vid,self.did,self.rid)
            logger().error( msg )
            raise UnknownChipsetError (msg)


    def destroy( self, start_driver ):
        self.helper.stop( start_driver )

    def get_chipset_id(self):
        return self.id

    def get_pch_id(self):
        return self.pch_id

    def get_chipset_code(self):
        return self.code

    def get_pch_code(self):
        return self.pch_code

    def get_chipset_name(self, id):
        return self.longname

    def get_pch_name(self, id):
        return self.pch_longname

    def print_chipset(self):
        logger().log("[*] Platform: {}\n          VID: {:04X}\n          DID: {:04X}\n          RID: {:02X}".format(self.longname, self.vid, self.did, self.rid))

    def print_pch(self):
        logger().log("[*] PCH     : {}\n          VID: {:04X}\n          DID: {:04X}\n          RID: {:02X}".format(self.pch_longname, self.pch_vid, self.pch_did, self.pch_rid))

    def is_core(self):
        return  self.get_chipset_id() in CHIPSET_FAMILY_CORE

    def is_server(self):
        return  self.get_chipset_id() in CHIPSET_FAMILY_XEON

    def is_atom(self):
        return self.get_chipset_id() in CHIPSET_FAMILY_ATOM

    def use_native_api(self):
        return self.helper.use_native_api()

    ##################################################################################
    #
    # Loading platform configuration from XML files in chipsec/cfg/
    #
    ##################################################################################

    def init_xml_configuration( self ):
        # Create a sorted config file list (xml only)
        _cfg_files = []
        _cfg_path = os.path.join( chipsec.file.get_main_dir(), 'chipsec/cfg' )
        for root, subdirs, files in os.walk(_cfg_path):
            _cfg_files.extend([os.path.join(root, x) for x in files if fnmatch.fnmatch(x, '*.xml')])
        _cfg_files.sort()
        if logger().DEBUG:
            logger().log("[*] Configuration Files:")
            for _xml in _cfg_files:
                logger().log("[*] - {}".format(_xml))

        # Locate common (chipsec/cfg/common*.xml) configuration XML files.
        loaded_files = []
        for _xml in _cfg_files:
            if fnmatch.fnmatch(os.path.basename(_xml), 'common*.xml'):
                loaded_files.append(_xml)

        # Locate platform specific (chipsec/cfg/<code>*.xml) configuration XML files.
        if self.code and CHIPSET_CODE_UNKNOWN != self.code:
            for _xml in _cfg_files:
                if fnmatch.fnmatch(os.path.basename(_xml), '{}*.xml'.format(self.code)):
                    loaded_files.append(_xml)

        # Locate PCH specific (chipsec/cfg/pch_<code>*.xml) configuration XML files.
        if self.pch_code and CHIPSET_CODE_UNKNOWN != self.pch_code:
            for _xml in _cfg_files:
                if fnmatch.fnmatch(os.path.basename(_xml), '{}*.xml'.format(self.pch_code)):
                    loaded_files.append(_xml)

        # Locate configuration files from all other XML files recursively (if any) excluding other platform configuration files.
        platform_files = []
        for plat in [c.lower() for c in Chipset_Code]:
            platform_files.extend([x for x in _cfg_files if fnmatch.fnmatch(os.path.basename(x), '{}*.xml'.format(plat)) or os.path.basename(x).startswith(PCH_CODE_PREFIX.lower())])
        loaded_files.extend([x for x in _cfg_files if x not in loaded_files and x not in platform_files])

        # Load all configuration files for this platform.
        if logger().DEBUG: logger().log("[*] Loading Configuration Files:")
        for _xml in loaded_files:
            self.init_cfg_xml(_xml, self.code, self.pch_code)

        # Load Bus numbers for this platform.
        if logger().DEBUG: logger().log("[*] Discovering Bus Configuration:")
        self.init_cfg_bus()

        self.Cfg.XML_CONFIG_LOADED = True


    def init_cfg_xml(self, fxml, code, pch_code):
        import xml.etree.ElementTree as ET
        if not os.path.exists( fxml ): return
        if logger().DEBUG: logger().log( "[*] looking for platform config in '{}'..".format(fxml) )
        tree = ET.parse( fxml )
        root = tree.getroot()
        for _cfg in root.iter('configuration'):
            if 'platform' not in _cfg.attrib:
                if logger().DEBUG: logger().log( "[*] loading common platform config from '{}'..".format(fxml) )
            elif code == _cfg.attrib['platform'].lower():
                if logger().DEBUG: logger().log( "[*] loading '{}' platform config from '{}'..".format(code,fxml) )
            elif pch_code == _cfg.attrib['platform'].lower():
                if logger().DEBUG: logger().log("[*] loading '{}' PCH config from '{}'..".format(pch_code,fxml))
            else: continue

            if logger().DEBUG: logger().log( "[*] loading integrated devices/controllers.." )
            for _pci in _cfg.iter('pci'):
                for _device in _pci.iter('device'):
                    _name = _device.attrib['name']
                    del _device.attrib['name']
                    if 'undef' in _device.attrib:
                        if _name in self.Cfg.CONFIG_PCI:
                            if logger().DEBUG: logger().log("    - {:16}: {}".format(_name, _device.attrib['undef']))
                            self.Cfg.CONFIG_PCI.pop(_name, None)
                        continue
                    self.Cfg.CONFIG_PCI[ _name ] = _device.attrib
                    if logger().DEBUG: logger().log( "    + {:16}: {}".format(_name, _device.attrib) )
            if logger().DEBUG: logger().log( "[*] loading MMIO BARs.." )
            for _mmio in _cfg.iter('mmio'):
                for _bar in _mmio.iter('bar'):
                    _name = _bar.attrib['name']
                    del _bar.attrib['name']
                    if 'undef' in _bar.attrib:
                        if _name in self.Cfg.MMIO_BARS:
                            if logger().DEBUG: logger().log("    - {:16}: {}".format(_name, _bar.attrib['undef']))
                            self.Cfg.MMIO_BARS.pop(_name, None)
                        continue
                    self.Cfg.MMIO_BARS[ _name ] = _bar.attrib
                    if logger().DEBUG: logger().log( "    + {:16}: {}".format(_name, _bar.attrib) )
            if logger().DEBUG: logger().log( "[*] loading I/O BARs.." )
            for _io in _cfg.iter('io'):
                for _bar in _io.iter('bar'):
                    _name = _bar.attrib['name']
                    del _bar.attrib['name']
                    if 'undef' in _bar.attrib:
                        if _name in self.Cfg.IO_BARS:
                            if logger().DEBUG: logger().log("    - {:16}: {}".format(_name, _bar.attrib['undef']))
                            self.Cfg.IO_BARS.pop(_name, None)
                        continue
                    self.Cfg.IO_BARS[ _name ] = _bar.attrib
                    if logger().DEBUG: logger().log( "    + {:16}: {}".format(_name, _bar.attrib) )
            if logger().DEBUG: logger().log( "[*] loading memory ranges.." )
            for _memory in _cfg.iter('memory'):
                for _range in _memory.iter('range'):
                    _name = _range.attrib['name']
                    del _range.attrib['name']
                    if 'undef' in _range.attrib:
                        if _name in self.Cfg.MEMORY_RANGES:
                            if logger().DEBUG: logger().log("    - {:16}: {}".format(_name, _range.attrib['undef']))
                            self.Cfg.MEMORY_RANGES.pop(_name, None)
                        continue
                    self.Cfg.MEMORY_RANGES[ _name ] = _range.attrib
                    if logger().DEBUG: logger().log( "    + {:16}: {}".format(_name, _range.attrib) )
            if logger().DEBUG: logger().log( "[*] loading configuration registers.." )
            for _registers in _cfg.iter('registers'):
                for _register in _registers.iter('register'):
                    _name = _register.attrib['name']
                    del _register.attrib['name']
                    if 'undef' in _register.attrib:
                        if _name in self.Cfg.REGISTERS:
                            if logger().DEBUG: logger().log("    - {:16}: {}".format(_name, _register.attrib['undef']))
                            self.Cfg.REGISTERS.pop(_name, None)
                        continue
                    if 'size' not in _register.attrib: _register.attrib['size'] = "0x4"
                    if 'desc' not in _register.attrib: _register.attrib['desc'] = ''
                    reg_fields = {}
                    if _register.find('field') is not None:
                        for _field in _register.iter('field'):
                            _field_name = _field.attrib['name']
                            del _field.attrib['name']
                            if 'desc' not in _field.attrib: _field.attrib['desc'] = ''
                            reg_fields[ _field_name ] = _field.attrib
                        _register.attrib['FIELDS'] = reg_fields
                    self.Cfg.REGISTERS[ _name ] = _register.attrib
                    if logger().DEBUG: logger().log( "    + {:16}: {}".format(_name, _register.attrib) )
            if logger().DEBUG: logger().log( "[*] loading controls.." )
            for _controls in _cfg.iter('controls'):
                for _control in _controls.iter('control'):
                    _name = _control.attrib['name']
                    del _control.attrib['name']
                    if 'undef' in _control.attrib:
                        if _name in self.Cfg.CONTROLS:
                            if logger().DEBUG: logger().log("    - {:16}: {}".format(_name, _control.attrib['undef']))
                            self.Cfg.CONTROLS.pop(_name, None)
                        continue
                    self.Cfg.CONTROLS[ _name ] = _control.attrib
                    if logger().DEBUG: logger().log( "    + {:16}: {}".format(_name, _control.attrib) )

    def init_cfg_bus( self ):
        if logger().DEBUG: logger().log( '[*] loading device buses..' )
        if QUIET_PCI_ENUM:
            old_hal_state = logger().HAL
            logger().HAL = False
        try:
            enum_devices = self.pci.enumerate_devices()
        except:
            if logger().DEBUG: logger().log('[*] Unable to enumerate PCI devices.')
            enum_devices = []
        if QUIET_PCI_ENUM:
            logger().HAL = old_hal_state
        for config_device in self.Cfg.CONFIG_PCI:
            device_data = self.Cfg.CONFIG_PCI[config_device]
            xml_vid  = device_data.get( 'vid', None )
            xml_did  = device_data.get( 'did', None )
            if (xml_vid and xml_did):
                bus_list = []
                did_list = [int(_,16) for _ in xml_did.split(',')]
                for enum_dev in enum_devices:
                    if ((int(device_data['dev'],16), int(device_data['fun'],16), int(xml_vid,16)) == enum_dev[1:4]) and (enum_dev[4] in did_list):
                        bus_list.append( hex(enum_dev[0]) )
                        if logger().DEBUG: logger().log( '    + {:16s}: VID 0x{:04X} - DID 0x{:04X} -> Bus 0x{:02X}'.format(config_device, enum_dev[3], enum_dev[4], enum_dev[0]) )
                if len(bus_list):
                    self.Cfg.BUS[ config_device ] = bus_list

    #
    # Load chipsec/cfg/<code>.py configuration file for platform <code>
    #
    def init_cfg(self):
        if self.code and '' != self.code:
            try:
                module_path = 'chipsec.cfg.' + self.code
                module = importlib.import_module( module_path )
                logger().log_good( "imported platform specific configuration: chipsec.cfg.{}".format(self.code) )
                self.Cfg = getattr( module, self.code )()
            except ImportError as msg:
                if logger().DEBUG: logger().log( "[*] Couldn't import chipsec.cfg.{}\n{}".format( self.code, str(msg) ) )

        #
        # Initialize platform configuration from XML files
        #
        try:
            self.init_xml_configuration()
        except:
            if logger().DEBUG: logger().log_bad(traceback.format_exc())
            pass


    ##################################################################################
    #
    # Functions which access configuration of integrated PCI devices (interfaces, controllers)
    # by device name (defined in XML configuration files)
    #
    ##################################################################################

    def get_device_BDF( self, device_name ):
        device = self.Cfg.CONFIG_PCI[ device_name ]
        if device is None or device == {}: raise DeviceNotFoundError ('DeviceNotFound: {}'.format(device_name))
        b = int(device['bus'],16)
        d = int(device['dev'],16)
        f = int(device['fun'],16)
        return (b,d,f)

    def get_DeviceVendorID( self, device_name ):
        (b,d,f) = self.get_device_BDF( device_name )
        return self.pci.get_DIDVID( b, d, f )

    def is_device_enabled( self, device_name ):
        (b,d,f) = self.get_device_BDF( device_name )
        return self.pci.is_enabled( b, d, f )

    def switch_device_def( self, target_dev, source_dev ):
        (b,d,f) = self.get_device_BDF( source_dev )
        self.Cfg.CONFIG_PCI[ target_dev ]['bus'] = str(b)
        self.Cfg.CONFIG_PCI[ target_dev ]['dev'] = str(d)
        self.Cfg.CONFIG_PCI[ target_dev ]['fun'] = str(f)

##################################################################################
#
# Main functionality to read/write configuration registers
# based on their XML configuration
#
# is_register_defined
#   checks if register is defined in the XML config
# get_register_bus/get_device_bus
#   returns list of buses device/register was discovered on
# read_register/write_register
#   reads/writes configuration register (by name)
# get_register_field (set_register_field)
#   reads/writes the value of the field (by name) of configuration register (by register value)
# read_register_field (write_register_field)
#   reads/writes the value of the field (by name) of configuration register (by register name)
# register_has_field
#   checks if the register has specific field
# print_register
#   prints configuration register
# get_control/set_control
#   reads/writes some control field (by name)
#
##################################################################################


    def is_register_defined(self, reg_name):
        try:
            return (self.Cfg.REGISTERS[reg_name] is not None)
        except KeyError:
            #if logger().DEBUG: logger().error( "'{}' register definition not found in XML config".format(reg_name))
            #raise RegisterNotFoundError, ('RegisterNotFound: {}'.format(reg_name))
            return False

    def get_register_def(self, reg_name, bus_index=0):
        reg_def = self.Cfg.REGISTERS[reg_name]
        if (reg_def["type"] == "pcicfg" or reg_def["type"] == "mmcfg") and ("device" in reg_def):
            dev_name = reg_def["device"]
            if dev_name in self.Cfg.CONFIG_PCI:
                dev = self.Cfg.CONFIG_PCI[dev_name]
                reg_def['bus'] = dev['bus']
                reg_def['dev'] = dev['dev']
                reg_def['fun'] = dev['fun']
                if dev_name in self.Cfg.BUS:
                    if bus_index < len(self.Cfg.BUS[dev_name]):
                        reg_def['bus'] = self.Cfg.BUS[dev_name][bus_index]
                    else:
                        logger().error( "Bus index {:d} for '{}' not found.".format(bus_index, dev_name) )
        return reg_def

    def get_register_bus(self, reg_name):
        name = self.Cfg.REGISTERS[reg_name].get( 'device', None )
        return self.get_device_bus( name )

    def get_device_bus(self, dev_name):
        return self.Cfg.BUS.get( dev_name, None )

    def read_register(self, reg_name, cpu_thread=0, bus_index=0):
        reg = self.get_register_def( reg_name, bus_index )
        rtype = reg['type']
        reg_value = 0
        if RegisterType.PCICFG == rtype:
            b = int(reg['bus'], 16)
            d = int(reg['dev'], 16)
            f = int(reg['fun'], 16)
            o = int(reg['offset'], 16)
            size = int(reg['size'], 16)
            if   1 == size: reg_value = self.pci.read_byte ( b, d, f, o )
            elif 2 == size: reg_value = self.pci.read_word ( b, d, f, o )
            elif 4 == size: reg_value = self.pci.read_dword( b, d, f, o )
            elif 8 == size: reg_value = (self.pci.read_dword( b, d, f, o+4 ) << 32) | self.pci.read_dword(b, d, f, o)
        elif RegisterType.MMCFG == rtype:
            reg_value = self.mmio.read_mmcfg_reg(int(reg['bus'],16), int(reg['dev'],16), int(reg['fun'],16), int(reg['offset'],16), int(reg['size'],16) )
        elif RegisterType.MMIO == rtype:
            reg_value = self.mmio.read_MMIO_BAR_reg(reg['bar'], int(reg['offset'],16), int(reg['size'],16) )
        elif RegisterType.MSR == rtype:
            (eax, edx) = self.msr.read_msr( cpu_thread, int(reg['msr'],16) )
            reg_value = (edx << 32) | eax
        elif RegisterType.PORTIO == rtype:
            port = int(reg['port'],16)
            size = int(reg['size'],16)
            reg_value = self.io._read_port( port, size )
        elif RegisterType.IOBAR == rtype:
            reg_value = self.iobar.read_IO_BAR_reg( reg['bar'], int(reg['offset'],16), int(reg['size'],16) )
        elif RegisterType.MSGBUS == rtype:
            reg_value = self.msgbus.msgbus_reg_read( int(reg['port'],16), int(reg['offset'],16) )
        elif RegisterType.MM_MSGBUS == rtype:
            reg_value = self.msgbus.mm_msgbus_reg_read(int(reg['port'],16), int(reg['offset'],16))
        else:
            raise RegisterTypeNotFoundError("Register type not found: {}".format(rtype))

        return reg_value

    def write_register(self, reg_name, reg_value, cpu_thread=0, bus_index=0):
        reg = self.get_register_def( reg_name, bus_index )
        rtype = reg['type']
        if RegisterType.PCICFG == rtype:
            b = int(reg['bus'],16)
            d = int(reg['dev'],16)
            f = int(reg['fun'],16)
            o = int(reg['offset'],16)
            size = int(reg['size'],16)
            if   1 == size: self.pci.write_byte( b, d, f, o, reg_value )
            elif 2 == size: self.pci.write_word( b, d, f, o, reg_value )
            elif 4 == size: self.pci.write_dword( b, d, f, o, reg_value )
            elif 8 == size:
                self.pci.write_dword( b, d, f, o, (reg_value & 0xFFFFFFFF) )
                self.pci.write_dword( b, d, f, o + 4, (reg_value>>32 & 0xFFFFFFFF) )
        elif RegisterType.MMCFG == rtype:
            self.mmio.write_mmcfg_reg(int(reg['bus'],16), int(reg['dev'],16), int(reg['fun'],16), int(reg['offset'],16), int(reg['size'],16), reg_value )
        elif RegisterType.MMIO == rtype:
            self.mmio.write_MMIO_BAR_reg(reg['bar'], int(reg['offset'],16), reg_value, int(reg['size'],16) )
        elif RegisterType.MSR == rtype:
            eax = (reg_value & 0xFFFFFFFF)
            edx = ((reg_value >> 32) & 0xFFFFFFFF)
            self.msr.write_msr( cpu_thread, int(reg['msr'],16), eax, edx )
        elif RegisterType.PORTIO == rtype:
            port = int(reg['port'],16)
            size = int(reg['size'],16)
            self.io._write_port( port, reg_value, size )
        elif RegisterType.IOBAR == rtype:
            self.iobar.write_IO_BAR_reg( reg['bar'], int(reg['offset'],16), int(reg['size'],16), reg_value )
        elif RegisterType.MSGBUS == rtype:
            self.msgbus.msgbus_reg_write( int(reg['port'],16), int(reg['offset'],16), reg_value )
        elif RegisterType.MM_MSGBUS == rtype:
            self.msgbus.mm_msgbus_reg_write(int(reg['port'],16), int(reg['offset'],16), reg_value)
        else:
            raise RegisterTypeNotFoundError("Register type not found: {}".format(rtype))

    def read_register_dict( self, reg_name):
        reg_value = self.read_register(reg_name)
        reg_def = self.get_register_def(reg_name)
        result = reg_def
        result['value'] = reg_value
        for f in reg_def['FIELDS']:
            result['FIELDS'][f]['bit'] = field_bit = int(reg_def['FIELDS'][f]['bit'])
            result['FIELDS'][f]['size'] = field_size = int(reg_def['FIELDS'][f]['size'])
            field_mask = 0
            for i in range(field_size):
                field_mask = (field_mask << 1) | 1
            result['FIELDS'][f]['value'] = (reg_value >> field_bit) & field_mask
        return result

    def get_register_field_mask(self, reg_name, reg_field=None,
                                preserve_field_position=False):
        reg_def = self.get_register_def(reg_name)
        if reg_field is not None:
            field_attrs = reg_def['FIELDS'][reg_field]
            mask_start = int(field_attrs['bit'])
            mask = (1 << int(field_attrs['size'])) - 1
        else:
            mask_start = 0
            mask = (1 << (int(reg_def['size'],16) * 8)) - 1
        if preserve_field_position:
            return mask << mask_start
        else:
            return mask

    def get_register_field(self, reg_name, reg_value, field_name,
                           preserve_field_position=False):
        field_attrs = self.get_register_def(reg_name)['FIELDS'][field_name]
        field_bit   = int(field_attrs['bit'])
        field_mask  = (1 << int(field_attrs['size'])) - 1
        if preserve_field_position: return reg_value & (field_mask << field_bit)
        else:                       return (reg_value >> field_bit) & field_mask

    def set_register_field(self, reg_name, reg_value, field_name,
                           field_value, preserve_field_position=False):
        field_attrs = self.get_register_def(reg_name)['FIELDS'][field_name]
        field_bit   = int(field_attrs['bit'])
        field_mask  = (1 << int(field_attrs['size'])) - 1
        reg_value  &= ~(field_mask << field_bit) # keep other fields
        if preserve_field_position: reg_value |= (field_value & (field_mask << field_bit))
        else:                       reg_value |= ((field_value & field_mask) << field_bit)
        return reg_value

    def read_register_field( self, reg_name, field_name, preserve_field_position=False, cpu_thread=0 ):
        reg_value = self.read_register(reg_name, cpu_thread)
        return self.get_register_field(reg_name, reg_value, field_name, preserve_field_position)

    def write_register_field( self, reg_name, field_name, field_value, preserve_field_position=False, cpu_thread=0 ):
        reg_value = self.read_register(reg_name, cpu_thread)
        reg_value_new = self.set_register_field(reg_name, reg_value, field_name, field_value, preserve_field_position)
        #logger().log("set register {} (0x{:x}) field {} = 0x{:x} ==> 0x{:x}".format(reg_name, reg_value, field_name, field_value, reg_value_new))
        return self.write_register(reg_name, reg_value_new, cpu_thread)

    def register_has_field( self, reg_name, field_name ):
        reg_def = self.get_register_def(reg_name )
        if 'FIELDS' not in reg_def:
            return False
        return (field_name in reg_def['FIELDS'])

    def _register_fields_str(self, reg_def, reg_val):
        reg_fields_str = ''
        if 'FIELDS' in reg_def:
          reg_fields_str += '\n'
          # sort fields by their bit position in the register
          sorted_fields = sorted( reg_def['FIELDS'].items(), key=lambda field: int(field[1]['bit']) )
          for f in sorted_fields:
            field_attrs = f[1]
            field_bit = int(field_attrs['bit'])
            field_size = int(field_attrs['size'])
            field_mask = 0
            for i in range(field_size):
                field_mask = (field_mask << 1) | 1
            field_value = (reg_val >> field_bit) & field_mask
            field_desc = (' << ' + field_attrs['desc'] + ' ') if (field_attrs['desc'] != '') else ''
            reg_fields_str += ("    [{:02d}] {:16} = {:X}{}\n".format(field_bit,f[0],field_value,field_desc))

        if '' != reg_fields_str: reg_fields_str = reg_fields_str[:-1]
        return reg_fields_str

    def print_register(self, reg_name, reg_val, bus_index=0):
        reg = self.get_register_def( reg_name, bus_index )
        rtype = reg['type']
        reg_str = ''
        reg_val_str = "0x{:{width}X}".format(reg_val,width=(int(reg['size'],16)*2))
        if RegisterType.PCICFG == rtype or RegisterType.MMCFG == rtype:
            b = int(reg['bus'],16)
            d = int(reg['dev'],16)
            f = int(reg['fun'],16)
            o = int(reg['offset'],16)
            mmcfg_off_str =  ''
            if RegisterType.MMCFG == rtype:
                mmcfg_off_str += ", MMCFG + 0x{:X}".format((b*32*8 + d*8 + f) * 0x1000 + o)
            reg_str = "[*] {} = {} << {} (b:d.f {:02d}:{:02d}.{:d} + 0x{:X}{})".format(reg_name, reg_val_str, reg['desc'], b, d, f, o, mmcfg_off_str)
        elif RegisterType.MMIO == rtype:
            reg_str = "[*] {} = {} << {} ({} + 0x{:X})".format(reg_name, reg_val_str, reg['desc'], reg['bar'], int(reg['offset'],16))
        elif RegisterType.MSR == rtype:
            reg_str = "[*] {} = {} << {} (MSR 0x{:X})".format(reg_name, reg_val_str, reg['desc'], int(reg['msr'],16))
        elif RegisterType.PORTIO == rtype:
            reg_str = "[*] {} = {} << {} (I/O port 0x{:X})".format(reg_name, reg_val_str, reg['desc'], int(reg['port'],16))
        elif RegisterType.IOBAR == rtype:
            reg_str = "[*] {} = {} << {} (I/O {} + 0x{:X})".format(reg_name, reg_val_str, reg['desc'], reg['bar'], int(reg['offset'],16))
        elif RegisterType.MSGBUS == rtype or RegisterType.MM_MSGBUS == rtype:
            reg_str = "[*] {} = {} << {} (msgbus port 0x{:X}, off 0x{:X})".format(reg_name, reg_val_str, reg['desc'], int(reg['port'],16), int(reg['offset'],16))

        reg_str += self._register_fields_str(reg, reg_val)
        logger().log( reg_str )
        return reg_str

    def get_control(self, control_name, cpu_thread=0, with_print=0):
        control = self.Cfg.CONTROLS[ control_name ]
        reg     = control['register']
        field   = control['field']
        reg_data = self.read_register(reg)
        if with_print: self.print_register(reg, reg_data)
        return self.get_register_field(reg, reg_data, field)

    def set_control(self, control_name, control_value, cpu_thread=0):
        control = self.Cfg.CONTROLS[control_name]
        reg     = control['register']
        field   = control['field']
        return self.write_register_field(reg, field, control_value, cpu_thread)

    def is_control_defined(self, control_name):
        try:
            return (self.Cfg.CONTROLS[ control_name ] is not None)
        except KeyError:
            return False

_chipset = None

def cs():
    global _chipset
    from chipsec.helper.oshelper import helper
    if _chipset is None:
        _chipset = Chipset(helper())
    return _chipset
