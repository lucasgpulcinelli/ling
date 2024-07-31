from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from . import models

from datetime import datetime, timezone
import random as r
import json


class RegisterView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy("login")
    template_name = "register.html"


class HomeView(TemplateView):
    template_name = "index.html"


class CoursesView(LoginRequiredMixin, TemplateView):
    template_name = "courses.html"


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # for all courses, get the course general data and
        # if the current user is subscribed or not, and
        # the percentage of the course completed, calculated as the amount of
        # lessons with >50% correct answers divided by the total amount of
        # lessons
        context['courses'] = models.Course.objects.raw('''
        SELECT
            s.id IS NOT NULL AS subscribed,
            CASE
                WHEN completion.pct_completed IS NULL
                THEN 0.00
                ELSE completion.pct_completed
            END AS pct_completed,
            c.*
        FROM ling_course c
            LEFT JOIN ling_subscription s
                ON c.id = s.course_id
                AND s.user_id = %s
            LEFT JOIN (
                -- get, for each subscription, the percentage of the course
                -- completed
                SELECT
                    SUM(
                        CASE WHEN best_completion >= 50 THEN 1 ELSE 0 END
                    ) / CAST(COUNT(*) AS FLOAT) * 100 AS pct_completed,
                    subscription_id
                FROM (
                    -- get, for each lesson/subscription pair (maybe without a
                    -- previous class_execution) the best percentage of
                    -- completion
                    SELECT
                        MAX(pct_correct) AS best_completion,
                        l.id AS lesson_id,
                        s.id AS subscription_id
                    FROM ling_lesson l
                    JOIN ling_subscription s ON s.course_id = l.course_id
                    LEFT JOIN (
                        -- get, for every class execution, the percentage of
                        -- correct questions
                        SELECT
                            CAST(
                                SUM(CASE WHEN a.correct THEN 1 ELSE 0 END)
                                AS FLOAT
                            ) / COUNT(a.id) * 100 AS pct_correct,
                            ex.subscription_id,
                            ex.lesson_id,
                            ex.id
                        FROM ling_classexecution ex
                            JOIN ling_answer a
                                ON a.class_execution_id = ex.id
                        GROUP BY ex.id, ex.lesson_id, ex.subscription_id
                    ) performance_execution
                        ON l.id = performance_execution.lesson_id
                        AND s.id = performance_execution.subscription_id
                    GROUP BY lesson_id, subscription_id
                ) best_executions
                GROUP BY subscription_id
            ) completion
                ON completion.subscription_id = s.id
        ''', [self.request.user.pk])

        return context


class SubscribeView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        course = models.Course.objects.get(pk=kwargs['id'])

        if request.user.subscription_set.filter(course=course):
            return HttpResponse(status=401)

        subscription = models.Subscription(user=request.user, course=course)
        subscription.save()

        return HttpResponse(status=301,
                            headers={"Location": f"../{course.pk}"}
                            )


