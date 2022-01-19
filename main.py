import asyncio
import discord

import config

from discord.ext import commands
from discord import FFmpegPCMAudio
from discord import TextChannel
from youtube_dl import YoutubeDL
import math
import random

from youtube_search import YoutubeSearch  

client = commands.Bot(command_prefix='-')  # prefix our commands with '.'

queues = {} 
is_loop = {}
last_song={}


@client.event  # check if bot is readyd
async def on_ready():
    print('Logged on')

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
	}
	FFMPEG_OPTIONS = {
		'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
		'options': '-vn',
	}


	def create_embed(self):
		embed = (discord.Embed(title='Сейчас играет',
							description='```css\n{0.title}\n```'.format(self),
							color=discord.Color.blurple())
				.add_field(name='Время прослушивания', value=self.duration)
				.add_field(name='Автор видео', value='[{0.uploader}]({0.uploader_url})'.format(self))
				.add_field(name='Ссылка(кликни)', value='[Click]({0.url})'.format(self))
				.set_thumbnail(url=self.thumbnail))

		return embed

	async def ytd_play(self, ctx, voice, info):
		URL = info['url']
		voice.play(FFmpegPCMAudio(URL, **self.FFMPEG_OPTIONS))
		
		self.data = info

		self.uploader = info.get('uploader')
		self.uploader_url = info.get('uploader_url')
		date = info.get('upload_date')
		self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
		self.title = info.get('title')
		self.thumbnail = info.get('thumbnail')
		self.duration = self.parse_duration(int(info.get('duration')))
		self.url = info.get('webpage_url')
		self.stream_url = info.get('url')
		if is_loop[ctx.channel.guild.id] != '1':
			await ctx.send(embed=self.create_embed())
		if not voice.is_playing():
			voice.play(FFmpegPCMAudio(URL, **self.FFMPEG_OPTIONS))


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




async def loop_add(ctx, voice, info, id,need_message, pos = -23):
	try:
		if not id in queues:
			queues[id] = [info]
			is_loop[id] = '0'
		else:
			if pos == -23:
				queues[id].append(info)
			else:
				if pos<=len(queues[id]) and pos>=0:
					if is_loop[id] == '1' and pos == 0:
						pos = 1
					queues[id].insert(pos, info)

				else:
					await ctx.send("Введенные данные неверны")
					return
					
		if need_message == 1:
			await ctx.send("Песня **{}** добавлена".format(info['title']))
	except Exception:
		await ctx.send('Что то пошло не так')

async def player(ctx, voice, info ,id):
	ydl = YTDLSource()
	await ydl.ytd_play(ctx, voice, queues[id][0])
	if is_loop[id] == '0':
		last_song[id] = queues[id][0]
		queues[id].pop(0)

	# print(queues)

async def audio_player_task(ctx, voice, id):
	timer = 0
	while True:
		timer += 2
		if id in queues:
			if queues[id] == ['final']:
				queues.pop(id)
				is_loop.pop(id)
				last_song.pop(id)
				break
		try:
			if not voice.is_playing() and not voice.is_paused():
				await player(ctx,voice,queues[id][0],id)
				timer = 0				
				await asyncio.sleep(2)
			else:
				# print(0)
				if not voice.is_paused():
					timer = 0
				await asyncio.sleep(2)
		except Exception as e:
			# print(e,2)
			await asyncio.sleep(2)
		if timer >= 1800:
			try:
				queues.pop(id)
			except KeyError:
				pass
			await voice.disconnect()
			break



# command for bot to join the channel of the user, if the bot has already joined and is in a different channel, it will move to the channel the user is in
@client.command(name='join')
async def _join(ctx):
	"""Добавляет бота в голосовой чат"""
	try:
		voice_channel = ctx.author.voice.channel
		voice = ctx.channel.guild.voice_client
		tmp = 1
		if voice is None:
			voice = await voice_channel.connect()
			tmp = 0
		elif voice.channel != voice_channel:
			await voice.move_to(voice_channel)
		if tmp == 0:
			await audio_player_task(ctx, voice, ctx.channel.guild.id)
	except AttributeError:
		await ctx.send("Для добавления бота требуется находиться в голосовом чате")



