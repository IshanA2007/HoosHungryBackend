# CavBot AI Chat Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a fully functional AI chat backend (CavBot) that answers meal questions using real dining hall data and the user's current plan, powered by Claude Haiku via the Anthropic SDK.

**Architecture:** New `prompt` Django app with `ChatSession`/`ChatMessage` models. A single `POST /api/prompt/chat/` view assembles context (today's menu, daily plan, user goals/dietary prefs), sends a rolling 20-message history to Claude Haiku, parses the JSON response, saves both messages to DB, and returns `{ message, suggestions[] }`. History and clear endpoints complete the contract. Frontend stubs are replaced with real API calls.

**Tech Stack:** Django 5, DRF, Anthropic Python SDK, Claude Haiku (`claude-haiku-4-5-20251001`), Poetry, React/TypeScript, Axios

---

## Task 1: Install Anthropic SDK

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add anthropic to pyproject.toml**

In the `[tool.poetry.dependencies]` section, add:
```toml
anthropic = "^0.40.0"
```

**Step 2: Install via poetry**

```bash
cd /Users/ishanajwani/Documents/HoosHungryBackend/HoosHungryBackend/hooshungrybackend
poetry add anthropic
```

Expected: `anthropic` appears in `poetry.lock` with no errors.

**Step 3: Verify install**

```bash
poetry run python -c "import anthropic; print(anthropic.__version__)"
```

Expected: prints a version number like `0.40.0`.

**Step 4: Commit**

```bash
git add pyproject.toml poetry.lock
git commit -m "feat: add anthropic SDK dependency"
```

---

## Task 2: Configure ANTHROPIC_API_KEY in settings

**Files:**
- Modify: `config/settings.py`
- Create: `.env` (gitignored)

**Step 1: Add os import and API key setting to settings.py**

At the top of `config/settings.py`, after the existing `from pathlib import Path` line, add:

```python
import os
```

At the bottom of `config/settings.py`, add:

```python
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
```

**Step 2: Create .env file with your API key**

Create a file at the project root `/Users/ishanajwani/Documents/HoosHungryBackend/HoosHungryBackend/hooshungrybackend/.env`:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Step 3: Verify .env is gitignored**

```bash
cat .gitignore
```

If `.env` is not listed, add it:
```bash
echo ".env" >> .gitignore
```

**Step 4: Set the env var for the current shell session (for running tests/server)**

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Step 5: Commit**

```bash
git add config/settings.py .gitignore
git commit -m "feat: add ANTHROPIC_API_KEY settings config"
```

---

## Task 3: Add dietary preference fields to UserProfile

**Files:**
- Modify: `accounts/models.py`
- Create: `accounts/migrations/000X_userprofile_dietary_prefs.py` (auto-generated)
- Modify: `accounts/serializers.py`
- Modify: `accounts/tests.py` (create if not exists)

**Step 1: Write the failing test**

Open `accounts/tests.py`. If it doesn't exist, create it. Add:

```python
from django.test import TestCase
from django.contrib.auth.models import User
from .models import UserProfile

class UserProfileDietaryPrefsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')

    def test_dietary_pref_fields_exist_with_defaults(self):
        profile = self.user.profile
        self.assertFalse(profile.is_vegan)
        self.assertFalse(profile.is_vegetarian)
        self.assertFalse(profile.is_gluten_free)

    def test_dietary_prefs_can_be_set(self):
        profile = self.user.profile
        profile.is_vegan = True
        profile.save()
        profile.refresh_from_db()
        self.assertTrue(profile.is_vegan)
```

**Step 2: Run test to confirm it fails**

```bash
poetry run python manage.py test accounts.tests.UserProfileDietaryPrefsTest -v 2
```

Expected: `AttributeError: 'UserProfile' object has no attribute 'is_vegan'`

**Step 3: Add the three fields to UserProfile**

In `accounts/models.py`, inside the `UserProfile` class after the `premium_member` field (line 22), add:

```python
    is_vegan = models.BooleanField(default=False)
    is_vegetarian = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
```

**Step 4: Create and apply migration**

```bash
poetry run python manage.py makemigrations accounts --name userprofile_dietary_prefs
poetry run python manage.py migrate
```

Expected: new migration file created, migration applied.

**Step 5: Run test to confirm it passes**

```bash
poetry run python manage.py test accounts.tests.UserProfileDietaryPrefsTest -v 2
```

Expected: `OK`

**Step 6: Expose fields in serializer**

In `accounts/serializers.py`, update `UserProfileSerializer.Meta.fields` from:

```python
fields = ['remaining_ai_usages', 'plans', 'premium_member', 'created_at']
```

to:

```python
fields = ['remaining_ai_usages', 'plans', 'premium_member', 'created_at',
          'is_vegan', 'is_vegetarian', 'is_gluten_free',
          'default_calorie_goal', 'default_protein_goal',
          'default_carbs_goal', 'default_fat_goal']
```

**Step 7: Commit**

```bash
git add accounts/models.py accounts/migrations/ accounts/serializers.py accounts/tests.py
git commit -m "feat: add dietary preference fields to UserProfile"
```

---

## Task 4: Create prompt Django app

**Files:**
- Create: `prompt/__init__.py`
- Create: `prompt/apps.py`
- Create: `prompt/models.py`
- Create: `prompt/views.py`
- Create: `prompt/urls.py`
- Create: `prompt/serializers.py`
- Create: `prompt/tests.py`
- Create: `prompt/admin.py`
- Modify: `config/settings.py`
- Modify: `config/urls.py`

**Step 1: Scaffold the app**

```bash
cd /Users/ishanajwani/Documents/HoosHungryBackend/HoosHungryBackend/hooshungrybackend
poetry run python manage.py startapp prompt
```

Expected: `prompt/` directory created with `models.py`, `views.py`, `tests.py`, `apps.py`, `admin.py`.

**Step 2: Add to INSTALLED_APPS**

In `config/settings.py`, add `'prompt'` to `INSTALLED_APPS` after `'plans'`:

```python
INSTALLED_APPS = [
    ...
    'plans',
    'prompt',
]
```

**Step 3: Create prompt/urls.py**

Replace the auto-generated content of `prompt/urls.py` (or create it) with:

```python
from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.ChatView.as_view(), name='prompt-chat'),
    path('history/', views.HistoryView.as_view(), name='prompt-history'),
]
```

**Step 4: Register in config/urls.py**

In `config/urls.py`, add after the existing `path('api/plan/', ...)` line:

```python
path('api/prompt/', include('prompt.urls')),
```

**Step 5: Verify routing compiles**

```bash
poetry run python manage.py check
```

Expected: `System check identified no issues.`

**Step 6: Commit**

```bash
git add prompt/ config/settings.py config/urls.py
git commit -m "feat: scaffold prompt app with URL routing"
```

---

## Task 5: ChatSession and ChatMessage models

**Files:**
- Modify: `prompt/models.py`
- Create: `prompt/migrations/` (auto-generated)
- Modify: `prompt/admin.py`
- Modify: `prompt/tests.py`

**Step 1: Write failing tests**

In `prompt/tests.py`, replace all content with:

```python
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
```

**Step 2: Run tests to confirm they fail**

```bash
poetry run python manage.py test prompt.tests.ChatSessionTest prompt.tests.ChatMessageTest -v 2
```

Expected: `ImportError` or `AttributeError` — models don't exist yet.

**Step 3: Implement the models**

Replace all content of `prompt/models.py` with:

```python
from django.db import models
from django.contrib.auth.models import User


class ChatSession(models.Model):
    """One chat session per user."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_session')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s chat session"


class ChatMessage(models.Model):
    """Individual turns in the conversation."""
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant')]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    suggestions_json = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}"
```

**Step 4: Create and apply migration**

```bash
poetry run python manage.py makemigrations prompt --name initial
poetry run python manage.py migrate
```

Expected: migration created and applied.

**Step 5: Run tests to confirm they pass**

```bash
poetry run python manage.py test prompt.tests.ChatSessionTest prompt.tests.ChatMessageTest -v 2
```

Expected: `OK` — 5 tests pass.

**Step 6: Register models in admin**

In `prompt/admin.py`:

```python
from django.contrib import admin
from .models import ChatSession, ChatMessage

admin.site.register(ChatSession)
admin.site.register(ChatMessage)
```

**Step 7: Commit**

```bash
git add prompt/models.py prompt/migrations/ prompt/admin.py prompt/tests.py
git commit -m "feat: add ChatSession and ChatMessage models"
```

---

## Task 6: Implement POST /api/prompt/chat/ view

**Files:**
- Modify: `prompt/views.py`
- Modify: `prompt/tests.py`

**Step 1: Write failing tests**

Append to `prompt/tests.py`:

```python
import json
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token


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
```

**Step 2: Run tests to confirm they fail**

```bash
poetry run python manage.py test prompt.tests.ChatViewTest -v 2
```

Expected: errors about missing view or 404s.

**Step 3: Implement the view**

Replace all content of `prompt/views.py` with:

```python
import json
import re
from datetime import date as date_type, timedelta

import anthropic
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from api.models import Day
from plans.models import Plan, DailyMealPlan
from .models import ChatSession, ChatMessage


SYSTEM_PROMPT_TEMPLATE = """\
You are CavBot, a friendly dining assistant for UVA students. \
Help them find meals matching their nutritional goals from today's actual dining hall menus.

Today is {date}.

USER GOALS: {calorie_goal} cal | {protein_goal}g protein | {carbs_goal}g carbs | {fat_goal}g fat
DIETARY PREFERENCES: {dietary_prefs}

TODAY'S PLAN SO FAR ({date}):
  Already consumed: {consumed_cal} cal, {consumed_protein}g protein, \
{consumed_carbs}g carbs, {consumed_fat}g fat
  Remaining: {remaining_cal} cal, {remaining_protein}g protein, \
{remaining_carbs}g carbs, {remaining_fat}g fat
  Items added: {items_added}

AVAILABLE MENU ITEMS TODAY (JSON array):
{menu_json}

When suggesting specific items, respond ONLY with valid JSON in this exact format:
{{
  "message": "Your conversational response here",
  "suggestions": [
    {{
      "id": 42,
      "item_name": "Grilled Chicken",
      "dining_hall": "OHill",
      "station": "Grill",
      "calories": 280,
      "protein": 35,
      "action": "add",
      "reason": "High protein, fits your remaining macros"
    }}
  ]
}}
If not suggesting specific items, omit the "suggestions" field. \
Always respond with valid JSON containing at least a "message" field."""


def _get_menu_context(today):
    """Return a list of today's menu items across all dining halls and periods."""
    items = []
    days = Day.objects.filter(date=today).select_related('dining_hall')
    for day in days:
        for period in day.periods.prefetch_related('stations__menu_items__nutrition_info').all():
            for station in period.stations.all():
                for item in station.menu_items.all():
                    try:
                        n = item.nutrition_info
                        items.append({
                            'id': item.id,
                            'name': item.item_name,
                            'dining_hall': day.dining_hall.name,
                            'station': station.name,
                            'period': period.name,
                            'calories': int(n.calories or 0),
                            'protein': round(float(n.protein or 0), 1),
                            'carbs': round(float(n.total_carbohydrates or 0), 1),
                            'fat': round(float(n.total_fat or 0), 1),
                            'is_vegan': item.is_vegan,
                            'is_vegetarian': item.is_vegetarian,
                            'gluten_free': not item.is_gluten,
                        })
                    except Exception:
                        pass
    return items


def _get_daily_plan_context(user, today):
    """Return the user's daily nutrition totals and item names for today."""
    try:
        days_since_sunday = (today.weekday() + 1) % 7
        sunday = today - timedelta(days=days_since_sunday)
        plan = Plan.objects.get(user=user, week_start_date=sunday)
        daily = DailyMealPlan.objects.get(plan=plan, date=today)
        items = list(daily.meal_items.values_list('menu_item_name', flat=True))
        return {
            'consumed_cal': daily.total_calories,
            'consumed_protein': float(daily.total_protein),
            'consumed_carbs': float(daily.total_carbs),
            'consumed_fat': float(daily.total_fat),
            'items': items,
        }
    except (Plan.DoesNotExist, DailyMealPlan.DoesNotExist):
        return {
            'consumed_cal': 0, 'consumed_protein': 0.0,
            'consumed_carbs': 0.0, 'consumed_fat': 0.0,
            'items': [],
        }


def _build_system_prompt(user, today):
    """Assemble the full system prompt with user context and menu data."""
    profile = user.profile
    menu_items = _get_menu_context(today)
    plan_ctx = _get_daily_plan_context(user, today)

    calorie_goal = profile.default_calorie_goal or 2000
    protein_goal = profile.default_protein_goal or 50
    carbs_goal = profile.default_carbs_goal or 250
    fat_goal = profile.default_fat_goal or 65

    dietary_prefs = []
    if profile.is_vegan:
        dietary_prefs.append('Vegan')
    if profile.is_vegetarian:
        dietary_prefs.append('Vegetarian')
    if profile.is_gluten_free:
        dietary_prefs.append('Gluten-free')

    remaining_cal = max(0, calorie_goal - plan_ctx['consumed_cal'])
    remaining_protein = max(0.0, protein_goal - plan_ctx['consumed_protein'])
    remaining_carbs = max(0.0, carbs_goal - plan_ctx['consumed_carbs'])
    remaining_fat = max(0.0, fat_goal - plan_ctx['consumed_fat'])

    return SYSTEM_PROMPT_TEMPLATE.format(
        date=today.strftime('%A, %B %d, %Y'),
        calorie_goal=calorie_goal,
        protein_goal=protein_goal,
        carbs_goal=carbs_goal,
        fat_goal=fat_goal,
        dietary_prefs=', '.join(dietary_prefs) if dietary_prefs else 'None specified',
        consumed_cal=plan_ctx['consumed_cal'],
        consumed_protein=round(plan_ctx['consumed_protein'], 1),
        consumed_carbs=round(plan_ctx['consumed_carbs'], 1),
        consumed_fat=round(plan_ctx['consumed_fat'], 1),
        remaining_cal=remaining_cal,
        remaining_protein=round(remaining_protein, 1),
        remaining_carbs=round(remaining_carbs, 1),
        remaining_fat=round(remaining_fat, 1),
        items_added=', '.join(plan_ctx['items']) if plan_ctx['items'] else 'None yet',
        menu_json=json.dumps(menu_items, separators=(',', ':')),
    )


def _parse_ai_response(response_text):
    """
    Parse Claude's response text into (message, suggestions).
    Falls back gracefully if response is not valid JSON.
    """
    # Strip markdown code fences if present
    text = re.sub(r'^```(?:json)?\s*', '', response_text.strip(), flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text)

    try:
        data = json.loads(text)
        return data.get('message', response_text), data.get('suggestions')
    except json.JSONDecodeError:
        # Try to extract JSON object from surrounding text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return data.get('message', response_text), data.get('suggestions')
            except json.JSONDecodeError:
                pass
    return response_text, None


class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        profile = user.profile
        user_message = request.data.get('message', '').strip()

        if not user_message:
            return Response({'error': 'message is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Usage enforcement: block if 0 usages and not premium
        if not profile.premium_member and not profile.has_ai_usage_remaining():
            return Response({'error': 'usage_limit_reached'}, status=status.HTTP_402_PAYMENT_REQUIRED)

        today = date_type.today()
        system_prompt = _build_system_prompt(user, today)

        # Get or create session and load last 20 messages as conversation history
        session, _ = ChatSession.objects.get_or_create(user=user)
        recent = session.messages.order_by('-timestamp')[:20]
        history = [
            {'role': msg.role, 'content': msg.content}
            for msg in reversed(list(recent))
        ]
        history.append({'role': 'user', 'content': user_message})

        # Call Claude Haiku
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        ai_response = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1024,
            system=system_prompt,
            messages=history,
        )
        response_text = ai_response.content[0].text

        # Parse response
        ai_message, suggestions = _parse_ai_response(response_text)

        # Decrement usage (only for non-premium users)
        if not profile.premium_member:
            profile.decrement_ai_usage()

        # Persist both messages
        ChatMessage.objects.create(session=session, role='user', content=user_message)
        ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=ai_message,
            suggestions_json=suggestions,
        )

        result = {'message': ai_message}
        if suggestions:
            result['suggestions'] = suggestions
        return Response(result, status=status.HTTP_200_OK)
```

**Step 4: Run tests**

```bash
poetry run python manage.py test prompt.tests.ChatViewTest -v 2
```

Expected: all 7 tests pass.

**Step 5: Commit**

```bash
git add prompt/views.py prompt/tests.py
git commit -m "feat: implement POST /api/prompt/chat/ view with Claude Haiku"
```

---

## Task 7: Implement GET and DELETE /api/prompt/history/

**Files:**
- Modify: `prompt/views.py`
- Modify: `prompt/tests.py`

**Step 1: Write failing tests**

Append to `prompt/tests.py`:

```python
class HistoryViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='histuser', password='pass')
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.url = '/api/prompt/history/'
        # Seed some messages
        session = ChatSession.objects.create(user=self.user)
        ChatMessage.objects.create(session=session, role='user', content='Hello')
        ChatMessage.objects.create(session=session, role='assistant', content='Hi there!')

    def test_get_history_requires_auth(self):
        unauth = APIClient()
        self.assertEqual(unauth.get(self.url).status_code, 401)

    def test_get_history_returns_messages(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_get_history_shape(self):
        response = self.client.get(self.url)
        msg = response.data[0]
        self.assertIn('role', msg)
        self.assertIn('content', msg)
        self.assertIn('timestamp', msg)

    def test_get_history_returns_empty_for_new_user(self):
        new_user = User.objects.create_user(username='newuser2', password='pass')
        token = Token.objects.create(user=new_user)
        new_client = APIClient()
        new_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = new_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_delete_history_clears_messages(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 204)
        session = ChatSession.objects.get(user=self.user)
        self.assertEqual(session.messages.count(), 0)

    def test_delete_history_requires_auth(self):
        unauth = APIClient()
        self.assertEqual(unauth.delete(self.url).status_code, 401)
```

**Step 2: Run tests to confirm they fail**

```bash
poetry run python manage.py test prompt.tests.HistoryViewTest -v 2
```

Expected: 404 or `AttributeError` — view not implemented yet.

**Step 3: Add HistoryView to prompt/views.py**

At the bottom of `prompt/views.py`, append:

```python
class HistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return the user's full chat history."""
        try:
            session = ChatSession.objects.get(user=request.user)
        except ChatSession.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)

        messages = session.messages.all()
        data = [
            {
                'id': msg.pk,
                'role': msg.role,
                'content': msg.content,
                'suggestions': msg.suggestions_json,
                'timestamp': msg.timestamp.isoformat(),
            }
            for msg in messages
        ]
        return Response(data, status=status.HTTP_200_OK)

    def delete(self, request):
        """Clear the user's chat history."""
        try:
            session = ChatSession.objects.get(user=request.user)
            session.messages.all().delete()
        except ChatSession.DoesNotExist:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)