class CourseView(LoginRequiredMixin, TemplateView):
    template_name = "course.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        prev_subscription = models.Subscription.objects.filter(
            user=self.request.user,
            course=self.kwargs['id']
        )
        context['is_subscribed'] = len(prev_subscription) != 0

        context['course'] = models.Course.objects.get(pk=self.kwargs['id'])

        # select all lessons and, for each lesson, also get:
        # if it exists, the current class execution;
        # if you already did the lesson in the past:
        #   the amount of times you did this lesson,
        #   and, for your best attempt:
        #     the time you took to finish the lesson and
        #     the percentage of questions you got right
        #
        # if anyone knows how to make this query smaller (without modifying the
        # schema or the results, and without correlated queries such as I did)
        # i would love to know
        context['lessons'] = models.Lesson.objects.raw('''
        -- for each class execution, get the percentage of correct answers
        WITH past_attempts AS (
            SELECT
                CAST(
                    SUM(CASE WHEN a.correct THEN 1 ELSE 0 END)
                    AS FLOAT
                ) / COUNT(a.id) * 100 AS pct_correct,
                timediff(
                    ex.date_end,
                    ex.date_start
                ) AS time,
                subscription_id,
                lesson_id,
                ex.id
            FROM ling_classexecution ex
                JOIN ling_answer a
                    ON a.class_execution_id = ex.id
            WHERE ex.date_end IS NOT NULL
            GROUP BY
                time,
                subscription_id,
                lesson_id,
                ex.id
        )
        SELECT
            current.id AS current_execution_id,
            COUNT(past.id) AS past_execution_count,
            best.pct_correct AS best_pct_correct,
            best.time AS best_time,
            l.*
        FROM ling_lesson l
            JOIN ling_subscription s
                ON s.course_id = l.course_id
            LEFT JOIN (
                -- for all lesson/subscription pair, get the best percentage
                -- of correct questions and the best time with this percentage
                -- NOTE: because the window function FIRST_VALUE is evaluated
                --   before the GROUP BY, there needs to be two subqueries:
                --   one for the FIRST_VALUE with repeats,
                --   and one to correctly group stuff
                SELECT * FROM( SELECT
                    FIRST_VALUE(p.pct_correct) OVER(
                        PARTITION BY p.lesson_id, p.subscription_id
                        ORDER BY p.time ASC
                    ) AS pct_correct,
                    FIRST_VALUE(p.time) OVER(
                        PARTITION BY p.lesson_id, p.subscription_id
                        ORDER BY p.time ASC
                    ) AS time,
                    p.subscription_id,
                    p.lesson_id
                FROM past_attempts p
                    JOIN (
                        -- for all lesson/subscription pair, get the maximum
                        --percentage of correct questions
                        SELECT
                            MAX(pct_correct) AS pct_correct,
                            lesson_id,
                            subscription_id
                        FROM past_attempts
                        GROUP BY
                            lesson_id,
                            subscription_id
                    ) best_inner
                        ON best_inner.lesson_id = p.lesson_id
                        AND best_inner.subscription_id = p.subscription_id
                WHERE p.pct_correct = best_inner.pct_correct
                ) p
                GROUP BY p.lesson_id, p.subscription_id
            ) best
                ON l.id = best.lesson_id
                AND s.id = best.subscription_id
            LEFT JOIN ling_classexecution AS current
                ON l.id = current.lesson_id
                AND s.id = current.subscription_id
                AND current.date_end IS NULL
            LEFT JOIN ling_classexecution AS past
                ON l.id = past.lesson_id
                AND s.id = past.subscription_id
                AND past.date_end IS NOT NULL
        WHERE s.user_id = %s AND l.course_id = %s
        GROUP BY l.id
        ORDER BY l.id
        ''', [self.request.user.pk, self.kwargs['id']])

        for lesson in context['lessons']:
            if lesson.best_time is not None:
                lesson.best_time = lesson.best_time[-12:]

        return context


class StartClassView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        lesson = models.Lesson.objects.get(pk=kwargs['id'])
        subscription = request.user.subscription_set.filter(
            course=lesson.course
        )

        if not subscription:
            return HttpResponse(status=401)

        prev_classes = models.ClassExecution.objects.filter(
            subscription=subscription[0], lesson=lesson, date_end=None
        )

        if len(prev_classes) != 0:
            return HttpResponse(status=303,
                                headers={"Location": f"../../class/{prev_classes[0].pk}"}
                                )

        class_execution = models.ClassExecution(
            subscription=subscription[0], lesson=lesson
        )

        class_execution.save()

        questions = models.Question.objects.filter(lesson=lesson)

        for question in r.sample(list(questions), lesson.question_number):
            answer = models.Answer(
                question=question,
                class_execution=class_execution
            )
            answer.save()

        return HttpResponse(status=302,
                            headers={"Location": f"../../class/{class_execution.pk}"}
                            )


class ClassView(LoginRequiredMixin, TemplateView):
    template_name = "class.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["class_execution"] = models.ClassExecution.objects.get(
            pk=self.kwargs['id']
        )

        return context


class QuestionsView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        ret = []
        for answer in models.Answer.objects.filter(class_execution=kwargs['id']):
            ret.append({
                "correct": answer.correct,
                "text": answer.question.text,
                "images": [
                    answer.question.image_1.url,
                    answer.question.image_2.url,
                    answer.question.image_3.url,
                    answer.question.image_4.url
                ],
                "options": [
                    answer.question.option_1,
                    answer.question.option_2,
                    answer.question.option_3,
                    answer.question.option_4
                ],
                "id": answer.question.pk,
            })

        return HttpResponse(json.dumps(ret),
                            headers={"Content-Type": "application/json"}
                            )


class AnswerView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        class_execution = models.ClassExecution.objects.get(pk=kwargs['class_id'])
        question = models.Question.objects.get(pk=kwargs['id'])

        answer = models.Answer.objects.get(
            class_execution=class_execution, question=question
        )

        if answer.correct is not None:
            return HttpResponse(status=409)

        answer.correct = int(json.loads(request.body)['option']) == question.correct_option
        answer.save()

        return HttpResponse(json.dumps({"correct": answer.correct}),
                            headers={"Content-Type": "application/json"}
                            )


class ConcludeClassView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        class_execution = models.ClassExecution.objects.get(pk=kwargs['id'])
        if class_execution.subscription.user != request.user:
            return HttpResponse(status=401)

        if class_execution.date_end:
            return HttpResponse(status=409)

        if models.Answer.objects.filter(class_execution=class_execution, correct=None):
            return HttpResponse(status=400)

        class_execution.date_end = datetime.now(timezone.utc)
        class_execution.save()

        return HttpResponse(status=201)
