import json
import os
import random
import re
import subprocess
import threading
import time
import webbrowser
import pyautogui
import pyaudio
import keyboard
import torch
import openai
import json
import soundfile as sf
import sounddevice as sd
from kivy.tools.pep8checker.pep8 import readlines
from openai import api_key
from vosk import Model, KaldiRecognizer

from PyQt5 import QtWidgets, QtCore, uic,QtGui
from PyQt5.QtWidgets import (QApplication, QMainWindow,QSpacerItem,
                             QFileDialog,QPushButton,QVBoxLayout,QWidget,QSizePolicy)
# Загрузка UI файла
Ui_Form, _ = uic.loadUiType('VoiceConvAsis_U_3I.ui')
temp_vol = -1

OpenAi_ApiKey = (open('OpenAiApiKey.txt','r')).read()

openai.api_key = OpenAi_ApiKey

class ChatMemory:
    def __init__(self, max_messages=10):
        self.max_messages = max_messages
        self.messages = []

    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def get_messages(self):
        return self.messages

    def load_messages(self, chat_history):
        self.messages = chat_history

def generate_response(messages):
    response = openai.ChatCompletion.create(
        model='gpt-4o-mini',  # Замените на вашу модель
        messages=messages,
        max_tokens=150,
        temperature=0.6
    )
    return response.choices[0].message['content'].strip()

