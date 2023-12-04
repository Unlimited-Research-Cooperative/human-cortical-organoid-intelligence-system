# Adrian Foy September 2023

"""Module to set up resources used in conversion of data from Intan format
to NWB.
"""

import os
from datetime import datetime
from dateutil.tz import tzlocal

import numpy as np


def later_than_v1_2(header):
    """ Check header to return if the software generating the Intan file was
    version 1.2 or later.
    """
    return (
        header['version']['major'] == 1 and header['version']['minor'] >= 2
        or header['version']['major'] > 1)


def preallocate_data(header, file_format, amp_samples):
    """ Preallocate 'data' dictionary members with numpy arrays of the size
    for one chunk of data.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.
    amp_samples : int
        How many amplifier samples (per channel) are in this chunk of data.
    Returns
    -------
    data : dict
        Dict containing fields of numpy arrays to write data to.
    """

    # Create empty dictionary for data.
    data = {}

    if header['filetype'] == 'rhd':

        # For files prior to v1.2, read timestamps as uint. Otherwise,
        # read them as int.
        dtype = np.int_ if later_than_v1_2(header) else np.uint
        data['t_amplifier'] = np.zeros(
            amp_samples,
            dtype=dtype)

        # For traditional file format, read amplifier samples as uint.
        # Otherwise, read them as int.
        dtype = np.uint if file_format == 'traditional' else np.int_
        data['amplifier_data'] = np.zeros(
            [header['num_amplifier_channels'], amp_samples],
            dtype=dtype)

        # If lowpass data is present, preallocate an array for it
        # (size reduced by the downsample factor if downsampling occurred).
        if header['lowpass_present']:
            lowpass_amp_samples = int(
                amp_samples / header['lowpass_downsample_factor'])
            data['lowpass_data'] = np.zeros(
                [header['num_amplifier_channels'], lowpass_amp_samples],
                dtype=dtype)

        # If highpass data is present, preallocate an array for it.
        if header['highpass_present']:
            data['highpass_data'] = np.zeros(
                [header['num_amplifier_channels'], amp_samples],
                dtype=dtype)

        # Preallocate arrays for various signal types.
        aux_samples = int(amp_samples / 4)
        data['aux_input_data'] = np.zeros(
            [header['num_aux_input_channels'], aux_samples],
            dtype=np.uint)

        supply_samples = int(
            amp_samples / header['num_samples_per_data_block'])
        data['supply_voltage_data'] = np.zeros(
            [header['num_supply_voltage_channels'], supply_samples],
            dtype=np.uint)
        data['temp_sensor_data'] = np.zeros(
            [header['num_temp_sensor_channels'], supply_samples],
            dtype=np.uint)
        data['board_adc_data'] = np.zeros(
            [header['num_board_adc_channels'], amp_samples],
            dtype=np.uint)

        data['board_dig_in_data'] = np.zeros(
            [header['num_board_dig_in_channels'], amp_samples],
            dtype=np.uint)
        data['board_dig_in_raw'] = np.zeros(
            amp_samples,
            dtype=np.uint)

        data['board_dig_out_data'] = np.zeros(
            [header['num_board_dig_out_channels'], amp_samples],
            dtype=np.uint)
        data['board_dig_out_raw'] = np.zeros(
            amp_samples,
            dtype=np.uint)

    else:

        data['t'] = np.zeros(
            amp_samples,
            dtype=np.int_)

        # For traditional file format, read amplifier samples as uint.
        # Otherwise, read them as int.
        dtype = np.uint if file_format == 'traditional' else np.int_
        data['amplifier_data'] = np.zeros(
            [header['num_amplifier_channels'], amp_samples], dtype=dtype)

        # If lowpass data is present, preallocate an array for it
        # (size reduced by the downsample factor if downsampling occurred).
        if header['lowpass_present']:
            lowpass_amp_samples = int(
                amp_samples / header['lowpass_downsample_factor'])
            data['lowpass_data'] = np.zeros(
                [header['num_amplifier_channels'], lowpass_amp_samples],
                dtype=dtype)

        # If highpass data is present, preallocate an array for it.
        if header['highpass_present']:
            data['highpass_data'] = np.zeros(
                [header['num_amplifier_channels'], amp_samples],
                dtype=dtype)

        if header['dc_amplifier_data_saved']:
            data['dc_amplifier_data'] = np.zeros(
                [header['num_amplifier_channels'], amp_samples],
                dtype=dtype)

        data['stim_data_raw'] = np.zeros(
            [header['num_amplifier_channels'], amp_samples],
            dtype=np.int_)
        data['stim_data'] = np.zeros(
            [header['num_amplifier_channels'], amp_samples],
            dtype=np.int_)

        data['board_adc_data'] = np.zeros(
            [header['num_board_adc_channels'], amp_samples],
            dtype=np.uint)
        data['board_dac_data'] = np.zeros(
            [header['num_board_dac_channels'], amp_samples],
            dtype=np.uint)

        data['board_dig_in_data'] = np.zeros(
            [header['num_board_dig_in_channels'], amp_samples],
            dtype=np.uint)
        data['board_dig_in_raw'] = np.zeros(
            amp_samples,
            dtype=np.uint)

        data['board_dig_out_data'] = np.zeros(
            [header['num_board_dig_out_channels'], amp_samples],
            dtype=np.uint)
        data['board_dig_out_raw'] = np.zeros(
            amp_samples,
            dtype=np.uint)

    return data


