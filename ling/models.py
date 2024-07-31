from django.db import models
from django.contrib.auth.models import User


class Course(models.Model):
    name = models.CharField(max_length=30)
    image = models.ImageField(upload_to='static/courses/', null=True)


class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    description = models.CharField(max_length=200)
    image = models.ImageField(upload_to='static/lessons/', null=True)
    question_number = models.IntegerField()


class Question(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    correct_option = models.IntegerField()
    image_1 = models.ImageField(upload_to='static/alternatives', null=True)
    image_2 = models.ImageField(upload_to='static/alternatives', null=True)
    image_3 = models.ImageField(upload_to='static/alternatives', null=True)
    image_4 = models.ImageField(upload_to='static/alternatives', null=True)
    option_1 = models.CharField(max_length=100)
    option_2 = models.CharField(max_length=100)
    option_3 = models.CharField(max_length=100)
    option_4 = models.CharField(max_length=100)
    text = models.CharField(max_length=100)


class ClassExecution(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    date_start = models.DateTimeField(auto_now_add=True)
    date_end = models.DateTimeField(null=True)


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    class_execution = models.ForeignKey(ClassExecution,
                                        on_delete=models.CASCADE
                                        )
    correct = models.BooleanField(null=True)
