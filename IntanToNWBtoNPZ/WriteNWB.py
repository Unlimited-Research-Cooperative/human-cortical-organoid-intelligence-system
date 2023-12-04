# Adrian Foy September 2023

"""Module to write data imported from Intan into NWB format.
"""

from hdmf.backends.hdf5.h5_utils import H5DataIO
import numpy as np


class WrappedData:
    """Class for storing wrapped data arrays.
    """

    def __init__(self):
        self.t = None
        self.t_lowpass = None
        self.t_supply_voltage = None
        self.t_aux_input = None
        self.data_amplifier = None
        self.data_dc_amplifier = None
        self.data_lowpass = None
        self.data_highpass = None
        self.data_stim = None
        self.data_board_adc = None
        self.data_board_dac = None
        self.data_board_dig_in = None
        self.data_board_dig_out = None
        self.data_amp_settle = None
        self.data_charge_recovery = None
        self.data_compliance_limit = None
        self.data_aux_in = None
        self.data_supply_voltage = None
        self.data_temp = None


def create_intan_device(nwbfile, header):
    """ Create 'device' object for the Intan system that the data
    was acquired with.

    Parameters
    ----------
    nwbfile : pynwb.file.NWBFile
        Previously created NWB file that should contain this device.
    header : dict
        Dict containing previously read header information.

    Returns
    -------
    pynwb.device.Device
        Created NWB device representing Intan system.
    """
    intan_device_name = 'Unknown Intan System'
    board_mode = (str(header['board_mode']) if header['filetype'] == 'rhd'
                  else str(header['eval_board_mode']))
    intan_device_description = (
        'Unrecognized system that generated an .' + header['filetype']
        + ' file with a board mode of ' + board_mode)
    if header['filetype'] == 'rhd':
        if header['board_mode'] == 0:
            intan_device_name = 'Intan USB Interface Board'
            intan_device_description = (
                '256-channel RHD2000 USB Interface Board, part number C3100')
        elif header['board_mode'] == 13:
            intan_device_name = 'Intan Recording Controller'
            intan_device_description = (
                '512-channel or 1024-channel RHD2000 Recording Controller, '
                'part number C3004 or C3008'
            )
    else:
        intan_device_name = 'Intan StimulationRecording Controller'
        intan_device_description = (
            '128-channel RHS2000 StimulationRecording Controller, '
            'part number M4200')

    intan_device_description += (
        '. File version ' + str(header['version']['major']) + '.'
        + str(header['version']['minor']))
    return nwbfile.create_device(name=intan_device_name,
                                 description=intan_device_description,
                                 manufacturer='Intan Technologies')


def create_electrode_table_region(nwbfile, header, intan_device):
    """ Create 'electrode table region' object for the electrodes that
    the data was acquired with.

    Parameters
    ----------
    nwbfile : pynwb.file.NWBFile
        Previously created NWB file that should contain this
        electrode table region.
    header : dict
        Dict containing previously read header information
    intan_device : pynwb.device.Device
        Previously created NWB device representing Intan system

    Returns
    -------
    electrode_table_region : hdmf.common.table.DynamicTableRegion
        Electrode table region for the electrodes that the
        data was acquired with.
    """
    # Create an electrode group for each port
    if header['num_amplifier_channels'] > 0:
        nwbfile.add_electrode_column(
            name='imp_phase',
            description='phase (in degrees) of complex impedance '
            'of this channel')
        nwbfile.add_electrode_column(
            name='native_channel_name',
            description='native, uneditable name (for example, A-000)'
            'of this channel')
        nwbfile.add_electrode_column(
            name='custom_channel_name',
            description='custom, user-editable name of this channel')
        created_electrode_groups = {}

    for channel in range(header['num_amplifier_channels']):
        group_name = 'Intan ' + \
            header['amplifier_channels'][channel]['port_name'] + \
            ' electrode group'
        if group_name not in created_electrode_groups:
            electrode_group = nwbfile.create_electrode_group(
                name=group_name,
                description='description',
                location='location',
                device=intan_device)
            created_electrode_groups[group_name] = electrode_group

    # Create an electrode for each channel,
    # and associate it with it's port's group.
    for channel in range(header['num_amplifier_channels']):
        this_channel_struct = header['amplifier_channels'][channel]
        custom_channel_name = this_channel_struct['custom_channel_name']
        group_name = 'Intan ' + \
            this_channel_struct['port_name'] + ' electrode group'
        # Apparently this description is unused - how to give channel name?
        _ = 'electrode for channel ' + custom_channel_name
        location = 'none'
        nwbfile.add_electrode(
            id=channel,
            x=0.0,
            y=0.0,
            z=0.0,
            imp=this_channel_struct['electrode_impedance_magnitude'],
            imp_phase=this_channel_struct['electrode_impedance_phase'],
            native_channel_name=this_channel_struct['native_channel_name'],
            custom_channel_name=this_channel_struct['custom_channel_name'],
            location=location,
            filtering='none',
            group=created_electrode_groups[group_name])

    # If there are any amplifier channels, create this region
    if header['num_amplifier_channels'] > 0:
        electrode_table_region = nwbfile.create_electrode_table_region(
            list(range(0, header['num_amplifier_channels'])),
            'Intan electrode table region')
    else:
        electrode_table_region = None

    return electrode_table_region