def initialize_indices(filetype):
    """ Initialize indices used to store data when looping over blocks.

    Parameters
    ----------
    filetype : str
        Either 'rhd' for .rhd filetype or 'rhs' for .rhs filetype.

    Returns
    -------
    indices : dict
        Dictionary containing indices initialized to 0.
    """
    # Create empty dictionary for indices.
    indices = {}

    # Initialize all indices to 0.
    indices['amplifier'] = 0
    if filetype == 'rhd':
        indices['aux_input'] = 0
        indices['supply_voltage'] = 0
    else:
        indices['board_dac'] = 0
    indices['board_adc'] = 0
    indices['board_dig_in'] = 0
    indices['board_dig_out'] = 0

    return indices


def get_data_size(header, fids, bytes_per_block, print_summary=True):
    """ Determine the file format, and consult present files to determine
    how many data blocks can be read.

    Parameters
    ----------
    filesize : int
        Size (in bytes) of the intan file that contains header information
        (and data for the 'traditional' file format).
    header : dict
        Dict containing previously read header information.
    fids : dict
        Empty dict containing binary streams of files to read from that this
        function will fill.
    bytes_per_block : int
        Size (in bytes) of each data block in the intan file. Non-traditional
        file formats will ignore this value.

    Returns
    -------
    total_num_data_blocks : int
        How many data blocks can be read from the file(s) in the current
        directory.
    file_format : str
        Which file format is suitable for this read - 'traditional',
        'per_signal_type', or 'per_channel'.
    """

    # Determine how much data remains in intan file.
    data_present_in_intan_file = header['data_present']
    intan_fid = header['fid']
    bytes_remaining_in_intan_file = header['total_file_size'] - header['size']

    # Determine file format used to save data.
    file_format = determine_file_format(
        header['filetype'], data_present_in_intan_file)

    # For traditional file format, the only file to read from
    # is the intan file.
    if file_format == 'traditional':
        fids['fid'] = intan_fid

    # Report if the bytes remaining is not an integer multiple of bytes
    # per block.
    if bytes_remaining_in_intan_file % bytes_per_block != 0:
        raise FileSizeError(
            'Something is wrong with file size: should have a whole number '
            'of data blocks.')

    # Determine number of data blocks to read.
    total_num_data_blocks = get_num_data_blocks(
        file_format, bytes_remaining_in_intan_file,
        bytes_per_block, header, fids)

    # Calculate how much time has been recorded.
    record_time = header['num_samples_per_data_block'] * \
        total_num_data_blocks / header['sample_rate']

    # Output a summary of contents of header file.
    if print_summary:
        if data_present_in_intan_file:
            print('File contains {:0.3f} seconds of data.  Amplifiers were '
                  'sampled at {:0.2f} kS/s.'.format(
                      record_time, header['sample_rate'] / 1000))
        else:
            print('Directory contains {:0.3f} seconds of data.  Amplifiers '
                  'were sampled at {:0.2f} kS/s.'.format(
                      record_time, header['sample_rate'] / 1000))

    return total_num_data_blocks, file_format


