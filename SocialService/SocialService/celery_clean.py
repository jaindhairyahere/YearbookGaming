from django_celery_beat.models import *

models = [ClockedSchedule, IntervalSchedule, CrontabSchedule, SolarSchedule, PeriodicTasks, PeriodicTask]

for model in models:
    model.objects.all().delete()