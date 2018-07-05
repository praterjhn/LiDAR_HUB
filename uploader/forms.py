from django.forms import ClearableFileInput
from django.forms.utils import ErrorList
from django import forms
from .srs_choices import txsp_north, txsp_north_central, txsp_central, txsp_south_central, txsp_south

srs_choices = (
    (txsp_north, 'TXSP North FIPS 4201'),
    (txsp_north_central, 'TXSP North Central FIPS 4202'),
    (txsp_central, 'TXSP Central FIPS 4203'),
    (txsp_south_central, 'TXSP South Central FIPS 4204'),
    (txsp_south, 'TXSP South FIPS 4205'),
    ('', '------')
)


class UploadForm(forms.Form):
    name = forms.CharField(max_length=250,
                           label='Project Name',
                           required=True)
    file_data = forms.FileField(label='File',
                                widget=ClearableFileInput(attrs={'accept': '.las', 'multiple': True}),
                                required=True)
    srs = forms.ChoiceField(choices=srs_choices,
                            label='Spatial Reference', required=True)

    def clean(self):
        files = self.files.getlist('file_data')

        for item in files:
            if not str(item.name).endswith('.las'):
                self.add_error('las_file',
                               '{0} is not a LAS file'.format(item.name))

        return files


class MyErrorList(ErrorList):
    def __str__(self):
        return self.as_divs()

    def as_divs(self):
        if not self:
            return ''
        return '<div class="errorlist">%s</div>' % ''.join(['<div class="error">'
                                                            '<strong style="color: red">'
                                                            '<i class="fa fa-exclamation-circle"></i> %s '
                                                            '<i class="fa fa-exclamation-circle"></i>'
                                                            '</strong></div>' % e for e in self])
