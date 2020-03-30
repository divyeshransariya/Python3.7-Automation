from airflow.utils import timezone
from airflow.utils.decorators import apply_defaults
from datetime import datetime,time,date
from airflow.sensors.base_sensor_operator import BaseSensorOperator 

class CustomTimeSensor(BaseSensorOperator):
    """
    Waits until the specified time of the day.

    :param target_time: time after which the job succeeds
    :type target_time: time (Which is absolute time)
    """
    template_fields = ('curr_date',)

    @apply_defaults
    def __init__(self, target_time, curr_date= '{{ next_ds }}', local_tz = None, *args, **kwargs):
        super(CustomTimeSensor, self).__init__(*args, **kwargs)
        self.target_time = target_time
        self.curr_date=curr_date
        self.local_tz=local_tz
        
    def poke(self, context):
        """
            First, we convert target_time into datetime.datetime from datetime.time (input target time)
            then, Convert target time in given timezone aware datetime
            if local_tz is not Specified then default timezone take as utc
        """
        year, month, day = map(int,self.curr_date.split('-'))
        curr_date = date(year, month, day)
        target_time = datetime.combine(curr_date, self.target_time)
        
        ## checking target_time is naive
        assert target_time.utcoffset() is None, "target time should be naive"

        ## convert Input time into time aware datetime object 
        #  if local_tz is None then convert default timezone take as UTC  
        if self.local_tz:
            target_time=timezone.make_aware(target_time, self.local_tz)
        else:
            target_time=timezone.make_aware(target_time)

        self.log.info('Checking if the time (%s) has come', target_time)
        return timezone.utcnow() > target_time