```

**Step 4: Run all prompt tests**

```bash
poetry run python manage.py test prompt -v 2
```

Expected: all tests pass (aim for 18+).

**Step 5: Commit**

```bash
git add prompt/views.py prompt/tests.py
git commit -m "feat: implement GET and DELETE /api/prompt/history/ endpoints"
```

---

## Task 8: Run full backend test suite

**Step 1: Run all tests**

```bash
poetry run python manage.py test -v 2
```

Expected: all tests pass. Fix any regressions before proceeding.

**Step 2: Start the dev server and smoke test the endpoints**

```bash
poetry run python manage.py runserver
```

In a separate terminal, get a token first:

```bash
curl -X POST http://localhost:8000/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_user", "password": "your_pass"}'
```

Then test the chat endpoint:

```bash
curl -X POST http://localhost:8000/api/prompt/chat/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN_HERE" \
  -d '{"message": "What has the most protein today?"}'
```

Expected: real response from Claude Haiku with dining hall suggestions.

**Step 3: Commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: resolve any test suite regressions"
```

---

## Task 9: Update frontend promptEndpoints.ts

**Files:**
- Modify: `/Users/ishanajwani/Documents/HoosHungry/HoosHungry/hooshungry/src/api/promptEndpoints.ts`

**Step 1: Read the current file**

