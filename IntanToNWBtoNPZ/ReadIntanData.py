# Adrian Foy September 2023

"""Module to read Intan data in preparation for conversion to NWB.
"""

import struct

import numpy as np

from SetupResources import later_than_v1_2


def read_into_1D(destination, offset, format_string, fid, bytes_per_sample,
                 num_samples, repeat_factor=1):
    """ Read from file into 1D destination array.

    Parameters
    ----------
    destination : numpy.ndarray
        1D array to write to.
    offset : int
        Index of the destination array to start writing to.
    format_string : str
        String specifying the format of the read data (for example, '<iiii').
    fid : _io.BufferedReader
        Binary stream of a file to read from.
    bytes_per_sample : int
        Number of bytes per sample (for example, 2 for uint16, 4 for int32).
    num_samples : int
        Number of samples to read
    repeat_factor : int
        How many times a unique sample has been repeated so that slower-sampled
        signals have the same length as faster-sampled signals.

    Returns
    -------
    None
    """
    # While slower-sampled signals may be read with repeating samples, we want
    # to store them at their native, slower rate.
    # Calculate num_unique_samples to determine how many actual_samples were
    # gathered, ignoring repeats.
    num_unique_samples = int(num_samples / repeat_factor)

    # Read data into temp array.
    end = offset + num_unique_samples
    bytes_to_read = bytes_per_sample * num_samples
    tmp = np.array(struct.unpack(format_string, fid.read(bytes_to_read)))

    # Discard repeated samples, only saving unique samples to destination.
    destination[offset:end] = tmp[::repeat_factor]


def read_into_2D(destination, offset, fid, dtype, num_channels, num_samples,
                 order, repeat_factor=1):
    """ Read from file into 2D destination array.

    Parameters
    ----------
    destination : numpy.ndarray
        2D array to write to.
    offset : int
        Sample index of the destination array to start writing to.
    fid : _io.BufferedReader
        Binary stream of a file to read from.
    dtype : str
        Data type to read data as.
    num_channels : int
        Number of channels (rows) to write to.
    num_samples : int
        Number of samples per channel (columns) to write to.
    order : str
        'F' for Fortran-like index ordering (last index changes slowest), 'C'
        for C-like index ordering (last index changes fastest).
    repeat_factor : int
        How many times a unique sample has been repeated so that slower-sampled
        signals have the same length as faster-sampled signals.

    Returns
    -------
    None
    """
    # While slower-sampled signals may be read with repeating samples, we want
    # to store them at their native, slower rate.
    # Calculate num_unique_samples to determine how many actual samples were
    # gathered, ignoring repeats.
    num_unique_samples = int(num_samples / repeat_factor)

    # Read data into temp array.
    end = offset + num_unique_samples
    items_to_read = num_channels * num_samples
    tmp = np.fromfile(fid, dtype=dtype, count=items_to_read)

    # Discard repeated samples, only saving unique samples to destination.
    tmp = tmp[::repeat_factor]
    destination[range(num_channels), offset:end] = tmp.reshape(
        num_channels, num_unique_samples, order=order)


def read_timestamp_block(header, data, indices, fids, file_format):
    """ Populate data['t_amplifier'] with a block of timestamp data. For rhs
    files, populate it as data['t'] instead.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    data : dict
        Dict containing fields to write data to - in this case,
        data['t_amplifier'] or data['t'].
    indices : dict
        Dict containing indices keeping track of written data position.
    fids : dict
        Dict containing binary streams of files to read from.
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.

    Returns
    -------
    None
    """
    # Determine which binary stream to read timestamp data from.
    fid = fids['fid'] if file_format == 'traditional' else fids['time.dat']

    if header['filetype'] == 'rhd':
        # Determine suitable format string (pre-1.2 files had unsigned int
        # timestamps, after that they are signed).
        signing_character = 'i' if later_than_v1_2(header) else 'I'
        format_string = (
            '<' + signing_character * header['num_samples_per_data_block'])
        t_key = 't_amplifier'

    else:
        format_string = '<' + 'i' * header['num_samples_per_data_block']
        t_key = 't'

    # Read this block's timestamps into data['t_amplifier'] or data['t'].
    read_into_1D(destination=data[t_key],
                 offset=indices['amplifier'],
                 format_string=format_string,
                 fid=fid,
                 bytes_per_sample=4,
                 num_samples=header['num_samples_per_data_block'])


