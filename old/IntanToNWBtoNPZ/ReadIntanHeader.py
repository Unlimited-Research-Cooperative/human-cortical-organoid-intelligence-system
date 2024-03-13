# Adrian Foy September 2023

"""Module to read Intan header in preparation for conversion to NWB.
"""

import struct
import os

from SetupResources import later_than_v1_2, get_data_size


def read_header(filename, print_status=True):
    """Read the Intan File Format header from the given file.

    Parameters
    ----------
    filename : str
        Name of the intan file to read from
    print_status : bool
        Whether a summary of this header should be printed

    Returns
    -------
    header : dict
        Dict containing read header information.
    """
    fid = open(filename, 'rb')

    header = {}
    filetype = filename[-3:]
    if filetype in ('rhd', 'rhs'):
        header['filetype'] = filetype
    else:
        raise UnrecognizedFileExtensionError(
            'Unrecognized file extension: {}'.format(filetype))

    rhd = filetype == 'rhd'

    # Check 'magic number' at beginning of file to make sure this is an Intan
    # Technologies RHD2000 or RHS2000 data file.
    magic_number, = struct.unpack('<I', fid.read(4))
    correct_magic_number = int('c6912702', 16) if rhd else int('d69127ac', 16)
    if magic_number != correct_magic_number:
        raise UnrecognizedFileTypeError('Unrecognized file type.')

    header['fid'] = fid
    header['filename'] = filename
    header['lowpass_present'] = False
    header['lowpass_downsample_factor'] = 1
    header['highpass_present'] = False
    # Read version number.
    version = {}
    (version['major'], version['minor']) = struct.unpack('<hh', fid.read(4))
    header['version'] = version

    if print_status:
        print('')
        system_name = 'RHD2000' if rhd else 'RHS2000'
        print('Reading Intan Technologies {} Data File, Version {}.{}'.format(
            system_name, version['major'], version['minor']))
        print('')

    # Read information of sampling rate and amplifier frequency settings.
    header['sample_rate'], = struct.unpack('<f', fid.read(4))
    if rhd:
        freq = {}
        (freq['dsp_enabled'],
         freq['actual_dsp_cutoff_frequency'],
         freq['actual_lower_bandwidth'],
         freq['actual_upper_bandwidth'],
         freq['desired_dsp_cutoff_frequency'],
         freq['desired_lower_bandwidth'],
         freq['desired_upper_bandwidth']) = struct.unpack(
             '<hffffff', fid.read(26))

    else:
        (header['dsp_enabled'],
         header['actual_dsp_cutoff_frequency'],
         header['actual_lower_bandwidth'],
         header['actual_lower_settle_bandwidth'],
         header['actual_upper_bandwidth'],
         header['desired_dsp_cutoff_frequency'],
         header['desired_lower_bandwidth'],
         header['desired_lower_settle_bandwidth'],
         header['desired_upper_bandwidth']) = struct.unpack(
             '<hffffffff', fid.read(34))

    # This tells us if a software 50/60 Hz notch filter was enabled during
    # the data acquisition.
    notch_filter_mode, = struct.unpack('<h', fid.read(2))
    header['notch_filter_frequency'] = 0
    if notch_filter_mode == 1:
        header['notch_filter_frequency'] = 50
    elif notch_filter_mode == 2:
        header['notch_filter_frequency'] = 60

    if rhd:
        freq['notch_filter_frequency'] = header['notch_filter_frequency']
        (freq['desired_impedance_test_frequency'],
         freq['actual_impedance_test_frequency']) = struct.unpack(
             '<ff', fid.read(8))

    else:
        (header['desired_impedance_test_frequency'],
         header['actual_impedance_test_frequency']) = struct.unpack(
             '<ff', fid.read(8))
        (header['amp_settle_mode'], header['charge_recovery_mode']
         ) = struct.unpack('<hh', fid.read(4))

        frequency_parameters = {}
        frequency_parameters['amplifier_sample_rate'] = header[
            'sample_rate']
        frequency_parameters['board_adc_sample_rate'] = header[
            'sample_rate']
        frequency_parameters['board_dig_in_sample_rate'] = header[
            'sample_rate']
        frequency_parameters['desired_dsp_cutoff_frequency'] = header[
            'desired_dsp_cutoff_frequency']
        frequency_parameters['actual_dsp_cutoff_frequency'] = header[
            'actual_dsp_cutoff_frequency']
        frequency_parameters['dsp_enabled'] = header[
            'dsp_enabled']
        frequency_parameters['desired_lower_bandwidth'] = header[
            'desired_lower_bandwidth']
        frequency_parameters['desired_lower_settle_bandwidth'] = header[
            'desired_lower_settle_bandwidth']
        frequency_parameters['actual_lower_bandwidth'] = header[
            'actual_lower_bandwidth']
        frequency_parameters['actual_lower_settle_bandwidth'] = header[
            'actual_lower_settle_bandwidth']
        frequency_parameters['desired_upper_bandwidth'] = header[
            'desired_upper_bandwidth']
        frequency_parameters['actual_upper_bandwidth'] = header[
            'actual_upper_bandwidth']
        frequency_parameters['notch_filter_frequency'] = header[
            'notch_filter_frequency']
        frequency_parameters['desired_impedance_test_frequency'] = header[
            'desired_impedance_test_frequency']
        frequency_parameters['actual_impedance_test_frequency'] = header[
            'actual_impedance_test_frequency']

        header['frequency_parameters'] = frequency_parameters

        (header['stim_step_size'],
         header['recovery_current_limit'],
         header['recovery_target_voltage']) = struct.unpack(
             'fff', fid.read(12))

    note1 = read_qstring(fid)
    note2 = read_qstring(fid)
    note3 = read_qstring(fid)
    header['notes'] = {'note1': note1, 'note2': note2, 'note3': note3}

    if rhd:
        # If data file is from GUI v1.1 or later, see if temperature sensor
        # data was saved.
        header['num_temp_sensor_channels'] = 0
        if ((version['major'] == 1 and version['minor'] >= 1)
                or (version['major'] > 1)):
            header['num_temp_sensor_channels'], = struct.unpack(
                '<h', fid.read(2))

        # If data file is from GUI v1.3 or later, load eval board mode.
        header['board_mode'] = 0
        if (((version['major'] == 1) and (version['minor'] >= 3))
                or (version['major'] > 1)):
            header['board_mode'], = struct.unpack('<h', fid.read(2))

        header['num_samples_per_data_block'] = 60
        # If data file is from v2.0 or later (Intan Recording Controller),
        # load name of digital reference channel
        if version['major'] > 1:
            header['reference_channel'] = read_qstring(fid)
            header['num_samples_per_data_block'] = 128

        # Place frequency-related information in data structure.
        # (Note: much of this structure is set above)
        freq['amplifier_sample_rate'] = header['sample_rate']
        freq['aux_input_sample_rate'] = header['sample_rate'] / 4
        freq['supply_voltage_sample_rate'] = (
            header['sample_rate'] / header['num_samples_per_data_block'])
        freq['board_adc_sample_rate'] = header['sample_rate']
        freq['board_dig_in_sample_rate'] = header['sample_rate']

        header['frequency_parameters'] = freq

    else:
        header['num_samples_per_data_block'] = 128
        (header['dc_amplifier_data_saved'],
         header['eval_board_mode']) = struct.unpack('<hh', fid.read(4))

        header['reference_channel'] = read_qstring(fid)

    if rhd:
        # Create structure arrays for each type of data channel.
        header['spike_triggers'] = []
        header['amplifier_channels'] = []
        header['aux_input_channels'] = []
        header['supply_voltage_channels'] = []
        header['board_adc_channels'] = []
        header['board_dig_in_channels'] = []
        header['board_dig_out_channels'] = []

    else:
        # Create structure arrays for each type of data channel.
        header['spike_triggers'] = []
        header['amplifier_channels'] = []
        header['dc_amplifier_channels'] = []
        header['stim_channels'] = []
        header['amp_settle_channels'] = []
        header['charge_recovery_channels'] = []
        header['compliance_limit_channels'] = []
        header['board_adc_channels'] = []
        header['board_dac_channels'] = []
        header['board_dig_in_channels'] = []
        header['board_dig_out_channels'] = []

    # Read signal summary from data file header.

    number_of_signal_groups, = struct.unpack('<h', fid.read(2))

    for signal_group in range(1, number_of_signal_groups + 1):
        signal_group_name = read_qstring(fid)
        signal_group_prefix = read_qstring(fid)
        (signal_group_enabled, signal_group_num_channels,
         _) = struct.unpack('<hhh', fid.read(6))

        if (signal_group_num_channels > 0) and (signal_group_enabled > 0):
            for _ in range(0, signal_group_num_channels):
                new_channel = {'port_name': signal_group_name,
                               'port_prefix': signal_group_prefix,
                               'port_number': signal_group}
                new_channel['native_channel_name'] = read_qstring(fid)
                new_channel['custom_channel_name'] = read_qstring(fid)
                if rhd:
                    (new_channel['native_order'],
                     new_channel['custom_order'],
                     signal_type,
                     channel_enabled,
                     new_channel['chip_channel'],
                     new_channel['board_stream']) = struct.unpack(
                         '<hhhhhh', fid.read(12))
                else:
                    (new_channel['native_order'], new_channel['custom_order'],
                     signal_type, channel_enabled, new_channel['chip_channel'],
                     _, new_channel['board_stream']) = struct.unpack(
                         '<hhhhhhh', fid.read(14))  # ignore command_stream

                new_trigger_channel = {}
                (new_trigger_channel['voltage_trigger_mode'],
                 new_trigger_channel['voltage_threshold'],
                 new_trigger_channel['digital_trigger_channel'],
                 new_trigger_channel['digital_edge_polarity']) = struct.unpack(
                     '<hhhh', fid.read(8))
                (new_channel['electrode_impedance_magnitude'],
                 new_channel['electrode_impedance_phase']) = struct.unpack(
                     '<ff', fid.read(8))

                if channel_enabled:
                    if signal_type == 0:
                        header['amplifier_channels'].append(new_channel)
                        if not rhd:
                            # If dc amplifier data is being saved,
                            # dc_amplifier_channels
                            if header['dc_amplifier_data_saved']:
                                new_dc_channel = {
                                    'port_name':
                                        new_channel['port_name'],
                                    'port_prefix':
                                        new_channel['port_prefix'],
                                    'port_number':
                                        new_channel['port_number'],
                                    'native_channel_name':
                                        'dc-' +
                                        new_channel['native_channel_name'],
                                    'custom_channel_name':
                                        'dc-' +
                                        new_channel['custom_channel_name'],
                                    'native_order':
                                        new_channel['native_order'],
                                    'custom_order':
                                        new_channel['custom_order'],
                                    'chip_channel':
                                        new_channel['chip_channel'],
                                    'board_stream':
                                        new_channel['board_stream'],
                                    'electrode_impedance_magnitude':
                                        new_channel['electrode_impedance_'
                                                    'magnitude'],
                                    'electrode_impedance_phase':
                                        new_channel['electrode_impedance_'
                                                    'phase']}
                                header['dc_amplifier_channels'].append(
                                    new_dc_channel)

                            # stim_channels
                            new_stim_channel = {
                                'port_name':
                                    new_channel['port_name'],
                                'port_prefix':
                                    new_channel['port_prefix'],
                                'port_number':
                                    new_channel['port_number'],
                                'native_channel_name':
                                    'stim-' +
                                    new_channel['native_channel_name'],
                                'custom_channel_name':
                                    'stim-' +
                                    new_channel['custom_channel_name'],
                                'native_order':
                                    new_channel['native_order'],
                                'custom_order':
                                    new_channel['custom_order'],
                                'chip_channel':
                                    new_channel['chip_channel'],
                                'board_stream':
                                    new_channel['board_stream'],
                                'electrode_impedance_magnitude':
                                    new_channel['electrode_impedance_'
                                                'magnitude'],
                                'electrode_impedance_phase':
                                    new_channel['electrode_impedance_phase']}
                            header['stim_channels'].append(new_stim_channel)

                            # amp_settle_channels
                            new_amp_settle_channel = {
                                'port_name':
                                    new_channel['port_name'],
                                'port_prefix':
                                    new_channel['port_prefix'],
                                'port_number':
                                    new_channel['port_number'],
                                'native_channel_name':
                                    'AMP_SETTLE_'
                                    + new_channel['native_channel_name'],
                                'custom_channel_name':
                                    'AMP_SETTLE_'
                                    + new_channel['custom_channel_name'],
                                'native_order':
                                    new_channel['native_order'],
                                'custom_order':
                                    new_channel['custom_order'],
                                'chip_channel':
                                    new_channel['chip_channel'],
                                'board_stream':
                                    new_channel['board_stream'],
                                'electrode_impedance_magnitude':
                                    new_channel['electrode_impedance_'
                                                'magnitude'],
                                'electrode_impedance_phase':
                                    new_channel['electrode_impedance_phase']}
                            header['amp_settle_channels'].append(
                                new_amp_settle_channel)

                            # charge_recovery_channels
                            new_charge_recovery_channel = {
                                'port_name':
                                    new_channel['port_name'],
                                'port_prefix':
                                    new_channel['port_prefix'],
                                'port_number':
                                    new_channel['port_number'],
                                'native_channel_name':
                                    'CHARGE_RECOVERY_'
                                    + new_channel['native_channel_name'],
                                'custom_channel_name':
                                    'CHARGE_RECOVERY_'
                                    + new_channel['custom_channel_name'],
                                'native_order':
                                    new_channel['native_order'],
                                'custom_order':
                                    new_channel['custom_order'],
                                'chip_channel':
                                    new_channel['chip_channel'],
                                'board_stream':
                                    new_channel['board_stream'],
                                'electrode_impedance_magnitude':
                                    new_channel['electrode_impedance_'
                                                'magnitude'],
                                'electrode_impedance_phase':
                                    new_channel['electrode_impedance_phase']}
                            header['charge_recovery_channels'].append(
                                new_charge_recovery_channel)

                            # compliance_limit_channels
                            new_compliance_limit_channel = {
                                'port_name':
                                    new_channel['port_name'],
                                'port_prefix':
                                    new_channel['port_prefix'],
                                'port_number':
                                    new_channel['port_number'],
                                'native_channel_name':
                                    'COMPLIANCE_LIMIT_' +
                                    new_channel['native_channel_name'],
                                'custom_channel_name':
                                    'COMPLIANCE_LIMIT_' +
                                    new_channel['custom_channel_name'],
                                'native_order':
                                    new_channel['native_order'],
                                'custom_order':
                                    new_channel['custom_order'],
                                'chip_channel':
                                    new_channel['chip_channel'],
                                'board_stream':
                                    new_channel['board_stream'],
                                'electrode_impedance_magnitude':
                                    new_channel['electrode_impedance_'
                                                'magnitude'],
                                'electrode_impedance_phase':
                                    new_channel['electrode_impedance_phase']}
                            header['compliance_limit_channels'].append(
                                new_compliance_limit_channel)

                        header['spike_triggers'].append(new_trigger_channel)
                    elif signal_type == 1:
                        if rhd:
                            header['aux_input_channels'].append(new_channel)
                        else:
                            raise SignalTypeError('Wrong signal type for '
                                                  'rhs format')
                    elif signal_type == 2:
                        if rhd:
                            header['supply_voltage_channels'].append(
                                new_channel)
                        else:
                            raise SignalTypeError('Wrong signal type for '
                                                  'rhs format')
                    elif signal_type == 3:
                        header['board_adc_channels'].append(new_channel)
                    elif signal_type == 4:
                        if rhd:
                            header['board_dig_in_channels'].append(new_channel)
                        else:
                            header['board_dac_channels'].append(new_channel)
                    elif signal_type == 5:
                        if rhd:
                            header['board_dig_out_channels'].append(
                                new_channel)
                        else:
                            header['board_dig_in_channels'].append(new_channel)
                    elif signal_type == 6:
                        if rhd:
                            raise SignalTypeError('Wrong signal type for '
                                                  'rhd format')
                        else:
                            header['board_dig_out_channels'].append(
                                new_channel)
                    else:
                        raise UnknownChannelType('Unknown channel type.')

    # Summarize contents of data file.
    header['num_amplifier_channels'] = len(header['amplifier_channels'])
    if rhd:
        header['num_aux_input_channels'] = len(header['aux_input_channels'])
        header['num_supply_voltage_channels'] = len(
            header['supply_voltage_channels'])
    else:
        header['num_stim_channels'] = len(header['stim_channels'])
        header['num_board_dac_channels'] = len(header['board_dac_channels'])
    header['num_board_adc_channels'] = len(header['board_adc_channels'])
    header['num_board_dig_in_channels'] = len(header['board_dig_in_channels'])
    header['num_board_dig_out_channels'] = len(
        header['board_dig_out_channels'])

    header['size'] = fid.tell()
    header['total_file_size'] = os.path.getsize(filename)
    header['data_present'] = (header['total_file_size'] - header['size']) > 0

    return header