Open and read `promptEndpoints.ts` to understand what to replace.
Current file location: `/Users/ishanajwani/Documents/HoosHungry/HoosHungry/hooshungry/src/api/promptEndpoints.ts`

**Step 2: Replace the entire file with real implementations**

Replace the full file content with:

```typescript
import apiClient from "./client";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  suggestions?: MealSuggestion[];
}

export interface MealSuggestion {
  id: number;
  item_name: string;
  dining_hall: string;
  station: string;
  calories: number;
  protein: number;
  action: "add" | "remove" | "swap";
  reason: string;
}

export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  message: string;
  suggestions?: MealSuggestion[];
}

/** Infer meal type from the current time of day. */
function inferMealType(): string {
  const hour = new Date().getHours();
  if (hour < 11) return "breakfast";
  if (hour < 15) return "lunch";
  if (hour < 20) return "dinner";
  return "snack";
}

export const promptAPI = {
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await apiClient.post("/prompt/chat/", request);
    return response.data;
  },

  getHistory: async (): Promise<ChatMessage[]> => {
    const response = await apiClient.get("/prompt/history/");
    return response.data.map((msg: {
      id: number;
      role: "user" | "assistant";
      content: string;
      timestamp: string;
      suggestions: MealSuggestion[] | null;
    }) => ({
      id: String(msg.id),
      role: msg.role,
      content: msg.content,
      timestamp: new Date(msg.timestamp),
      suggestions: msg.suggestions ?? undefined,
    }));
  },

  clearHistory: async (): Promise<void> => {
    await apiClient.delete("/prompt/history/");
  },

  applySuggestion: async (suggestion: MealSuggestion): Promise<void> => {
    const today = new Date().toISOString().split("T")[0];
    await apiClient.post("/plan/add-item/", {
      date: today,
      menu_item_id: suggestion.id,
      meal_type: inferMealType(),
      servings: 1,
    });
  },
};

export default promptAPI;
```

