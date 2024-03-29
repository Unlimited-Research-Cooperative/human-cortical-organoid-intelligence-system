#! /bin/env python
#
# Michael Gibson 27 April 2015
# Modified Zeke Arneodo Dec 2017
# Modified Adrian Foy Sep 2018

def data_to_result(header, data, data_present):
    """Moves the header and data (if present) into a common object."""
    
    result = {}
    result['t'] = data['t']
    
    stim_parameters = {}
    stim_parameters['stim_step_size'] = header['stim_step_size']
    stim_parameters['charge_recovery_current_limit'] = header['recovery_current_limit']
    stim_parameters['charge_recovery_target_voltage'] = header['recovery_target_voltage']
    stim_parameters['amp_settle_mode'] = header['amp_settle_mode']
    stim_parameters['charge_recovery_mode'] = header['charge_recovery_mode']
    result['stim_parameters'] = stim_parameters
    
    result['stim_data'] = data['stim_data']
    result['spike_triggers'] = header['spike_triggers']
    result['notes'] = header['notes']
    result['frequency_parameters'] = header['frequency_parameters']
    
    if header['dc_amplifier_data_saved']:
        result['dc_amplifier_data'] = data['dc_amplifier_data']
        
    if header['num_amplifier_channels'] > 0:
        if data_present:
            result['compliance_limit_data'] = data['compliance_limit_data']
            result['charge_recovery_data'] = data['charge_recovery_data']
            result['amp_settle_data'] = data['amp_settle_data']
    
    if header['num_board_dig_out_channels'] > 0:
        result['board_dig_out_channels'] = header['board_dig_out_channels']
        if data_present:
            result['board_dig_out_data'] = data['board_dig_out_data']
        
    if header['num_board_dig_in_channels'] > 0:
        result['board_dig_in_channels'] = header['board_dig_in_channels']
        if data_present:
            result['board_dig_in_data'] = data['board_dig_in_data']
        
    if header['num_board_dac_channels'] > 0:
        result['board_dac_channels'] = header['board_dac_channels']
        if data_present:
            result['board_dac_data'] = data['board_dac_data']
        
    if header['num_board_adc_channels'] > 0:
        result['board_adc_channels'] = header['board_adc_channels']
        if data_present:
            result['board_adc_data'] = data['board_adc_data']
            
    if header['num_amplifier_channels'] > 0:
        result['amplifier_channels'] = header['amplifier_channels']
        if data_present:
            result['amplifier_data'] = data['amplifier_data']
            
    return result