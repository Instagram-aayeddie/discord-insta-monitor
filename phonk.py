import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import yt_dlp
import asyncio
from discord import opus

# This reads the TOKEN from the .env file instead of having it here
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# --- CONFIG ---
TOKEN = os.getenv('DISCORD_TOKEN')
VOICE_CHANNEL_ID = 1486506960470675457 

# --- MAC OPUS FIX ---
def load_opus():
    if not opus.is_loaded():
        paths = ['/opt/homebrew/lib/libopus.dylib', '/usr/local/lib/libopus.dylib']
        for path in paths:
            try:
                opus.load_opus(path)
                print(f"✅ Loaded Opus from: {path}")
                return
            except:
                continue
        print("❌ Could not find libopus. Run 'brew install opus'.")

load_opus()

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Global settings
current_volume = 0.20
audio_mode = "normal" 

@bot.event
async def on_ready():
    print(f'✅ {bot.user} is online!')
    print(f'Commands: !play_phonk <link/search>, !pause, !resume, !stop, !volume, !nightcore, !slowed, !normal')

@bot.command()
async def play_phonk(ctx, *, search: str = None):
    if search is None:
        return await ctx.send("❓ What should I play? Provide a name or a link.")

    # Clean the search string if a link was pasted with brackets
    search = search.strip("()<>")

    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if not channel:
        return await ctx.send("❌ Voice channel ID not found.")

    vc = ctx.voice_client or await channel.connect()

    await ctx.send(f"📡 Processing: **{search}** (Mode: `{audio_mode}`)")

    # yt-dlp options to handle both links and searches
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'default_search': 'ytsearch',
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info - this works for links OR search queries
            info = ydl.extract_info(search, download=False)
            
            # If it was a search result, get the first entry
            if 'entries' in info:
                info = info['entries'][0]
            
            url = info['url']
            title = info['title']
        
        await asyncio.sleep(1.5)
        if vc.is_playing(): vc.stop()

        # Build FFmpeg filters based on mode
        filters = "-vn"
        if audio_mode == "nightcore":
            filters = '-af "asetrate=44100*1.25,atempo=1.25"'
        elif audio_mode == "slowed":
            filters = '-af "asetrate=44100*0.85,atempo=1.0,aecho=0.8:0.9:1000:0.3"'

        ffmpeg_vars = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': filters
        }

        # Apply volume transformer
        source = discord.FFmpegPCMAudio(url, **ffmpeg_vars)
        vc.play(discord.PCMVolumeTransformer(source, volume=current_volume))
        
        await ctx.send(f"🎶 Now playing: **{title}** at {int(current_volume*100)}% volume.")
        
    except Exception as e:
        print(f"ERROR: {e}")
        await ctx.send(f"⚠️ Failed to play. Error: `{str(e)[:100]}`")

# --- CONTROLS ---

@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Paused.")

@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Resumed.")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("⏹️ Stopped.")

@bot.command()
async def volume(ctx, vol: int):
    global current_volume
    if 0 <= vol <= 100:
        current_volume = vol / 100
        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = current_volume
        await ctx.send(f"🔊 Volume set to **{vol}%**")
    else:
        await ctx.send("❌ Use a number between 0 and 100.")

# --- MODES ---

@bot.command()
async def nightcore(ctx):
    global audio_mode
    audio_mode = "nightcore"
    await ctx.send("🌙 **Nightcore Mode Active** (Effect applies on next song)")

@bot.command()
async def slowed(ctx):
    global audio_mode
    audio_mode = "slowed"
    await ctx.send("☁️ **Slowed + Reverb Active** (Effect applies on next song)")

@bot.command()
async def normal(ctx):
    global audio_mode
    audio_mode = "normal"
    await ctx.send("⏺️ **Normal Mode Active**")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Left the voice channel.")

bot.run(TOKEN)