def get_num_data_blocks(file_format, bytes_remaining,
                        bytes_per_block, header, fids):
    """ Determine the number of data blocks that can be read from the
    currently present files.
    If necessary (for example if a .dat file is missing), modify 'header'
    with the unavailable channels removed.

    Parameters
    ----------
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.
    bytes_remaining : int
        How many unread bytes are remaining in the intan file.
        Only used for traditional file format.
    bytes_per_block : int
        Size (in bytes) of each data block in the intan files.
        Non-traditional file formats will ignore this value.
    header : dict
        Dict containing previously read header information.
    fids : dict
        Possibly empty dict that may have the 'time.dat' key added to it,
        containing the binary stream to read timestamps from.

    Returns
    -------
    total_num_data_blocks : int
        How many data blocks can be read from the file(s) in
        the current directory.
    """
    # For traditional file format, return the number of data blocks
    # in intan file.
    if file_format == 'traditional':
        total_num_data_blocks = int(bytes_remaining / bytes_per_block)

    # For non-traditional file formats, return the number of data blocks
    # in 'time.dat' file.
    else:
        filename = 'time.dat'
        if os.path.isfile(filename):
            fid = open(filename, 'rb')
            total_num_samples = int(os.path.getsize(
                filename) - fid.tell()) / 4  # 4 bytes per timestamp.
            # 60 or 128 samples per data block.
            total_num_data_blocks = int(
                total_num_samples / header['num_samples_per_data_block'])
            fids['time.dat'] = fid

            # Check that all enabled channels or signal types in header can
            # be located, give a warning for each that can't.

            # First return value (currently unused) would contain the name
            # of the size-limiting file.
            _, total_num_samples = verify_dat_files(
                file_format, header, total_num_samples, fids)

            # Limit number of data blocks to shortest .dat file.
            limited_num_data_blocks = int(
                total_num_samples / header['num_samples_per_data_block'])
            if limited_num_data_blocks < total_num_data_blocks:
                total_num_data_blocks = limited_num_data_blocks

        else:
            # For non-traditional file formats, a 'time.dat' file is necessary.
            raise MissingTimestampsFileError(
                'No data found in header file, and no time.dat file found '
                'in current directory.')
    return total_num_data_blocks


