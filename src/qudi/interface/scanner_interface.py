# -*- coding: utf-8 -*-

"""
This module contains the Qudi interface file for scanning probe hardware.

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-iqo-modules/>

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

import datetime
import numpy as np
from abc import abstractmethod
from qudi.core.module import Base

__all__ = ['ScannerInterface']

from PySide2 import QtCore
from abc import abstractmethod

from qudi.core.module import Base


class ScannerInterface(Base):
    """ This is the Interface class to define the controls for a scanning probe device

    A scanner device is hardware that can move multiple axes.
    """

    @abstractmethod
    def get_constraints(self):
        """ Get hardware constraints/limitations.

        @return dict: scanner constraints
        """
        pass

    @abstractmethod
    def get_position(self):
        """ Get current scanner position (i.e. from position feedback sensors).

        For scanning devices that do not have position feedback sensors, simply return the target
        position

        @return dict: current position per axis of the scanner.
        """
        pass

    @abstractmethod
    def set_position(self, position_dict):
        """ Set scanner position.

        @param dict position_dict: dictionary of the positions where the scanner should go.
        """
        pass

    @abstractmethod
    def go_home(self):
        """ Homing of the scanner positions.
        """
        pass