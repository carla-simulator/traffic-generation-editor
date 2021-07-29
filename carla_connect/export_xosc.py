# -*- coding: utf-8 -*-
# Copyright (c) 2019-2020 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

'''
carla_connect - Export XOSC file
'''
from pathlib import Path
from ..osc_generator.export_xosc import GenerateXML


class Exportxosc():
    '''
    Class to generate and Export XML file to /tmp
    '''

    def __init__(self, road_network):
        '''
        Initialize the variables.
        '''
        self.road_network = road_network
        self.dirname = '/tmp'   # nosec
        self.filename = 'scenariogenerator1'
        self.suffix = ".xosc"
        self.filepath_posix = Path(self.dirname, self.filename).with_suffix(self.suffix)
        self.filepath = str(self.filepath_posix)
        # self.road_network = 'Town01'

    def save_file(self):
        '''
        Method to save XML file.
        '''
        print("EXPORTING >>>" + self.filepath)
        generate_xml = GenerateXML(self.filepath, self.road_network)
        generate_xml.main()