def get_mergeable_files(original_header):
    """ Return a list of filenames that have headers similar enough to the
    original intan file that merging is possible

    Parameters
    ----------
    original_header : dict
        Dict containing previously read header information from the original
        intan file

    Returns
    -------
    mergeable_files : list
        List containing header info of a mergeable file
    """
    original_filename = original_header['filename']
    mergeable_files = []  # List of headers

    # Get all .rhd or .rhs files in this directory (excluding the original),
    # and compare their headers to the original.
    # Also, peek at the last timestamp of the previous file, and ensure the
    # first timestamp of this file comes immediately after.
    # For each mergeable header, add header to the 'mergeable' variables that
    # will be returned.
    # For each mergeable header, also print a message describing that this
    # file is valid for merge.
    last_timestamp = peek_timestamp('last', original_header)

    keep_looking = True
    while keep_looking:

        found_mergeable = False

        # Go through all files in this directory
        for this_filename in os.listdir():
            # If a mergeable file is found, escape for loop and continue with
            # a new for loop.
            # If no mergeable file is found, continue with for loop

            if not this_filename.endswith('.' + original_header['filetype']):
                continue

            if this_filename == original_filename:
                continue

            this_header = read_header(this_filename, False)
            if not this_header['data_present']:
                continue

            consistent_headers = not conflict_in_headers(
                original_header, this_header)
            continuous_timestamps = check_continuous(
                this_header, last_timestamp)
            mergeable = consistent_headers and continuous_timestamps

            if not mergeable:
                continue

            mergeable_files.append(this_header)
            last_timestamp = peek_timestamp('last', this_header)
            found_mergeable = True
            print('Data in {} will be included in this conversion'.format(
                this_filename))
            # Break out of for loop, start new iteration because keep_looking
            # is True.
            break

        # If for loop has completed with no mergeable file found, stop looking.
        if not found_mergeable:
            keep_looking = False

    return mergeable_files