def verify_dat_files(file_format, header, total_num_samples, fids):
    """ Verify that expected .dat files are present. If any expected files
    aren't present, give a warning and  change the header to reflect that. If
    any present file is shorter than expected, give a warning and change
    total_num_samples to reflect that.

    Parameters
    ----------
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.
    header : dict
        Dict containing previously read header information.
    total_num_samples : int
        Total number of samples (per channel) that are expected to be present
        given the length of 'time.dat'.
    fids : dict
        Dict which may be appended to, with each key-value pair representing
        a binary stream to read data from.

    Returns
    -------
    limiting_file : str
        Filename of the shortest file (if any) that limits the amount of data
        that can be loaded.
    total_num_samples : int
        Total number of samples (per channel) that are valid for reading from
        all available sources.
        This may be smaller than the input parameter if one or more files is
        shorter than expected, limiting the read.
    """
    # Check which signal types have .dat files, and verify each dat file.
    if file_format == 'per_signal_type':
        limiting_file = None

        # amplifier.dat
        result = verify_per_signal_dat_file(
            header['num_amplifier_channels'], 'amplifier.dat',
            total_num_samples, fids, limiting_file)
        header['num_amplifier_channels'] = result[0]
        limiting_file = result[1]
        total_num_samples = result[2]

        if header['filetype'] == 'rhd':
            # auxiliary.dat
            fids['aux_in_amplifier'] = False
            result = verify_per_signal_dat_file(
                header['num_aux_input_channels'], 'auxiliary.dat',
                total_num_samples, fids, limiting_file)
            if result[0] == 0:
                aux_in_amplifier = check_aux_in_amp_file(
                    header, total_num_samples)
                if aux_in_amplifier:
                    fids['aux_in_amplifier'] = True
            else:
                header['num_aux_input_channels'] = result[0]
                limiting_file = result[1]
                total_num_samples = result[2]

            # supply.dat
            result = verify_per_signal_dat_file(
                header['num_supply_voltage_channels'], 'supply.dat',
                total_num_samples, fids, limiting_file)
            header['num_supply_voltage_channels'] = result[0]
            limiting_file = result[1]
            total_num_samples = result[2]

        else:
            # dcamplifier.dat
            if header['dc_amplifier_data_saved']:
                result = verify_per_signal_dat_file(
                    header['num_amplifier_channels'], 'dcamplifier.dat',
                    total_num_samples, fids, limiting_file)
                header['num_amplifier_channels'] = result[0]
                limiting_file = result[1]
                total_num_samples = result[2]

            # stim.dat
            result = verify_per_signal_dat_file(
                header['num_amplifier_channels'], 'stim.dat',
                total_num_samples, fids, limiting_file)
            header['num_amplifier_channels'] = result[0]
            limiting_file = result[1]
            total_num_samples = result[2]

            # analogout.dat
            result = verify_per_signal_dat_file(
                header['num_board_dac_channels'], 'analogout.dat',
                total_num_samples, fids, limiting_file)
            header['num_board_dac_channels'] = result[0]
            limiting_file = result[1]
            total_num_samples = result[2]

        # analogin.dat
        result = verify_per_signal_dat_file(
            header['num_board_adc_channels'], 'analogin.dat',
            total_num_samples, fids, limiting_file)
        header['num_board_adc_channels'] = result[0]
        limiting_file = result[1]
        total_num_samples = result[2]

        # digitalin.dat
        result = verify_per_signal_dat_file(
            header['num_board_dig_in_channels'], 'digitalin.dat',
            total_num_samples, fids, limiting_file)
        header['num_board_dig_in_channels'] = result[0]
        limiting_file = result[1]
        total_num_samples = result[2]

        # digitalout.dat
        result = verify_per_signal_dat_file(
            header['num_board_dig_out_channels'], 'digitalout.dat',
            total_num_samples, fids, limiting_file)
        header['num_board_dig_out_channels'] = result[0]
        limiting_file = result[1]
        total_num_samples = result[2]

        # lowpass.dat
        result = verify_per_signal_dat_file(
            header['num_amplifier_channels'], 'lowpass.dat',
            total_num_samples, fids, limiting_file)
        num_lowpass_channels = result[0]
        lowpass_samples = result[2]
        header['lowpass_present'] = True if num_lowpass_channels > 0 else False
        if lowpass_samples < total_num_samples:
            downsample_factor = total_num_samples / lowpass_samples
            print('Lowpass data was downsampled by a factor of {}.'.format(
                downsample_factor))
            if (downsample_factor != 2 and
                    downsample_factor != 4 and
                    downsample_factor != 8 and
                    downsample_factor != 16 and
                    downsample_factor != 32 and
                    downsample_factor != 64 and
                    downsample_factor != 128):
                print(
                    'Warning: This downsample factor is not recognized as a '
                    'standard Intan option. Conversion may be unpredictable.')
            header['lowpass_downsample_factor'] = int(downsample_factor)

        # highpass.dat
        result = verify_per_signal_dat_file(
            header['num_amplifier_channels'], 'highpass.dat',
            total_num_samples, fids, limiting_file)
        header['highpass_present'] = True if result[0] > 0 else False

        if limiting_file is not None:
            print('Warning: Data limited by short file {}'.format(
                limiting_file))

    elif file_format == 'per_channel':
        limiting_file = None

        # Amplifier files.
        limiting_file, total_num_samples = verify_per_channel_files(
            prefix='amp-',
            group_name='amplifier_channels',
            header=header,
            total_num_samples=total_num_samples,
            fids=fids,
            limiting_file=limiting_file)

        if header['filetype'] == 'rhd':
            # Auxiliary files.
            limiting_file, total_num_samples = verify_per_channel_files(
                prefix='aux-',
                group_name='aux_input_channels',
                header=header,
                total_num_samples=total_num_samples,
                fids=fids,
                limiting_file=limiting_file)

            # Supply files.
            limiting_file, total_num_samples = verify_per_channel_files(
                prefix='vdd-',
                group_name='supply_voltage_channels',
                header=header,
                total_num_samples=total_num_samples,
                fids=fids,
                limiting_file=limiting_file)

        else:
            # DC amplifier files.
            limiting_file, total_num_samples = verify_per_channel_files(
                prefix='',
                group_name='dc_amplifier_channels',
                header=header,
                total_num_samples=total_num_samples,
                fids=fids,
                limiting_file=limiting_file)

            # Stim files.
            limiting_file, total_num_samples = verify_per_channel_files(
                prefix='',
                group_name='stim_channels',
                header=header,
                total_num_samples=total_num_samples,
                fids=fids,
                limiting_file=limiting_file)

            # Analog output files.
            limiting_file, total_num_samples = verify_per_channel_files(
                prefix='board-',
                group_name='board_dac_channels',
                header=header,
                total_num_samples=total_num_samples,
                fids=fids,
                limiting_file=limiting_file)

        # Analog in files.
        limiting_file, total_num_samples = verify_per_channel_files(
            prefix='board-',
            group_name='board_adc_channels',
            header=header,
            total_num_samples=total_num_samples,
            fids=fids,
            limiting_file=limiting_file)

        # Digital in files.
        limiting_file, total_num_samples = verify_per_channel_files(
            prefix='board-',
            group_name='board_dig_in_channels',
            header=header,
            total_num_samples=total_num_samples,
            fids=fids,
            limiting_file=limiting_file)

        # Digital out files.
        limiting_file, total_num_samples = verify_per_channel_files(
            prefix='board-',
            group_name='board_dig_out_channels',
            header=header,
            total_num_samples=total_num_samples,
            fids=fids,
            limiting_file=limiting_file)

        # Lowpass files.
        # Because lowpass files can be downsampled, and can be expected to be
        # shorter than other files, don't write to limiting_file.
        _, lowpass_samples = verify_per_channel_files(
            prefix='low-',
            group_name='amplifier_channels',
            header=header,
            total_num_samples=total_num_samples,
            fids=fids,
            limiting_file=limiting_file)

        if lowpass_samples < total_num_samples:
            downsample_factor = total_num_samples / lowpass_samples
            print('Lowpass data was downsampled by a factor of {}.'.format(
                downsample_factor))
            if (downsample_factor != 2 and
                    downsample_factor != 4 and
                    downsample_factor != 8 and
                    downsample_factor != 16 and
                    downsample_factor != 32 and
                    downsample_factor != 64 and
                    downsample_factor != 128):
                print(
                    'Warning: This downsample factor is not recognized as a '
                    'standard Intan option. Conversion may be unpredictable.')
            header['lowpass_downsample_factor'] = int(downsample_factor)

        # Highpass files.
        limiting_file, total_num_samples = verify_per_channel_files(
            prefix='high-',
            group_name='amplifier_channels',
            header=header,
            total_num_samples=total_num_samples,
            fids=fids,
            limiting_file=limiting_file)

        if limiting_file is not None:
            print('Warning: Data limited by short file {}'.format(
                limiting_file))

    return limiting_file, total_num_samples


