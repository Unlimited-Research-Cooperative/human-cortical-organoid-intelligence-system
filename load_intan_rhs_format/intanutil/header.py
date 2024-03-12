# Adrian Foy September 2023

"""Interacts with RHD header files, both directly at the binary level and at
the Python level with dictionaries.
"""

import struct

from intanutil.report import read_qstring


def read_header(fid):
    """Reads the Intan File Format header from the given file.
    """
    check_magic_number(fid)

    header = {}

    read_version_number(header, fid)
    set_num_samples_per_data_block(header)

    read_sample_rate(header, fid)
    read_freq_settings(header, fid)

    read_notch_filter_frequency(header, fid)
    read_impedance_test_frequencies(header, fid)
    read_amp_settle_mode(header, fid)
    read_charge_recovery_mode(header, fid)

    create_frequency_parameters(header)

    read_stim_step_size(header, fid)
    read_recovery_current_limit(header, fid)
    read_recovery_target_voltage(header, fid)

    read_notes(header, fid)
    read_dc_amp_saved(header, fid)
    read_eval_board_mode(header, fid)
    read_reference_channel(header, fid)

    initialize_channels(header)
    read_signal_summary(header, fid)

    return header


def check_magic_number(fid):
    """Checks magic number at beginning of file to verify this is an Intan
    Technologies RHS data file.
    """
    magic_number, = struct.unpack('<I', fid.read(4))
    if magic_number != int('d69127ac', 16):
        raise UnrecognizedFileError('Unrecognized file type.')


def read_version_number(header, fid):
    """Reads version number (major and minor) from fid. Stores them into
    header['version']['major'] and header['version']['minor'].
    """
    version = {}
    (version['major'], version['minor']) = struct.unpack('<hh', fid.read(4))
    header['version'] = version

    print('\nReading Intan Technologies RHS Data File, Version {}.{}\n'
          .format(version['major'], version['minor']))


def set_num_samples_per_data_block(header):
    """Determines how many samples are present per data block (always 128 for
    RHS files)
    """
    header['num_samples_per_data_block'] = 128


def read_sample_rate(header, fid):
    """Reads sample rate from fid. Stores it into header['sample_rate'].
    """
    header['sample_rate'], = struct.unpack('<f', fid.read(4))


def read_freq_settings(header, fid):
    """Reads amplifier frequency settings from fid. Stores them in 'header'
    dict.
    """
    (header['dsp_enabled'],
     header['actual_dsp_cutoff_frequency'],
     header['actual_lower_bandwidth'],
     header['actual_lower_settle_bandwidth'],
     header['actual_upper_bandwidth'],
     header['desired_dsp_cutoff_frequency'],
     header['desired_lower_bandwidth'],
     header['desired_lower_settle_bandwidth'],
     header['desired_upper_bandwidth']) = struct.unpack('<hffffffff',
                                                        fid.read(34))


def read_notch_filter_frequency(header, fid):
    """Reads notch filter mode from fid, and stores frequency (in Hz) in
    'header' dict.
    """
    notch_filter_mode, = struct.unpack('<h', fid.read(2))
    header['notch_filter_frequency'] = 0
    if notch_filter_mode == 1:
        header['notch_filter_frequency'] = 50
    elif notch_filter_mode == 2:
        header['notch_filter_frequency'] = 60


def read_impedance_test_frequencies(header, fid):
    """Reads desired and actual impedance test frequencies from fid, and stores
    them (in Hz) in 'freq' dicts.
    """
    (header['desired_impedance_test_frequency'],
     header['actual_impedance_test_frequency']) = (
         struct.unpack('<ff', fid.read(8)))


def read_amp_settle_mode(header, fid):
    """Reads amp settle mode from fid, and stores it in 'header' dict.
    """
    header['amp_settle_mode'], = struct.unpack('<h', fid.read(2))


def read_charge_recovery_mode(header, fid):
    """Reads charge recovery mode from fid, and stores it in 'header' dict.
    """
    header['charge_recovery_mode'], = struct.unpack('<h', fid.read(2))


def create_frequency_parameters(header):
    """Copy various frequency-related parameters (set in other functions) to
    the dict at header['frequency_parameters'].
    """
    freq = {}
    freq['amplifier_sample_rate'] = header['sample_rate']
    freq['board_adc_sample_rate'] = header['sample_rate']
    freq['board_dig_in_sample_rate'] = header['sample_rate']
    copy_from_header(header, freq, 'desired_dsp_cutoff_frequency')
    copy_from_header(header, freq, 'actual_dsp_cutoff_frequency')
    copy_from_header(header, freq, 'dsp_enabled')
    copy_from_header(header, freq, 'desired_lower_bandwidth')
    copy_from_header(header, freq, 'desired_lower_settle_bandwidth')
    copy_from_header(header, freq, 'actual_lower_bandwidth')
    copy_from_header(header, freq, 'actual_lower_settle_bandwidth')
    copy_from_header(header, freq, 'desired_upper_bandwidth')
    copy_from_header(header, freq, 'actual_upper_bandwidth')
    copy_from_header(header, freq, 'notch_filter_frequency')
    copy_from_header(header, freq, 'desired_impedance_test_frequency')
    copy_from_header(header, freq, 'actual_impedance_test_frequency')
    header['frequency_parameters'] = freq