def read_amplifier_block(header, data, indices, fids, file_format):
    """ Populate data['amplifier_data'] with a block of amplifier data.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    data : dict
        Dict containing fields to write data to - in this case,
        data['amplifier_data'].
    indices : dict
        Dict containing indices keeping track of written data position.
    fids : dict
        Dict containing binary streams of files to read from.
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.

    Returns
    -------
    None
    """
    # Only attempt reading if the header indicates there are amplifier
    # channels to read.
    if header['num_amplifier_channels'] > 0:

        # For traditional file format, read this block's amplifier data from
        # .rhd file into data['amplifier_data'].
        if file_format == 'traditional':
            read_into_2D(
                destination=data['amplifier_data'],
                offset=indices['amplifier'],
                fid=fids['fid'],
                dtype='uint16',
                num_channels=header['num_amplifier_channels'],
                num_samples=header['num_samples_per_data_block'],
                order='C',
                repeat_factor=1)

        # For one file per signal type format, read this block's amplifier
        # data from amplifier.dat into data['amplifier_data'].
        elif file_format == 'per_signal_type':

            if header['filetype'] == 'rhd':
                # In the case that auxiliary inputs were saved in the same
                # file as amplifier data,
                # read this block's amplifier data and then read this
                # block's auxiliary data.
                if fids['aux_in_amplifier']:

                    # Read amplifier and auxiliary data together into
                    # temp_list.
                    combined_channels = (header['num_amplifier_channels']
                                         + header['num_aux_input_channels'])
                    temp_list = np.zeros(
                        [combined_channels,
                         header['num_samples_per_data_block']],
                        dtype='int16')
                    read_into_2D(
                        destination=temp_list,
                        offset=0,
                        fid=fids['amplifier.dat'],
                        dtype='int16',
                        num_channels=combined_channels,
                        num_samples=header['num_samples_per_data_block'],
                        order='F',
                        repeat_factor=1)

                    # Read amplifier data from the beginning of temp_list.
                    data['amplifier_data'][
                        range(header['num_amplifier_channels']),
                        indices['amplifier']:indices['amplifier']
                        + header['num_samples_per_data_block']] = temp_list[
                            0:header['num_amplifier_channels']]

                    # Read auxiliary data from temp_list, starting after the
                    # end of amplifier data.
                    aux_list = temp_list[
                        header['num_amplifier_channels']:
                        header['num_amplifier_channels'] +
                        header['num_aux_input_channels']]

                    # Convert auxiliary data from signed to unsigned.
                    # This data is sampled 4x slower than amplifier data, so
                    # only read every 4th sample into data['aux_input_data'].
                    unique_list = np.bitwise_xor(
                        0x8000, aux_list[:, ::4]).astype(np.uint16)
                    unique_samples = int(
                        header['num_samples_per_data_block'] / 4)
                    data['aux_input_data'][
                        range(header['num_aux_input_channels']),
                        indices['aux_input']:indices['aux_input']
                        + unique_samples] = unique_list

                # In the case that amplifier.dat only contains amplifier data,
                # just read directly to data['amplifier_data'].
                else:
                    read_into_2D(
                        destination=data['amplifier_data'],
                        offset=indices['amplifier'],
                        fid=fids['amplifier.dat'],
                        dtype='int16',
                        num_channels=header['num_amplifier_channels'],
                        num_samples=header['num_samples_per_data_block'],
                        order='F',
                        repeat_factor=1)

            else:
                read_into_2D(
                    destination=data['amplifier_data'],
                    offset=indices['amplifier'],
                    fid=fids['amplifier.dat'],
                    dtype='int16',
                    num_channels=header['num_amplifier_channels'],
                    num_samples=header['num_samples_per_data_block'],
                    order='F',
                    repeat_factor=1)

        # For one file per channel format, read this block's amplifier data
        # from various .dat files into data['amplifier_data'].
        elif file_format == 'per_channel':

            for idx, channel in enumerate(header['amplifier_channels']):
                read_into_1D(
                    destination=data['amplifier_data'][idx],
                    offset=indices['amplifier'],
                    format_string=(
                        '<' + 'h' * header['num_samples_per_data_block']),
                    fid=fids['amp-' + channel['native_channel_name'] + '.dat'],
                    bytes_per_sample=2,
                    num_samples=header['num_samples_per_data_block'])

        else:
            raise UnrecognizedFileFormatError(
                'Unrecognized file format: {}'.format(file_format))