def check_continuous(this_header, last_timestamp):
    """ Check last timestamp of previous file and first timestamp of this
    file to determine if they are continuous. """
    first_timestamp = peek_timestamp('first', this_header)
    return True if (first_timestamp - 1) == last_timestamp else False


def peek_timestamp(position, header):
    """ Peek into the data file associated with the given header, and return
    either the first or last timestamp of that file

    Parameters
    ----------
    position : str
        Either 'first' to get the first timestamp of the file, or 'last' to
        get the last timestamp of the file
    header : dict
        Dict containing previously read header information from the intan file

    Returns
    -------
    timestamp : int
        The first or last timestamp of this file
    """
    fid = header['fid']
    pos = fid.tell()
    size_timestamp = 4
    start_data_pos = header['size']

    if position == 'first':
        timestamp_pos = start_data_pos

    elif position == 'last':
        file_size = os.path.getsize(header['filename'])
        data_size = file_size - start_data_pos
        bytes_per_block = get_bytes_per_data_block(header)
        blocks_in_file = data_size / bytes_per_block

        if not blocks_in_file.is_integer():
            raise FileSizeError(
                'Calculations show file has non-integer number of data blocks')

        start_last_block_pos = start_data_pos + \
            get_bytes_per_data_block(header) * (blocks_in_file - 1)
        timestamp_pos = start_last_block_pos + \
            (header['num_samples_per_data_block'] - 1) * size_timestamp

    else:
        raise FileSizeError(
            'Unrecognized position argument for peek_timestamp()')
    fid.seek(int(timestamp_pos))

    signing_character = 'i' if later_than_v1_2(header) else 'I'
    format_string = '<' + signing_character
    timestamp, = struct.unpack(format_string, fid.read(size_timestamp))

    fid.seek(pos)
    return timestamp


