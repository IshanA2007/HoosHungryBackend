import json
import re
from datetime import date as date_type, timedelta

import anthropic
from django.conf import settings
from django.db import transaction
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
        user_message_raw = request.data.get('message', '')
        if not isinstance(user_message_raw, str):
            return Response({'error': 'message must be a string'}, status=status.HTTP_400_BAD_REQUEST)
        user_message = user_message_raw.strip()

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
        try:
            ai_response = client.messages.create(
                model='claude-haiku-4-5-20251001',
                max_tokens=1024,
                system=system_prompt,
                messages=history,
            )
            response_text = ai_response.content[0].text
        except anthropic.APIError:
            return Response(
                {'error': 'AI service temporarily unavailable. Please try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Parse response
        ai_message, suggestions = _parse_ai_response(response_text)

        # Persist both messages and decrement usage atomically
        with transaction.atomic():
            if not profile.premium_member:
                profile.decrement_ai_usage()
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
