#! /bin/env python
#
# Michael Gibson 23 April 2015
# Modified Zeke Arneodo Dec 2017
# Modified Adrian Foy Sep 2018

import struct
import numpy as np


def read_one_data_block(data, header, indices, fid):
    """Reads one 128-sample data block from fid into data, at the location indicated by indices."""

    data['t'][indices['amplifier']:
    (indices['amplifier']+128)] = np.array(struct.unpack('<' + 'i' * 128, fid.read(128*4)))

    if header['num_amplifier_channels'] > 0:
        tmp = np.fromfile(fid, dtype='uint16', count=128 * header['num_amplifier_channels'])
        data['amplifier_data'][range(header['num_amplifier_channels']),
        indices['amplifier']:(indices['amplifier']+128)] = tmp.reshape(header['num_amplifier_channels'], 128)

        # check if dc amplifier voltage was saved
        if header['dc_amplifier_data_saved']:
            tmp = np.fromfile(fid, dtype='uint16', count=128 * header['num_amplifier_channels'])
            data['dc_amplifier_data'][range(header['num_amplifier_channels']),
            indices['amplifier']:(indices['amplifier'] + 128)] = tmp.reshape(header['num_amplifier_channels'], 128)

        # get the stimulation data
        tmp = np.fromfile(fid, dtype='uint16', count=128 * header['num_amplifier_channels'])
        data['stim_data_raw'][range(header['num_amplifier_channels']),
        indices['amplifier']:(indices['amplifier'] + 128)] = tmp.reshape(header['num_amplifier_channels'], 128)

    if header['num_board_adc_channels'] > 0:
        tmp = np.fromfile(fid, dtype='uint16', count=128 * header['num_board_adc_channels'])
        data['board_adc_data'][range(header['num_board_adc_channels']),
        indices['board_adc']:(indices['board_adc'] + 128)] = tmp.reshape(header['num_board_adc_channels'], 128)

    if header['num_board_dac_channels'] > 0:
        tmp = np.fromfile(fid, dtype='uint16', count=128 * header['num_board_dac_channels'])
        data['board_dac_data'][range(header['num_board_dac_channels']),
        indices['board_dac']:(indices['board_dac'] + 128)] = tmp.reshape(header['num_board_dac_channels'], 128)

    if header['num_board_dig_in_channels'] > 0:
        data['board_dig_in_raw'][indices['board_dig_in']:(indices['board_dig_in'] + 128)] = np.array(struct.unpack('<' + 'H' * 128, fid.read(256)))

    if header['num_board_dig_out_channels'] > 0:
        data['board_dig_out_raw'][indices['board_dig_out']:(indices['board_dig_out'] + 128)] = np.array(struct.unpack('<' + 'H' * 128, fid.read(256)))