@client.command(name='play')
async def _play(ctx, *, url):
	"""Добавляет указанныю песню в очередь"""
	ydl = YTDLSource()

	try:
		voice_channel = ctx.author.voice.channel
		voice = ctx.channel.guild.voice_client
		tmp = 1
		if voice is None:
			voice = await voice_channel.connect()
			tmp = 0
		elif voice.channel != voice_channel:
			await voice.move_to(voice_channel)

		try:
			if url.find('https:') != -1 and url.find('https://www.youtube.com/watch?v=') != -1:
				with YoutubeDL(ydl.YDL_OPTIONS) as ydl1:
					info = ydl1.extract_info(url, download=False)
				URL = info['url']
				print(URL)
			else:
				if url.find('https://youtu.be/')!=-1:
					with YoutubeDL(ydl.YDL_OPTIONS) as ydl1:
						info = ydl1.extract_info(url, download=False)
					URL = info['url']
					print(URL)
				elif url.find('https:') == -1:
					raise KeyError
				else:
					raise Exception
		except KeyError:
			print(1)
			search = url
			yt = YoutubeSearch(search, max_results=1).to_dict()
			yt_id = yt[0]['id']
			yt_url = 'https://www.youtube.com/watch?v='+yt_id
			print(yt_url)
			with YoutubeDL(ydl.YDL_OPTIONS) as ydl1:
				info = ydl1.extract_info(yt_url, download=False)
		except Exception as e:
			await ctx.send("Что то пошло не так")
			# print(e)
		try:
			await loop_add(ctx, voice, info ,ctx.channel.guild.id, 1)
		except:
			pass
		if tmp == 0:
			tmp = 1
			await audio_player_task(ctx, voice, ctx.channel.guild.id)

		
	except AttributeError:
		await ctx.send("Перед добавлением песни нужно подключиться к голосовому чату")


@client.command(name='p')
async def _p(ctx, *, url):
	"""Сокращенный аналог play"""
	ydl = YTDLSource()

	try:
		voice_channel = ctx.author.voice.channel
		voice = ctx.channel.guild.voice_client
		tmp = 1
		if voice is None:
			voice = await voice_channel.connect()
			tmp = 0
		elif voice.channel != voice_channel:
			await voice.move_to(voice_channel)

		try:
			if url.find('https:') != -1 and url.find('https://www.youtube.com/watch?v=') != -1:
				with YoutubeDL(ydl.YDL_OPTIONS) as ydl1:
					info = ydl1.extract_info(url, download=False)
				URL = info['url']
				print(URL)
			else:
				if url.find('https://youtu.be/')!=-1:
					with YoutubeDL(ydl.YDL_OPTIONS) as ydl1:
						info = ydl1.extract_info(url, download=False)
					URL = info['url']
					print(URL)
				elif url.find('https:') == -1:
					raise KeyError
				else:
					raise Exception
		except KeyError:
			print(1)
			search = url
			yt = YoutubeSearch(search, max_results=1).to_dict()
			yt_id = yt[0]['id']
			yt_url = 'https://www.youtube.com/watch?v='+yt_id
			print(yt_url)
			with YoutubeDL(ydl.YDL_OPTIONS) as ydl1:
				info = ydl1.extract_info(yt_url, download=False)
		except Exception as e:
			await ctx.send("Что то пошло не так")
			# print(e)
		try:
			await loop_add(ctx, voice, info ,ctx.channel.guild.id, 1)
		except Exception:
			pass
		if tmp == 0:
			tmp = 1
			await audio_player_task(ctx, voice, ctx.channel.guild.id)

		
	except AttributeError:
		await ctx.send("Перед добавлением песни нужно подключиться к голосовому чату")

@client.command(name='insert')
async def _insert(ctx, pos, *, url):
	"""Позволяет вставить песню в любой место очереди."""
	ydl = YTDLSource()

	try:
		voice_channel = ctx.author.voice.channel
		voice = ctx.channel.guild.voice_client
		tmp = 1
		if voice is None:
			voice = await voice_channel.connect()
			tmp = 0
		elif voice.channel != voice_channel:
			await voice.move_to(voice_channel)

		try:
			if url.find('https:') != -1 and url.find('https://www.youtube.com/watch?v=') != -1:
				with YoutubeDL(ydl.YDL_OPTIONS) as ydl1:
					info = ydl1.extract_info(url, download=False)
				URL = info['url']
				print(URL)
			else:
				if url.find('https://youtu.be/')!=-1:
					with YoutubeDL(ydl.YDL_OPTIONS) as ydl1:
						info = ydl1.extract_info(url, download=False)
					URL = info['url']
					print(URL)
				elif url.find('https:') == -1:
					raise KeyError
				else:
					raise Exception
		except KeyError:
			search = url
			yt = YoutubeSearch(search, max_results=1).to_dict()
			yt_id = yt[0]['id']
			yt_url = 'https://www.youtube.com/watch?v='+yt_id
			print(yt_url)
			with YoutubeDL(ydl.YDL_OPTIONS) as ydl1:
				info = ydl1.extract_info(yt_url, download=False)
		except Exception:
			await ctx.send("Что то пошло не так")
		try:
			await loop_add(ctx, voice, info ,ctx.channel.guild.id, 1, int(pos)-1)
		except:
			await ctx.send("Формат команды должен быть -insert [место в очреди] [песня]")
		if tmp == 0:
			tmp = 1
			await audio_player_task(ctx, voice, ctx.channel.guild.id)

		
	except AttributeError:
		await ctx.send("Перед добавлением песни нужно подключиться к голосовому чату")

