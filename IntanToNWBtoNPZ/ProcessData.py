# Adrian Foy September 2023

"""Module to process Intan data in preparation for conversion to NWB.
"""

import math

import numpy as np


def extract_digital_data(header, raw_data, extracted_data):
    """ Extract digital i/o from a 1D raw array to a 2D array with
    separate channels.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    raw_data :
        Populated 1D array from which channel-specific data must be extracted.
    extracted_data :
        Previously allocated 2D array to which extracted data is written.

    Returns
    -------
    None
    """
    # Apply channel-specific masks to raw digin data to determine each
    # channel's samples as 1 or 0.
    for channel in range(header['num_board_dig_in_channels']):
        channel_mask = 1 << (
            header['board_dig_in_channels'][channel]['native_order'])
        extracted_data[channel, :] = np.not_equal(
            np.bitwise_and(raw_data, channel_mask), 0)


def extract_stim_data(data):
    """ Extract raw stim data containing multiple fields in a 2D array of
    uint16 to multiple 2D arrays for each field.

    Parameters
    ----------
    data :
        Dict containing both previously read 'raw' data, and previously
        allocated data fields to which extracted data is written.

    Returns
    -------
    None
    """
    # Interpret 2^15 bit (compliance limit) as True or False.
    data['compliance_limit_data'] = (np.bitwise_and(
        data['stim_data_raw'], 32768) >= 1).astype(int)

    # Interpret 2^14 bit (charge recovery) as True or False.
    data['charge_recovery_data'] = (np.bitwise_and(
        data['stim_data_raw'], 16384) >= 1).astype(int)

    # Interpret 2^13 bit (amp settle) as True or False.
    data['amp_settle_data'] = (np.bitwise_and(
        data['stim_data_raw'], 8192) >= 1).astype(int)

    # Interpret x^8 bit (stim polarity) as +1 for 0_bit or -1 for 1_bit.
    data['stim_polarity'] = (1 - (2*(np.bitwise_and(
        data['stim_data_raw'], 256) >> 8))).astype(int)

    # Get least-significant 8 bits corresponding to the current amplitude.
    curr_amp = np.bitwise_and(data['stim_data_raw'], 255)

    # Multiply current amplitude by the correct sign.
    data['stim_data'] = curr_amp * data['stim_polarity']


def check_for_gaps(t_amplifier, previous_num_gaps, previous_timestamp,
                   chunk_idx):
    """ Check for gaps in timestamp data.

    Parameters
    ----------
    t_amplifier : numpy.ndarray
        1D numpy array containing previously read timestamp data.
    previous_num_gaps : int
        After this function call, how many gaps have been found.
    previous_timestamp : int
        Last timestamp of the previous chunk.
    chunk_idx : int
        Index of which chunk is currently being converted (if this is 0, the
        first chunk has no previous data to consult).

    Returns
    -------
    previous_timestamp : int
        Last timestamp of this chunk to pass along to the next chunk for
        continuity between chunks.
    num_gaps : int
        After this function call, how many gaps have been found.
    """
    # Check for gaps across this whole chunk.
    num_gaps = previous_num_gaps + np.sum(
        np.not_equal(t_amplifier[1:]-t_amplifier[:-1], 1))

    # Handle seam case between the previous chunk and this one.
    if chunk_idx > 0:
        if t_amplifier[0] - previous_timestamp != 1:
            num_gaps = num_gaps + 1

    # Save this chunk's last timestamp for the next iteration.
    previous_timestamp = t_amplifier[-1]

    return previous_timestamp, num_gaps


def scale(header, data, file_format):
    """ Scale data arrays from the read integer values to appropriate SI units.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    data : dict
        Dict with fields containing data that needs to be scaled.
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.

    Returns
    -------
    None
    """
    scale_timestamps(header, data)
    scale_data(header, data, file_format)