def read_dc_amplifier_block(header, data, indices, fids, file_format):
    """ Populate data['dc_amplifier_data'] with a block of amplifier data.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    data : dict
        Dict containing fields to write data to - in this case,
        data['amplifier_data'].
    indices : dict
        Dict containing indices keeping track of written data position.
    fids : dict
        Dict containing binary streams of files to read from.
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.

    Returns
    -------
    None
    """
    if not header['dc_amplifier_data_saved']:
        return

    # For traditional file format, read this block's dc amplifier data
    # from intan file into data['dc_amplifier_data'].
    if file_format == 'traditional':
        read_into_2D(
            destination=data['dc_amplifier_data'],
            offset=indices['amplifier'],
            fid=fids['fid'],
            dtype='uint16',
            num_channels=header['num_amplifier_channels'],
            num_samples=header['num_samples_per_data_block'],
            order='C',
            repeat_factor=1)

    # For one file per signal type format, read this block's dc amplifier data
    # from dcamplifier.dat into data['dc_amplifier_data'].
    elif file_format == 'per_signal_type':
        read_into_2D(
            destination=data['dc_amplifier_data'],
            offset=indices['amplifier'],
            fid=fids['dcamplifier.dat'],
            dtype='int16',
            num_channels=header['num_amplifier_channels'],
            num_samples=header['num_samples_per_data_block'],
            order='F',
            repeat_factor=1)

    elif file_format == 'per_channel':
        for idx, channel in enumerate(header['amplifier_channels']):
            read_into_1D(
                destination=data['dc_amplifier_data'][idx],
                offset=indices['amplifier'],
                format_string='<' + 'h' * header['num_samples_per_data_block'],
                fid=fids['dc-' + channel['native_channel_name'] + '.dat'],
                bytes_per_sample=2,
                num_samples=header['num_samples_per_data_block'])

    else:
        raise UnrecognizedFileFormatError(
            'Unrecognized file format: {}'.format(file_format))


def read_stim_block(header, data, indices, fids, file_format):
    """ Populate data['stim_data_raw'] with a block of stim data.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    data : dict
        Dict containing fields to write data to - in this case,
        data['stim_data_raw'].
    indices : dict
        Dict containing indices keeping track of written data position.
    fids : dict
        Dict containing binary streams of files to read from.
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.

    Returns
    -------
    None
    """

    # For traditional file format, read this block's stim data from intan
    # file into data['stim_data_raw'].
    if file_format == 'traditional':
        read_into_2D(
            destination=data['stim_data_raw'],
            offset=indices['amplifier'],
            fid=fids['fid'],
            dtype='uint16',
            num_channels=header['num_amplifier_channels'],
            num_samples=header['num_samples_per_data_block'],
            order='C',
            repeat_factor=1)

    # For one file per signal type format, read this block's stim data
    # from stim.dat into data['stim_data_raw'].
    elif file_format == 'per_signal_type':
        read_into_2D(
            destination=data['stim_data_raw'],
            offset=indices['amplifier'],
            fid=fids['stim.dat'],
            dtype='uint16',
            num_channels=header['num_amplifier_channels'],
            num_samples=header['num_samples_per_data_block'],
            order='F',
            repeat_factor=1)

    elif file_format == 'per_channel':
        for idx, channel in enumerate(header['stim_channels']):
            # It's possible for un-stimmed channels to not have a .dat file,
            # so if this is the case, just move on to the next channel.
            if not channel['native_channel_name'] + '.dat' in fids:
                continue
            read_into_1D(
                destination=data['stim_data_raw'][idx],
                offset=indices['amplifier'],
                format_string='<' + 'H' * header['num_samples_per_data_block'],
                fid=fids[channel['native_channel_name'] + '.dat'],
                bytes_per_sample=2,
                num_samples=header['num_samples_per_data_block'])

    else:
        raise UnrecognizedFileFormatError(
            'Unrecognized file format: {}'.format(file_format))