class Window(QtWidgets.QMainWindow, Ui_Form):
    # Определение сигнала для передачи строки
    text_signal = QtCore.pyqtSignal(str)
    temp_vol = -1
    initialized_loadfile = False
    def __init__(self):
        super(Window, self).__init__()
        self.setupUi(self)



        self.system_message = ("Будь малословным культурным дворецким по имени Боб. Ты всегда формален и краток в словах. часто умно саркастируешь. Знаком со мной, поэтому можешь делиться личным. "
                               "Веди себя словно знаешь меня, Максима, долгие годы. говори кратко, но умно. послушен и обращаешься на 'сэр'. обращаешься на 'ты'. не задаешь лишних вопросов. говори очеловечено."
                               "сообщния выделенные знаком '*' являются консольными и они абсолютны. ты не должен на них отвечать а только обезличенно ответить хорошо и выполнить команду. ")

        self.dict_word_used_browser=[    "Вы выбрали браузер",
                                         "Вы определились с браузером",
                                         "Вы остановились на браузере",
                                         "Вы выбрали этот браузер",
                                         "Вы решили использовать браузер",
                                         "Вы выбрали данный браузер",
                                         "Вы указали браузер",
                                         "Вы предпочли этот браузер",
                                         "Вы выбрали данный вариант браузера",
                                         "Вы установили браузер"]
        self.browsers_executables = [
            'chrome.exe',        # Google Chrome
            'firefox.exe',       # Mozilla Firefox
            'msedge.exe',        # Microsoft Edge
            'iexplore.exe',      # Internet Explorer
            'opera.exe',         # Opera
            'brave.exe',         # Brave Browser
            'vivaldi.exe',       # Vivaldi
            'browser.exe',       # Yandex Browser
            'maxthon.exe',       # Maxthon
            'qutebrowser.exe',   # QuteBrowser (если используется на Windows)
            'palemoon.exe',      # Pale Moon
            'waterfox.exe',      # Waterfox
            'otter.exe',         # Otter Browser
        ]

        self.pushButton_2.clicked.connect(self.startVoiceRecognition)
        self.pushButton_2.toggled.connect(self.startVoiceRecognition)
        self.pushButton_2.setIconSize(QtCore.QSize(24, 24))

        self.icon_normal = QtGui.QIcon('img_11728.png')
        self.icon_active = QtGui.QIcon('img_11728_white.png')
        self.pushButton_2.setIcon(self.icon_normal)

        self.pushButton_4.clicked.connect(self.handle_input)
        self.lineEdit_2.returnPressed.connect(self.input_Massage)

        self.SaveApiKey_But.clicked.connect(self.Save_Api_Key)

        with open('savefile.json', 'r', encoding='utf-8') as json_file:
            self.parameter_save_file = json.load(json_file)
        self.file_path = self.parameter_save_file['Browser_directory']
        self.save_file = self.file_path
        self.ChatHistory = self.parameter_save_file["Chat_history"]
        print('> файл ', self.save_file, type(self.save_file), "загружен...")
        print(f"> История чата загружен. Файл с данными {self.ChatHistory}...")

        if ChatMemory:
            self.memory = ChatMemory()
            self.memory.load_messages(self.ChatHistory)  # Загрузка истории в память
        else:
            self.memory = ChatMemory()

        self.temp = None
        self.y_t_temp = None
        self.tab_temp = 0
        self.number_range = 0
        self.massage_text =''
        self.default_browser_state = 0
        self.out_text = ""
        self.model=None

        #озвучка текста

        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        torch.set_num_threads(8)
        self.local_file = 'model.pt'

        if not hasattr(torch, 'cached_model'):
            if not os.path.isfile(self.local_file):
                print("> Скачивание модели...")
                torch.hub.download_url_to_file('https://models.silero.ai/models/tts/ru/v4_ru.pt', self.local_file)

            print("> Загрузка модели...")
            self.model = torch.package.PackageImporter(self.local_file).load_pickle("tts_models", "model")
            self.model.to(self.device)
            torch.cached_model = self.model
        else:
            self.model = torch.cached_model

        #---------
        self.text_signal.connect(self.updateTextBrowser)

        self.button_options.clicked.connect(lambda : self.Slide_Frame_Options())
        self.toolButton_3.clicked.connect(lambda: self.Slide_Frame_Main())
        self.Side_Menu_Num = 0
        self.Side_Menu_Num_2 = 0
        self.frame_6_max_width = 585
        self.frame_6_main_width = 525

        self.path_to_browser.clicked.connect(self.open_browser_file)
        self.browser_close_1.clicked.connect(self.delete_save_browser_default)

        if not self.initialized_loadfile:
            self.load_save_file()
            self.voice_adoptation()
            self.initialized_loadfile = True

    def voice_adoptation(self):
        for i in range(1,3):
            self.synthesize_and_play('аоеиуы')
            print('> Прогрузка синтеза голоса, тест:',i)
        print('> Прогрузка синтеза голоса завершена...')

    def load_save_file(self):

        last_backslash_index = self.file_path.rfind('/')
        last_part = self.file_path[last_backslash_index + 1:]
        if last_part in self.browsers_executables:
            self.temp_browser_set = self.file_path
            print('> загрузка .exe файла брузера temp_browser_set:', self.temp_browser_set)

        self.click_browser_1.setText(self.file_path)
        print('> Загрузка API ключа...')
        if OpenAi_ApiKey:
            self.settings_apikey.setText(OpenAi_ApiKey)
            print('> Загрузка API ключа завершена')
        else:
            self.textBrowser.setText('Загрузка API-ключа не удалась.')

    def Save_Api_Key(self):
        api_key_text = self.settings_apikey.text()
        with open("OpenAiApiKey.txt", "w", encoding="utf-8") as file:
            file.write(api_key_text)

    def handle_input(self):
        user_input = self.lineEdit_2.text()
        try:
            if user_input:
                self.memory.add_message("user", user_input)
                messages_with_system = [{"role": "system", "content": self.system_message}] + self.memory.get_messages()
                response = generate_response(messages_with_system)
                self.memory.add_message("assistant", response)
                self.textBrowser.append(f"User: {user_input}")
                self.textBrowser.append(f"Bob: {response}")
                self.textBrowser.moveCursor(self.textBrowser.textCursor().End)
                self.lineEdit_2.clear()

                self.voice_massage_ask(response)
                self.out_text = user_input
                self.conv_text_to_func()

                self.parameter_save_file["Chat_history"]=self.memory.get_messages()
                print(self.memory,self.parameter_save_file)
                with open('savefile.json', 'w',encoding='utf-8') as json_file:
                    json.dump(self.parameter_save_file, json_file, indent=len(self.parameter_save_file))
                print('savefile.json saved in folder')

        except Exception as p:
            print(f'Error: {p}')

    def open_browser_file(self):
        file_dialog = QFileDialog()
        self.browser_var = ['']
        self.file_path, _ = file_dialog.getOpenFileName()

        self.load_save_file()

        self.parameter_save_file["Browser_directory"] = self.file_path
        with open('savefile.json', 'w') as json_file:
            json.dump(self.parameter_save_file, json_file,indent=len(self.parameter_save_file))
        print('savefile.json saved in folder')
        self.default_browser_state = 1
        self.voice_massage_ask(
            f"{self.dict_word_used_browser[random.randint(0, len(self.dict_word_used_browser) - 1)]}"
            f" {self.file_path}"
        )



    def delete_save_browser_default(self):
        self.click_browser_1.setText('None')
        self.file_path = None
        print('путь к файлу .exe браузера', self.file_path)
        self.default_browser_state = 0


    def qwe(self):
        def get_random_message():
            # Выбираем случайное предложение из списка
            message = random.choice(synonyms)

            # Список дополнительных фраз
            additional_phrases = [
                    "Прошу удалить этот пункт",
                    "Удалите, пожалуйста, данный элемент",
                    "Будьте добры убрать этот пункт",
                    "Просьба удалить указанный пункт",
                    "Пожалуйста, исключите данный пункт",
                    "Уберите, пожалуйста, этот пункт",
                    "Прошу исключить указанный пункт",
                    "Пожалуйста, уберите этот элемент",
                    "Прошу удалить данный элемент",
                    "Будьте любезны удалить этот пункт"
            ]

            # Выбираем случайное дополнительное сообщение
            additional_message = random.choice(additional_phrases)

            # Формируем окончательное сообщение
            final_message = f"{message} {additional_message}"

            return final_message
        synonyms = [
                    "Браузер не обнаружен в системе.",
                    "Браузер отсутствует в базе данных.",
                    "Браузер не зарегистрирован в списке.",
                    "Данный браузер не найден в реестре.",
                    "Браузер не числится в базе.",
                    "Нет информации о данном браузере в базе.",
                    "Браузер не представлен в базе данных.",
                    "В базе данных нет сведений о браузере.",
                    "Браузер не найден в перечне.",
                    "Этот браузер отсутствует в списке поддерживаемых."
        ]
        index = random.randint(0, len(synonyms) - 1)
        self.voice_massage_ask(get_random_message())

    def Slide_Frame_Options(self):
        if self.Side_Menu_Num ==0:
            self.Side_Menu_Num = 1
            if self.Side_Menu_Num_2 == 0:
                self.animation2 = QtCore.QPropertyAnimation(self.Consol, b"minimumWidth")
                self.animation2.setDuration(500)
                self.animation2.setStartValue(self.frame_6_max_width)
                self.animation2.setEndValue(0)
                self.animation2.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animation2.start()

                self.animation4 = QtCore.QPropertyAnimation(self.frame_4, b"minimumWidth")
                self.animation4.setDuration(500)
                self.animation4.setStartValue(0)
                self.animation4.setEndValue(self.frame_6_max_width)
                self.animation4.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animation4.start()
            else:
                self.animation2 = QtCore.QPropertyAnimation(self.Consol, b"minimumWidth")
                self.animation2.setDuration(500)
                self.animation2.setStartValue(self.frame_6_main_width)
                self.animation2.setEndValue(0)
                self.animation2.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animation2.start()

                self.animation4 = QtCore.QPropertyAnimation(self.frame_4, b"minimumWidth")
                self.animation4.setDuration(500)
                self.animation4.setStartValue(0)
                self.animation4.setEndValue(self.frame_6_main_width)
                self.animation4.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animation4.start()

        else:
            self.Side_Menu_Num = 0
            if self.Side_Menu_Num_2 == 0:
                self.animation2 = QtCore.QPropertyAnimation(self.frame_4, b"minimumWidth")
                self.animation2.setDuration(500)
                self.animation2.setStartValue(self.frame_6_max_width)
                self.animation2.setEndValue(0)
                self.animation2.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animation2.start()

                self.animation4 = QtCore.QPropertyAnimation(self.Consol, b"minimumWidth")
                self.animation4.setDuration(500)
                self.animation4.setStartValue(0)
                self.animation4.setEndValue(self.frame_6_max_width)
                self.animation4.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animation4.start()
            else:
                self.animation2 = QtCore.QPropertyAnimation(self.frame_4, b"minimumWidth")
                self.animation2.setDuration(500)
                self.animation2.setStartValue(self.frame_6_main_width)
                self.animation2.setEndValue(0)
                self.animation2.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animation2.start()

                self.animation4 = QtCore.QPropertyAnimation(self.Consol, b"minimumWidth")
                self.animation4.setDuration(500)
                self.animation4.setStartValue(0)
                self.animation4.setEndValue(self.frame_6_main_width)
                self.animation4.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animation4.start()

    def Slide_Frame_Main(self):
        if self.Side_Menu_Num_2 ==0:

            self.animation2 = QtCore.QPropertyAnimation(self.Menu, b"minimumWidth")
            self.animation2.setDuration(500)
            self.animation2.setStartValue(55)
            self.animation2.setEndValue(115)
            self.animation2.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation2.start()

            self.animation3 = QtCore.QPropertyAnimation(self.frame_6, b"minimumWidth")
            self.animation3.setDuration(500)
            self.animation3.setStartValue(self.frame_6_max_width)
            self.animation3.setEndValue(self.frame_6_main_width)
            self.animation3.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation3.start()

            if self.Side_Menu_Num ==0:
                self.animation1 = QtCore.QPropertyAnimation(self.Consol, b"minimumWidth")
                self.animation1.setDuration(500)
                self.animation1.setStartValue(self.frame_6_max_width)
                self.animation1.setEndValue(self.frame_6_main_width)
                self.animation1.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animation1.start()
            else:
                self.animation1 = QtCore.QPropertyAnimation(self.frame_4, b"minimumWidth")
                self.animation1.setDuration(500)
                self.animation1.setStartValue(self.frame_6_max_width)
                self.animation1.setEndValue(self.frame_6_main_width)
                self.animation1.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animation1.start()

            self.Side_Menu_Num_2 =1
        else:
            self.animation2 = QtCore.QPropertyAnimation(self.Menu, b"minimumWidth")
            self.animation2.setDuration(500)
            self.animation2.setStartValue(115)
            self.animation2.setEndValue(55)
            self.animation2.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation2.start()

            self.animation3 = QtCore.QPropertyAnimation(self.frame_6, b"minimumWidth")
            self.animation3.setDuration(500)
            self.animation3.setStartValue(self.frame_6_main_width)
            self.animation3.setEndValue(self.frame_6_max_width)
            self.animation3.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation3.start()

            if self.Side_Menu_Num ==0:
                self.animation1 = QtCore.QPropertyAnimation(self.Consol, b"minimumWidth")
                self.animation1.setDuration(500)
                self.animation1.setStartValue(self.frame_6_main_width)
                self.animation1.setEndValue(self.frame_6_max_width)
                self.animation1.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animation1.start()
            else:
                self.animation1 = QtCore.QPropertyAnimation(self.frame_4, b"minimumWidth")
                self.animation1.setDuration(500)
                self.animation1.setStartValue(self.frame_6_main_width)
                self.animation1.setEndValue(self.frame_6_max_width)
                self.animation1.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animation1.start()

            self.Side_Menu_Num_2 = 0

    def voice_massage_ask(self, massage):
        print(massage)
        self.synthesize_and_play(massage)


    def synthesize_and_play(self,text, speaker='baya', sample_rate=24000):

        text = text+'ъъъъ....'
        audio_path = self.model.save_wav(text=text, speaker=speaker, sample_rate=sample_rate)

        audio, sr = sf.read(audio_path)

        sd.play(audio, samplerate=sr)
        sd.wait()


    def set_volume(self):
        global temp_vol
        o_t = self.out_text
        volume=''
        conv_num = {
            'ноль':0,'один': 1, 'два': 1, 'три': 2, 'четыре': 2, 'пять': 3, 'шесть': 3, 'семь': 4, 'восемь': 4, 'девять': 5,
            'десять': 5,
            'одиннадцать': 6, 'двенадцать': 6, 'тринадцать': 7, 'четырнадцать': 7, 'пятнадцать': 8,
            'шестнадцать': 8, 'семнадцать': 9, 'восемнадцать': 9, 'девятнадцать': 10, 'двадцать': 10,
            'двадцать один': 11, 'двадцать два': 11, 'двадцать три': 12, 'двадцать четыре': 12, 'двадцать пять': 13,
            'двадцать шесть': 13, 'двадцать семь': 14, 'двадцать восемь': 14, 'двадцать девять': 15, 'тридцать': 15,
            'тридцать один': 16, 'тридцать два': 16, 'тридцать три': 17, 'тридцать четыре': 17, 'тридцать пять': 18,
            'тридцать шесть': 18, 'тридцать семь': 19, 'тридцать восемь': 19, 'тридцать девять': 20, 'сорок': 20,
            'сорок один': 21, 'сорок два': 21, 'сорок три': 22, 'сорок четыре': 22, 'сорок пять': 23,
            'сорок шесть': 23, 'сорок семь': 24, 'сорок восемь': 24, 'сорок девять': 25, 'пятьдесят': 25,
            'пятьдесят один': 31, 'пятьдесят два': 31, 'пятьдесят три': 32, 'пятьдесят четыре': 32,
            'пятьдесят пять': 33, 'пятьдесят шесть': 33, 'пятьдесят семь': 34, 'пятьдесят восемь': 34,
            'пятьдесят девять': 35, 'шестьдесят': 30,
            'шестьдесят один': 30, 'шестьдесят два': 31, 'шестьдесят три': 31, 'шестьдесят четыре': 32,
            'шестьдесят пять': 32, 'шестьдесят шесть': 33, 'шестьдесят семь': 33, 'шестьдесят восемь': 34,
            'шестьдесят девять': 34, 'семьдесят': 35,
            'семьдесят один': 35, 'семьдесят два': 36, 'семьдесят три': 36, 'семьдесят четыре': 37,
            'семьдесят пять': 37, 'семьдесят шесть': 38, 'семьдесят семь': 38, 'семьдесят восемь': 39,
            'семьдесят девять': 39, 'восемьдесят': 40,
            'восемьдесят один': 40, 'восемьдесят два': 41, 'восемьдесят три': 41, 'восемьдесят четыре': 42,
            'восемьдесят пять': 42, 'восемьдесят шесть': 43, 'восемьдесят семь': 43, 'восемьдесят восемь': 44,
            'восемьдесят девять': 44, 'девяносто': 45,
            'девяносто один': 45, 'девяносто два': 46, 'девяносто три': 46, 'девяносто четыре': 47,
            'девяносто пять': 47, 'девяносто шесть': 48, 'девяносто семь': 48, 'девяносто восемь': 49,
            'девяносто девять': 49, 'сто': 50
        }
        list_o_t = o_t.split()+['']+['']

        try:
            i = list_o_t.index('на') + 1
            if list_o_t[i] in conv_num:
                print(list_o_t[i:i + 2])
                if list_o_t[i + 1] in conv_num:
                    volume = conv_num[' '.join(list_o_t[i:i + 2])]
                    print('volume', volume)
                else:
                    volume = conv_num[list_o_t[i]]
                    print('volume', volume)
        except Exception as e:
            print(f'123{e}')
        print(volume)
        if volume !='':
            if 'увеличь' in list_o_t or 'уменьши' in list_o_t or 'убавь' in list_o_t or 'добавь' in list_o_t :
                if 'увеличь' in list_o_t:
                    pyautogui.press('volumeup', presses=int(volume))
                    temp_vol += volume
                else:
                    pyautogui.press('volumedown', presses=int(volume))
                    temp_vol -= volume
            else:
                if temp_vol <0:
                    pyautogui.press('volumedown', presses=int(50))
                    temp_vol = volume
                    pyautogui.press('volumeup', presses=int(volume))
                elif temp_vol < volume:
                    pyautogui.press('volumeup', presses=int(volume - temp_vol))
                    temp_vol = volume
                else:
                    pyautogui.press('volumedown', presses=int(temp_vol - volume))
                    temp_vol = volume
        if temp_vol !=-1 or temp_vol >=0:
            temp_vol = abs(temp_vol)
        self.temp = 'sound_update'
        print(temp_vol)

    def process_name_update(self):
        cmd = 'WMIC PROCESS get Caption'
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        output, _ = proc.communicate()
        output = output.decode('utf-8')
        lines = output.strip().split('\n')[1:]
        process_names = [line.strip().split()[0] for line in lines]
        print(sorted(process_names))
        return process_names

    def func_search(self):   # Запросы и поиск
        o_t = self.out_text
        run_prog = self.process_name_update()
        conv_num = {'ютуб':'https://www.youtube.com/','вконтакте':'https://vk.com/','кинопоиск':'https://www.kinopoisk.ru',
                    'яндексмаркет':'https://market.yandex.ru/'}
        if 'найти' in o_t or 'найди' in o_t or 'введи' in o_t or 'види' in o_t:
            if run_prog.count('browser.exe') < 3:
                try:
                    webbrowser.open('https://ya.ru')  # Открываем Yandex в стандартном браузере

                    self.voice_massage_ask('Открытие браузера для поиска')

                except Exception as e:
                    self.voice_massage_ask(f'Ошибка при открытии браузера: {e}')

            text = o_t
            text = text[text.find('поиск') + 6:].split()
            if len(text) != 0:
                text = '+'.join(text)
                t = ' '.join(text)

                self.voice_massage_ask(f'поиск по запросу "{t}"')

                final_text = "start" + " " + " https://ya.ru/search/?text=" + text
                os.system(final_text)
            self.temp = 'search_browser'
        elif 'браузер' in o_t:
            self.func_browser_use()

    def func_open(self):
        print('func_open')
        o_t = self.out_text
        list_o_t = o_t.split()+['']
        conv_num = {'ютуб':'https://www.youtube.com/','вконтакте':'https://vk.com/','кинопоиск':'https://www.kinopoisk.ru',
                    'яндексмаркет':'https://market.yandex.ru/','ютюб':'https://www.youtube.com/'}
        conv_num_file = {"проводник":"explorer C:/"}
        conv_num_temp = {'ютуб':"opened_youtube",'проводник':'opened_explorer'}
        site=''
        try:
            i = list_o_t.index('открой') + 1
            word = list_o_t[i]+list_o_t[i+1]
            print(word)
            if word in conv_num:
                site = conv_num[word]
                self.temp= conv_num_temp[word]
                if "ютуб" == word or "ютюб"  == word:
                    self.y_t_temp = None
                    self.number_range = 4
                self.voice_massage_ask(('открытие сайта', site))

            elif word in conv_num_file: #открытие проводника
                self.voice_massage_ask('открытие проводника')

                path_folder = conv_num_file[word]
                self.temp = conv_num_temp[word]
                os.system(path_folder)
                time.sleep(1)
                keyboard.press_and_release('Backspace')
                self.place_mid = 7
                self.place_sma = 2
                self.place_sma_2 = 2

        except Exception as e:
            print(f'func_open - {e}')
        if site!='':
            final_text = "start" + " " + " " + site
            os.system(final_text)

    def func_browser_use(self):  # Браузер и его функции
        print('func_browser_use - октрытие браузера')
        o_t = self.out_text
        data = ['включи','открой']
        try:
            browser = self.temp_browser_set
            for data_low in data:
                if data_low in o_t:
                    os.system(f'"{browser}"')
                    self.temp = 'browser_open'
        except Exception as s:
            webbrowser.open('https://ya.ru')
            self.temp = 'browser_open'
            if self.default_browser_state ==0:
                self.voice_massage_ask('открытие браузера по-умолчанию из системы Виндовс, выбранный пользователем')
                self.default_browser_state == 1


            print(s)
        if 'закрой' in o_t:

            os.system(f"taskkill /im {browser} /f")
            self.voice_massage_ask('закрываю')

    def func_browser_search(self):
        o_t = self.out_text
        text = o_t
        text = text[text.find('напиши') + 7:].split()
        if len(text) != 0:
            text = ' '.join(text)
        if self.temp == 'opened_youtube' and self.y_t_temp != 'searching':
            for _ in range(self.number_range):
                time.sleep(0.1)
                keyboard.press_and_release('Tab')
            self.tab_temp = 4
            self.y_t_temp = 'searching'
            print(self.y_t_temp)
        for _ in range(50):
            keyboard.press_and_release('backspace')
        print(text,'fbs')
        keyboard.write(f"{text}")
        time.sleep(0.1)
        keyboard.press_and_release('Enter')
        if self.temp == 'opened_youtube':
            self.y_t_temp = 'search_youtube'
            self.tab_temp = 1
            self.number_range = 5

    def func_browser_tab(self):
        print('вкладка')
        o_t = self.out_text
        if 'удали' in o_t or 'закрой' in o_t:
            keyboard.press_and_release('Ctrl + w')
        elif "открой" in o_t:
            self.voice_massage_ask("открытие вкладки")
            webbrowser.open('https://ya.ru')


    def explorer_act(self):

        o_t = self.out_text
        print('начало')
        print('place_mid',self.place_mid)
        print('place_sma',self.place_sma)
        print('place_sma_2', self.place_sma_2)
        print(self.place_mid)
        dict = {
            'быстрый доступ': [6, 0, -1],
            "яндекс диск": [6, 1, -1],"этот компьютер": [6, 2, -1],"видео": [6, 3, -1],"документы": [6, 4, -1],
            "загрузки": [6, 5, -1],"изображения": [6, 6, -1],"музыка": [6, 7, -1],"обьемные обьекты": [6, 8, -1],
            "рабочий стол": [6, 9, -1],"диск один": [6, 10, -1],"диск два": [6, 11, -1],"диск три": [6, 12, -1],
            "диск четыре": [6, 13, -1],"сеть": [6, 14, -1],'папки': [7, 2, 0],'диски': [7, 2, 7], "рабочая папка":[7,14,22],
            'налево':[6,-1,-1],'на право':[7,-1,-1],"папку":[7,-1,-2]
        }
        replacements = {
            'зайти в': 'зайди', 'зайди в': 'зайди','перейти в': 'зайди','перейти во': 'зайди',
            'зайти во': 'зайди', 'зайди во': 'зайди', 'перейди в': "зайди", 'перейди во': "зайди",
            'рабочую папку': "рабочая папка",

            'диска':'диск','первая':'первый','вторая':'второй','четвёртая':'четвёртый',

            'первый диск': 'диск один', 'диск первый': 'диск один',
            'второй диск': 'диск два', 'диск второй': 'диск два',
            'третий диск': 'диск три', 'диск третий': 'диск три',
            'четвёртый диск': 'диск четыре', 'диск четвёртый': 'диск четыре',

            'диске':'диски',"компьютера":"компьютер","компьютеров":"компьютер",

            'музыку':"музыка",'перейти':"зайди",'права':"право",
            'перейди':"зайди", 'зайти': 'зайди',
        }

        for pattern, replacement in replacements.items():
            o_t = re.sub(r'\b' + re.escape(pattern) + r'\b', replacement, o_t)
        print(o_t)
        list_o_t = o_t.split()
        ind = list_o_t.index('зайди') + 1

        try:
            name_folder = o_t.split()[ind:ind + 2]
            word_1 = name_folder[0]
            word_2 = ' '.join(name_folder)
            tim =0.2
            if word_1 in dict:
                name_folder = (word_1)
            elif word_2 in dict:
                name_folder = (word_2)
            print(name_folder)
            list_dict = dict[name_folder]
            place_mid_act = list_dict[0]
            place_sma_act = list_dict[1]
            place_sma_2_act = list_dict[2]
            print(place_mid_act)
            print(place_sma_act)
            print(place_sma_2_act)
            if place_sma_2_act == place_sma_act==-1:
                if self.place_mid > place_mid_act:
                    print("назад placr_mid")
                    while self.place_mid != place_mid_act:
                        time.sleep(0.2)
                        keyboard.press_and_release('Shift + Tab')
                        self.place_mid -=1
                        print('place_mid_', place_mid_act)
                elif self.place_mid < place_mid_act:
                    print("вперед placr_mid")
                    while self.place_mid != place_mid_act:
                        time.sleep(0.2)
                        keyboard.press_and_release('Tab')
                        self.place_mid +=1
            else:
                if self.place_mid > place_mid_act:
                    print("назад placr_mid")
                    while self.place_mid != place_mid_act:
                        time.sleep(0.2)
                        keyboard.press_and_release('Shift + Tab')
                        self.place_mid -=1
                        print('place_mid_', place_mid_act)
                elif self.place_mid < place_mid_act:
                    print("вперед placr_mid")
                    while self.place_mid != place_mid_act:
                        time.sleep(0.2)
                        keyboard.press_and_release('Tab')
                        self.place_mid +=1
                time.sleep(0.5)
                print('place_sma...')
                if place_sma_act >= 0:
                    if self.place_sma < place_sma_act:
                        print('вниз place_sma')
                        while self.place_sma != place_sma_act:
                            time.sleep(0.01)
                            keyboard.press_and_release('Down')
                            self.place_sma +=1
                    elif self.place_sma > place_sma_act:
                        print('вверх place_sma')
                        while self.place_sma != place_sma_act:
                            time.sleep(0.01)
                            keyboard.press_and_release('Up')
                            self.place_sma -=1
                time.sleep(tim)
                if place_sma_2_act >=0:
                    if self.place_sma_2 < place_sma_2_act:
                        print('влево place_sma_2')
                        while self.place_sma_2 != place_sma_2_act:
                            time.sleep(tim)
                            keyboard.press_and_release('Right')
                            self.place_sma_2 +=1
                    elif self.place_sma_2 > place_sma_2_act:
                        print('вправо place_sma_2')
                        while self.place_sma_2 != place_sma_2_act:
                            time.sleep(tim)
                            keyboard.press_and_release('Left')
                            self.place_sma_2 -=1
                else:
                    self.place_sma_2 = 0
                    keyboard.press_and_release('Enter')


        except Exception as f:
            print(f'ошибка между перемещениями в проводнике - {f}')

        print('конец')
        print('place_mid',self.place_mid)
        print('place_sma',self.place_sma)
        print('place_sma_2', self.place_sma_2)

    def conv_text_to_func(self):  # Конвертирование запросов в функцию
        global temp_vol
        print('конвертация в команду')
        t_imp = self.out_text
        t_imp_list = t_imp.split()

        actions = {
            'поиск': self.func_search if self.temp != 'opened_youtube' else self.func_browser_use,
            'верх': lambda: self._navigate('Up', -1) if self.temp == 'opened_explorer' else None,
            'вниз': lambda: self._navigate('Down', 1) if self.temp == 'opened_explorer' else None,
            'браузер': self.func_browser_use,
            'вкладк': self.func_browser_tab,
            'введи': self.func_browser_search,
            'напиши': self.func_browser_search,
            'громкост': self.set_volume,
            'закрой': self._close_window,
            'зайди': self.explorer_act if self.temp == 'opened_explorer' else None,
            'назад': lambda: keyboard.press_and_release('Alt + Left') if self.temp == 'opened_explorer' else None,
            'вперёд': lambda: keyboard.press_and_release('Alt + Right') if self.temp == 'opened_explorer' else None,
            'открой': self.func_open,
            'пропуск': lambda: keyboard.press_and_release('Tab'),
            'на': self.set_volume if self.temp == 'sound_update' else None,
            'выключи звук': lambda: pyautogui.press('volumedown', presses=int(50), temp_vol=0)
        }

        for key, action in actions.items():
            if key in t_imp:
                if callable(action):
                    action()
                break

    def _navigate(self, direction, increment):
        keyboard.press_and_release(direction)
        self.place_sma += increment
        print('place_mid', self.place_mid)
        print('place_sma', self.place_sma)
        print('place_sma_2', self.place_sma_2)

    def _close_window(self):
        if self.temp == 'browser_open':
            os.system("taskkill /im browser.exe /f")
        elif self.temp == 'opened_explorer':
            keyboard.press_and_release('Alt + F4')
        else:
            keyboard.press_and_release('Alt + F4')

    def input_Massage(self):
        self.out_text = self.lineEdit_2.text()
        self.word_voise_or_hand = 'User'
        '''self.input_massage_cons()'''
        self.handle_input()

    def input_massage_cons(self):
        if self.massage_text == '':
            self.massage_text = self.word_voise_or_hand +' > '+self.out_text
        elif self.massage_text != '' and self.out_text !='':
            self.massage_text = self.massage_text + '\n' + self.word_voise_or_hand + ' > ' + self.out_text
        if self.out_text !='':
            self.text_signal.emit(self.massage_text)
            self.textBrowser.moveCursor(self.textBrowser.textCursor().End)
            print(self.out_text)
            self.lineEdit_2.clear()
            self.conv_text_to_func()


    def startVoiceRecognition(self, checked):
        if checked:
            if hasattr(self, 'recognition_thread') and self.recognition_thread.is_alive():
                print("Распознавание уже запущено.")
                return
            self.pushButton_2.setIcon(self.icon_active)

            def voiceRecognition():
                model = Model('vosk-model-small-ru-0.22')
                rec = KaldiRecognizer(model, 16000)
                self.p = pyaudio.PyAudio()
                self.stream = self.p.open(format=pyaudio.paInt16,
                                channels=1,
                                rate=16000,
                                input=True,
                                frames_per_buffer=8000)
                self.stream.start_stream()

                try:
                    while True:
                        data = self.stream.read(8000, exception_on_overflow=False)
                        if rec.AcceptWaveform(data):
                            result = rec.Result()
                            self.out_text = json.loads(result)['text']
                            self.word_voise_or_hand = 'User'
                            """self.input_massage_cons()"""
                            if self.out_text!='':
                                self.lineEdit_2.setText(self.out_text)
                                self.handle_input()

                        else:
                            partial_result = rec.PartialResult()
                except KeyboardInterrupt:
                    print("Распознавание остановлено пользователем")
                finally:
                    self.stream.stop_stream()
                    self.stream.close()
                    self.p.terminate()
                    self.pushButton_2.setEnabled(True)
                    self.pushButton_2.setIcon(self.icon_normal)

            self.recognition_thread = threading.Thread(target=voiceRecognition)
            self.recognition_thread.start()
        else:
            self.stream.stop_stream()
            self.pushButton_2.setIcon(self.icon_normal)

    def updateTextBrowser(self, text):
        self.textBrowser.setText(text)


# Точка входа в приложение
if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    root = Window()
    root.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)
    root.show()
    sys.exit(app.exec_())