def conflict_in_headers(h1, h2):
    """ Compare critical values (like channel numbers and names)
    between 2 headers.
    Non-critical differences that can be ignored include:
    notch filter mode, impedance frequency, notes, and reference channel

    Parameters
    ----------
    h1 : dict
        Dict containing read header information from the original file
    h2 : dict
        Dict containing read header information from the file to compare to

    Returns
    -------
    bool
        Whether a significant conflict was detected between these headers
    """
    # Double-check that files are of the same type
    if conflict_in_field(h1, h2, 'filetype'):
        return True

    # Detect conflicts in general system parameters
    if conflict_in_version(h1, h2):
        return True
    if conflict_in_field(h1, h2, 'sample_rate'):
        return True
    if conflict_in_frequency_parameters(h1, h2):
        return True
    if h1['filetype'] == 'rhd':
        if conflict_in_field(h1, h2, 'board_mode'):
            return True
        if conflict_in_field(h1, h2, 'num_temp_sensor_channels'):
            return True

    else:
        if conflict_in_field(h1, h2, 'eval_board_mode'):
            return True
        if conflict_in_signal_type(h1, h2, 'board_adc_channels'):
            return True
        if conflict_in_signal_type(h1, h2, 'board_dig_in_channels'):
            return True
        if conflict_in_signal_type(h1, h2, 'board_dig_out_channels'):
            return True

    # Detect conflicts in enabled signals
    if conflict_in_signal_type(h1, h2, 'amplifier_channels'):
        return True
    if h1['filetype'] == 'rhd':
        if conflict_in_signal_type(h1, h2, 'aux_input_channels'):
            return True
        if conflict_in_signal_type(h1, h2, 'supply_voltage_channels'):
            return True
    else:
        if conflict_in_signal_type(h1, h2, 'board_dac_channels'):
            return True

    return False