**Step 3: Verify TypeScript compiles**

```bash
cd /Users/ishanajwani/Documents/HoosHungry/HoosHungry/hooshungry
npm run build 2>&1 | head -30
```

Expected: no TypeScript errors in `promptEndpoints.ts`.

**Step 4: Commit in the frontend repo**

```bash
cd /Users/ishanajwani/Documents/HoosHungry/HoosHungry/hooshungry
git add src/api/promptEndpoints.ts
git commit -m "feat: replace promptEndpoints stubs with real API calls"
```

---

## Task 10: Update frontend useChat.ts to load history on mount

**Files:**
- Modify: `/Users/ishanajwani/Documents/HoosHungry/HoosHungry/hooshungry/src/hooks/useChat.ts`

**Step 1: Read the current file**

Open `/Users/ishanajwani/Documents/HoosHungry/HoosHungry/hooshungry/src/hooks/useChat.ts`.

**Step 2: Add history loading on mount**

After the existing `useEffect` for auto-scrolling (lines 87-89), add a new `useEffect` that loads history on mount. Insert after line 89:

```typescript
  // Load chat history from backend on mount
  useEffect(() => {
    promptAPI.getHistory().then((history) => {
      if (history.length > 0) {
        setMessages(history);
      }
    }).catch(() => {
      // silently ignore — user just starts with empty chat
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // run once on mount
```