@client.command(name='shuffle')
async def _shuffle(ctx):
	"""Перемещивает песни в очереди"""
	try:
		id = ctx.channel.guild.id
		if not is_loop[id] == '1':
			random.shuffle(queues[id])
			await ctx.send("Перемешанно..")
		else:
			await ctx.send("Отключите loop перед использованием этой функции")
	except:
		await ctx.send("Что-то пошло не так")

@client.command(name='playlist')
async def _playlist(ctx,url, tmp = 1):
	'''Позволяет добавить целый плейлист в очередь(может работать нестабильно)'''
	if url.find('https://www.youtube.com/playlist') != -1 or url.find('https://youtube.com/playlist') != -1:
		if tmp!=0 and tmp!=1:
			await ctx.send('Напишите команду в формате -playlist [ссылка на плейлист]')
			return
	else:
		await ctx.send('Напишите команду в формате -playlist [ссылка на плейлист]')
		return

	try:
		voice_channel = ctx.author.voice.channel
		voice = ctx.channel.guild.voice_client
		if voice is None:
			voice = await voice_channel.connect()
			tmp = 0
		elif voice.channel != voice_channel:
			await voice.move_to(voice_channel)
		ydl = YTDLSource()

		event_loop = asyncio.get_event_loop()
		await ctx.send("Подождите немного")
		with YoutubeDL(ydl.YDL_OPTIONS) as ydl1:
			info = await event_loop.run_in_executor(None, lambda:ydl1.extract_info(url,download=False))
		URL = info
		for i in URL['entries']:
			try:
				await loop_add(ctx, voice, i ,ctx.channel.guild.id, 0)
			except:
				pass
		await ctx.send("**Плейлист добавлен**")
		if tmp == 0:
			tmp = 1
			await audio_player_task(ctx, voice, ctx.channel.guild.id)

	except AttributeError:
		await ctx.send("Скорее всего вы еще не в голосовом чате")
	except Exception as e:
		print(e)
		if tmp == 0:
			await add_playlist(ctx,url, 0)
		elif tmp == 1:
			await add_playlist(ctx,url)

async def add_playlist(ctx,url, tmp = 1):
	try:
		voice = ctx.channel.guild.voice_client
		ydl = YTDLSource()

		event_loop = asyncio.get_event_loop()
		with YoutubeDL(ydl.YDL_OPTIONS) as ydl1:
			info = await event_loop.run_in_executor(None, lambda:ydl1.extract_info(url,download=False))
		URL = info
		for i in URL['entries']:
			await loop_add(ctx, voice, i ,ctx.channel.guild.id, 0)
		await ctx.send("**Плейлист добавлен**")
		if tmp == 0:
			tmp = 1
			await audio_player_task(ctx, voice, ctx.channel.guild.id)


	except Exception as e:
		if tmp == 0:
			await add_playlist(ctx,url, 0)
		else:
			await add_playlist(ctx,url)


@client.command(name='loop')
async def _loop(ctx):
	"""Зацикливает текущий трек (для отмены введите команду вновь)"""
	try:
		voice = ctx.channel.guild.voice_client
		if voice.is_playing():
			if is_loop[ctx.channel.guild.id] != '1':
				is_loop[ctx.channel.guild.id] =	'1'
				queues[ctx.channel.guild.id].insert(0,last_song[ctx.channel.guild.id])
				await ctx.send('Зацикливаю...')
			else:
				is_loop[ctx.channel.guild.id] =	'0'
				queues[ctx.channel.guild.id].pop(0)
				await ctx.send('Отмена цикла...')
	except Exception as e:
		# print(e,2)
		await ctx.send("Что то пошло не так")