def read_lowpass_block(header, data, indices, fids, file_format):
    """ Populate data['lowpass_data'] with a block of lowpass amplifier data.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    data : dict
        Dict containing fields to write data to - in this case,
        data['supply_voltage_data'].
    indices : dict
        Dict containing indices keeping track of written data position.
    fids : dict
        Dict containing binary streams of files to read from.
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.

    Returns
    -------
    None
    """

    # Only attempt reading if the header indicates there are amplifier
    # channels to read, and lowpass data present.
    if header['num_amplifier_channels'] > 0 and header['lowpass_present']:

        # For one file per signal type format, read this block's lowpass
        # data from lowpass.dat into data['lowpass_data'].
        if file_format == 'per_signal_type':
            num_lowpass_samples = int(header['num_samples_per_data_block']
                                      / header['lowpass_downsample_factor'])
            lowpass_offset = int(indices['amplifier']
                                 / header['lowpass_downsample_factor'])
            read_into_2D(
                destination=data['lowpass_data'],
                offset=lowpass_offset,
                fid=fids['lowpass.dat'],
                dtype='int16',
                num_channels=header['num_amplifier_channels'],
                num_samples=num_lowpass_samples,
                order='F',
                repeat_factor=1)

        # For one file per channel format, read this block's lowpass data
        # from various .dat files into data['lowpass_data'].
        elif file_format == 'per_channel':
            num_lowpass_samples = int(header['num_samples_per_data_block']
                                      / header['lowpass_downsample_factor'])
            lowpass_offset = int(indices['amplifier']
                                 / header['lowpass_downsample_factor'])

            for idx, channel in enumerate(header['amplifier_channels']):
                read_into_1D(
                    destination=data['lowpass_data'][idx],
                    offset=lowpass_offset,
                    format_string='<' + 'h' * num_lowpass_samples,
                    fid=fids['low-' + channel['native_channel_name'] + '.dat'],
                    bytes_per_sample=2,
                    num_samples=num_lowpass_samples)

        else:
            raise UnrecognizedFileFormatError(
                'Unrecognized file format: {}'.format(file_format))


def read_highpass_block(header, data, indices, fids, file_format):
    """ Populate data['highpass_data'] with a block of highpass amplifier data.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    data : dict
        Dict containing fields to write data to - in this case,
        data['supply_voltage_data'].
    indices : dict
        Dict containing indices keeping track of written data position.
    fids : dict
        Dict containing binary streams of files to read from.
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.

    Returns
    -------
    None
    """
    # Only attempt reading if the header indicates there are amplifier
    # channels to read, and highpass data present.
    if header['num_amplifier_channels'] > 0 and header['highpass_present']:
        # For one file per signal type format, read this block's highpass data
        # from highpass.dat into data['highpass_data'].
        if file_format == 'per_signal_type':
            read_into_2D(
                destination=data['highpass_data'],
                offset=indices['amplifier'],
                fid=fids['highpass.dat'],
                dtype='int16',
                num_channels=header['num_amplifier_channels'],
                num_samples=header['num_samples_per_data_block'],
                order='F',
                repeat_factor=1)

        # For one file per channel format, read this block's highpass data
        # from various .dat files into data['highpass_data'].
        elif file_format == 'per_channel':
            for idx, channel in enumerate(header['amplifier_channels']):
                read_into_1D(
                    destination=data['highpass_data'][idx],
                    offset=indices['amplifier'],
                    format_string=(
                        '<' + 'h' * header['num_samples_per_data_block']),
                    fid=(fids['high-'
                              + channel['native_channel_name']
                              + '.dat']),
                    bytes_per_sample=2,
                    num_samples=header['num_samples_per_data_block'])

        else:
            raise UnrecognizedFileFormatError(
                'Unrecognized file format: {}'.format(file_format))


