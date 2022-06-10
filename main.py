import asyncio
import os
import youtube_dl
import discord
import math
import ffmpeg

import googleapiclient.discovery
from urllib.parse import parse_qs, urlparse

# CONFIG

TOKEN = ""
DEVELOPER_KEY = ""
VOICE_CHANNEL_ID = 0
TEXT_CHANNEL_ID = 0

# CONFIG

client = discord.Client()
stack = list()

voiceChannel: discord.VoiceChannel
textChannel: discord.TextChannel
voiceClient: discord.VoiceClient


def download(video_url: str) -> None:
    video_info = youtube_dl.YoutubeDL().extract_info(
        url=video_url, download=False
    )
    filename = f"{video_info['title']}.mp3"

    print(filename)

    if os.path.exists(filename):
        stack.append(filename)
        return
    options = {
        'format': 'bestaudio/best',
        'keepvideo': False,
        'outtmpl': filename,
    }
    with youtube_dl.YoutubeDL(options) as ydl:
        ydl.download([video_info['webpage_url']])
    stack.append(filename)


@client.event
async def on_ready():
    global voiceClient, voiceChannel, textChannel

    textChannel = client.get_channel(TEXT_CHANNEL_ID)
    await textChannel.send("Activated")
    voiceChannel = client.get_channel(VOICE_CHANNEL_ID)
    voiceClient = await voiceChannel.connect()
    while True:
        if not len(stack):
            await asyncio.sleep(1)
        else:
            try:
                voiceClient.play(discord.FFmpegPCMAudio(stack[0]))
                await asyncio.sleep(math.ceil(float(ffmpeg.probe(stack[0])['format']['duration'])))
                print("AGAIN")
                voiceClient.stop()
                stack.pop(0)
            except discord.errors.ClientException:
                voiceClient = await voiceChannel.connect()


@client.event
async def on_message(msg: discord.Message):
    if msg.author == client.user:pass
    if msg.content.startswith("> play "):
        try:
            download(msg.content[7::])
            await msg.channel.send("Downloaded!")
        except youtube_dl.utils.DownloadError:
            await msg.channel.send("It's not a video's link!")
        except youtube_dl.utils.ExtractorError:
            await msg.channel.send("Sorry, but video have 18+ content")
    if msg.content.startswith("> list "):
        try:
            url = msg.content[7::]
            query = parse_qs(urlparse(url).query, keep_blank_values=True)
            playlist_id = query["list"][0]

            youtube = googleapiclient.discovery.build("youtube", "v3",
                                                      developerKey=DEVELOPER_KEY)

            request = youtube.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50
            )
            request.execute()

            playlist_items = []
            while request is not None:
                response = request.execute()
                playlist_items += response["items"]
                request = youtube.playlistItems().list_next(request, response)

            links = [f'https://www.youtube.com/watch?v={t["snippet"]["resourceId"]["videoId"]}&list={playlist_id}&t=0s'for t in playlist_items]
            for i in range(len(links)-1):
                print(links[i].split("&list=")[0])
                download(links[i].split("&list=")[0])
                await msg.channel.send("Downloaded {} of them!".format(i+1))
            download(links[len(links)-1].split("&list=")[0])
            await msg.channel.send("Downloaded all of them!".format(i + 1))
        except KeyError:await msg.channel.send("It's not playlist's link!")
        except youtube_dl.utils.ExtractorError:await msg.channel.send("Sorry, but playlist have 18+ content")

client.run(TOKEN)