def verify_per_signal_dat_file(num_channels, filename, total_num_samples,
                               fids, limiting_file):
    """ Verify that the specified .dat file is present. If not, give a warning
    and change num_channels to 0.
    If it's shorter than expected, give a warning and change total_num_samples.

    Parameters
    ----------
    num_channels : int
        How many channels should have data present in this file.
    filename : str
        Name of this file that should contain data.
    total_num_samples : int
        Total number of samples (per channel) that are expected to be present
        given the length of previous .dat files.
    fids : dict
        Dict which may be appended to, with each key-value pair representing a
        binary stream to read data from.
    limiting_file : str
        Filename of the (so far) shortest file (if any) that limits the amount
        of data that can be loaded.

    Returns
    -------
    num_channels : int
        How many channels actually have data present in this file.
    limiting_file : str
        Filename of the shortest file (if any) that limits the amount of data
        that can be loaded.
    total_num_samples : int
        Total number of samples (per channel) that are valid for reading from
        all available sources.
        This may be smaller than the input parameter if this file is shorter
        than expected, limiting the read.
    """
    # Only look for files if the header reports that at least one channel
    # of this signal type is present.
    if num_channels > 0:
        # Check if this file is present, reporting a warning and modifying
        # the header object if not.
        try:
            fid = open(filename, 'rb')
            filesize = os.path.getsize(filename)

            # Digital i/o files don't scale with num_channels, each sample of
            # all channels is 2 bytes.
            if filename == 'digitalin.dat' or filename == 'digitalout.dat':
                num_samples = filesize / 2
            # All other files scale with num_channels, each sample of one
            # channel is 2 bytes.
            else:
                num_samples = filesize / (num_channels * 2)

            # If this file now limits the number of readable samples,
            # return that result.
            if num_samples < total_num_samples:
                total_num_samples = num_samples
                limiting_file = filename
            fids[filename] = fid

        except FileNotFoundError:
            # Give a warning for a missing file (as long as it's
            # non-essential ... low or highpass data files shouldn't give
            # a warning).
            if filename != 'lowpass.dat' and filename != 'highpass.dat':
                print('Warning: Could not open {}'.format(filename))
            num_channels = 0

    return num_channels, limiting_file, total_num_samples


