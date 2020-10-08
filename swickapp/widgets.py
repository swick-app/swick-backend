from django.forms import DateTimeInput

class DateTimePickerInput(DateTimeInput):
    template_name = 'widgets/datetimepicker.html'