**Step 3: Handle 402 usage limit error in sendMessage**

In the `sendMessage` function's `catch` block (currently lines 139-150), replace:

```typescript
      } catch (error) {
        console.error("Failed to send message:", error);
        onError?.(error as Error);

        // Add error message
        const errorMessage: ChatMessage = {
          id: generateId("error"),
          role: "assistant",
          content: "Sorry, I encountered an error. Please try again.",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
```

with:

```typescript
      } catch (error: unknown) {
        console.error("Failed to send message:", error);
        onError?.(error as Error);

        // Check for usage limit error (HTTP 402)
        const isUsageLimit =
          typeof error === "object" &&
          error !== null &&
          "response" in error &&
          (error as { response?: { status?: number } }).response?.status === 402;

        const errorContent = isUsageLimit
          ? "You've used all your CavBot messages. Upgrade to premium for unlimited access."
          : "Sorry, I encountered an error. Please try again.";

        const errorMessage: ChatMessage = {
          id: generateId("error"),
          role: "assistant",
          content: errorContent,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
```

**Step 4: Verify TypeScript compiles**

```bash
cd /Users/ishanajwani/Documents/HoosHungry/HoosHungry/hooshungry
npm run build 2>&1 | head -30
```

Expected: clean build with no TypeScript errors.

