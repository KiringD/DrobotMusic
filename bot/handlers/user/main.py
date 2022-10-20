import asyncio
import random

import nextcord
from nextcord.ext import commands
from youtube_dl import YoutubeDL

guilds_objects = {}

def register_user_handlers(bot):
    bot.add_command(_join)
    bot.add_command(_play)
    bot.add_command(_queue)
    bot.add_command(_leave)
    bot.add_command(_next)
    bot.add_command(_clear)
    bot.add_command(_remove)
    bot.add_command(_pause)
    bot.add_command(_resume)
    bot.add_command(_shuffle)
    bot.add_command(_loop)
    bot.add_command(_insert)
    bot.add_command(_playlist)


@commands.command(name="join")
async def _join(ctx):
    """Добавляет бота в голосовой чат"""
    try:
        guild_id = ctx.channel.guild.id
        voice_channel = ctx.author.voice.channel
        voice = ctx.channel.guild.voice_client
        if voice is None:
            voice = await voice_channel.connect()
        elif voice.channel != voice_channel:
            await voice.move_to(voice_channel)

        if guild_id not in guilds_objects.keys():
            guilds_objects[guild_id] = Guild_Objects()
            loop = asyncio.get_event_loop()
            loop.create_task(audio_player_task(ctx, voice, guild_id))
    except AttributeError:
        await ctx.send("Для добавления бота требуется находиться в голосовом чате")


@commands.command(aliases=['play','p'])
async def _play(ctx, *, url):
    """Добавляет указанныю песню в очередь"""
    await _join(ctx)
    voice = ctx.channel.guild.voice_client
    voice_channel = ctx.author.voice.channel
    if voice is None or voice_channel is None:
        return 0
    info = await get_video_info(url)
    if info is not False:
        try:
            await loop_add(ctx, info, ctx.channel.guild.id)
        except:
            pass
    else:
        await ctx.send("Что то пошло не так")

@commands.command(name='insert')
async def _insert(ctx, pos, *, url):
    """Позволяет вставить песню в любой место очереди."""
    await _join(ctx)
    voice = ctx.channel.guild.voice_client
    voice_channel = ctx.author.voice.channel
    if voice is None or voice_channel is None:
        return 0

    info = await get_video_info(url)
    if info is not False:
        try:
            await loop_add(ctx, info, ctx.channel.guild.id, 1, int(pos) - 1)
        except:
            await ctx.send("Формат команды должен быть -insert [место в очреди] [песня]")
    else:
        await ctx.send("Что то пошло не так")


@commands.command(name='playlist')
async def _playlist(ctx, url):
    '''Позволяет добавить целый плейлист в очередь(может работать нестабильно)'''
    if url.find('https://www.youtube.com/playlist') == -1 and url.find('https://youtube.com/playlist') == -1:
        await ctx.send('Напишите команду в формате -playlist [ссылка на плейлист]')
        return

    await _join(ctx)
    voice = ctx.channel.guild.voice_client
    voice_channel = ctx.author.voice.channel
    if voice is None or voice_channel is None:
        return 0

    ydl = YTDLSource()
    await ctx.send("Подождите немного")
    loop = asyncio.get_event_loop()
    with YoutubeDL(ydl.YDL_OPTIONS) as ydl1:
        info = ydl1.extract_info(url, download=False)
    URLS = info['entries']
    flag = True
    for i in URLS:
        if not ctx.channel.guild.id in guilds_objects.keys():
            flag = False
            break
        link = i['url']
        try:
            with YoutubeDL(YTDLSource.YDL_OPTIONS) as ydl1:
                current_info = await loop.run_in_executor(None, lambda: ydl1.extract_info(link, download=False))
            await loop_add(ctx, current_info, ctx.channel.guild.id, 0)
        except:
            pass
    if flag:
        await ctx.send("**Плейлист добавлен**")



@commands.command(aliases=['queue','q'])
async def _queue(ctx):
    """Показыват какие треки сейчас в очереди"""
    try:
        guild_id = ctx.channel.guild.id
        queue = ''
        for i in range(len(guilds_objects[guild_id].queue)):
            if len(queue) < 3800:
                queue += '`{0}.` [**{1}**]\n'.format(i + 1, guilds_objects[guild_id].queue[i]['title'])
            else:
                break
        if queue!= '':
            embed = (nextcord.Embed(description='**{} tracks:**\n\n{}'.format(len(guilds_objects[guild_id].queue), queue)))
            await ctx.send(embed=embed)
        else:
            await ctx.send("В очереди нет треков")
    except Exception as e:
        # print(e,2)
        await ctx.send("В очереди нет треков")


