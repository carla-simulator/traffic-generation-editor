# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

"""
This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load OSC_Generator class from file OSC_Generator.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .carla_scenario_editor import OSC_Generator    # pylint: disable=import-outside-toplevel,import-error
    return OSC_Generator(iface)