def copy_from_header(header, freq_params, key):
    """Copy from header
    """
    freq_params[key] = header[key]


def read_stim_step_size(header, fid):
    """Reads stim step size from fid, and stores it in 'header' dict.
    """
    header['stim_step_size'], = struct.unpack('f', fid.read(4))


def read_recovery_current_limit(header, fid):
    """Reads charge recovery current limit from fid, and stores it in 'header'
    dict.
    """
    header['recovery_current_limit'], = struct.unpack('f', fid.read(4))


def read_recovery_target_voltage(header, fid):
    """Reads charge recovery target voltage from fid, and stores it in 'header'
    dict.
    """
    header['recovery_target_voltage'], = struct.unpack('f', fid.read(4))


def read_notes(header, fid):
    """Reads notes as QStrings from fid, and stores them as strings in
    header['notes'] dict.
    """
    header['notes'] = {'note1': read_qstring(fid),
                       'note2': read_qstring(fid),
                       'note3': read_qstring(fid)}


def read_dc_amp_saved(header, fid):
    """Reads whether DC amp data was saved from fid, and stores it in 'header'
    dict.
    """
    header['dc_amplifier_data_saved'], = struct.unpack('<h', fid.read(2))


def read_eval_board_mode(header, fid):
    """Stores eval board mode in header['eval_board_mode'].
    """
    header['eval_board_mode'], = struct.unpack('<h', fid.read(2))


def read_reference_channel(header, fid):
    """Reads name of reference channel as QString from fid, and stores it as
    a string in header['reference_channel'].
    """
    header['reference_channel'] = read_qstring(fid)


def initialize_channels(header):
    """Creates empty lists for each type of data channel and stores them in
    'header' dict.
    """
    header['spike_triggers'] = []
    header['amplifier_channels'] = []
    header['board_adc_channels'] = []
    header['board_dac_channels'] = []
    header['board_dig_in_channels'] = []
    header['board_dig_out_channels'] = []


def read_signal_summary(header, fid):
    """Reads signal summary from data file header and stores information for
    all signal groups and their channels in 'header' dict.
    """
    number_of_signal_groups, = struct.unpack('<h', fid.read(2))
    for signal_group in range(1, number_of_signal_groups + 1):
        add_signal_group_information(header, fid, signal_group)
    add_num_channels(header)
    print_header_summary(header)


def add_signal_group_information(header, fid, signal_group):
    """Adds information for a signal group and all its channels to 'header'
    dict.
    """
    signal_group_name = read_qstring(fid)
    signal_group_prefix = read_qstring(fid)
    (signal_group_enabled, signal_group_num_channels, _) = struct.unpack(
        '<hhh', fid.read(6))

    if signal_group_num_channels > 0 and signal_group_enabled > 0:
        for _ in range(0, signal_group_num_channels):
            add_channel_information(header, fid, signal_group_name,
                                    signal_group_prefix, signal_group)


def add_channel_information(header, fid, signal_group_name,
                            signal_group_prefix, signal_group):
    """Reads a new channel's information from fid and appends it to 'header'
    dict.
    """
    (new_channel, new_trigger_channel, channel_enabled,
     signal_type) = read_new_channel(
         fid, signal_group_name, signal_group_prefix, signal_group)
    append_new_channel(header, new_channel, new_trigger_channel,
                       channel_enabled, signal_type)


def read_new_channel(fid, signal_group_name, signal_group_prefix,
                     signal_group):
    """Reads a new channel's information from fid.
    """
    new_channel = {'port_name': signal_group_name,
                   'port_prefix': signal_group_prefix,
                   'port_number': signal_group}
    new_channel['native_channel_name'] = read_qstring(fid)
    new_channel['custom_channel_name'] = read_qstring(fid)
    (new_channel['native_order'],
     new_channel['custom_order'],
     signal_type, channel_enabled,
     new_channel['chip_channel'],
     _,  # ignore command_stream
     new_channel['board_stream']) = (
         struct.unpack('<hhhhhHh', fid.read(14)))
    new_trigger_channel = {}
    (new_trigger_channel['voltage_trigger_mode'],
     new_trigger_channel['voltage_threshold'],
     new_trigger_channel['digital_trigger_channel'],
     new_trigger_channel['digital_edge_polarity']) = (
         struct.unpack('<hhhh', fid.read(8)))
    (new_channel['electrode_impedance_magnitude'],
     new_channel['electrode_impedance_phase']) = (
         struct.unpack('<ff', fid.read(8)))

    return new_channel, new_trigger_channel, channel_enabled, signal_type


