# Adrian Foy September 2023

"""UI for conversion of Intan data files to NWB format.
"""

from datetime import datetime

import ipywidgets as widgets
from IPython.display import display
import pynwb

from ConvertIntanToNWB import convert_to_nwb


def main():
    """Main function that creates and displays UI.
    """
    ConverterUI()


class ConverterUI:
    """Class containing all widgets of converter UI.
    """
    def __init__(self):
        self.create_widgets()
        self.display_widgets()

    def create_widgets(self):
        """Creates all widgets of converter UI, and populates them with
        descriptions and default values.
        """
        self.settings_label = widgets.HTML(
            value='<b>Conversion Settings</b>')

        self.filename_label = widgets.Label(
            'File to convert:')
        self.filename_text = widgets.Text(
            value='example_intan_file.rhd')
        self.filename_text.observe(
            self.change_intan_filename_eventhandler,
            names='value')

        self.out_filename_label = widgets.Label(
            'Output filename (my_intan_file.nwb if left empty):')
        self.out_filename_text = widgets.Text(
            value='')

        self.text_layout = widgets.Layout(
            width='auto')
        self.manual_start_time_checkbox = widgets.Checkbox(
            description='Manual session start time',
            value=False,
            indent=False)
        self.manual_start_time_checkbox.observe(
            self.toggle_checkbox_eventhandler)
        self.manual_start_time_label = widgets.Label(
            value='If not manually specified, start time will be inferred '
            'from timestamp at end of filename.')
        self.manual_start_time_year = widgets.BoundedIntText(
            value=2022,
            min=1,
            max=3000,
            step=1,
            description='Year',
            layout=self.text_layout)
        self.manual_start_time_month = widgets.BoundedIntText(
            value=1,
            min=1,
            max=12,
            step=1,
            description='Month',
            layout=self.text_layout)
        self.manual_start_time_day = widgets.BoundedIntText(
            value=1,
            min=1,
            max=31,
            step=1,
            description='Day',
            layout=self.text_layout)
        self.manual_start_time_hour = widgets.BoundedIntText(
            value=0,
            min=0,
            max=23,
            step=1,
            description='Hour',
            layout=self.text_layout)
        self.manual_start_time_minute = widgets.BoundedIntText(
            value=0,
            min=0,
            max=59,
            step=1,
            description='Minute',
            layout=self.text_layout)
        self.manual_start_time_second = widgets.BoundedIntText(
            value=0,
            min=0,
            max=59,
            step=1,
            description='Second',
            layout=self.text_layout)

        self.manual_session_description_checkbox = widgets.Checkbox(
            description='Manual session description',
            value=False,
            indent=False)
        self.manual_session_description_checkbox.observe(
            self.toggle_checkbox_eventhandler)
        self.manual_session_description_label = widgets.Label(
            value='If not manually specified, description will be Note1 + '
            'Note2 + Note3 of the Intan file.')

        self.manual_session_description_text_label = widgets.Label(
            value='Session description')
        self.manual_session_description_text = widgets.Text(
            value='')

        self.subject_warning = widgets.HTML(
            value='<br>')
        self.subject_checkbox = widgets.Checkbox(
            description='Include subject metadata in NWB file',
            value=True,
            indent=False)
        self.subject_checkbox.observe(
            self.toggle_checkbox_eventhandler)

        self.label_layout = widgets.Layout(
            width='100px')
        self.age_label = widgets.Label(
            'Age',
            layout=self.label_layout)
        self.age = widgets.Text(
            placeholder='P90D')
        self.age_description = widgets.Label(
            'The age of the subject. The ISO 8601 Duration format is '
            'recommended.')

        self.description_label = widgets.Label(
            'Description',
            layout=self.label_layout)
        self.description = widgets.Text(
            placeholder='mouse A10')
        self.description_description = widgets.Label(
            'A description of the subject.')

        self.genotype_label = widgets.Label(
            'Genotype',
            layout=self.label_layout)
        self.genotype = widgets.Text(
            placeholder='Sst-IRES-Cre/wt;Ai32(RCL-ChR2(H134R)_EYFP)/wt')
        self.genotype_description = widgets.Label(
            'The genotype of the subject.')

        self.sex_label = widgets.Label(
            'Sex',
            layout=self.label_layout)
        self.sex = widgets.Text(
            placeholder='F')
        self.sex_description = widgets.Label(
            'The sex of the subject.')

        self.species_label = widgets.Label(
            'Species',
            layout=self.label_layout)
        self.species = widgets.Text(
            placeholder='Mus musculus')
        self.species_description = widgets.Label(
            'The species of the subject. The formal Latin binomal name '
            'is recommended.')

        self.id_label = widgets.Label(
            'Subject ID',
            layout=self.label_layout)
        self.subject_id = widgets.Text(
            placeholder='A10')
        self.id_description = widgets.Label(
            'A unique identifier for the subject.')

        self.weight_label = widgets.Label(
            'Weight (kg)',
            layout=self.label_layout)
        self.weight = widgets.FloatText(
            step=0.01)
        self.weight_description = widgets.Label(
            'The weight of the subject, in kilograms.')

        self.strain_label = widgets.Label(
            'Strain',
            layout=self.label_layout)
        self.strain = widgets.Text(placeholder='C57BL/6J')
        self.strain_description = widgets.Label('The strain of the subject.')

        self.dob_checkbox = widgets.Checkbox(
            description='Include date of birth',
            value=False,
            indent=False)
        self.dob_checkbox.observe(
            self.toggle_checkbox_eventhandler)
        self.dob_year = widgets.BoundedIntText(
            value=2022,
            min=1,
            max=3000,
            step=1,
            description='Year',
            layout=self.text_layout)
        self.dob_month = widgets.BoundedIntText(
            value=1,
            min=1,
            max=12,
            step=1,
            description='Month',
            layout=self.text_layout)
        self.dob_day = widgets.BoundedIntText(
            value=1,
            min=1,
            max=31,
            step=1,
            description='Day',
            layout=self.text_layout)

        self.compression_checkbox = widgets.Checkbox(
            description='Enable compression',
            value=True,
            indent=False)
        self.compression_checkbox.observe(
            self.toggle_checkbox_eventhandler)

        self.compression_slider = widgets.IntSlider(
            description='Level',
            min=0,
            max=9,
            step=1,
            value=4)

        self.blocks_per_chunk_label = widgets.Label(
            'Data blocks per chunk')
        self.blocks_per_chunk_text = widgets.BoundedIntText(
            min=1,
            max=100000,
            step=1,
            value=1000)

        self.lowpass_description_label = widgets.Label(
            'Lowpass filter description (filter order, type, cutoff '
            'frequency, etc.)')
        self.lowpass_description_text = widgets.Text(
            value='Unknown lowpass filtering process')

        self.highpass_description_label = widgets.Label(
            'Highpass filter description (filter order, type, '
            'cutoff frequency, etc.)')
        self.highpass_description_text = widgets.Text(
            value='Unknown highpass filtering process')

        self.merge_checkbox = widgets.Checkbox(
            description='Merge multiple contiguous files',
            value=False,
            indent=False)
        self.merge_checkbox.observe(
            self.toggle_checkbox_eventhandler)
        self.merge_label = widgets.Label(
            'If selected, this program will attempt to include data from '
            'all other traditional-format files in this directory.')

        self.load_settings_checkbox = widgets.Checkbox(
            description='Load conversion settings file',
            value=False,
            indent=False)
        self.load_settings_checkbox.observe(
            self.toggle_checkbox_eventhandler)
        self.load_settings_label = widgets.Label(
            'If selected, all settings from UI will be ignored.')
        self.load_settings_filename_text = widgets.Text(
            placeholder='Example_NWB_Conversion_Settings.xlsx')

        self.filename_row = widgets.HBox(
            [self.filename_label,
             self.filename_text])
        self.out_filename_row = widgets.HBox(
            [self.out_filename_label, self.out_filename_text])
        self.manual_start_time_row1 = widgets.HBox(
            [self.manual_start_time_checkbox,
             self.manual_start_time_label])
        self.manual_start_time_row2 = widgets.HBox(
            [self.manual_start_time_year,
             self.manual_start_time_month,
             self.manual_start_time_day,
             self.manual_start_time_hour,
             self.manual_start_time_minute,
             self.manual_start_time_second])
        self.manual_session_description_row1 = widgets.HBox(
            [self.manual_session_description_checkbox,
             self.manual_session_description_label])
        self.manual_session_description_row2 = widgets.HBox(
            [self.manual_session_description_text_label,
             self.manual_session_description_text])

        self.age_row = widgets.HBox(
            [self.age_label,
             self.age,
             self.age_description])
        self.description_row = widgets.HBox(
            [self.description_label,
             self.description,
             self.description_description])
        self.genotype_row = widgets.HBox(
            [self.genotype_label,
             self.genotype,
             self.genotype_description])
        self.sex_row = widgets.HBox(
            [self.sex_label,
             self.sex,
             self.sex_description])
        self.species_row = widgets.HBox(
            [self.species_label,
             self.species,
             self.species_description])
        self.id_row = widgets.HBox(
            [self.id_label,
             self.subject_id,
             self.id_description])
        self.weight_row = widgets.HBox(
            [self.weight_label,
             self.weight,
             self.weight_description])
        self.strain_row = widgets.HBox(
            [self.strain_label,
             self.strain,
             self.strain_description])
        self.dob_row = widgets.HBox(
            [self.dob_checkbox,
             self.dob_year,
             self.dob_month,
             self.dob_day])

        self.subject_column = widgets.VBox(
            [self.subject_warning,
             self.subject_checkbox,
             self.age_row,
             self.description_row,
             self.genotype_row,
             self.sex_row,
             self.species_row,
             self.id_row,
             self.weight_row,
             self.strain_row,
             self.dob_row])
        self.subject_accordion = widgets.Accordion(
            children=[self.subject_column],
            selected_index=0)
        self.subject_accordion.set_title(
            0,
            'Subject Metadata')

        self.blocks_per_chunk_row = widgets.HBox(
            [self.blocks_per_chunk_label,
             self.blocks_per_chunk_text])
        self.compression_row = widgets.HBox(
            [self.compression_checkbox,
             self.compression_slider])
        self.lowpass_row = widgets.HBox(
            [self.lowpass_description_label,
             self.lowpass_description_text])
        self.highpass_row = widgets.HBox(
            [self.highpass_description_label,
             self.highpass_description_text])
        self.merge_row = widgets.HBox(
            [self.merge_checkbox,
             self.merge_label])
        self.load_settings_row = widgets.HBox(
            [self.load_settings_checkbox,
             self.load_settings_label,
             self.load_settings_filename_text])
        self.advanced_column = widgets.VBox(
            [self.blocks_per_chunk_row,
             self.compression_row,
             self.lowpass_row,
             self.highpass_row,
             self.merge_row,
             self.load_settings_row])

        self.begin_button = widgets.Button(
            description='Begin Conversion')
        self.begin_button.on_click(
            self.begin_eventhandler)

        self.advanced_accordion = widgets.Accordion(
            children=[self.advanced_column],
            selected_index=None)
        self.advanced_accordion.set_title(
            0,
            'Advanced Settings')

    def display_widgets(self):
        """ Display all widgets and set them to the correct initial
        'disable' state.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        # Display all widgets.
        display(self.settings_label)
        display(self.filename_row)
        display(self.out_filename_row)
        display(self.manual_session_description_row1)
        display(self.manual_session_description_row2)
        display(self.manual_start_time_row1)
        display(self.manual_start_time_row2)
        display(self.subject_accordion)
        display(self.advanced_accordion)
        display(self.begin_button)

        # Update all widgets to correct initial 'disable' state.
        self.update_widgets()

    def toggle_checkbox_eventhandler(self, event):
        """ Callback function for when a checkbox is toggled
        that updates all widgets.

        Parameters
        ----------
        event : traitlets.utils.bunch.Bunch
            Information about the event that triggered this callback function.

        Returns
        -------
        None
        """
        # Ignore events that are not a change of value.
        if not (event.name == 'value' and event.type == 'change'):
            return

        # If the 'Load Conversion Settings File' checkbox is ticked,
        # determine if all UI elements should be disabled.
        if event.owner.description == 'Load conversion settings file':
            if event.owner.value:
                self.update_widgets(
                    global_disable=True,
                    exception_for_load_settings_widgets=True)
                return

        self.update_widgets()

    def change_intan_filename_eventhandler(self, obj):
        """ Callback function for when the user changes the content of the
        Intan file name field. Take the contents of the filename (minus the
        last 4 characters for .rhd or .rhs), add the .nwb suffix, and display
        the default output filename for when the output file name field is
        left empty.

        Parameters
        ----------
        obj : traitlets.utils.bunch.Bunch
            Information about the object that triggered this callback function.

        Returns
        -------
        None
        """
        _ = obj  # obj can be accessed but is unused.
        intan_filename = self.filename_text.value
        auto_detect_name = intan_filename[:-4] + '.nwb'
        self.out_filename_label.value = (
            'Output filename (' + auto_detect_name + ' if left empty):')

    def begin_eventhandler(self, obj):
        """ Callback function for when the user begins conversion.
        Disable all widgets, get subject and manual start time info from UI,
        and begin conversion. When conversion ends, update all widgets to
        their proper 'disable' state.

        Parameters
        ----------
        obj : ipywidgets.widgets.widget_button.Button
            Button that began this conversion.

        Returns
        -------
        None
        """
        _ = obj  # obj can be accessed but is unused.
        # If settings file is loaded, just pass NWB conversion the filename.
        if self.load_settings_checkbox.value:

            # Disable all widgets (including load settings widgets)
            # during conversion.
            self.update_widgets(global_disable=True)

            # Convert to NWB.
            convert_to_nwb(
                settings_filename=self.load_settings_filename_text.value)

            # Update widgets to their proper disable state
            # (all but load settings disabled).
            self.update_widgets(
                global_disable=True,
                exception_for_load_settings_widgets=True)

            return

        # Otherwise, get NWB settings from UI and pass these to NWB conversion.
        # Check if specified file ends with .rhd or .rhs.
        # If not, give an explanatory message and return.
        if (self.filename_text.value[-3:] != 'rhd'
                and self.filename_text.value[-3:] != 'rhs'):
            print('Conversion canceled. '
                  'Please select an rhd or rhs file to convert.')
            print('For traditional file format, '
                  'please specify the data file itself.')
            print('For other file formats, please specify the header file '
                  '(dat files in this directory will be included '
                  'in the conversion).')
            return

        # Global disable all widgets during conversion.
        self.update_widgets(global_disable=True)

        # Gather subject and manual start time info from UI.
        subject = self.get_subject()
        manual_start_time = self.get_manual_start_time()

        # Gather NWB output file name from UI.
        nwb_filename = None
        if self.out_filename_text.value != '':
            nwb_filename = self.out_filename_text.value

        session_description = None
        if self.manual_session_description_checkbox.value:
            session_description = self.manual_session_description_text.value

        convert_to_nwb(
            intan_filename=self.filename_text.value,
            nwb_filename=nwb_filename,
            session_description=session_description,
            blocks_per_chunk=self.blocks_per_chunk_text.value,
            use_compression=self.compression_checkbox.value,
            compression_level=self.compression_slider.value,
            lowpass_description=self.lowpass_description_text.value,
            highpass_description=self.highpass_description_text.value,
            merge_files=self.merge_checkbox.value,
            subject=subject,
            manual_start_time=manual_start_time)

        # After conversion finished,
        # update widgets to their proper 'disable' state.
        self.update_widgets()

    def update_widgets(self, global_disable=False,
                       exception_for_load_settings_widgets=False):
        """ Update all widgets, checking each group for the proper logic to
        determine their 'disable' state. If global_disable is True, then
        disable all widgets.

        Parameters
        ----------
        global_disable :
            Whether all widgets should globally be disabled.
        exception_for_load_settings_widgets :
            Whether there should be an exception forwidgets related to
            loading settings.

        Returns
        -------
        None
        """
        # Update all groups of widgets.
        self.update_filename(global_disable)
        self.update_manual_start_time(global_disable)
        self.update_manual_session_description(global_disable)
        self.update_subject(global_disable)
        self.update_dob(global_disable)
        self.update_compression(global_disable)
        self.update_filter_descriptions(global_disable)
        self.update_merge(global_disable)
        self.update_blocks_per_chunk(global_disable)
        self.update_load_conversion_settings(
            global_disable, exception_for_load_settings_widgets)

    def update_filename(self, global_disable=False):
        """ Update filename widget, only disabling it if widgets
        are globally disabled.

        Parameters
        ----------
        global_disable :
            Whether all widgets should globally be disabled.

        Returns
        -------
        None
        """
        # Disable filename text if global_disable is True.
        self.filename_text.disabled = global_disable

    def update_manual_start_time(self, global_disable=False):
        """ Update manual start time widgets, disabling them depending
        on checkbox state or if widgets are globally disabled.

        Parameters
        ----------
        global_disable :
            Whether all widgets should globally be disabled.

        Returns
        -------
        None
        """
        # Disable manual start time widgets for global disable, or if manual
        # start time checkbox is unchecked.
        disable = not self.manual_start_time_checkbox.value or global_disable
        self.manual_start_time_year.disabled = disable
        self.manual_start_time_month.disabled = disable
        self.manual_start_time_day.disabled = disable
        self.manual_start_time_hour.disabled = disable
        self.manual_start_time_minute.disabled = disable
        self.manual_start_time_second.disabled = disable

        # Disable manual start time checkbox for global disable.
        self.manual_start_time_checkbox.disabled = global_disable

    def update_manual_session_description(self, global_disable=False):
        """ Update manual session description widgets, disabling them
        depending on checkbox state or if widgets are globally disabled.

        Parameters
        ----------
        global_disable :
            Whether all widgets should globally be disabled.

        Returns
        -------
        None
        """
        # Disable manual session description widgets for global disable,
        # or if manual session description checkbox is unchecked.
        disable = (not self.manual_session_description_checkbox.value
                   or global_disable)
        self.manual_session_description_text.disabled = disable

        # Disable manual session description checkbox for global disable.
        self.manual_session_description_checkbox.disabled = global_disable

    def update_dob(self, global_disable=False):
        """ Update date-of-birth widgets, disabling them depending on
        checkbox states or if widgets are globally disabled.

        Parameters
        ----------
        global_disable :
            Whether all widgets should globally be disabled.

        Returns
        -------
        None
        """
        # Disable dob widgets for global disable, or if subject checkbox
        # is unchecked, or if dob checkbox is unchecked.
        disable = (not self.dob_checkbox.value
                   or not self.subject_checkbox.value
                   or global_disable)
        self.dob_year.disabled = disable
        self.dob_month.disabled = disable
        self.dob_day.disabled = disable

        # Disable dob checkbox for global disable,
        # or if subject checkbox is unchecked.
        self.dob_checkbox.disabled = (not self.subject_checkbox.value
                                      or global_disable)

    def update_compression(self, global_disable=False):
        """ Update compression widgets, disabling them based on checkbox state
        or if widgets are globally disabled.

        Parameters
        ----------
        global_disable :
            Whether all widgets should globally be disabled.

        Returns
        -------
        None
        """
        # Disable compression slider for global disable,
        # or if compression checkbox is unchecked.
        self.compression_slider.disabled = (not self.compression_checkbox.value
                                            or global_disable)

        # Disable compression checkbox for global disable.
        self.compression_checkbox.disabled = global_disable

    def update_filter_descriptions(self, global_disable=False):
        """ Update filter description widgets, disabling them
        if widgets are globally disabled.

        Parameters
        ----------
        global_disable :
            Whether all widgets should globally be disabled.

        Returns
        -------
        None
        """
        # Disable lowpass and highpass description text widgets
        # for global disable.
        self.lowpass_description_text.disabled = global_disable
        self.highpass_description_text.disabled = global_disable

    def update_merge(self, global_disable=False):
        """ Update merge widget, disabling it if widgets are globally disabled.

        Parameters
        ----------
        global_disable :
            Whether all widgets should globally be disabled.

        Returns
        -------
        None
        """
        # Disable merge checkbox widget for global disable.
        self.merge_checkbox.disabled = global_disable

    def update_blocks_per_chunk(self, global_disable=False):
        """ Update blocks-per-chunk widget,
        disabling it if widgets are globally disabled.

        Parameters
        ----------
        global_disable :
            Whether all widgets should globally be disabled.

        Returns
        -------
        None
        """
        # Disable blocks per chunk text for global disable.
        self.blocks_per_chunk_text.disabled = global_disable

    def update_load_conversion_settings(
            self,
            global_disable=False,
            exception_for_load_settings_widgets=False):
        """ Update load-conversion-settings widgets,
        disabling them if widgets are globally disabled.

        Parameters
        ----------
        global_disable :
            Whether all widgets should globally be disabled.
        exception_for_load_settings_widgets:
            Whether these widgets should be exempt from global disable
            because they're related to loading settings.

        Returns
        -------
        None
        """
        if global_disable and not exception_for_load_settings_widgets:
            self.load_settings_checkbox.disabled = True
            self.load_settings_filename_text.disabled = True

        else:
            self.load_settings_checkbox.disabled = False
            self.load_settings_filename_text.disabled = False

    def update_subject(self, global_disable=False):
        """ Update subject widgets, disabling them based on checkbox state
        or if widgets are globally disabled. Also, update subject warning
        based on checkbox state.

        Parameters
        ----------
        global_disable :
            Whether all widgets should globally be disabled.

        Returns
        -------
        None
        """
        # Disable subject widgets for global disable,
        # or if subject checkbox is unchecked.
        disable = not self.subject_checkbox.value or global_disable
        self.age.disabled = disable
        self.description.disabled = disable
        self.genotype.disabled = disable
        self.sex.disabled = disable
        self.species.disabled = disable
        self.subject_id.disabled = disable
        self.weight.disabled = disable
        self.dob_checkbox.disabled = disable
        self.strain.disabled = disable

        # Disable subject checkbox for global disable.
        self.subject_checkbox.disabled = global_disable

        # Populate subject warning based on subject checkbox.
        if self.subject_checkbox.value:
            # Set subject warning to a simple Line Break element,
            # so that it only takes up space.
            self.subject_warning.value = '<br>'
        else:
            # Set subject warning to red text describing DANDI's
            # need for subject metadata.
            self.subject_warning.value = (
                '<p style="color:red">Warning: '
                'Please note that the DANDI archive requires subject metadata.'
                ' Not including this will result in an NWB file that is '
                'ineligible for the DANDI archive.</p>')

        self.update_dob(global_disable)

    def get_subject(self):
        """ Get an NWB Subject object from the information
        currently present in the UI.

        Parameters
        ----------
        None

        Returns
        -------
        pynwb.file.Subject
            Subject populated with data based on current UI values.
        """
        # If subject checkbox is checked, get subject.
        if self.subject_checkbox.value:
            # If date of birth checkbox is checked,
            # get date of birth as datetime.
            if self.dob_checkbox.value:
                date_of_birth = datetime(
                    self.dob_year.value,
                    self.dob_month.value,
                    self.dob_day.value,
                    tzinfo=datetime.tzlocal())

            # If date of birth checkbox is unchecked, don't get date of birth.
            else:
                date_of_birth = None

            # Populate subject with current values.
            subject = pynwb.file.Subject(age=self.age.value,
                                         description=self.description.value,
                                         genotype=self.genotype.value,
                                         sex=self.sex.value,
                                         species=self.species.value,
                                         subject_id=self.subject_id.value,
                                         weight=self.weight.value,
                                         date_of_birth=date_of_birth,
                                         strain=self.strain.value)

        # If subject checkbox is unchecked, don't get subject.
        else:
            subject = None

        return subject

    def get_manual_start_time(self):
        """ Get a datetime object for the manual session start time from
        the information currently present in the UI.

        Parameters
        ----------
        None

        Returns
        -------
        manual_start_time : datetime.datetime
            Datetime populated based on current UI values.
        """
        # If manual start time checkbox is checked,
        # get manual start time as datetime.
        if self.manual_start_time_checkbox.value:

            # Populate manual start time with current values
            manual_start_time = datetime(
                self.manual_start_time_year.value,
                self.manual_start_time_month.value,
                self.manual_start_time_day.value,
                self.manual_start_time_hour.value,
                self.manual_start_time_minute.value,
                self.manual_start_time_second.value,
                tzinfo=datetime.tzlocal())

        # If manual start time checkbox is unchecked,
        # don't get manual start time.
        else:
            manual_start_time = None

        return manual_start_time


if __name__ == "__main__":
    main()
