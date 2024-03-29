#! /bin/env python
#
# Michael Gibson 23 April 2015
# Modified Zeke Arneodo Dec 2017
# Modified Adrian Foy Sep 2018

def get_bytes_per_data_block(header):
    """Calculates the number of bytes in each 128-sample datablock."""
    N = 128 # n of amplifier samples
    # Each data block contains N amplifier samples.
    bytes_per_block = N * 4  # timestamp data
    
    bytes_per_block += N * 2 * header['num_amplifier_channels']

    # DC amplifier voltage (absent if flag was off)
    # bytes_per_block += N * 2 * header['dc_amplifier_data_saved']
    if header['dc_amplifier_data_saved'] > 0:
        bytes_per_block += N * 2 * header['num_amplifier_channels']

    # Stimulation data, one per enabled amplifier channels
    bytes_per_block += N * 2 * header['num_amplifier_channels']

    # Board analog inputs are sampled at same rate as amplifiers
    bytes_per_block += N * 2 * header['num_board_adc_channels']

    # Board analog outputs are sampled at same rate as amplifiers
    bytes_per_block += N * 2 * header['num_board_dac_channels']

    # Board digital inputs are sampled at same rate as amplifiers
    if header['num_board_dig_in_channels'] > 0:
        bytes_per_block += N * 2

    # Board digital outputs are sampled at same rate as amplifiers
    if header['num_board_dig_out_channels'] > 0:
        bytes_per_block += N * 2

    return bytes_per_block