def conflict_in_frequency_parameters(h1, h2):
    """ Compare critical values (related to bandwidth and filtering)
    between 2 headers.

    Parameters
    ----------
    h1 : dict
        Dict containing read header information from the original file
    h2 : dict
        Dict containing read header information from the file to compare to

    Returns
    -------
    bool
        Whether a significant conflict related to bandwidth and filtering
        was detected between these headers
    """
    f1 = h1['frequency_parameters']
    f2 = h2['frequency_parameters']

    if conflict_in_field(f1, f2, 'dsp_enabled'):
        return True
    if conflict_in_field(f1, f2, 'actual_dsp_cutoff_frequency'):
        return True
    if conflict_in_field(f1, f2, 'actual_lower_bandwidth'):
        return True
    if conflict_in_field(f1, f2, 'actual_upper_bandwidth'):
        return True
    if conflict_in_field(f1, f2, 'desired_dsp_cutoff_frequency'):
        return True
    if conflict_in_field(f1, f2, 'desired_lower_bandwidth'):
        return True
    if conflict_in_field(f1, f2, 'desired_upper_bandwidth'):
        return True
    if conflict_in_field(f1, f2, 'notch_filter_frequency'):
        return True

    if h1['filetype'] == 'rhs':
        if conflict_in_field(f1, f2, 'actual_lower_settle_bandwidth'):
            return True
        if conflict_in_field(f1, f2, 'desired_lower_settle_bandwidth'):
            return True

    return False