# command to resume voice if it is paused
@client.command(name='resume')
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
@client.command(name='pause')
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


@client.command(name='next')
async def _next(ctx):
	"""Включает следующий трек"""
	try:
		voice = ctx.channel.guild.voice_client

		if voice.is_playing() or voice.is_paused():
			if is_loop[ctx.channel.guild.id] == '1':
				is_loop[ctx.channel.guild.id] = '0'
				queues[ctx.channel.guild.id].pop(0)
			voice.stop()
	except Exception as e:
		# print(e,2)
		await ctx.send("Вы еще не добавили ни одного трека")

@client.command(name='n')
async def _n(ctx):
	"""Сокращенный аналог next"""
	try:
		voice = ctx.channel.guild.voice_client

		if voice.is_playing() or voice.is_paused():
			if is_loop[ctx.channel.guild.id] == '1':
				is_loop[ctx.channel.guild.id] = '0'
				queues[ctx.channel.guild.id].pop(0)
			voice.stop()
	except Exception as e:
		# print(e,2)
		await ctx.send("Вы еще не добавили ни одного трека")


# command to clear channel messages
@client.command(name='clear')
async def _clear(ctx):
	"""Очищает очередь на воспроизведение"""
	try:
		voice = ctx.channel.guild.voice_client
		if voice.is_playing() or voice.is_paused():
			voice.stop()
		if ctx.channel.guild.id in queues:
			is_loop = '0'
			last_song.pop(ctx.channel.guild.id)
			queues[ctx.channel.guild.id].clear()
	except Exception as e:
		# print(e,2)
		await ctx.send("Вы еще не добавили ни одного трека")

@client.command(name='queue')
async def _queue(ctx):
	"""Показыват какие треки сейчас в очереди"""
	try:
		queue = ''
		for i in range(len(queues[ctx.channel.guild.id])):
			if len(queue) < 3800:
				queue += '`{0}.` [**{1}**]\n'.format(i + 1, queues[ctx.channel.guild.id][i]['title'])
			else:
				break
		if queue!= '':
			embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(queues[ctx.channel.guild.id]), queue)))
			await ctx.send(embed=embed)
		else:
			await ctx.send("В очереди нет треков")
	except Exception as e:
		# print(e,2)
		await ctx.send("В очереди нет треков")

@client.command(name='q')
async def _q(ctx):
	"""Сокращенный аналог queue"""
	try:
		queue = ''
		for i in range(len(queues[ctx.channel.guild.id])):
			if len(queue) < 3800:
				queue += '`{0}.` [**{1}**]\n'.format(i + 1, queues[ctx.channel.guild.id][i]['title'])
			else:
				break
		if queue!= '':
			embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(queues[ctx.channel.guild.id]), queue)))
			await ctx.send(embed=embed)
		else:
			await ctx.send("В очереди нет треков")
	except Exception as e:
		# print(e,2)
		await ctx.send("В очереди нет треков")

@client.command(name='leave')
async def _leave(ctx):
	"""Убирает бота из голосового чата"""
	try:
		voice = ctx.channel.guild.voice_client
		if ctx.channel.guild.id in queues:
			queues[ctx.channel.guild.id] = ['final']
		if voice.is_playing() or voice.is_paused():
			voice.stop()
		await voice.disconnect()
		
	except Exception as e:
		# print(e,2)
		await ctx.send("Бот и так не в голосовом канале")

@client.command(name='remove')
async def _remove(ctx, del_id):
	"""Удаляет песню под указанным номером из очереди"""
	try:
		if int(del_id) <= len(queues[ctx.channel.guild.id]) and is_loop[ctx.channel.guild.id] != '1':
			queues[ctx.channel.guild.id].pop(int(del_id)-1)
			await ctx.send("Трек был удален")
		else:
			await ctx.send("Трека под этим номером не существует")
	except Exception as e:
		# print(e,2)
		await ctx.send("Что то пошло не так")

@client.command(name='r')
async def _r(ctx, del_id):
	"""Сокращенный аналог remove"""
	try:
		if int(del_id) <= len(queues[ctx.channel.guild.id]) and is_loop[ctx.channel.guild.id] != '1':
			queues[ctx.channel.guild.id].pop(int(del_id)-1)
			await ctx.send("Трек был удален")
		else:
			await ctx.send("Трека под этим номером не существует")
	except Exception as e:
		# print(e,2)
		await ctx.send("Что то пошло не так")

client.run(config.TOKEN)