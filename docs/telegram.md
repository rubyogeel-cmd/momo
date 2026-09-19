# Telegram integration

The onboarding flow notifies you (the operator) via a Telegram bot
whenever a user crosses a checkpoint, and lets you approve or reject
the flow by tapping inline buttons.

## 1. Create a bot

1. Open Telegram and message @BotFather.
2. Send /newbot and follow the prompts.
3. Copy the bot token you receive.

## 2. Find your chat id

1. Send any message to your new bot (for example, "hi").
2. Visit https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   in a browser.
3. Copy the value at result[0].message.chat.id.

## 3. Configure

Copy config/telegram.example.json to config/telegram.json and fill in
both values:

    {
      "bot_token": "123456789:ABC-DEF...",
      "chat_id": "123456789"
    }

config/telegram.json is git-ignored and must never be committed.

## 4. Checkpoints

The bot sends a message at each checkpoint:

    1. Onboarding - user taps a plan on page 2. No buttons.
    2. PIN + phone - user confirms on page 3.
       Buttons: Approve PIN / Reject PIN.
    3. OTP SMS - user submits the pasted SMS.
       Buttons: Approve OTP / Reject OTP.

Buttons carry the session id, so pressing them applies to the correct
user regardless of message order.

## 5. Operator actions

* Approve PIN -> the user goes to the SMS verification page.
* Reject PIN  -> the user returns to page 3 with an error; the phone
                 is kept and the PIN cleared.
* Approve OTP -> the user sees the success page with a reference
                 number and thank-you copy.
* Reject OTP  -> the user sees "invalid confirmation message, please
                 wait for a new one and try again".