def append_new_channel(header, new_channel, new_trigger_channel,
                       channel_enabled, signal_type):
    """"Appends 'new_channel' to 'header' dict depending on if channel is
    enabled and the signal type.
    """
    if not channel_enabled:
        return

    if signal_type == 0:
        header['amplifier_channels'].append(new_channel)
        header['spike_triggers'].append(new_trigger_channel)
    elif signal_type == 1:
        raise UnknownChannelTypeError('No aux input signals in RHS format.')
    elif signal_type == 2:
        raise UnknownChannelTypeError('No Vdd signals in RHS format.')
    elif signal_type == 3:
        header['board_adc_channels'].append(new_channel)
    elif signal_type == 4:
        header['board_dac_channels'].append(new_channel)
    elif signal_type == 5:
        header['board_dig_in_channels'].append(new_channel)
    elif signal_type == 6:
        header['board_dig_out_channels'].append(new_channel)
    else:
        raise UnknownChannelTypeError('Unknown channel type.')


def add_num_channels(header):
    """Adds channel numbers for all signal types to 'header' dict.
    """
    header['num_amplifier_channels'] = len(header['amplifier_channels'])
    header['num_board_adc_channels'] = len(header['board_adc_channels'])
    header['num_board_dac_channels'] = len(header['board_dac_channels'])
    header['num_board_dig_in_channels'] = len(header['board_dig_in_channels'])
    header['num_board_dig_out_channels'] = len(
        header['board_dig_out_channels'])


def header_to_result(header, result):
    """Merges header information from .rhs file into a common 'result' dict.
    If any fields have been allocated but aren't relevant (for example, no
    channels of this type exist), does not copy those entries into 'result'.
    """
    stim_parameters = {}
    stim_parameters['stim_step_size'] = header['stim_step_size']
    stim_parameters['charge_recovery_current_limit'] = \
        header['recovery_current_limit']
    stim_parameters['charge_recovery_target_voltage'] = \
        header['recovery_target_voltage']
    stim_parameters['amp_settle_mode'] = header['amp_settle_mode']
    stim_parameters['charge_recovery_mode'] = header['charge_recovery_mode']
    result['stim_parameters'] = stim_parameters

    result['notes'] = header['notes']

    if header['num_amplifier_channels'] > 0:
        result['spike_triggers'] = header['spike_triggers']
        result['amplifier_channels'] = header['amplifier_channels']

    result['notes'] = header['notes']
    result['frequency_parameters'] = header['frequency_parameters']
    result['reference_channel'] = header['reference_channel']

    if header['num_board_adc_channels'] > 0:
        result['board_adc_channels'] = header['board_adc_channels']

    if header['num_board_dac_channels'] > 0:
        result['board_dac_channels'] = header['board_dac_channels']

    if header['num_board_dig_in_channels'] > 0:
        result['board_dig_in_channels'] = header['board_dig_in_channels']

    if header['num_board_dig_out_channels'] > 0:
        result['board_dig_out_channels'] = header['board_dig_out_channels']

    return result


def print_header_summary(header):
    """Prints summary of contents of RHD header to console.
    """
    print('Found {} amplifier channel{}.'.format(
        header['num_amplifier_channels'],
        plural(header['num_amplifier_channels'])))
    if header['dc_amplifier_data_saved']:
        print('Found {} DC amplifier channel{}.'.format(
            header['num_amplifier_channels'],
            plural(header['num_amplifier_channels'])))
    print('Found {} board ADC channel{}.'.format(
        header['num_board_adc_channels'],
        plural(header['num_board_adc_channels'])))
    print('Found {} board DAC channel{}.'.format(
        header['num_board_dac_channels'],
        plural(header['num_board_dac_channels'])))
    print('Found {} board digital input channel{}.'.format(
        header['num_board_dig_in_channels'],
        plural(header['num_board_dig_in_channels'])))
    print('Found {} board digital output channel{}.'.format(
        header['num_board_dig_out_channels'],
        plural(header['num_board_dig_out_channels'])))
    print('')


def plural(number_of_items):
    """Utility function to pluralize words based on the number of items.
    """
    if number_of_items == 1:
        return ''
    return 's'


class UnrecognizedFileError(Exception):
    """Exception returned when reading a file as an RHS header yields an
    invalid magic number (indicating this is not an RHS header file).
    """


class UnknownChannelTypeError(Exception):
    """Exception returned when a channel field in RHS header does not have
    a recognized signal_type value. Accepted values are:
    0: amplifier channel
    1: aux input channel (RHD only, invalid for RHS)
    2: supply voltage channel (RHD only, invalid for RHS)
    3: board adc channel
    4: board dac channel
    5: dig in channel
    6: dig out channel
    """