def read_aux_input_block(header, data, indices, fids, file_format):
    """ Populate data['aux_input_data'] with a block of auxiliary input data.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    data : dict
        Dict containing fields to write data to - in this case,
        data['aux_input_data'].
    indices : dict
        Dict containing indices keeping track of written data position.
    fids : dict
        Dict containing binary streams of files to read from.
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.

    Returns
    -------
    None
    """
    # Only attempt reading if the header indicates there are auxiliary input
    # channels to read.
    if header['num_aux_input_channels'] > 0:
        # For traditional file format, read this block's auxiliary data from
        # .rhd file into data['aux_input_data'].
        if file_format == 'traditional':
            read_into_2D(
                destination=data['aux_input_data'],
                offset=indices['aux_input'],
                fid=fids['fid'],
                dtype='uint16',
                num_channels=header['num_aux_input_channels'],
                num_samples=int(header['num_samples_per_data_block']
                                / 4),
                order='C',
                repeat_factor=1)

        # For one file per signal type, read this block's auxiliary data
        # from auxiliary.dat into data['aux_input_data'].
        elif file_format == 'per_signal_type':
            # Handle aux in amplifier in the read_amplifier_block function.
            if not fids['aux_in_amplifier']:
                read_into_2D(
                    destination=data['aux_input_data'],
                    offset=indices['aux_input'],
                    fid=fids['auxiliary.dat'],
                    dtype='uint16',
                    num_channels=header['num_aux_input_channels'],
                    num_samples=header['num_samples_per_data_block'],
                    order='F',
                    repeat_factor=4)

        # For one file per channel format, read this block's auxiliary data
        # from various .dat files into data['aux_input_data'].
        elif file_format == 'per_channel':
            for idx, channel in enumerate(header['aux_input_channels']):
                read_into_1D(
                    destination=data['aux_input_data'][idx],
                    offset=indices['aux_input'],
                    format_string=(
                        '<' + 'H' * header['num_samples_per_data_block']),
                    fid=fids['aux-' + channel['native_channel_name'] + '.dat'],
                    bytes_per_sample=2,
                    num_samples=header['num_samples_per_data_block'],
                    repeat_factor=4)

        else:
            raise UnrecognizedFileFormatError(
                'Unrecognized file format: {}'.format(file_format))


def read_supply_voltage_block(header, data, indices, fids, file_format):
    """ Populate data['supply_voltage_data'] with a block of supply voltage
    data.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    data : dict
        Dict containing fields to write data to - in this case,
        data['supply_voltage_data'].
    indices : dict
        Dict containing indices keeping track of written data position.
    fids : dict
        Dict containing binary streams of files to read from.
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.

    Returns
    -------
    None
    """
    # Only attempt reading if the header indicates there are supply voltage
    # channels to read.
    if header['num_supply_voltage_channels'] > 0:
        # For traditional file format, read this block's supply voltage data
        # from .rhd file into data['supply_voltage_data'].
        if file_format == 'traditional':
            read_into_2D(
                destination=data['supply_voltage_data'],
                offset=indices['supply_voltage'],
                fid=fids['fid'],
                dtype='uint16',
                num_channels=header['num_supply_voltage_channels'],
                num_samples=1,
                order='C',
                repeat_factor=1)

        # For one file per signal type, read this block's supply voltage data
        # from supply.dat into data['supply_voltage_data'].
        elif file_format == 'per_signal_type':
            read_into_2D(
                destination=data['supply_voltage_data'],
                offset=indices['supply_voltage'],
                fid=fids['supply.dat'],
                dtype='uint16',
                num_channels=header['num_supply_voltage_channels'],
                num_samples=header['num_samples_per_data_block'],
                order='F',
                repeat_factor=header['num_samples_per_data_block'])

        # For one file per channel format, read this block's supply voltage
        # data from various .dat files into data['supply_voltage_data'].
        elif file_format == 'per_channel':
            for idx, channel in enumerate(header['supply_voltage_channels']):
                read_into_1D(
                    destination=data['supply_voltage_data'][idx],
                    offset=indices['supply_voltage'],
                    format_string=(
                        '<' + 'H' * header['num_samples_per_data_block']),
                    fid=fids['vdd-' + channel['native_channel_name'] + '.dat'],
                    bytes_per_sample=2,
                    num_samples=header['num_samples_per_data_block'],
                    repeat_factor=header['num_samples_per_data_block'])

        else:
            raise UnrecognizedFileFormatError(
                'Unrecognized file format: {}'.format(file_format))


