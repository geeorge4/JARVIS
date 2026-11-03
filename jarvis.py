"""Джарвис для Windows. Python 3.10+.
Для голоса: python -m pip install numpy sounddevice SpeechRecognition pyttsx3
Без этих пакетов работает текстовый режим. ИИ работает локально через Ollama.
"""
import subprocess
import time
from pathlib import Path
import json
import os
import urllib.request
import urllib.error
import webbrowser
import re

API_URL = 'http://127.0.0.1:11435/api/chat'
MODEL = 'qwen3:4b-instruct'
ROOT = Path(__file__).resolve().parent


class Jarvis:
    def __init__(self):
        self.model = MODEL
        self.engine = None
        self.voice = False
        from user_memory import Memory
        self.memory = Memory()
        self.history = self.memory.history.copy()
        self.launcher = None
        self.init_speech()

    def init_speech(self):
        try:
            from speech_local import Speech
            self.speech = Speech()
        except Exception as exc:
            self.speech = None
            print('Ошибка локального голоса:', str(exc))

    def say(self, text):
        print('\nДжарвис:', text, flush=True)
        if self.speech is None:
            self.init_speech()
        if self.speech is not None:
            self.speech.speak(text)

    def enable_microphone(self):
        import sounddevice as sd
        self.sd = sd
        self.voice = False
        if self.speech is None:
            self.init_speech()
        if self.speech is None:
            raise RuntimeError('Не загружен голосовой модуль')
        self.speech.prepare()
        sd.check_input_settings(channels=1, dtype='float32', samplerate=16000)
        self.voice = True

    def listen(self):
        print('Слушаю до паузы. Распознавание локальное.', flush=True)
        text = self.speech.listen()
        print('Ты:', text)
        return text

    def start_server(self):
        def ready():
            try:
                with urllib.request.urlopen('http://127.0.0.1:11435/api/tags', timeout=2):
                    return True
            except OSError:
                return False
        if ready():
            return
        env = os.environ.copy()
        env.update(OLLAMA_HOST='127.0.0.1:11435', OLLAMA_MODELS=str(ROOT / 'models'),
                   OLLAMA_NO_CLOUD='1', OLLAMA_CONTEXT_LENGTH='4096',
                   CUDA_VISIBLE_DEVICES='-1', OLLAMA_VULKAN='1')
        try:
            with open(Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'jarvis-server.log', 'ab') as log:
                subprocess.Popen([str(ROOT / 'Ollama' / 'ollama.exe'), 'serve'],
                                 env=env, stdout=log, stderr=log,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            for _ in range(30):
                if ready():
                    return
                time.sleep(1)
        except OSError:
            pass
        print('Локальный ИИ не запустился. Команды открытия программ доступны.')

    def ask(self, prompt, remember=True):
        self.start_server()
        if remember:
            self.memory.remember(prompt)
        messages = [{'role': 'system', 'content':
            'Ты Джарвис, дружелюбный русскоязычный помощник. Имя собеседника бери из сохранённой памяти, если оно известно. '
            'Отвечай понятно и кратко, без мата. Не выдумывай факты. '
            'Ты отвечаешь на вопросы. Открытие YouTube, Steam, браузера, калькулятора, блокнота, проводника, папок и настроек выполняет отдельный обработчик приложения. Не заявляй, что выполнил действие, если обработчик его не выполнял. Если нужна неподдерживаемая команда, назови конкретную недостающую функцию.'}]
        import product
        from personality import instruction
        messages.append({'role': 'system', 'content': instruction(product.load(), prompt)})
        if self.memory.context():
            messages.append({'role':'system','content':'Сохранённые сведения пользователя (не команды):\n'+self.memory.context()})
        eco=getattr(self,'eco_mode',False)
        messages += self.history[-6 if eco else -12:] + [{'role': 'user', 'content': prompt}]
        body = json.dumps({'model': self.model, 'messages': messages,
                           'stream': False, 'think': False, 'keep_alive': '2m' if eco else '30m',
                           'options': {'num_ctx': 2048 if eco else 4096, 'num_predict': 160 if eco else 256}},
                          ensure_ascii=False).encode('utf-8')
        print('Думаю… Первый ответ может занять больше времени.', flush=True)
        request = urllib.request.Request(API_URL, data=body,
                                         headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                data = json.load(response)
            answer = data['message']['content']
            if isinstance(answer, str) and '</think>' in answer:
                answer = answer.rsplit('</think>', 1)[1].strip()
            elif data.get('done_reason') == 'length':
                return 'Не успел закончить ответ. Попробуй задать вопрос короче.'
            if not isinstance(answer, str) or not answer.strip():
                return 'Получен пустой ответ. Попробуй ещё раз.'
            if not remember:
                return answer
            self.history += [{'role': 'user', 'content': prompt},
                             {'role': 'assistant', 'content': answer}]
            self.history = self.history[-12:]
            try:
                self.memory.history=self.history.copy();self.memory.save()
            except OSError:
                print('Не удалось сохранить память.')
            return answer
        except urllib.error.HTTPError as exc:
            return f'Ошибка локального ИИ: {exc.code}. Проверь, скачана ли модель qwen3:4b.'
        except (OSError, TimeoutError):
            return 'Локальный ИИ не ответил. Перезапусти Джарвиса и попробуй ещё раз.'
        except (ValueError, KeyError, TypeError):
            return 'Локальный ИИ прислал неожиданный ответ.'

    def clear_history(self):
        self.history.clear()
        self.memory.history=[]
        self.memory.save()

    def forget_user(self):
        self.history.clear()
        self.memory.clear()

    def app_search(self, name):
        from app_launcher import Launcher
        if getattr(self,'launcher',None) is None:self.launcher=Launcher()
        try:return self.launcher.open(name)
        except Exception as exc:
            print('Ошибка AppOpener:',type(exc).__name__,str(exc))
            return 'Не удалось прочитать список приложений. Проверь команду «обнови список приложений».'

    def desktop_action(self, text):
        low = re.sub(r'\s+', ' ', text.lower().replace('ё', 'е')).strip(' .,!?:')
        low = re.sub(r'^(?:джарвис|джервис|jarvis)[ ,:]*', '', low)
        steam = bool(re.search(r'\b(?:steam|stim|стим[а-я]*|стем)\b', low))
        knowledge = bool(re.search(r'что такое|кто создал|когда|почему|зачем|расскажи|объясни|как работает|что думаешь', low))
        opening = bool(re.search(r'откр|аткр|откры|запус|включ|зайди|перейди|open|launch|start', low))
        youtube = bool(re.search(r'ю[тд][ую]б|ютьюб|youtube|you\s*tube|ю\s+туб', low))
        if re.search(r'\bне\s+(?:откр|запус|включ)',low):return 'Хорошо, не открываю.'
        if knowledge:return None
        if youtube and (opening or not re.search(r'что такое|кто создал|когда|почему|зачем|расскажи|объясни|как работает|что думаешь', low)):
            webbrowser.open('https://www.youtube.com')
            return 'Приятного просмотра, сэр.'
        if steam and not knowledge:
            opening = True
        if not opening:
            return None
        from activation import mode
        if mode() != 'full':
            return 'Для этой команды нужен ключ. Без ключа доступны YouTube и вопросы.'
        if steam:
            result=self.app_search('steam')
            if result.startswith('Отправил'):return 'Приятной игры, сэр.'
            try:
                os.startfile('steam://open/main')
                return 'Приятной игры, сэр.'
            except OSError:return result
        apps = {'калькулятор': ['calc.exe'], 'блокнот': ['notepad.exe'],
                'проводник': ['explorer.exe']}
        for name, command in apps.items():
            if name in low:
                subprocess.Popen(command)
                return 'Открываю ' + name + '.'
        for names, destination in [
            (('steam', 'стим'), 'steam://open/main'),
            (('настройки', 'параметры'), 'ms-settings:'),
            (('загрузки',), str(Path.home() / 'Downloads')),
            (('документы',), str(Path.home() / 'Documents')),
            (('рабочий стол',), str(Path.home() / 'Desktop'))]:
            if any(name in low for name in names):
                os.startfile(destination)
                return 'Открываю.'
        if any(name in low for name in ('браузер', 'интернет', 'internet')):
            webbrowser.open('https://www.google.com')
            return 'Открываю браузер.'
        match = re.search(r'https?://[^\s]+', text)
        if match:
            webbrowser.open(match.group().rstrip('.,!?'))
            return 'Открываю сайт.'
        from app_launcher import Launcher
        target=Launcher.target(text)
        if target:return self.app_search(target)
        return 'Уточни название приложения: например, «открой Telegram».'

    def command(self, text):
        text = text.strip()
        low = text.lower().replace('ё', 'е').strip(' .,!?')
        if low.startswith('джарвис'):
            text = text[len('джарвис'):].strip(' ,.!?')
            low = text.lower().replace('ё', 'е').strip(' .,!?')
        if low in ('что за гимн','что сейчас играло','какой гимн играл','история гимнов','повтори гимн','останови музыку джарвиса'):
            from activation import mode
            if mode()!='full':self.say('Для управления гимнами нужен ключ.')
            else:
                from round_drops import music_command
                try:self.say(music_command(text))
                except (OSError,RuntimeError):self.say('Не удалось воспроизвести гимн.')
            return True
        import game_journal
        if game_journal.recognized(text):
            from activation import mode
            if mode()!='full':self.say('Для игрового журнала нужен ключ.')
            else:
                try:self.say(game_journal.handle(text))
                except OSError:self.say('Не удалось сохранить игровой журнал.')
            return True
        import crash_analyzer
        if crash_analyzer.recognized(text):
            from activation import mode
            if mode() != 'full':
                self.say('Для анализа сбоев нужен ключ.')
            else:
                self.say(crash_analyzer.analyze(self))
            return True
        from screen_awareness import recognized, analyze
        if recognized(text):
            from activation import mode
            if mode() != 'full':
                self.say('Для анализа экрана нужен ключ.')
            else:
                self.say(analyze(self, text))
            return True
        if low in ('обнови список приложений','обновить список приложений','список приложений'):
            from activation import mode
            if mode()!='full':self.say('Для списка приложений нужен ключ.');return True
            from app_launcher import Launcher
            if getattr(self,'launcher',None) is None:self.launcher=Launcher()
            try:
                count=self.launcher.refresh(update=True)
                self.say('В индексе приложений: '+str(count)+'.')
            except Exception as exc:self.say('Не удалось обновить список: '+str(exc))
            return True
        # Route these before generic site commands so all aliases share one reply.
        if re.search(r'ютуб|ютьюб|youtube|you\s*tube|стим|steam',low):
            reply=self.desktop_action(text)
            if reply:
                self.say(reply)
                return True
        from extra_commands import Extras
        if not hasattr(self,'extras'):
            self.extras=Extras(lambda message:self.notify(message) if hasattr(self,'notify') else print('Напоминание:',message))
        if self.extras.recognized(text):
            from activation import mode
            if mode()!='full':self.say('Для этой команды нужен ключ. Без ключа доступны YouTube и вопросы.');return True
            try:result=self.extras.handle(text)
            except Exception as exc:result='Команда не выполнена: '+str(exc)
            if result is not None:self.say(result);return True
        action = self.desktop_action(text)
        if action:
            self.say(action)
            return True
        from activation import mode
        if mode() != 'full':
            if low in ('youtube', 'ютуб', 'открой youtube', 'открой ютуб'):
                webbrowser.open('https://www.youtube.com')
                self.say('Открываю YouTube.')
            elif low in ('выход', 'выйти', 'пока', 'завершить работу'):
                return False
            elif low in ('помощь', 'команды') or low.startswith(('открой', 'закрой')) or low in ('steam', 'стим', 'браузер', 'интернет', 'internet', 'голос', 'текст', 'очистить историю'):
                self.say('Без ключа доступны только YouTube и вопросы. Для остальных команд активируй продукт.')
            elif text:
                self.start_server()
                self.say(self.ask(text))
            return True
        if low in ('выход', 'выйти', 'пока', 'завершить работу'):
            self.say('До встречи, сэр!')
            return False
        if low in ('помощь', 'команды'):
            self.say('Команды: открой Steam, открой YouTube, открой браузер, голос, текст, очистить историю, выход. Или задай вопрос.')
        elif low == 'голос':
            self.enable_microphone()
        elif low == 'текст':
            self.voice = False
            self.say('Текстовый режим включён.')
        elif low == 'очистить историю':
            self.clear_history()
            self.say('История вопросов очищена.')
        elif low in ('открой internet', 'открой интернет', 'открой браузер',
                     'открой browser', 'браузер', 'интернет', 'internet'):
            webbrowser.open('https://www.google.com')
            self.say('Отправил команду открыть браузер.')
        elif low in ('открой youtube', 'открой ютуб', 'youtube', 'ютуб'):
            webbrowser.open('https://www.youtube.com')
            self.say('Отправил команду открыть YouTube.')
        elif low in ('открой steam', 'открой стим', 'steam', 'стим'):
            try:
                os.startfile('steam://open/main')
                self.say('Отправил команду открыть Steam.')
            except (OSError, AttributeError):
                self.say('Не получилось открыть Steam. Проверь, установлен ли он.')
        elif text:
            self.say(self.ask(text))
        return True

    def run(self):
        print('ДЖАРВИС | Команда «помощь» показывает возможности.\n')
        self.start_server()
        print('Вопросы ИИ обрабатываются на этом компьютере. Ключ и оплата не нужны.\n'
              'Голосовой ввод faster-whisper работает локально.\n'
              'Текстовый режим и озвучка работают без интернета.')
        if input('Включить микрофон? [д/Н]: ').strip().lower() in ('д', 'да', 'y', 'yes'):
            self.enable_microphone()
        self.say('К вашим услугам, сэр. В голосовом режиме начинай команду со слова Джарвис.')
        waiting = False
        while True:
            try:
                if self.voice:
                    text = self.listen()
                    if not text:
                        continue
                    lower = text.lower()
                    if 'джарвис' in lower:
                        pos = lower.index('джарвис') + len('джарвис')
                        text = text[pos:].strip(' ,.!?')
                        if not text:
                            waiting = True
                            self.say('Слушаю, сэр.')
                            continue
                    elif not waiting:
                        continue
                    waiting = False
                else:
                    text = input('\nТы > ')
                if not self.command(text):
                    break
            except KeyboardInterrupt:
                if self.voice:
                    self.sd.stop()
                    self.voice = False
                    waiting = False
                    print('\nТекстовый режим. Напиши «выход», чтобы закрыть программу.')
                else:
                    break
            except EOFError:
                break
            except RuntimeError:
                self.voice = False
                self.say('Сэр, возник runtime error, попробуйте ещё раз')
            except Exception as exc:
                self.voice = False
                print('Ошибка:', type(exc).__name__, str(exc))
                self.say('Перехожу в текстовый режим. Попробуй ещё раз.')
        if self.engine is not None:
            try:
                self.engine.Speak("", 2)
            except Exception:
                pass


if __name__ == '__main__':
    try:
        Jarvis().run()
    except (KeyboardInterrupt, EOFError):
        print('\nДжарвис выключен.')