def check_aux_in_amp_file(header, total_num_samples):
    """ Check if the 'amplifier.dat' file has a size indicating that auxiliary
        inputs have been saved in it.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    total_num_samples : int
        Total number of samples (per channel) that are expected to be present
        given the length of previous .dat files.

    Returns
    -------
    bool
        Whether auxiliary input data is saved in 'amplifier.dat'.
    """
    extra_aux_samples = total_num_samples * \
        header['num_aux_input_channels']  # all auxiliary input samples.
    original_amp_samples = total_num_samples * \
        header['num_amplifier_channels']  # all amplifier input samples.
    total_samples_in_file = os.path.getsize(
        'amplifier.dat') / 2  # total samples.
    # Compare total samples in file with auxiliary input and
    # amplifier input samples.
    if total_samples_in_file == (original_amp_samples + extra_aux_samples):
        return True
    return False


def verify_per_channel_files(prefix, group_name, header, total_num_samples,
                             fids, limiting_file):
    """ Verify that  channels in header have corresponding .dat files. If not,
    give a warning and change num_channels to accurately reflect
    the present files.
    If a file(s) is shorter than expected, give a warning and
    change total_num_samples.

    Parameters
    ----------
    prefix : str
        Prefix (like 'amp-', 'aux-', 'vdd-', or 'board-') that comes before
        the native channel name in the channel's filename.
    group_name : str
        Name of the group of this signal type as recognized by header.
    header : dict
        Dict containing previously read header information.
    total_num_samples : int
        Total number of samples (per channel) that are expected to be present
        given the length of previous .dat files.
    fids : dict
        Dict which may be appended to, wich each key-value pair representing
        a binary stream to read data from.
    limiting_file : str
        Filename of the (so far) shortest file (if any) that limits the amount
        of data that can be loaded.

    Returns
    -------
    limiting_file : str
        Filename of the shortest file (if any) that limits the amount of data
        that can be loaded.
    total_num_samples : int
        Total number of sample (per channel) that are valid for reading from
        all available sources.
        This may be smaller than the input parameter if this file is shorter
        than expected, limiting the read.
    """
    missing_channels = 0

    for channel in header[group_name]:
        filename = prefix + channel['native_channel_name'] + '.dat'

        # Check if this file is present, reporting a warning and modifying
        # the header object if not.
        try:
            fid = open(filename, 'rb')
            filesize = os.path.getsize(filename)

            num_samples = filesize / 2

            # If this file now limits the number of readable samples,
            # return that result.
            if num_samples < total_num_samples:
                total_num_samples = num_samples
                limiting_file = filename
            fids[filename] = fid

            if prefix == 'low-':
                header['lowpass_present'] = True
            elif prefix == 'high-':
                header['highpass_present'] = True

        except FileNotFoundError:
            # Give a warning for a missing file
            # (as long as it's non-essential).
            if prefix != 'low-' and prefix != 'high-':
                print('Warning: Could not open {}'.format(filename))
                missing_channels = missing_channels + 1

    if missing_channels != 0 and prefix != 'low-' and prefix != 'high-':
        header['num_' + group_name] = header['num_' +
                                             group_name] - missing_channels

    return limiting_file, total_num_samples


