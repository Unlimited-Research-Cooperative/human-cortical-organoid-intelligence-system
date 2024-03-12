#! /bin/env python3
# Adrian Foy September 2023

"""Module to read Intan Technologies RHS2000 data file generated by
acquisition software (IntanRHX, or legacy Stimulation/Recording Controller
software).
"""

import sys
import time

import matplotlib.pyplot as plt

from intanutil.header import (read_header,
                              header_to_result)
from intanutil.data import (calculate_data_size,
                            read_all_data_blocks,
                            check_end_of_file,
                            parse_data,
                            data_to_result)
from intanutil.filter import apply_notch_filter


def read_data(filename):
    """Reads Intan Technologies RHS2000 data file generated by acquisition
    software (IntanRHX, or legacy Stimulation/Recording Controller software).

    Data are returned in a dictionary, for future extensibility.
    """
    # Start measuring how long this read takes.
    tic = time.time()

    # Open file for reading.
    with open(filename, 'rb') as fid:

        # Read header and summarize its contents to console.
        header = read_header(fid)

        # Calculate how much data is present and summarize to console.
        data_present, filesize, num_blocks, num_samples = (
            calculate_data_size(header, filename, fid))

        # If .rhs file contains data, read all present data blocks into 'data'
        # dict, and verify the amount of data read.
        print('FINISHED HEADER')
        if data_present:
            data = read_all_data_blocks(header, num_samples, num_blocks, fid)
            check_end_of_file(filesize, fid)

    # Save information in 'header' to 'result' dict.
    result = {}
    header_to_result(header, result)

    # If .rhs file contains data, parse data into readable forms and, if
    # necessary, apply the same notch filter that was active during recording.
    if data_present:
        parse_data(header, data)
        apply_notch_filter(header, data)

        # Save recorded data in 'data' to 'result' dict.
        data_to_result(header, data, result)

    # Otherwise (.rhs file is just a header for One File Per Signal Type or
    # One File Per Channel data formats, in which actual data is saved in
    # separate .dat files), just return data as an empty list.
    else:
        data = []

    # Report how long read took.
    print('Done!  Elapsed time: {0:0.1f} seconds'.format(time.time() - tic))

    # Return 'result' dict.
    return result


if __name__ == '__main__':
    a = read_data(sys.argv[1])
    print(a)

    fig, ax = plt.subplots(7, 1)
    ax[0].set_ylabel('Amp')
    ax[0].plot(a['t'], a['amplifier_data'][0, :])
    ax[0].margins(x=0, y=0)

    ax[1].set_ylabel('Stim')
    ax[1].plot(a['t'], a['stim_data'][0, :])
    ax[1].margins(x=0, y=0)

    ax[2].set_ylabel('DC')
    ax[2].plot(a['t'], a['dc_amplifier_data'][0, :])
    ax[2].margins(x=0, y=0)

    ax[3].set_ylabel('ADC')
    ax[3].plot(a['t'], a['board_adc_data'][0, :])
    ax[3].margins(x=0, y=0)

    ax[4].set_ylabel('DAC')
    ax[4].plot(a['t'], a['board_dac_data'][0, :])
    ax[4].margins(x=0, y=0)

    ax[5].set_ylabel('DigIn')
    ax[5].plot(a['t'], a['board_dig_in_data'][0, :])
    ax[5].margins(x=0, y=0)

    ax[6].set_ylabel('DigOut')
    ax[6].plot(a['t'], a['board_dig_out_data'][0, :])
    ax[6].margins(x=0, y=0)

    plt.show()
