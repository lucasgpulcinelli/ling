"""
URL configuration for ling project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.HomeView.as_view()),

    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('register/', views.RegisterView.as_view()),

    path('course/', views.CoursesView.as_view()),
    path('course/<int:id>', views.CourseView.as_view()),
    path('course/<int:id>/subscribe', views.SubscribeView.as_view()),
    path('lesson/<int:id>/startclass', views.StartClassView.as_view()),
    path('class/<int:id>', views.ClassView.as_view()),
    path('class/<int:id>/question', views.QuestionsView.as_view()),
    path('class/<int:class_id>/question/<int:id>/answer', views.AnswerView.as_view()),
    path('class/<int:id>/conclude', views.ConcludeClassView.as_view()),
]