def determine_file_format(filetype, data_present_in_intan_file):
    """ Determine which file format is suitable for this read.

    Parameters
    ----------
    filetype : str
        Whether file is 'rhd' or 'rhs'.
    data_present_in_intan_file : bool
        Whether additional data beyond header information is included
        in the intan file.

    Returns
    -------
    str
        'traditional' for Traditional Format,
        'per_signal_type' for One File Per Signal Type Format, or
        'per_channel' for One Filer Per Channel Format.
    """
    if data_present_in_intan_file:
        return 'traditional'

    if filetype == 'rhd':
        perSignalTypeFileNames = ['amplifier.dat',
                                  'auxiliary.dat',
                                  'supply.dat',
                                  'analogin.dat',
                                  'digitalin.dat',
                                  'digitalout.dat'
                                  ]
    else:
        perSignalTypeFileNames = ['amplifier.dat',
                                  'dcamplifier.dat',
                                  'stim.dat',
                                  'analogin.dat',
                                  'analogout.dat',
                                  'digitalin.dat',
                                  'digitalout.dat',
                                  ]

    # Don't check for 'time' since time.dat is also found in
    # 'one file per channel' format.
    for name in perSignalTypeFileNames:
        if os.path.isfile(name):
            # If at least one of the standard per signal type file names
            # is found, it must be one file per signal type.
            return 'per_signal_type'

    # If none of the standard per signal type file names can be found,
    # assume it's one file per channel.
    return 'per_channel'


