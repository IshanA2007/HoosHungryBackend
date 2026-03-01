# CavBot AI Prompt Feature Design
**Date:** 2026-02-28
**Status:** Approved

---

## Overview

Implement the AI chat feature for the HoosHungry Prompt page. CavBot is a dining assistant that suggests personalized meals from UVA's real dining hall menus using Claude Haiku (Anthropic), with full conversation context, DB-persisted history, and direct plan integration.

---

## Approach

**Rolling context window (Approach B):** The last 20 messages are re-sent to Claude on each request, giving CavBot memory of the conversation. History is stored in the DB and loaded when the user opens the chat page.

---

## Backend — New `prompt` Django App

### Models

**`ChatSession`**
- `user` (OneToOne → User)
- `created_at`

**`ChatMessage`**
- `session` (FK → ChatSession)
- `role` — `'user'` or `'assistant'`
- `content` — text body of the message
- `suggestions_json` — nullable JSON field, populated on assistant messages that include meal suggestions
- `timestamp`

### Endpoints

| Method | URL | Auth | Purpose |
|--------|-----|------|---------|
| `POST` | `/api/prompt/chat/` | Required | Send message, receive AI response + suggestions |
| `GET` | `/api/prompt/history/` | Required | Load user's past messages |
| `DELETE` | `/api/prompt/history/` | Required | Clear user's chat history |

`applySuggestion` uses the existing `POST /api/plan/add-item/` endpoint — no new endpoint needed.

### POST /api/prompt/chat/ Logic

1. Auth check → 401 if not logged in
2. Usage check → 402 (`{ "error": "usage_limit_reached" }`) if `remaining_ai_usages == 0` and not `premium_member`
3. Decrement `remaining_ai_usages` by 1
4. Fetch today's menu — all dining halls, all periods — from `api.MenuItem` + `NutritionInfo`
5. Fetch user's `DailyMealPlan` for today from `plans` app
6. Fetch user's goals + dietary prefs from `accounts.UserProfile`
7. Load last 20 `ChatMessage` rows for this user's session
8. Assemble system prompt + message history array
9. Call Claude Haiku (`claude-haiku-4-5-20251001`) via Anthropic SDK
10. Parse JSON response → extract `message` + `suggestions[]`
11. Save user `ChatMessage` to DB
12. Save assistant `ChatMessage` + `suggestions_json` to DB
13. Return `{ message, suggestions }`

---

## AI Prompt Design

### System Prompt Structure

```
You are CavBot, a friendly dining assistant for UVA students. Help them find
meals matching their nutritional goals from today's actual dining hall menus.

Today is {date}.

USER GOALS: {calorie_goal} cal | {protein_goal}g protein | {carbs_goal}g carbs | {fat_goal}g fat
DIETARY PREFERENCES: {vegan/vegetarian/gluten-free flags, or "None specified"}

TODAY'S PLAN SO FAR ({date}):
  Already consumed: {X} cal, {X}g protein, {X}g carbs, {X}g fat
  Remaining: {X} cal, {X}g protein, {X}g carbs, {X}g fat
  Items: [list of already-added meal names]

AVAILABLE MENU ITEMS TODAY:
  [condensed array: id, name, dining_hall, station, period, calories, protein,
   carbs, fat, is_vegan, is_vegetarian, is_gluten_free]

When suggesting specific items, respond ONLY with valid JSON:
{
  "message": "Your conversational response",
  "suggestions": [
    {
      "id": 42,
      "item_name": "Grilled Chicken",
      "dining_hall": "OHill",
      "station": "Grill",
      "calories": 280,
      "protein": 35,
      "action": "add",
      "reason": "High protein, fits your remaining macros"
    }
  ]
}
If not suggesting specific items, the "suggestions" field can be omitted.
```

### Model
- **Model:** `claude-haiku-4-5-20251001`
- **Conversation history:** Last 20 messages passed as `messages` array
- **Max tokens:** 1024 (sufficient for message + 3-5 suggestions)

---

## UserProfile Changes

Add three boolean fields to `accounts.UserProfile` (all default `False`):
- `is_vegan`
- `is_vegetarian`
- `is_gluten_free`

Expose on existing `GET /accounts/user/` response. No frontend editing UI in this iteration — fields are set manually or via admin.

---

## Frontend Changes

### `promptEndpoints.ts` — replace all stubs

```typescript
sendMessage(req)     →  POST /api/prompt/chat/
getHistory()         →  GET  /api/prompt/history/
clearHistory()       →  DELETE /api/prompt/history/
applySuggestion(s)   →  POST /api/plan/add-item/
                          { date: today, menu_item_id: s.id,
                            meal_type: inferred from time of day,
                            servings: 1 }
```

### `useChat.ts` — two additions

1. **On mount:** call `getHistory()` and populate `messages` state
2. **On 402 error:** display system message: *"You've used all your CavBot messages. Upgrade to premium for unlimited access."*

---

## End-to-End Data Flow

```
User sends message
  → useChat.sendMessage()
    → POST /api/prompt/chat/
      → auth + usage check
      → fetch menu, plan, goals, history
      → assemble prompt → call Claude Haiku
      → parse JSON response
      → save both messages to DB
      → return { message, suggestions }
    → UI shows assistant message + suggestion cards
  → User taps "Add to plan"
    → POST /api/plan/add-item/  (existing endpoint)
      → meal added to today's plan
```

---

## Out of Scope (This Iteration)

- Frontend UI for editing dietary preferences
- Multiple named chat sessions per user
- Meal swap / remove suggestion actions (only "add" for now)
- Push notifications or proactive suggestions