def read_temp_sensor_block(header, data, indices, fids, file_format):
    """ Populate data['temp_sensor_data'] with a block of temperature sensor
    data.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    data : dict
        Dict containing fields to write data to - in this case,
        data['temp_sensor_data'].
    indices : dict
        Dict containing indices keeping track of written data position.
    fids : dict
        Dict containing binary streams of files to read from.
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.

    Returns
    -------
    None
    """
    # Only attempt reading if the header indicates there are temp sensor
    # channels to read.
    if header['num_temp_sensor_channels'] > 0:
        # For traditional file format, read this block's temp sensor data from
        # .rhd file into data['temp_sensor_data'].
        if file_format == 'traditional':
            read_into_2D(
                destination=data['temp_sensor_data'],
                offset=indices['supply_voltage'],
                fid=fids['fid'],
                dtype='uint16',
                num_channels=header['num_temp_sensor_channels'],
                num_samples=1,
                order='C',
                repeat_factor=1)

        # There's no way for temp sensor data to be saved outside of
        # traditional file format, so just return.
        else:
            return


def read_board_adc_block(header, data, indices, fids, file_format):
    """ Populate data['board_adc_data'] with a block of analog input data.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    data : dict
        Dict containing fields to write data to - in this case,
        data['board_adc_data'].
    indices : dict
        Dict containing indices keeping track of written data position.
    fids : dict
        Dict containing binary streams of files to read from.
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.

    Returns
    -------
    None
    """
    # Only attempt reading if the header indicates there are analog input
    # channels to read.
    if header['num_board_adc_channels'] > 0:

        # For traditional file format, read this block's analog input data
        # from .rhd file into data['board_adc_data'].
        if file_format == 'traditional':
            read_into_2D(
                destination=data['board_adc_data'],
                offset=indices['board_adc'],
                fid=fids['fid'],
                dtype='uint16',
                num_channels=header['num_board_adc_channels'],
                num_samples=header['num_samples_per_data_block'],
                order='C',
                repeat_factor=1)

        # For one file per signal type, read this block's analog input data
        # from analogin.dat into data['board_adc_data'].
        elif file_format == 'per_signal_type':
            read_into_2D(
                destination=data['board_adc_data'],
                offset=indices['board_adc'],
                fid=fids['analogin.dat'],
                dtype='uint16',
                num_channels=header['num_board_adc_channels'],
                num_samples=header['num_samples_per_data_block'],
                order='F',
                repeat_factor=1)

        # For one file per channel format, read this block's analog input
        # data from various .dat files into data['board_adc_data'].
        elif file_format == 'per_channel':
            for idx, channel in enumerate(header['board_adc_channels']):
                read_into_1D(
                    destination=data['board_adc_data'][idx],
                    offset=indices['board_adc'],
                    format_string=(
                        '<' + 'H' * header['num_samples_per_data_block']),
                    fid=fids['board-'
                             + channel['native_channel_name']
                             + '.dat'],
                    bytes_per_sample=2,
                    num_samples=header['num_samples_per_data_block'])

        else:
            raise UnrecognizedFileFormatError(
                'Unrecognized file format: {}'.format(file_format))