def conflict_in_channel(ch1, ch2):
    """ Compare critical values (native channel name, chip channel,
    and board stream) between 2 channels.

    Parameters
    ----------
    ch1 : dict
        Dict containing information about a single channel from the
        original header
    ch2 : dict
        Dict containing information about a single channel from the
        header to compare to

    Returns
    -------
    bool
        Whether a significant conflict was detected between these channels
    """
    if conflict_in_field(ch1, ch2, 'native_channel_name'):
        return True
    if conflict_in_field(ch1, ch2, 'chip_channel'):
        return True
    if conflict_in_field(ch1, ch2, 'board_stream'):
        return True

    return False


def conflict_in_version(h1, h2):
    """ Compare software version number between 2 headers.

    Parameters
    ----------
    h1 : dict
        Dict containing read header information from the original file
    h2 : dict
        Dict containing read header information from the file to compare to

    Returns
    -------
    bool
        Whether a significant conflict was detected between these headers
    """
    if h1['version']['major'] != h2['version']['major']:
        return True
    if h1['version']['minor'] != h2['version']['minor']:
        return True

    return False


def conflict_in_signal_type(h1, h2, signal_type):
    """ Compare an entire signal type between 2 headers.

    Parameters
    ----------
    h1 : dict
        Dict containing read header information from the original file
    h2 : dict
        Dict containing read header information from the file to compare to
    signal_type : str
        Name of signal type to compare

    Returns
    -------
    bool
        Whether a significant conflict was detected related to this signal type
    """

    # Detect conflicts in number of channels of this signal type
    num_channels_str = 'num_' + signal_type
    if conflict_in_field(h1, h2, num_channels_str):
        return True

    # Detect conflicts for each individual channel of this signal type
    for channel in range(h1[num_channels_str]):
        if conflict_in_channel(h1[signal_type][channel],
                               h2[signal_type][channel]):
            return True

    return False


