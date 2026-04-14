import discord
import os
import asyncio
from dotenv import load_dotenv
from sarvamai import AsyncSarvamAI
import re
from functionality import functional

# <--------------------Initializing project---------------------------------->

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SARVAM_API_KEY = os.getenv('SARVAM_API_KEY')

# Initialize the Sarvam AI client
client = AsyncSarvamAI(api_subscription_key=SARVAM_API_KEY)

# Load your "Syllabus" or System Instructions
try:
    with open('systemPrompt.txt', 'r', encoding='utf-8') as f:
        SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    SYSTEM_PROMPT = "You are a helpful assistant restricted to a specific syllabus."

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

# Initializing your custom functionality class
chad = functional(bot=bot)

@bot.event
async def on_ready():
    print(f'--- Logged in as {bot.user} (ID: {bot.user.id}) ---')

@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Trigger custom functionality (checks for prefixes, commands, etc.)
    await chad.call(message)

    # If the functional class determines no response is needed, exit
    if not chad.user_input:
        return

    async with message.channel.typing():
        try:
            # 1. Fetch message history for context
            # Increasing limit slightly to give the AI more "memory" of the conversation
            previous_messages = await chad.get_message_history(message.channel, limit=6)
            
            # 2. Reconstruct the conversation with CORRECT roles
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]
            
            for prev_msg in previous_messages:
                # Skip the current message (we add it last) and empty messages
                if prev_msg.id == message.id or not prev_msg.content.strip():
                    continue
                
                # RECTIFICATION: Assign 'assistant' role to bot messages, 'user' to others
                role = "assistant" if prev_msg.author == bot.user else "user"
                
                # If it's a user message, we keep the name for multi-user context
                content = f"{prev_msg.author.name}: {prev_msg.content}" if role == "user" else prev_msg.content
                
                messages.append({
                    "role": role,
                    "content": content
                })
            
            # 3. Add the latest user input
            messages.append({
                "role": "user",
                "content": chad.user_input
            })

            # 4. Generate response with strict parameters
            response = await client.chat.completions(
                model="sarvam-30b", 
                messages=messages,
                temperature=0.2, # Lower temperature = more focus, less "hallucination"
                top_p=0.9        # Ensures the model picks likely words
            )

            # 5. Extract and send the response
            if hasattr(response, 'choices') and len(response.choices) > 0:
                ai_response = response.choices[0].message.content
            else:
                ai_response = "I'm having trouble thinking right now. Please try again."

            if ai_response:
                # Discord character limit handling
                for i in range(0, len(ai_response), 2000):
                    await message.channel.send(ai_response[i:i+2000])

        except Exception as e:
            print(f"Error calling Sarvam API: {e}")
            await message.channel.send(
                "Sorry, I encountered an error while processing your request."
            )

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
