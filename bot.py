import discord
from discord.ext import commands
import json
import os
import re
from datetime import datetime, timedelta
import pytz

# Create bot
bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())

# Store user data
user_data = {}
data_file = 'user_data.json'

# Load saved data
def load_data():
    global user_data
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            user_data = json.load(f)
    else:
        user_data = {}

# Save data
def save_data():
    with open(data_file, 'w') as f:
        json.dump(user_data, f)

# Get user timezones
def get_user_tz(user_id):
    user_id = str(user_id)
    if user_id in user_data:
        return user_data[user_id].get('primary_tz', 'UTC')
    return 'UTC'

# Get all timezones for a user
def get_user_all_tz(user_id):
    user_id = str(user_id)
    if user_id in user_data:
        return user_data[user_id].get('all_tz', ['UTC'])
    return ['UTC']

# When bot starts
@bot.event
async def on_ready():
    load_data()
    print(f'✅ Bot is online as {bot.user}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="timezones ⏰"))

# Auto-react to times mentioned in chat
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Check if message contains a time pattern (e.g., "3pm", "15:30", "2:45 AM")
    time_pattern = r'\d{1,2}:?\d{0,2}\s*(am|pm|AM|PM)?'
    if re.search(time_pattern, message.content):
        try:
            await message.add_reaction('🕰️')
        except:
            pass
    
    await bot.process_commands(message)

# Command: !help
@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(
        title='⏰ TimeZone Bot - Commands',
        description='Convert times across timezones easily!',
        color=discord.Color.blue()
    )
    embed.add_field(name='!settimezone <timezone>', value='Set your primary timezone', inline=False)
    embed.add_field(name='!addtz <timezone>', value='Add a timezone to your list (up to 5)', inline=False)
    embed.add_field(name='!mytime', value='Show your current time + all your zones', inline=False)
    embed.add_field(name='!convert <time> <from_tz> <to_tz>', value='Convert time between zones\nExample: !convert 3pm America/New_York Europe/London', inline=False)
    embed.add_field(name='!listtz', value='Show popular timezones', inline=False)
    embed.add_field(name='!mytz', value='Show your saved timezones', inline=False)
    embed.set_footer(text='React with 🕰️ when you see a time!')
    await ctx.send(embed=embed)

# Command: !settimezone
@bot.command(name='settimezone')
async def set_timezone(ctx, tz):
    try:
        # Validate timezone
        pytz.timezone(tz)
        
        user_id = str(ctx.author.id)
        if user_id not in user_data:
            user_data[user_id] = {'primary_tz': tz, 'all_tz': [tz]}
        else:
            user_data[user_id]['primary_tz'] = tz
            if tz not in user_data[user_id]['all_tz']:
                user_data[user_id]['all_tz'].append(tz)
        
        save_data()
        
        embed = discord.Embed(
            title='✅ Timezone Set',
            description=f'Your timezone is now: **{tz}**',
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    except pytz.exceptions.UnknownTimeZoneError:
        embed = discord.Embed(
            title='❌ Invalid Timezone',
            description=f'**{tz}** is not a valid timezone.\nUse !listtz to see valid options.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

# Command: !addtz (NEW!)
@bot.command(name='addtz')
async def add_timezone(ctx, tz):
    try:
        pytz.timezone(tz)
        
        user_id = str(ctx.author.id)
        if user_id not in user_data:
            user_data[user_id] = {'primary_tz': 'UTC', 'all_tz': [tz]}
        else:
            all_tz = user_data[user_id].get('all_tz', ['UTC'])
            if len(all_tz) >= 5:
                embed = discord.Embed(
                    title='❌ Max Timezones',
                    description='You can only have 5 timezones. Remove one first.',
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
            
            if tz not in all_tz:
                all_tz.append(tz)
                user_data[user_id]['all_tz'] = all_tz
        
        save_data()
        
        embed = discord.Embed(
            title='✅ Timezone Added',
            description=f'**{tz}** has been added to your list!',
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    except pytz.exceptions.UnknownTimeZoneError:
        embed = discord.Embed(
            title='❌ Invalid Timezone',
            description=f'**{tz}** is not valid.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

# Command: !mytime (IMPROVED!)
@bot.command(name='mytime')
async def my_time(ctx):
    user_id = str(ctx.author.id)
    all_tz = get_user_all_tz(ctx.author.id)
    
    embed = discord.Embed(
        title=f'⏰ {ctx.author.name}\'s Timezones',
        color=discord.Color.purple()
    )
    
    for tz in all_tz:
        try:
            tz_obj = pytz.timezone(tz)
            now = datetime.now(tz_obj)
            time_str = now.strftime('%I:%M %p')
            embed.add_field(name=tz, value=f'**{time_str}**', inline=True)
        except:
            pass
    
    await ctx.send(embed=embed)

# Command: !convert (NEW!)
@bot.command(name='convert')
async def convert_time(ctx, time_str, from_tz, to_tz):
    try:
        # Parse time
        time_obj = datetime.strptime(time_str, '%I%p')
        
        # Get timezones
        tz_from = pytz.timezone(from_tz)
        tz_to = pytz.timezone(to_tz)
        
        # Create datetime in source timezone
        now = datetime.now(tz_from)
        dt = now.replace(hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0)
        
        # Convert to target timezone
        dt_converted = dt.astimezone(tz_to)
        
        embed = discord.Embed(
            title='⏰ Time Conversion',
            color=discord.Color.blue()
        )
        embed.add_field(name=f'📍 {from_tz}', value=f'**{dt.strftime("%I:%M %p")}**', inline=True)
        embed.add_field(name=f'📍 {to_tz}', value=f'**{dt_converted.strftime("%I:%M %p")}**', inline=True)
        
        await ctx.send(embed=embed)
    except ValueError:
        embed = discord.Embed(
            title='❌ Invalid Format',
            description='Use format: !convert 3pm America/New_York Europe/London',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    except pytz.exceptions.UnknownTimeZoneError:
        embed = discord.Embed(
            title='❌ Invalid Timezone',
            description='Check timezone spelling or use !listtz',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

# Command: !mytz (NEW!)
@bot.command(name='mytz')
async def my_tz(ctx):
    user_id = str(ctx.author.id)
    all_tz = get_user_all_tz(ctx.author.id)
    
    embed = discord.Embed(
        title='📍 Your Saved Timezones',
        color=discord.Color.orange()
    )
    
    tz_list = '\n'.join([f'• {tz}' for tz in all_tz])
    embed.description = tz_list
    embed.set_footer(text=f'You have {len(all_tz)}/5 timezones')
    
    await ctx.send(embed=embed)

# Command: !listtz
@bot.command(name='listtz')
async def list_timezones(ctx):
    embed = discord.Embed(
        title='🌍 Popular Timezones',
        color=discord.Color.green()
    )
    
    timezones = '''**Americas:**
America/New_York
America/Chicago
America/Denver
America/Los_Angeles
America/Mexico_City

**Europe:**
Europe/London
Europe/Paris
Europe/Berlin
Europe/Moscow
Europe/Istanbul

**Asia:**
Asia/Dubai
Asia/Kolkata
Asia/Bangkok
Asia/Shanghai
Asia/Tokyo
Asia/Hong_Kong
Asia/Singapore

**Oceania:**
Australia/Sydney
Australia/Melbourne
Pacific/Auckland'''
    
    embed.description = timezones
    embed.set_footer(text='Use !convert <time> <from_tz> <to_tz> to convert times')
    
    await ctx.send(embed=embed)

# Run bot
import os
bot.run(os.getenv('DISCORD_TOKEN'))