def conflict_in_field(d1, d2, field):
    """ Detect if the object named 'field' in dict d1 is not equal to an
    object of the same name in dict d2."""
    return d1[field] != d2[field]


def merged_samples(signal_type, mergeable_files):
    """ Return the number of samples of this signal type present in all
    mergeable files.

    Parameters
    ----------
    signal_type : str
        String describing the signal type to count samples of (for example,
        'amplifier', or 'board_dig_in')
    mergeable_files : list
        List of 'header' dicts

    Returns
    -------
    merged_samples : int
        Total number of samples (per channel) of this signal type across
        all mergeable files
    """
    merged_samples_count = 0
    for header in mergeable_files:
        bytes_per_block = get_bytes_per_data_block(header)
        fids = {}
        total_num_data_blocks, _ = get_data_size(
            header, fids, bytes_per_block, False)
        if (signal_type == 'amplifier'
                or signal_type == 'board_adc'
                or signal_type == 'board_dac'
                or signal_type == 'board_dig_in'
                or signal_type == 'board_dig_out'):
            merged_samples_count += (header['num_samples_per_data_block']
                                     * total_num_data_blocks)
        elif signal_type == 'aux_input':
            merged_samples_count += int(
                (header['num_samples_per_data_block'] / 4)
                * total_num_data_blocks)
        elif signal_type == 'supply_voltage':
            merged_samples_count += 1 * total_num_data_blocks
        else:
            raise SignalTypeError('Unrecognized signal type')
    return merged_samples_count


def get_bytes_per_data_block(header):
    """ Calculate the number of bytes in each 60 or 128 sample datablock.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information

    Returns
    -------
    int
        Number of bytes contained in each datablock.
    """
    # Each data block contains 60 or 128 amplifier samples.
    if header['filetype'] == 'rhd':
        N = header['num_samples_per_data_block']
    else:
        N = 128

    bytes_per_block = N * 4  # timestamp data
    bytes_per_block += N * 2 * header['num_amplifier_channels']

    if header['filetype'] == 'rhd':
        # Auxiliary inputs are sampled 4x slower than amplifiers
        bytes_per_block += (N / 4) * 2 * header['num_aux_input_channels']

        # Supply voltage is sampled 60 or 128x slower than amplifiers
        bytes_per_block += 1 * 2 * header['num_supply_voltage_channels']

        # Temp sensor is sampled 60 or 128x slower than amplifiers
        if header['num_temp_sensor_channels'] > 0:
            bytes_per_block += 1 * 2 * header['num_temp_sensor_channels']
    else:
        # DC amplifier voltage (absent if flag was off)
        if header['dc_amplifier_data_saved'] > 0:
            bytes_per_block += N * 2 * header['num_amplifier_channels']

        # Stimulation data, one per enabled amplifier channel
        bytes_per_block += N * 2 * header['num_amplifier_channels']

        # Board analog outputs are sampled at same rate as amplifiers
        bytes_per_block += N * 2 * header['num_board_dac_channels']

    # Board analog inputs are sampled at same rate as amplifiers
    bytes_per_block += N * 2 * header['num_board_adc_channels']

    # Board digital inputs are sampled at same rate as amplifiers
    if header['num_board_dig_in_channels'] > 0:
        bytes_per_block += N * 2

    # Board digital outputs are sampled at same rate as amplifiers
    if header['num_board_dig_out_channels'] > 0:
        bytes_per_block += N * 2

    return int(bytes_per_block)