def read_board_dac_block(header, data, indices, fids, file_format):
    """ Populate data['board_dac_data'] with a block of analog output data.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    data : dict
        Dict containing fields to write data to - in this case,
        data['board_dac_data'].
    indices : dict
        Dict containing indices keeping track of written data position.
    fids : dict
        Dict containing binary streams of files to read from.
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.

    Returns
    -------
    None
    """
    if header['filetype'] != 'rhs':
        return

    # Only attempt reading if the header indicates there are analog output
    # channels to read.
    if header['num_board_dac_channels'] > 0:
        # For traditional file format, read this block's analog output data
        # from intan file into data['board_dac_data'].
        if file_format == 'traditional':
            read_into_2D(
                destination=data['board_dac_data'],
                offset=indices['board_dac'],
                fid=fids['fid'],
                dtype='uint16',
                num_channels=header['num_board_dac_channels'],
                num_samples=header['num_samples_per_data_block'],
                order='C',
                repeat_factor=1)

        # For one file per signal type, read this block's analog output data
        # from analogout.dat into data['board_dac_data'].
        elif file_format == 'per_signal_type':
            read_into_2D(
                destination=data['board_dac_data'],
                offset=indices['board_dac'],
                fid=fids['analogout.dat'],
                dtype='uint16',
                num_channels=header['num_board_dac_channels'],
                num_samples=header['num_samples_per_data_block'],
                order='F',
                repeat_factor=1)

        # For one file per channel format, read this block's analog output
        # data from various .dat files into data['board_dac_data'].
        elif file_format == 'per_channel':
            for idx, channel in enumerate(header['board_dac_channels']):
                read_into_1D(
                    destination=data['board_dac_data'][idx],
                    offset=indices['board_dac'],
                    format_string=(
                        '<' + 'H' * header['num_samples_per_data_block']),
                    fid=(fids['board-'
                              + channel['native_channel_name']
                              + '.dat']),
                    bytes_per_sample=2,
                    num_samples=header['num_samples_per_data_block'])

        else:
            raise UnrecognizedFileFormatError(
                'Unrecognized file format: {}'.format(file_format))


def read_board_dig_in_block(header, data, indices, fids, file_format):
    """ Populate data['board_dig_in_raw'] with a block of digital input data.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    data : dict
        Dict containing fields to write data to - in this case,
        data['board_dig_in_raw'].
    indices : dict
        Dict containing indices keeping track of written data position.
    fids : dict
        Dict containing binary streams of files to read from.
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.

    Returns
    -------
    None
    """
    # Only attempt reading if the header indicates there are digital input
    # channels to read.
    if header['num_board_dig_in_channels'] > 0:
        # Determine which binary stream to read digital input from.
        if file_format == 'traditional':
            fid = fids['fid']
            use_raw = True
        elif file_format == 'per_signal_type':
            fid = fids['digitalin.dat']
            use_raw = True
        elif file_format == 'per_channel':
            use_raw = False
        else:
            raise UnrecognizedFileFormatError(
                'Unrecognized file format: {}'.format(file_format))

        if use_raw:
            # Read this block's digital input data from binary stream into
            # data['board_dig_in_raw'].
            # Later on, this raw data array will be separated to individual
            # digital input channels.
            read_into_1D(
                destination=data['board_dig_in_raw'],
                offset=indices['board_dig_in'],
                format_string='<' + 'H' * header['num_samples_per_data_block'],
                fid=fid,
                bytes_per_sample=2,
                num_samples=header['num_samples_per_data_block'])
        else:
            for idx, channel in enumerate(header['board_dig_in_channels']):
                read_into_1D(
                    destination=data['board_dig_in_data'][idx],
                    offset=indices['board_dig_in'],
                    format_string=(
                        '<' + 'H' * header['num_samples_per_data_block']),
                    fid=fids['board-'
                             + channel['native_channel_name']
                             + '.dat'],
                    bytes_per_sample=2,
                    num_samples=header['num_samples_per_data_block'])


