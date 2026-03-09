import datetime

from django.test import LiveServerTestCase, SimpleTestCase, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from polls.models import Choice, Question


class SimpleURLTests(SimpleTestCase):
    def test_index_url_resolves(self):
        url = reverse("polls:index")
        self.assertEqual(url, "/polls/")

    def test_results_url_resolves(self):
        url = reverse("polls:results", args=[1])
        self.assertEqual(url, "/polls/1/results/")


class QuestionModelTests(TestCase):
    def test_was_published_recently_with_future_question(self):
        time = timezone.now() + datetime.timedelta(days=30)
        future_question = Question(pub_date=time)
        self.assertIs(future_question.was_published_recently(), False)

    def test_was_published_recently_with_old_question(self):
        time = timezone.now() - datetime.timedelta(days=1, seconds=1)
        old_question = Question(pub_date=time)
        self.assertIs(old_question.was_published_recently(), False)

    def test_was_published_recently_with_recent_question(self):
        time = timezone.now() - datetime.timedelta(hours=23, minutes=59, seconds=59)
        recent_question = Question(pub_date=time)
        self.assertIs(recent_question.was_published_recently(), True)


def create_question(question_text, days):
    time = timezone.now() + datetime.timedelta(days=days)
    return Question.objects.create(question_text=question_text, pub_date=time)


class QuestionIndexViewTests(TestCase):
    def test_no_questions(self):
        response = self.client.get(reverse("polls:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No polls are available.")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

    def test_past_question(self):
        question = create_question(question_text="Past question.", days=-30)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(response.context["latest_question_list"], [question])

    def test_future_question(self):
        create_question(question_text="Future question.", days=30)
        response = self.client.get(reverse("polls:index"))
        self.assertContains(response, "No polls are available.")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

    def test_future_question_and_past_question(self):
        question = create_question(question_text="Past question.", days=-30)
        create_question(question_text="Future question.", days=30)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(response.context["latest_question_list"], [question])

    def test_two_past_questions(self):
        question1 = create_question(question_text="Past question 1.", days=-30)
        question2 = create_question(question_text="Past question 2.", days=-5)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            [question2, question1],
        )


class QuestionDetailViewTests(TestCase):
    def test_future_question(self):
        future_question = create_question(question_text="Future question.", days=5)
        url = reverse("polls:detail", args=(future_question.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_past_question(self):
        past_question = create_question(question_text="Past Question.", days=-5)
        url = reverse("polls:detail", args=(past_question.id,))
        response = self.client.get(url)
        self.assertContains(response, past_question.question_text)


class VoteTransactionTests(TransactionTestCase):
    def test_vote_increments_choice_count(self):
        question = Question.objects.create(
            question_text="Favourite colour?",
            pub_date=timezone.now(),
        )
        choice = Choice.objects.create(
            question=question,
            choice_text="Blue",
            votes=0,
        )

        response = self.client.post(
            reverse("polls:vote", args=[question.id]),
            {"choice": choice.id},
        )

        choice.refresh_from_db()
        self.assertEqual(choice.votes, 1)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("polls:results", args=[question.id]))


class PollsLiveServerTests(LiveServerTestCase):
    def test_home_page_loads(self):
        question = Question.objects.create(
            question_text="Live server question?",
            pub_date=timezone.now(),
        )

        response = self.client.get(f"{self.live_server_url}/polls/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, question.question_text)