def append_to_dataset(dataset, data_to_add):
    """ Append data_to_add to dataset, along the first axis.

    Parameters
    ----------
    dataset : h5py._hl.dataset.Dataset
        h5py dataset to be appended to
    data_to_add : hdmf.backends.hdf5.h5_utils.H5DataIO
        H5DataIO object containing data to be added

    Returns
    -------
    None
    """
    # Increase the dataset's size to handle this new chunk of data
    dataset.resize(dataset.shape[0] + data_to_add.shape[0], axis=0)

    # Write this chunk to the dataset
    dataset[-data_to_add.shape[0]:] = data_to_add


def get_compression_settings(use_compression, compression_level):
    """ Get compression settings to pass to H5DataIO functions.

    Parameters
    ----------
    use_compression : bool
        Whether compression is to be used for written NWB data.
    compression_level : int
        What level of compression is to be applied to written NWB data.

    Returns
    -------
    compression : str
        What type of compression is to be used for written NWB data,
        for example, 'gzip'
    compression_opts : int
        Options for compression. For gzip, what level of compression
        is to be applied to written NWB data.
    """
    if use_compression is False:
        compression = False
        compression_opts = None
    else:
        compression = 'gzip'
        compression_opts = compression_level

    return (compression, compression_opts)


def wrap_data_1D(data_array, samples_this_chunk, total_num_samples,
                 compression_settings):
    """ Wrap generic 1D data in a H5DataIO object

    Parameters
    ----------
    data_array : numpy.ndarray
        Array containing data that needs wrapping
    samples_this_chunk : int
        Number of samples in this chunk
    total_num_samples : int
        Total number of samples to write in this conversion
    compression_settings : tuple
        Tuple containing 'compression' and 'compression_opts'

    Returns
    -------
    d : hdmf.backends.hdf5.h5_utils.H5DataIO
        Wrapped H5DataIO object for this data
    """
    d = H5DataIO(data=data_array,
                 chunks=(samples_this_chunk,),
                 maxshape=(total_num_samples,),
                 compression=compression_settings[0],
                 compression_opts=compression_settings[1])
    return d


def wrap_data_2D(data_array, samples_this_chunk, total_num_samples,
                 num_channels, compression_settings):
    """ Wrap generic 2D data in a H5DataIO object

    Parameters
    ----------
    data_array :
        Array containing data that needs wrapping
    samples_this_chunk : int
        Number of samples in this chunk
    total_num_samples : int
        Total number of samples to write in this conversion
    compression_settings : tuple
        Tuple containing 'compression' and 'compression_opts'

    Returns
    -------
    d = hdmf.backends.hdf5.h5_utils.H5DataIO
        Wrapped H5DataIO object for this data
    """
    d = H5DataIO(data=np.array(data_array).T,
                 chunks=(samples_this_chunk, num_channels),
                 maxshape=(total_num_samples, num_channels),
                 compression=compression_settings[0],
                 compression_opts=compression_settings[1])
    return d