def print_summary(header):
    """ Print easily understandable summary of contents of header.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.

    Returns
    -------
    None
    """
    print('Found {} amplifier channel{}.'.format(
        header['num_amplifier_channels'], plural(
            header['num_amplifier_channels'])))
    if header['filetype'] == 'rhd':
        print('Found {} auxiliary input channel{}.'.format(
            header['num_aux_input_channels'], plural(
                header['num_aux_input_channels'])))
        print('Found {} supply voltage channel{}.'.format(
            header['num_supply_voltage_channels'], plural(
                header['num_supply_voltage_channels'])))
        print('Found {} temperature sensors channel{}.'.format(
            header['num_temp_sensor_channels'], plural(
                header['num_temp_sensor_channels'])))
    else:
        print('Found {} board DAC channel{}.'.format(
            header['num_board_dac_channels'], plural(
                header['num_board_dac_channels'])))

    print('Found {} board ADC channel{}.'.format(
        header['num_board_adc_channels'], plural(
            header['num_board_adc_channels'])))
    print('Found {} board digital input channel{}.'.format(
        header['num_board_dig_in_channels'], plural(
            header['num_board_dig_in_channels'])))
    print('Found {} board digital output channel{}.'.format(
        header['num_board_dig_out_channels'], plural(
            header['num_board_dig_out_channels'])))
    print('')


def plural(n):
    """Utility function to optionally pluralize words based on the value of n.

    Parameters
    ----------
    n : int
        Number of items. If n is 1, then pluralizing is inappropriate

    Returns
    -------
    str
        Either empty string '' or 's' if pluralizing is appropriate
    """
    if n == 1:
        return ''
    return 's'


def read_qstring(fid):
    """Read Qt style QString.

    The first 32-bit unsigned number indicates the length of the string
    (in bytes).
    If this number equals 0xFFFFFFFF, the string is null.

    Strings are stored as unicode.

    Parameters
    ----------
    fid : _io.BufferedReader
        Binary stream of the file to read from

    Returns
    -------
    a : str
        Read QString as a standard Python string
    """

    length, = struct.unpack('<I', fid.read(4))
    if length == int('ffffffff', 16):
        return ""

    if length > (os.fstat(fid.fileno()).st_size - fid.tell() + 1):
        print(length)
        raise QStringError('Length too long.')

    # convert length from bytes to 16-bit Unicode words
    length = int(length / 2)

    data = []
    for _ in range(0, length):
        c, = struct.unpack('<H', fid.read(2))
        data.append(c)

    a = ''.join([chr(c) for c in data])

    return a


class UnrecognizedFileExtensionError(Exception):
    """Exception returned when Intan file reading fails due to the file
    extension not being correct.
    """


class UnrecognizedFileTypeError(Exception):
    """Exception returned when Intan file reading fails due to the file header
    not having the expected Intan magic number .
    """


class SignalTypeError(Exception):
    """Exception returned when detected signal type does not match the Intan
    file type - for example, if a RHD-only signal type like 'auxiliary input'
    is detected in an RHS file.
    """


class UnknownChannelType(Exception):
    """Exception returned when detected channel is not recognized.
    """


class FileSizeError(Exception):
    """Exception returned when file reading fails due to the file size
    being invalid or the calculated file size differing from the actual
    file size.
    """


class QStringError(Exception):
    """Exception returned when reading a QString fails because it is too long.
    """
