from django.contrib import admin
from . import models

admin.site.register(models.Course)
admin.site.register(models.Subscription)
admin.site.register(models.Lesson)
admin.site.register(models.Question)
admin.site.register(models.ClassExecution)
admin.site.register(models.Answer)