def parse_filename(in_filename):
    """ Parse input filename to determine output filename
    and session start time.
    If input filename contains a date timestamp,
    that will be used for session start time.

    Parameters
    ----------
    in_filename : str
        Full name of intan file that is being read.

    Returns
    -------
    out_filename : str
        Full name of .nwb file that is being written.
    session_start_time : datetime.datetime
        Time that recording session began at. If this information can't be
        determined from the input filename, default to
        January 1st, 1970 midnight.
    """
    base_filename = in_filename[:-4]

    # Return out_filename.
    out_filename = base_filename + '.nwb'

    # If the targeted filename is the default 'info' file for non-traditional
    # file formats, try to get a more descriptive name from the directory.
    # If the directory name does not contain a timestamp, then just settle
    # for 'info.nwb' output filename.
    if base_filename == 'info':
        # Look at directory name for timestamp format, use that.
        (dir_has_timestamp,
         name_with_timestamp) = get_timestamp_from_directory()
        if dir_has_timestamp:
            out_filename = name_with_timestamp + '.nwb'

    # Determine if input filename included the default timestamp
    # from Intan software.
    # If so, parse that into session_start_time.
    # If not, then set session_start_time to January 1st, 1970 midnight.
    epoch_datetime = datetime(1970, 1, 1, tzinfo=tzlocal())
    valid_datetime = False

    # Check that underscores are where we'd expect in the format.
    # 'myfilename_YYMMDD_HHMMSS' of the base filename.
    if len(base_filename) >= 14:
        if base_filename[-14] == '_' and base_filename[-7] == '_':

            try:
                year = int(base_filename[-13:-11]) + 2000
                month = int(base_filename[-11:-9])
                day = int(base_filename[-9:-7])
                hour = int(base_filename[-6:-4])
                minute = int(base_filename[-4:-2])
                second = int(base_filename[-2:])
                valid_datetime = True
                session_start_time = datetime(
                    year, month, day, hour, minute, second, tzinfo=tzlocal())

            except ValueError:
                valid_datetime = False

    # Return session_start_time.
    if not valid_datetime:
        session_start_time = epoch_datetime

    return out_filename, session_start_time


def get_timestamp_from_directory():
    """ Determine if the parent directory has a name ending with a timestamp.
    If so, return the name of the directory.

    Parameters
    ----------
    None

    Returns
    -------
    dir_has_timestamp : bool
        Whether the parent directory has a name ending with a timestamp.
    name_with_timestamp : str
        The name of the directory that ends with a timestamp.
    """
    dir_has_timestamp = False
    name_with_timestamp = ""

    cwd = os.getcwd()
    directory_name = os.path.basename(cwd)

    if len(directory_name) > 14:
        if directory_name[-14] == '_' and directory_name[-7] == '_':

            try:
                int(directory_name[-13:-11])
                int(directory_name[-11:-9])
                int(directory_name[-9:-7])
                int(directory_name[-6:-4])
                int(directory_name[-4:-2])
                int(directory_name[-2:])
                dir_has_timestamp = True
                name_with_timestamp = directory_name

            except ValueError:
                dir_has_timestamp = False
                name_with_timestamp = ""

    return (dir_has_timestamp, name_with_timestamp)


def initialize_chunk_list(total_num_data_blocks, max_blocks_per_chunk):
    """ Initialize chunks_to_read as a list of ints containing how many
    data blocks are in each chunk.

    Parameters
    ----------
    total_num_data_blocks : int
        How many total data blocks, no matter the chunk size, should be read.
    max_blocks_per_chunk : int
        Maximum number of blocks that should be included in each chunk.

    Returns
    -------
    chunks_to_read : list
        List of ints containing how many data blocks are in each chunk.
    """
    # Create empty list that will contain how many data blocks
    # are in each chunk.
    chunks_to_read = []

    # Keep track of how many blocks remain.
    blocks_remaining = total_num_data_blocks

    # Cycle through all chunks.
    while blocks_remaining > 0:
        # If this chunk can be as large as max_blocks_per_chunk
        # make it that size.
        if blocks_remaining >= max_blocks_per_chunk:
            blocks_this_chunk = max_blocks_per_chunk
        # If this chunk cannot be as large as max_blocks_per_chunk
        # (at end of file), make it the size of the remaining data.
        else:
            blocks_this_chunk = blocks_remaining

        # Populate chunks_to_read list.
        chunks_to_read.append(blocks_this_chunk)

        # Subtract from blocks_remaining to prepare for next iteration.
        blocks_remaining = blocks_remaining - blocks_this_chunk

    return chunks_to_read


class MissingTimestampsFileError(Exception):
    """Exception returned when a required 'time.dat' file is not found.
    """


class FileSizeError(Exception):
    """Exception returned when file reading fails due to the file size
    being invalid or the calculated file size differing from the actual
    file size.
    """