def wrap_data_arrays(header, data, t_key, amp_samples_this_chunk,
                     total_num_amp_samples, use_compression,
                     compression_level):
    """TODO wrap_data_arrays
    """
    wrapped_data = WrappedData()

    # Determine compression settings to pass to H5DataIO functions
    compression_settings = get_compression_settings(
        use_compression, compression_level)

    wrapped_data.t = wrap_data_1D(
        data_array=data[t_key],
        samples_this_chunk=amp_samples_this_chunk,
        total_num_samples=total_num_amp_samples,
        compression_settings=compression_settings)

    if header['lowpass_present']:
        wrapped_data.t_lowpass = wrap_data_1D(
            data_array=data[t_key][0::header['lowpass_downsample_factor']],
            samples_this_chunk=int(
                amp_samples_this_chunk / header['lowpass_downsample_factor']),
            total_num_samples=int(
                total_num_amp_samples / header['lowpass_downsample_factor']),
            compression_settings=compression_settings)

    if header['num_amplifier_channels'] > 0:
        wrapped_data.data_amplifier = wrap_data_2D(
            data_array=data['amplifier_data'],
            samples_this_chunk=amp_samples_this_chunk,
            total_num_samples=total_num_amp_samples,
            num_channels=header['num_amplifier_channels'],
            compression_settings=compression_settings)

        if header['lowpass_present']:
            wrapped_data.data_lowpass = wrap_data_2D(
                data_array=data['lowpass_data'],
                samples_this_chunk=amp_samples_this_chunk,
                total_num_samples=total_num_amp_samples,
                num_channels=header['num_amplifier_channels'],
                compression_settings=compression_settings)

        if header['highpass_present']:
            wrapped_data.data_highpass = wrap_data_2D(
                data_array=data['highpass_data'],
                samples_this_chunk=amp_samples_this_chunk,
                total_num_samples=total_num_amp_samples,
                num_channels=header['num_amplifier_channels'],
                compression_settings=compression_settings)

    if header['num_board_adc_channels'] > 0:
        wrapped_data.data_board_adc = wrap_data_2D(
            data_array=data['board_adc_data'],
            samples_this_chunk=amp_samples_this_chunk,
            total_num_samples=total_num_amp_samples,
            num_channels=header['num_board_adc_channels'],
            compression_settings=compression_settings)

    if header['num_board_dig_in_channels'] > 0:
        wrapped_data.data_board_dig_in = wrap_data_2D(
            data_array=data['board_dig_in_data'],
            samples_this_chunk=amp_samples_this_chunk,
            total_num_samples=total_num_amp_samples,
            num_channels=header['num_board_dig_in_channels'],
            compression_settings=compression_settings)

    if header['num_board_dig_out_channels'] > 0:
        wrapped_data.data_board_dig_out = wrap_data_2D(
            data_array=data['board_dig_out_data'],
            samples_this_chunk=amp_samples_this_chunk,
            total_num_samples=total_num_amp_samples,
            num_channels=header['num_board_dig_out_channels'],
            compression_settings=compression_settings)

    if header['filetype'] == 'rhd':

        wrapped_data.t_supply_voltage = wrap_data_1D(
            data_array=data[t_key][0::header['num_samples_per_data_block']],
            samples_this_chunk=int(
                amp_samples_this_chunk / header['num_samples_per_data_block']),
            total_num_samples=int(
                total_num_amp_samples
                / header['num_samples_per_data_block']),
            compression_settings=compression_settings)

        if header['num_aux_input_channels'] > 0:
            wrapped_data.data_aux_in = wrap_data_2D(
                data_array=data['aux_input_data'],
                samples_this_chunk=int(amp_samples_this_chunk / 4),
                total_num_samples=int(total_num_amp_samples / 4),
                num_channels=header['num_aux_input_channels'],
                compression_settings=compression_settings)
            wrapped_data.t_aux_input = wrap_data_1D(
                data_array=data['t_aux_input'],
                samples_this_chunk=int(amp_samples_this_chunk / 4),
                total_num_samples=int(total_num_amp_samples / 4),
                compression_settings=compression_settings)

        if header['num_supply_voltage_channels'] > 0:
            wrapped_data.data_supply_voltage = wrap_data_2D(
                data_array=data['supply_voltage_data'],
                samples_this_chunk=int(
                    amp_samples_this_chunk
                    / header['num_samples_per_data_block']),
                total_num_samples=int(
                    total_num_amp_samples
                    / header['num_samples_per_data_block']),
                num_channels=header['num_supply_voltage_channels'],
                compression_settings=compression_settings)

        if header['num_temp_sensor_channels'] > 0:
            wrapped_data.data_temp = wrap_data_2D(
                data_array=data['temp_sensor_data'],
                samples_this_chunk=int(
                    amp_samples_this_chunk
                    / header['num_samples_per_data_block']),
                total_num_samples=int(
                    total_num_amp_samples
                    / header['num_samples_per_data_block']),
                num_channels=header['num_temp_sensor_channels'],
                compression_settings=compression_settings)

    else:
        if header['dc_amplifier_data_saved']:
            wrapped_data.data_dc_amplifier = wrap_data_2D(
                data_array=data['dc_amplifier_data'],
                samples_this_chunk=amp_samples_this_chunk,
                total_num_samples=total_num_amp_samples,
                num_channels=header['num_amplifier_channels'],
                compression_settings=compression_settings)

        wrapped_data.data_amp_settle = wrap_data_2D(
            data_array=data['amp_settle_data'],
            samples_this_chunk=amp_samples_this_chunk,
            total_num_samples=total_num_amp_samples,
            num_channels=header['num_amplifier_channels'],
            compression_settings=compression_settings)

        wrapped_data.data_charge_recovery = wrap_data_2D(
            data_array=data['charge_recovery_data'],
            samples_this_chunk=amp_samples_this_chunk,
            total_num_samples=total_num_amp_samples,
            num_channels=header['num_amplifier_channels'],
            compression_settings=compression_settings)

        wrapped_data.data_compliance_limit = wrap_data_2D(
            data_array=data['compliance_limit_data'],
            samples_this_chunk=amp_samples_this_chunk,
            total_num_samples=total_num_amp_samples,
            num_channels=header['num_amplifier_channels'],
            compression_settings=compression_settings)

        wrapped_data.data_stim = wrap_data_2D(
            data_array=data['stim_data'],
            samples_this_chunk=amp_samples_this_chunk,
            total_num_samples=total_num_amp_samples,
            num_channels=header['num_amplifier_channels'],
            compression_settings=compression_settings)

        if header['num_board_dac_channels'] > 0:
            wrapped_data.data_board_dac = wrap_data_2D(
                data_array=data['board_dac_data'],
                samples_this_chunk=amp_samples_this_chunk,
                total_num_samples=total_num_amp_samples,
                num_channels=header['num_board_dac_channels'],
                compression_settings=compression_settings)

    return wrapped_data
