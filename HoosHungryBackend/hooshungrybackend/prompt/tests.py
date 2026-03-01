import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
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


class ChatViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='viewuser', password='pass')
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.url = '/api/prompt/chat/'

    def test_requires_authentication(self):
        unauth_client = APIClient()
        response = unauth_client.post(self.url, {'message': 'hello'}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_returns_402_when_no_usages_remain(self):
        self.user.profile.remaining_ai_usages = 0
        self.user.profile.save()
        response = self.client.post(self.url, {'message': 'hello'}, format='json')
        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.data['error'], 'usage_limit_reached')

    def test_premium_user_bypasses_usage_limit(self):
        self.user.profile.remaining_ai_usages = 0
        self.user.profile.premium_member = True
        self.user.profile.save()

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"message": "Hi there!"}')]

        with patch('prompt.views.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.return_value = mock_response
            response = self.client.post(self.url, {'message': 'hello'}, format='json')

        self.assertEqual(response.status_code, 200)

    def test_successful_chat_returns_message(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"message": "Try the grilled chicken!"}')]

        with patch('prompt.views.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.return_value = mock_response
            response = self.client.post(self.url, {'message': 'What should I eat?'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'Try the grilled chicken!')

    def test_successful_chat_saves_messages_to_db(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"message": "Hello!"}')]

        with patch('prompt.views.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.return_value = mock_response
            self.client.post(self.url, {'message': 'Hello'}, format='json')

        session = ChatSession.objects.get(user=self.user)
        messages = session.messages.all()
        self.assertEqual(messages.count(), 2)
        self.assertEqual(messages[0].role, 'user')
        self.assertEqual(messages[1].role, 'assistant')

    def test_successful_chat_decrements_usage(self):
        initial_usages = self.user.profile.remaining_ai_usages
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"message": "Hello!"}')]

        with patch('prompt.views.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.return_value = mock_response
            self.client.post(self.url, {'message': 'Hello'}, format='json')

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.remaining_ai_usages, initial_usages - 1)

    def test_response_includes_suggestions_when_present(self):
        ai_json = json.dumps({
            "message": "Try this!",
            "suggestions": [
                {"id": 1, "item_name": "Grilled Chicken", "dining_hall": "OHill",
                 "station": "Grill", "calories": 280, "protein": 35, "action": "add",
                 "reason": "High protein"}
            ]
        })
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=ai_json)]

        with patch('prompt.views.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.return_value = mock_response
            response = self.client.post(self.url, {'message': 'Protein suggestions?'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertIn('suggestions', response.data)
        self.assertEqual(len(response.data['suggestions']), 1)
