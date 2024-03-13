# Adrian Foy September 2023

"""Module to read data from .xlsx settings filename.
"""

import pandas as pd


def read_field(settings_filename, field_name, var_type='str'):
    """ Read the value matching the field_name from the .xlsx file in
    settings_filename. Technically, this looks for the 'SettingsSheet' sheet of
    the Excel file, and returns the value for the first partial match of the
    field_name in Column 0. This could cause confusion if the .xlsx sheet is
    customized and fields are renamed or reordered, but leaving it as is this
    should cause no problems.

    Parameters
    ----------
    settings_filename : str
        Name of settings file to load to get conversion settings. Should be a
        .xlsx file.
    field_name : str
        String of text to search the first coFlumn of the settings file for.
        This function finds the first row that contains this field_name as part
        of its text, so beware reordering, renaming, or abbreviating fields.
    var_type : str
        String describing the return value of this variable. This can be
        'bool', 'str', or 'int' and determines how this field is returned.

    Returns
    -------
    field_value : str or None
        User-editable field value accessed from settings .xlsx file. If this
        field was removed from the .xlsx file, or just didn't have a value,
        return None. Otherwise, return as a string (note even numeric values
        are returned as strings).
    """

    # Read the 'SettingsSheet' sheet of the specified .xlsx file into a
    # DataFrame.
    settings_file = pd.ExcelFile(settings_filename)
    df = settings_file.parse('SettingsSheet')

    # Get a DataFrame of the rows that contain, at least partially,
    # field_name in Column 0.
    df_of_matching_rows = df[df.iloc[:, 0].str.contains(field_name)]

    # If that DataFrame is empty, that field is missing, so return None.
    if df_of_matching_rows.empty:
        return None

    # Get a Series of the first matching row (possible that other rows follow,
    # those will be ignored).
    series_of_first_matching_row = df_of_matching_rows.iloc[0, :]

    # If the 2nd-column value of this Series is missing, just return None.
    if series_of_first_matching_row.hasnans:
        field_value = None

    # If the 2nd-column value of this Series is present, convert to a string.
    else:
        field_value_str = str(series_of_first_matching_row.array[1])
        # Convert to the correct data type depending on var_type.
        if var_type == 'bool':
            field_value = field_value_str.lower() == 'true'
        elif var_type == 'str':
            field_value = field_value_str
        elif var_type == 'int':
            field_value = int(field_value_str)
        else:
            print('Error. Unrecognized var_type argument: '
                  + var_type + ' in read_field() function')
            field_value = None

    return field_value