def read_board_dig_out_block(header, data, indices, fids, file_format):
    """ Populate data['board_dig_out_raw'] with a block of digital output data.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    data : dict
        Dict containing fields to write data to - in this case,
        data['board_dig_out_raw'].
    indices : dict
        Dict containing indices keeping track of written data position.
    fids : dict
        Dict containing binary streams of files to read from.
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.

    Returns
    -------
    None
    """
    # Only attempt reading if the header indicates there are digital
    # output channels to read.
    if header['num_board_dig_out_channels'] > 0:

        # Determine which binary stream to read digital output from.
        if file_format == 'traditional':
            fid = fids['fid']
            use_raw = True
        elif file_format == 'per_signal_type':
            fid = fids['digitalout.dat']
            use_raw = True
        elif file_format == 'per_channel':
            use_raw = False
        else:
            raise UnrecognizedFileFormatError(
                'Unrecognized file format: {}'.format(file_format))

        if use_raw:
            # Read this block's digital output data from binary stream into
            # data['board_dig_out_raw'].
            # Later on, this raw data array will be separated to individual
            # digital output channels.
            read_into_1D(
                destination=data['board_dig_out_raw'],
                offset=indices['board_dig_out'],
                format_string='<' + 'H' * header['num_samples_per_data_block'],
                fid=fid,
                bytes_per_sample=2,
                num_samples=header['num_samples_per_data_block'])
        else:
            for idx, channel in enumerate(header['board_dig_out_channels']):
                read_into_1D(
                    destination=data['board_dig_out_data'][idx],
                    offset=indices['board_dig_out'],
                    format_string=(
                        '<' + 'H' * header['num_samples_per_data_block']),
                    fid=(fids['board-'
                              + channel['native_channel_name']
                              + '.dat']),
                    bytes_per_sample=2,
                    num_samples=header['num_samples_per_data_block'])


def read_one_data_block(header, data, indices, fids, file_format):
    """ Read one 60 or 128 sample data block into data, and increment all
    indices for that block.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    data : dict
        Dict containing fields to write data to - in this case,
        data['board_dig_out_raw'].
    indices : dict
        Dict containing indices keeping track of written data position.
    fids : dict
        Dict containing binary streams of files to read from.
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.

    Returns
    -------
    None
    """

    if header['filetype'] == 'rhd':
        # Read each possible signal type (each function checks if that
        # signal type is present before reading).
        read_timestamp_block(header, data, indices, fids, file_format)
        read_amplifier_block(header, data, indices, fids, file_format)
        read_lowpass_block(header, data, indices, fids, file_format)
        read_highpass_block(header, data, indices, fids, file_format)
        read_aux_input_block(header, data, indices, fids, file_format)
        read_supply_voltage_block(header, data, indices, fids, file_format)
        read_temp_sensor_block(header, data, indices, fids, file_format)
        read_board_adc_block(header, data, indices, fids, file_format)
        read_board_dig_in_block(header, data, indices, fids, file_format)
        read_board_dig_out_block(header, data, indices, fids, file_format)

        # Increment indices.
        indices['amplifier'] += header['num_samples_per_data_block']
        indices['aux_input'] += int(header['num_samples_per_data_block'] / 4)
        indices['supply_voltage'] += 1
        indices['board_adc'] += header['num_samples_per_data_block']
        indices['board_dig_in'] += header['num_samples_per_data_block']
        indices['board_dig_out'] += header['num_samples_per_data_block']

    else:
        # Read each possible signal type (each function checks if that signal
        # type is present before reading).
        read_timestamp_block(header, data, indices, fids, file_format)
        read_amplifier_block(header, data, indices, fids, file_format)
        read_dc_amplifier_block(header, data, indices, fids, file_format)
        read_stim_block(header, data, indices, fids, file_format)
        read_lowpass_block(header, data, indices, fids, file_format)
        read_highpass_block(header, data, indices, fids, file_format)
        read_board_adc_block(header, data, indices, fids, file_format)
        read_board_dac_block(header, data, indices, fids, file_format)
        read_board_dig_in_block(header, data, indices, fids, file_format)
        read_board_dig_out_block(header, data, indices, fids, file_format)

        # Increment indices.
        indices['amplifier'] += header['num_samples_per_data_block']
        indices['board_adc'] += header['num_samples_per_data_block']
        indices['board_dac'] += header['num_samples_per_data_block']
        indices['board_dig_in'] += header['num_samples_per_data_block']
        indices['board_dig_out'] += header['num_samples_per_data_block']


class UnrecognizedFileFormatError(Exception):
    """Exception returned when Intan file reading fails due to the file
    format not being consistent with Intan format.
    """