**Step 5: Commit**

```bash
git add src/hooks/useChat.ts
git commit -m "feat: load chat history on mount and handle 402 usage limit"
```

---

## Task 11: End-to-end smoke test

**Step 1: Start backend**

```bash
cd /Users/ishanajwani/Documents/HoosHungryBackend/HoosHungryBackend/hooshungrybackend
export ANTHROPIC_API_KEY=sk-ant-your-key-here
poetry run python manage.py runserver
```

**Step 2: Start frontend**

```bash
cd /Users/ishanajwani/Documents/HoosHungry/HoosHungry/hooshungry
npm run dev
```

**Step 3: Manual test checklist**

- [ ] Log in as an existing user
- [ ] Navigate to `/prompt`
- [ ] Send a message: "What has the most protein available today?"
- [ ] Verify CavBot responds with real dining hall items (not placeholder data)
- [ ] If suggestions appear, click "Add to plan" on one
- [ ] Navigate to `/plan` and verify the item was added to today's plan
- [ ] Return to `/prompt`, refresh the page
- [ ] Verify the previous conversation loaded from DB (history persists)
- [ ] Click "Clear chat" and verify messages are removed
- [ ] Set `remaining_ai_usages = 0` in Django admin for your user
- [ ] Send a message and verify the usage limit error message appears

**Step 4: Final commit**

```bash
cd /Users/ishanajwani/Documents/HoosHungryBackend/HoosHungryBackend/hooshungrybackend
git add -A
git commit -m "feat: complete CavBot AI chat feature end-to-end"
```