def scale_timestamps(header, data):
    """ Scale all timestamps arrays in data to seconds, with the correct
    sample rate for each signal type.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    data : dict
        Dict with fields containing data. In this case, timestamp data like
        data['t_amplifier'] can be written to.

    Returns
    -------
    None
    """
    # Divide int timestamp data by the sample rate in Hz to get timestamp data
    # in seconds.
    t_key = 't_amplifier' if header['filetype'] == 'rhd' else 't'
    base_timestamps = data[t_key] / header['sample_rate']

    # Amplifiers are sampled at the base sample rate, so all timestamps should
    # be included.
    data[t_key] = base_timestamps

    # Only for .rhd files are multiple timestamp vectors used.
    if header['filetype'] == 'rhs':
        return

    # Aux inputs are sampled 4x slower than the base sample rate, so every 4th
    # timestamp should be included.
    t_aux_range = range(0, len(base_timestamps), 4)
    data['t_aux_input'] = base_timestamps[t_aux_range]

    # Supply voltages are sampled 60x or 128x slower than the base sample rate,
    # so only one timestamp per data block should be included.
    t_supply_range = range(
        0, len(base_timestamps), header['num_samples_per_data_block'])
    data['t_supply_voltage'] = base_timestamps[t_supply_range]

    # Analog inputs are sampled at the base sample rate, so all timestamps
    # should be included.
    data['t_board_adc'] = base_timestamps

    # Digital inputs/outputs are sampled at the base sample rate, so all
    # timestamps should be included.
    data['t_dig'] = base_timestamps

    # Temp sensors are sampled at the same rate as supply voltages.
    data['t_temp_sensor'] = data['t_supply_voltage']


def scale_data(header, data, file_format):
    """ Scale data arrays from the read integer values to appropriate units.

    Parameters
    ----------
    header: dict
        Dict containing previously read header information.
    data : dict
        Dict with fields containing data that must be scaled.
    file_format : str
        Which file format this read is following - 'traditional',
        'per_signal_type', or 'per_channel'.

    Returns
    -------
    None
    """
    # Scale amplifier data to Volts.
    if file_format == 'traditional':
        data['amplifier_data'] = 1.95e-7 * (
            data['amplifier_data'].astype('float32') - 32768)
    else:
        data['amplifier_data'] = 1.95e-7 * (
            data['amplifier_data'].astype('float32'))

    if header['lowpass_present']:
        data['lowpass_data'] = 1.95e-7 * (
            data['lowpass_data'].astype('float32'))

    if header['highpass_present']:
        data['highpass_data'] = 1.95e-7 * (
            data['highpass_data'].astype('float32'))

    if header['filetype'] == 'rhd':

        # Scale aux input data to Volts.
        data['aux_input_data'] = 37.4e-6 * data['aux_input_data']

        # Scale supply voltage data to Volts.
        data['supply_voltage_data'] = 74.8e-6 * data['supply_voltage_data']

        # Scale temp sensor data to deg C.
        data['temp_sensor_data'] = data['temp_sensor_data'] / 100

        # Scale analog input data to Volts.
        if header['board_mode'] == 1:
            data['board_adc_data'] = 152.59e-6 * (
                data['board_adc_data'].astype(np.int32) - 32768)
        elif header['board_mode'] == 13:
            data['board_adc_data'] = 312.5e-6 * (
                data['board_adc_data'].astype(np.int32) - 32768)
        else:
            data['board_adc_data'] = 50.354e-6 * data['board_adc_data']

    else:
        # Scale stim data to Amps.
        data['stim_data'] = header['stim_step_size'] * data['stim_data']

        # If present, scale DC amp data to Volts.
        if header['dc_amplifier_data_saved']:
            data['dc_amplifier_data'] = -0.01923 * (
                data['dc_amplifier_data'].astype(np.int32) - 512)

        # Scale analog input data to Volts.
        data['board_adc_data'] = 312.5e-6 * (
            data['board_adc_data'].astype(np.int32) - 32768)
        data['board_dac_data'] = 312.5e-6 * (
            data['board_dac_data'].astype(np.int32) - 32768)


