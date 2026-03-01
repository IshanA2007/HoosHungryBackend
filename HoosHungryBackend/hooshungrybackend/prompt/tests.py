from django.test import TestCase
from django.contrib.auth.models import User
from .models import ChatSession, ChatMessage


class ChatSessionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='chatuser', password='pass')

    def test_get_or_create_session_creates_new(self):
        session, created = ChatSession.objects.get_or_create(user=self.user)
        self.assertTrue(created)
        self.assertEqual(session.user, self.user)

    def test_get_or_create_session_returns_existing(self):
        session1, _ = ChatSession.objects.get_or_create(user=self.user)
        session2, created = ChatSession.objects.get_or_create(user=self.user)
        self.assertFalse(created)
        self.assertEqual(session1.pk, session2.pk)


class ChatMessageTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='msguser', password='pass')
        self.session, _ = ChatSession.objects.get_or_create(user=self.user)

    def test_create_user_message(self):
        msg = ChatMessage.objects.create(
            session=self.session,
            role='user',
            content='What should I eat for lunch?'
        )
        self.assertEqual(msg.role, 'user')
        self.assertIsNone(msg.suggestions_json)

    def test_create_assistant_message_with_suggestions(self):
        suggestions = [{'id': 1, 'item_name': 'Grilled Chicken', 'action': 'add'}]
        msg = ChatMessage.objects.create(
            session=self.session,
            role='assistant',
            content='Try the grilled chicken!',
            suggestions_json=suggestions
        )
        self.assertEqual(msg.role, 'assistant')
        self.assertEqual(len(msg.suggestions_json), 1)

    def test_messages_ordered_by_timestamp(self):
        ChatMessage.objects.create(session=self.session, role='user', content='first')
        ChatMessage.objects.create(session=self.session, role='assistant', content='second')
        msgs = list(ChatMessage.objects.filter(session=self.session))
        self.assertEqual(msgs[0].content, 'first')
        self.assertEqual(msgs[1].content, 'second')
