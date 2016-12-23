#!/usr/bin/env python
#
# Copyright 2013 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

from __future__ import print_function

from gnuradio import gr, blocks
from gnuradio.eng_arg import eng_float, intx
from argparse import ArgumentParser
import os, sys

try:
    from gnuradio import qtgui
    from PyQt4 import QtGui, QtCore
    import sip
except ImportError:
    print("Error: Program requires PyQt4 and gr-qtgui.")
    sys.exit(1)

try:
    import scipy
except ImportError:
    print("Error: Scipy required (www.scipy.org).")
    sys.exit(1)

try:
    from gnuradio.qtgui.plot_form import *
    from gnuradio.qtgui.plot_base import *
except ImportError:
    from plot_form import *
    from plot_base import *

class plot_base(gr.top_block):
    def __init__(self, filelist, samp_rate, start,
                 nsamples, max_nsamples,
                 auto_scale):
        gr.top_block.__init__(self)

        self._filelist = filelist
        self._samp_rate = samp_rate
        self._center_freq = 0
        self._start = start
        self._max_nsamps = max_nsamples
        self._nsigs = len(self._filelist)
        self._auto_scale = auto_scale
        self._nsamps = nsamples
        self._is_setup = False

        self._y_min = -20
        self._y_max = 20
        self._y_range = 2
        self._y_value = 1
        self.gui_y_axis = None

        self.qapp = QtGui.QApplication(sys.argv)

    def setup(self):
        self.skip = blocks.skiphead(self.dsize, self._start)

        n = 0
        self.srcs = list()
        self._data_min = sys.maxsize
        self._data_max = -sys.maxsize - 1
        for f in self._filelist:
            data,_min,_max = self.read_samples(f, self._start, self._nsamps)
            if(_min < self._data_min):
                self._data_min = _min
            if(_max > self._data_max):
                self._data_max = _max

            self.srcs.append(self.src_type(data))

            # Set default labels based on file names
            fname = f.split("/")[-1]
            #self.gui_snk.set_line_label(n, "{0}".format(fname))
            n += 1

        self.connect(self.srcs[0], self.skip)
        self.connect(self.skip, (self.gui_snk, 0))

        for i,s in enumerate(self.srcs[1:]):
            self.connect(s, (self.gui_snk, i+1))

        self.gui_snk.set_update_time(0)
        self.gui_snk.enable_menu(False)
        self.auto_scale(self._auto_scale)

        # Get Python Qt references
        pyQt  = self.gui_snk.pyqwidget()
        self.pyWin = sip.wrapinstance(pyQt, QtGui.QWidget)

        self._is_setup = True

    def is_setup(self):
        return self._is_setup

    def set_y_axis(self, y_min, y_max):
        if(not self._auto_scale):
            self.gui_snk.set_intensity_range(y_min, y_max)
            return y_min, y_max
        else:
            return None

    def get_gui(self):
        if(self.is_setup()):
            return self.pyWin
        else:
            return None

    def reset(self, newstart, newnsamps):
        self.stop()
        self.wait()

        self._start = newstart

        self._data_min = sys.maxsize
        self._data_max = -sys.maxsize - 1
        for s,f in zip(self.srcs, self._filelist):
            data,_min,_max = self.read_samples(f, self._start, newnsamps)
            if(_min < self._data_min):
                self._data_min = _min
            if(_max > self._data_max):
                self._data_max = _max

            s.set_data(data)
            if(len(data) < newnsamps):
                newnsamps = len(data)

        self.auto_scale(self._auto_scale)
        self._nsamps = newnsamps
        self.start()

    def auto_scale(self, state):
        if(state > 0):
            self.gui_snk.set_intensity_range(self._data_min, self._data_max)
            self._auto_scale = True
            self._y_value = self._data_max
            self._y_range = self._data_max - self._data_min
            self._y_min = 10*self._data_min
            self._y_max = 10*self._data_max

            if(self.gui_y_axis):
                self.gui_y_axis(self._data_min, self._data_max)
        else:
            self._auto_scale = False

def setup_options(desc):
    parser = ArgumentParser(description=desc, conflict_handler="resolve")
    parser.add_argument("-N", "--nsamples", type=int, default=1000000,
                      help="Set the number of samples to display [default=%(default)r]")
    parser.add_argument("-S", "--start", type=int, default=0,
                      help="Starting sample number [default=%(default)r]")
    parser.add_argument("-C", "--ncols", type=int, default=100,
                      help="Number of columns [default=%(default)r]")
    parser.add_argument("-R", "--nrows", type=int, default=100,
                      help="Number of rows [default=%(default)r]")
    parser.add_argument("-r", "--sample-rate", type=eng_float, default=1.0,
                      help="Set the sample rate of the signal [default=%(default)r]")
    parser.add_argument("--no-auto-scale", action="store_true",
                      help="Do not auto-scale the plot [default=%(default)r]")
    parser.add_argument("files", nargs="+", metavar="FILE",
                      help="Input files with complex samples")
    args = parser.parse_args()

    return args