def process_wideband(header, chunk_idx, data, previous_samples):
    """ Process wideband data prior to final write, applying a notch filter
    if appropriate.

    Parameters
    ----------
    header : dict
        Dict containing previously read header information.
    chunk_idx : int
        Index of which chunk is currently being converted (if this is 0, the
        first chunk has no previous data to consult).
    data : dict
        Dict with fields containing data that must be processed.
    previous_samples : list
        List of last samples of previous chunk, used for allowing notch filter
        to be continuous across chunks.
    Returns
    -------
    wideband_filter_string :
        String describing how the wideband data has been filtered, used for
        writing to NWB later.
    previous_samples : list
        List of last samples of this chunk, used for allowing notch filter to
        be continuous across chunks.
    """
    wideband_filter_string = 'Wideband data'
    # If the software notch filter was selected during recording, apply the
    # same notch filter to amplifier data here.
    # But don't do this for v3.0+ files (from Intan RHX software) because RHX
    # saves notch-filtered data.
    if header['notch_filter_frequency'] > 0 and header['version']['major'] < 3:
        for channel in range(header['num_amplifier_channels']):
            continue_previous = not chunk_idx == 0
            data['amplifier_data'][channel, :] = notch_filter(
                data['amplifier_data'][channel, :],
                header['sample_rate'],
                header['notch_filter_frequency'],
                10,
                continue_previous,
                previous_samples[channel * 2],
                previous_samples[channel * 2 + 1])
            previous_samples[channel * 2] = data[
                'amplifier_data'][channel, -2]
            previous_samples[channel * 2 + 1] = data[
                'amplifier_data'][channel, -1]
        wideband_filter_string = (
            'Wideband data, filtered through a '
            + str(header['notch_filter_frequency'])
            + ' Hz IIR notch filter')
    return wideband_filter_string, previous_samples


def notch_filter(in_array, f_sample, f_notch, bandwidth, continue_previous,
                 second_to_last, last):
    """ Implement a notch filter (e.g., for 50 or 60 Hz) on input vector.

    Example:  If neural data was sampled at 30 kSamples/sec and you wish to
    implement a 60 Hz notch filter:
    out_array = notch_filter(in_array, 3000, 60, 10, false, None, None)

    Parameters
    ----------
    in_array : numpy.ndarray
        1D array containing unfiltered data that should have a notch filter
        applied to it.
    f_sample : float
        Sample rate of data (Hz or Samples/sec).
    f_notch : float or int
        Filter notch frequency (Hz).
    bandwidth : float or int
        Notch 3-dB bandwidth (Hz). A bandwidth of 10 Hz is recommended for
        50 or 60 Hz notch filters;
        narrower bandwidths lead to poor time-domain properties with an
        extended ringing response to transient disturbances.
    continue_previous : bool
        Whether this filter is continuous with earlier data, which should be
        stored in previous_samples.
    second_to_last : float
        Second to last sample used for continuous filtering if
        continue_previous is True.
    last : float
        Last sample used for continuous filtering if continue_previous is True.

    Returns
    -------
    out_array : numpy.ndarray
        1D array containing notch-filtered data.
    """
    t_step = 1.0/f_sample
    f_c = f_notch*t_step

    L = len(in_array)

    # Calculate IIR filter parameters.
    d = math.exp(-2.0*math.pi*(bandwidth/2.0)*t_step)
    b = (1.0 + d*d) * math.cos(2.0*math.pi*f_c)
    a0 = 1.0
    a1 = -b
    a2 = d*d
    a = (1.0 + d*d)/2.0
    b0 = 1.0
    b1 = -2.0 * math.cos(2.0*math.pi*f_c)
    b2 = 1.0

    out_array = np.zeros(len(in_array))
    if continue_previous:
        out_array[0] = second_to_last
        out_array[1] = last
    else:
        out_array[0] = in_array[0]
        out_array[1] = in_array[1]
    # (If filtering a continuous data stream, change out_array[0:1] to the
    #  previous final two values of out_array.)

    # Run filter.
    for i in range(2, L):
        out_array[i] = (a*b2*in_array[i-2]
                        + a*b1*in_array[i-1]
                        + a*b0*in_array[i]
                        - a2*out_array[i-2]
                        - a1*out_array[i-1])/a0

    return out_array
