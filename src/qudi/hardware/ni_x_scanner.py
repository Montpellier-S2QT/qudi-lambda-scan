# -*- coding: utf-8 -*-

__all__ = ['NIXScanner']

import time
import nidaqmx as ni
from PySide2 import QtCore
from scipy.interpolate import interp1d

from qudi.interface.scanner_interface import ScannerInterface
from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from qudi.util.mutex import Mutex
from qudi.util.helpers import natural_sort, in_range


class NIXScanner(ScannerInterface):
    """ This is a hardware module to control the NI x series card for scanners connected on the analog outputs.

    Example config for copy-paste:

    ni_x_scanner:
        module.Class: 'ni_x_scanner.NIXScanner'
        options:
            device_name: 'Dev1'
            scanner_axis:
                x:
                    channel: 'ao0'
                    unit: 'um'
                    voltage_range: [0, 8.0]
                    position_range: [0, 24.0]
                y:
                    channel: 'ao1'
                    unit: 'um'
                    voltage_range: [0, 8.0]
                    position_range: [0, 24.0]
                z:
                    channel: 'ao2'
                    unit: 'um'
                    voltage_range: [0, 8.0]
                    position_range: [0, 24.0]
                a:
                    channel: 'ao0'
                    unit: 'um'
                    voltage_range: [0, 8.0]
                    position_range: [0, 24.0]
    """
    _device_name = ConfigOption(name='device_name', default='Dev1', missing='warn')
    _scanner_axis = ConfigOption(name='scanner_axis', missing='warn')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mutex = Mutex()

    def on_activate(self):
        """ Activate NI card and perform sanity check.
        """
        # Find device name in available devices and open the corresponding device.
        device_names = ni.system.System().devices.device_names
        if self._device_name.lower() not in set(dev.lower() for dev in device_names):
            raise ValueError(
                f'Device name "{self._device_name}" not found in list of connected devices: '
                f'{device_names}\nActivation of NIXSeriesAnalogOutput failed!'
            )
        for device_name in device_names:
            if device_name.lower() == self._device_name.lower():
                self._device_name = device_name
                break
        self._device = ni.system.Device(self._device_name)

        #TODO : Check if channels are aivalble 'I am so lazy sorry'

        # Check the axis voltage range parameters with the hardware limits and define the conversion between voltage and return value.
        self._voltage_to_pos = {}
        self._pos_to_voltage = {}
        for axis, params in self._scanner_axis.items():
            v_min, v_max = params["voltage_range"]
            hw_min, hw_max = self._device.ao_voltage_rngs
            if not (hw_min < v_min < hw_max and hw_min < v_max < hw_max):
                self.log.error('Voltage range of axis {} ({}) is outside the hardware limits {}.'
                               .format(axis, (v_min, v_max), (hw_min, hw_max)))
                return 
            if not v_min < v_max:
                params["voltage_range"] = [v_max, v_min]
            self._voltage_to_pos[axis] = interp1d([v_min, v_max], params["position_range"])
            self._pos_to_voltage[axis] = interp1d(params["position_range"], [v_min, v_max])

        self._constraints = {
            "hardware_voltage_limits" : self._device.ao_voltage_rngs,
        }

        # Create NI tasks for each axis.
        self._axis_ao_task = {}
        self._axis_ai_task = {}
        for axis, params in self._scanner_axis.items():
            v_min, v_max = params["voltage_range"]

            self._axis_ao_task[axis] = ni.Task("{}_ao".format(axis))
            self._axis_ao_task.ao_channels.add_ao_voltage_chan(
                physical_channel="/{}/{}".format(self._device_name, params["channel"]),
                min_val=v_min,
                max_val=v_max,
            )

            self._axis_ai_task[axis] = ni.Task("{}_ai".format(axis))
            self._axis_ai_task.ai_channels.add_ai_voltage_chan(
                physical_channel="/{}/_{}_vs_aognd".format(self._device_name, params["channel"]),
                min_val=v_min,
                max_val=v_max,
            )

    def on_deactivate(self):

        # Check if ao task finished and close task :
        if self._axis_ao_task.is_task_done():
            self._axis_ao_task.stop()
        self._axis_ao_task.close()

        # Close ai task :
        self._axis_ai_task.close()

    def get_constraints(self):
        """ Get hardware constraints/limitations.

        @return dict: scanner constraints
        """
        return self._constraints

    def get_position(self):
        """ Get current scanner position (i.e. from position feedback sensors).

        For scanning devices that do not have position feedback sensors, simply return the target
        position

        @return dict: current position per axis of the scanner.
        """
        with self._thread_lock:
            position_dict = {}
            for axis in self._scanner_axis.keys():
                position_dict[axis] = self._axis_ai_task[axis]
            return position_dict

    def set_position(self, position_dict):
        """ Set scanner position.

        @param dict position_dict: dictionary of the positions where the scanner should go.
        """
        for axis, position in position_dict:
            self._axis_ao_task[axis].write(position)

    def go_home(self):
        """ Homing of the scanner positions.
        """
        for axis, position in position_dict:
            self._axis_ao_task[axis].write(0)