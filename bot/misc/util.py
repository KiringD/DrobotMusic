import asyncio

import nextcord
from nextcord import FFmpegPCMAudio
from youtube_dl import YoutubeDL

from ..handlers.user.main import guilds_objects


class YTDLSource():
    YDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        'cookiefile': 'yt_cookies.txt',
        'extract_flat': True,
    }
    YDL_OPTIONS2 = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        'cookiefile': 'yt_cookies.txt',
    }
    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    def create_embed(self):
        embed = (nextcord.Embed(title='Сейчас играет',
                               description='```css\n{0.title}\n```'.format(self),
                               color=nextcord.Color.blurple())
                 .add_field(name='Время прослушивания', value=self.duration)
                 .add_field(name='Автор видео', value='[{0.uploader}]({0.uploader_url})'.format(self))
                 .add_field(name='Ссылка(кликни)', value='[Click]({0.url})'.format(self))
                 .set_thumbnail(url=self.thumbnail))

        return embed

    async def ytd_play(self, ctx, voice, info):

        try:
            URL = info['url']
            voice.play(FFmpegPCMAudio(URL, **self.FFMPEG_OPTIONS))
            self.data = info

            self.uploader = info.get('uploader')
            self.uploader_url = info.get('uploader_url')
            self.title = info.get('title')
            self.thumbnail = info.get('thumbnail')
            self.duration = self.parse_duration(int(info.get('duration')))
            self.url = info.get('webpage_url')
            self.stream_url = info.get('url')
            if not guilds_objects[ctx.channel.guild.id].is_loop:
                await ctx.send(embed=self.create_embed())

        except Exception:
            pass

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append('{} дней'.format(days))
        if hours > 0:
            duration.append('{} часов'.format(hours))
        if minutes > 0:
            duration.append('{} минут'.format(minutes))
        if seconds > 0:
            duration.append('{} секунд'.format(seconds))

        return ', '.join(duration)


class Guild_Objects():
    def __init__(self):
        self.queue = []
        self.is_loop = False
        self.playing_song = ""

async def loop_add(ctx, info, guild_id, need_message=True, pos=-2):
    try:
        if pos == -2:
            guilds_objects[guild_id].queue.append(info)
        elif pos >= 0 and pos <= len(guilds_objects[guild_id].queue):
            if guilds_objects[guild_id].is_loop and pos == 0:
                pos = 1
            guilds_objects[guild_id].queue.insert(pos, info)
        else:
            await ctx.send("Введенные данные неверны")
            return
        if need_message:
            await ctx.send("Песня **{}** добавлена".format(info['title']))
    except KeyError:
        pass
    except Exception as e:
        await ctx.send('Что то пошло не так')



async def player(ctx, voice, info, guild_id):
    ydl = YTDLSource()
    await ydl.ytd_play(ctx, voice, guilds_objects[guild_id].queue[0])
    if not guilds_objects[guild_id].is_loop:
        guilds_objects[guild_id].queue.pop(0)


# print(queues)

async def audio_player_task(ctx, voice, guild_id):
    timer = 0
    while True:
        timer += 1
        if guild_id in guilds_objects:
            if guilds_objects[guild_id].queue == ['final']:
                try:
                    guilds_objects.pop(guild_id)
                except:
                    pass
                try:
                    await voice.disconnect()
                except:
                    pass
                break
        if not voice.is_playing() and not voice.is_paused() and len(guilds_objects[guild_id].queue) != 0:
            guilds_objects[guild_id].playing_song = guilds_objects[guild_id].queue[0]
            await player(ctx, voice, guilds_objects[guild_id].queue[0], guild_id)
        if voice.is_playing():
            timer = 0
        elif not voice.is_paused and not voice.is_playing:
            guilds_objects[guild_id].playing_song = ""
        await asyncio.sleep(1)

        if timer >= 1800:
            try:
                guilds_objects[guild_id].queue = ['final']
            except KeyError as e:
                pass

async def get_video_info(url):
    try:
        ydl = YTDLSource()
        if url.find('https:') != -1:
            if url.find('https://www.youtube.com/watch?v=') != -1 or url.find('https://youtu.be/') != -1:
                with YoutubeDL(ydl.YDL_OPTIONS) as ydl1:
                    info = ydl1.extract_info(url, download=False)
                URL = info['url']
            else:
                raise Exception
        else:
            with YoutubeDL(ydl.YDL_OPTIONS2) as ydl1:
                info = ydl1.extract_info(f"ytsearch:{url}", download=False)["entries"][0]
            URL = info['url']
    except Exception as e:
        return False

    return info