@commands.command(name='leave')
async def _leave(ctx):
    """Убирает бота из голосового чата"""
    try:
        voice = ctx.channel.guild.voice_client

        if voice.is_playing() or voice.is_paused():
            voice.stop()
        await voice.disconnect()
        if ctx.channel.guild.id in guilds_objects.keys():
            guilds_objects[ctx.channel.guild.id].queue = ['final']

    except Exception as e:
        # print(e,2)
        await ctx.send("Бот и так не в голосовом канале")

@commands.command(aliases=['next','n'])
async def _next(ctx):
    """Включает следующий трек"""
    try:
        voice = ctx.channel.guild.voice_client

        if voice.is_playing() or voice.is_paused():
            if guilds_objects[ctx.channel.guild.id].is_loop:
                guilds_objects[ctx.channel.guild.id].is_loop = False
                guilds_objects[ctx.channel.guild.id].queue.pop(0)
            voice.stop()
    except Exception as e:
        # print(e,2)
        await ctx.send("Вы еще не добавили ни одного трека")

@commands.command(name='clear')
async def _clear(ctx):
    """Очищает очередь на воспроизведение"""
    try:
        voice = ctx.channel.guild.voice_client
        if voice.is_playing() or voice.is_paused():
            voice.stop()
        if ctx.channel.guild.id in guilds_objects.keys():
            guilds_objects[ctx.channel.guild.id].is_loop = False
            guilds_objects[ctx.channel.guild.id].playing_song = ""
            guilds_objects[ctx.channel.guild.id].queue.clear()
    except Exception as e:
        # print(e,2)
        await ctx.send("Вы еще не добавили ни одного трека")

@commands.command(aliases=['remove', 'r'])
async def _remove(ctx, del_id):
    """Удаляет песню под указанным номером из очереди"""
    try:
        if int(del_id) <= len(guilds_objects[ctx.channel.guild.id].queue) and int(del_id) != 0:
            if guilds_objects[ctx.channel.guild.id].is_loop and int(del_id) == 1:
                await ctx.send("Вы не можете удалить зацикленный трек")
            else:
                guilds_objects[ctx.channel.guild.id].queue.pop(int(del_id)-1)
                await ctx.send("Трек был удален")
        else:
            await ctx.send("Трека под этим номером не существует")
    except Exception as e:
        # print(e,2)
        await ctx.send("Что то пошло не так")


@commands.command(name='resume')
async def _resume(ctx):
    """продолжает воспроизведение трека"""
    try:

        voice = ctx.channel.guild.voice_client

        if voice.is_paused():
            voice.resume()
            await ctx.send('Продолжаю...')

    except Exception as e:
        # print(e,2)
        await ctx.send("Вы еще не добавили ни одного трека")


# command to pause voice if it is playing
@commands.command(name='pause')
async def _pause(ctx):
    """Ставит трек на паузу"""
    try:
        voice = ctx.channel.guild.voice_client

        if voice.is_playing():
            voice.pause()
            await ctx.send('Пауза...')
    except Exception as e:
        # print(e,2)
        await ctx.send("Вы еще не добавили ни одного трека")

@commands.command(name='shuffle')
async def _shuffle(ctx):
    """Перемещивает песни в очереди"""
    try:
        id = ctx.channel.guild.id
        if not guilds_objects[id].is_loop:
            random.shuffle(guilds_objects[id].queue)
            await ctx.send("Перемешанно..")
        else:
            await ctx.send('Для перемешивания очереди отключите loop')
    except:
        await ctx.send("Что-то пошло не так")


@commands.command(name='loop')
async def _loop(ctx):
    """Зацикливает текущий трек (для отмены введите команду вновь)"""
    try:
        voice = ctx.channel.guild.voice_client
        if voice.is_playing():
            if not guilds_objects[ctx.channel.guild.id].is_loop:
                guilds_objects[ctx.channel.guild.id].is_loop = True
                guilds_objects[ctx.channel.guild.id].queue.insert(0,guilds_objects[ctx.channel.guild.id].playing_song)
                await ctx.send('Зацикливаю...')
            else:
                guilds_objects[ctx.channel.guild.id].is_loop = False
                guilds_objects[ctx.channel.guild.id].queue.pop(0)
                await ctx.send('Отмена цикла...')
        else:
            await ctx.send('Ни одна из песен не играет')
    except Exception as e:
        # print(e,2)
        await ctx.send("Что то пошло не так")




from ...misc.util import Guild_Objects, audio_player_task, YTDLSource, loop_add, get_video_info
