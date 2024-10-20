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
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QThread,pyqtSignal
from PyQt5.QtWidgets import QDialog, QPushButton, QVBoxLayout, QLabel
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QApplication, QDialog
from PyQt5.QtWidgets import QWidget
from vosk import Model, KaldiRecognizer
from PyQt5 import QtWidgets, QtCore, uic,QtGui
from PyQt5.QtWidgets import (QFileDialog)

from test import size_font

# Загрузка UI файла
Ui_Form, _ = uic.loadUiType('VoiceConvAsis_U_3I.ui')
Ui_Form_sub, _ = uic.loadUiType('Threaded_sub_window.ui')
temp_vol = -1

file_name = 'OpenAiApiKey.txt'
if not os.path.exists(file_name):
    open(file_name, 'w',encoding='utf-8').close()
with open(file_name, 'r',encoding='utf-8') as file:
    OpenAi_ApiKey = file.read()

openai.api_key = OpenAi_ApiKey

with open('savefile.json', 'r', encoding='utf-8') as json_file:
    parameter_save_file = json.load(json_file)
Number_of_tokens = parameter_save_file['Number_of_tokens']
Temperature = parameter_save_file['Temperature']

Min_STime_Question = parameter_save_file['Question_Interval_min']
Max_STime_Question = parameter_save_file['Question_Interval_max']

Manner_Voice_CP = parameter_save_file['Manner_Voice_CP']
History_Mem_CP = parameter_save_file['History_Mem_CP']
Personality_CP = parameter_save_file['Personality_CP']

Speaker_Voice = parameter_save_file['Speaker_Voice']

class ChatMemory:
    def __init__(self, max_messages=15):
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
    global Number_of_tokens, Temperature
    response = openai.ChatCompletion.create(
        model='gpt-4o-mini',  # Замените на вашу модель
        messages=messages,
        max_tokens=Number_of_tokens,
        temperature=Temperature
    )
    return response.choices[0].message['content'].strip()

class Sub_Win(QMainWindow):
    def __init__(self, thread):
        super().__init__()
        try:
            self.ui = uic.loadUi("Threaded_sub_window.ui", self)
            self.thread = thread
            screen = QApplication.primaryScreen()
            screen_size = screen.size()

            self.setWindowFlag(Qt.WindowStaysOnTopHint)
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.setWindowFlags(Qt.FramelessWindowHint)
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.move(int(screen_size.width()/2-250),int(screen_size.height())-150)
            self.screen_heights = {720:0, 1080:4, 1440:8, 2160:12, 2880:16, 4320:20}

            self.label.setStyleSheet (''
                                         'color:rgb(220, 220, 220);'
                                         'background:rgba(40,40,40,0);'
                                         'padding-left:10px;'
                                         'font-family: "TimesNewRoman";'
                                         f'font-size:{20+self.screen_heights[int(screen_size.height())]}px;'
                                         '')

            self.thread.send_param.connect(self.update_label)
        except Exception as e:
            print(f"Ошибка при инициализации Sub_Win: {e}")

    def update_label(self, text):
        self.label.setText(text)

class ThreadWindow(QThread):
    threadSignal = pyqtSignal(int)
    send_param = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.message = ''

    def set_message(self, text):
        self.message = text

    def run(self):
        self.send_param.emit(f"Сообщение {self.message}")  # Отправляем текст

    def stop(self):
        self.running = False

class Window(QtWidgets.QMainWindow, Ui_Form):
    text_signal = QtCore.pyqtSignal(str)
    temp_vol = -1
    initialized_loadfile = False

    def __init__(self):
        super(Window, self).__init__()
        self.setupUi(self)
        """self.setWindowFlag(Qt.FramelessWindowHint)"""
        self.system_message = Personality_CP + History_Mem_CP + Manner_Voice_CP

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

        self.deactivate_voice.clicked.connect(self.off_or_on_sint_voice)
        self.deactivate_voice.toggled.connect(self.off_or_on_sint_voice)
        self.deactivate_voice.setIconSize(QtCore.QSize(20, 20))

        self.icon_normal = QtGui.QIcon('icon/img_11728.png')
        self.icon_active = QtGui.QIcon('icon/img_11728_white.png')
        self.icon_voice_normal = QtGui.QIcon('icon/sound_asis_on.png')
        self.icon_voice_active = QtGui.QIcon('icon/sound_asis_off.png')

        self.pushButton_2.setIcon(self.icon_normal)
        self.deactivate_voice.setIcon(self.icon_voice_normal)
        self.check_activate_sint_voice = True

        self.pushButton_4.clicked.connect(self.handle_input)
        self.lineEdit_2.returnPressed.connect(self.input_Massage)

        self.SaveApiSet_But.clicked.connect(self.Save_OpenAI_settings)
        self.Question_Interval_saveButton.clicked.connect(self.Save_Ttaaq)

        self.file_path = parameter_save_file['Browser_directory']
        self.save_file = self.file_path
        self.ChatHistory = parameter_save_file["Chat_history"]
        print('> файл ', self.save_file, type(self.save_file), "загружен...")
        print(f"> История чата загружена. Файл с данными {self.ChatHistory}...")

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
        self.history_edit_check = 0



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
        self.Personality_Sett_TE_Button.clicked.connect(lambda : self.Anim_Slide_Frame_Pers_TE())
        self.History_Sett_TE_Button.clicked.connect(lambda : self.Anim_Slide_Frame_History_TE())
        self.Manner_Sett_TE_Button.clicked.connect(lambda: self.Anim_Slide_Frame_Manner_TE())

        self.baya_tButton.clicked.connect(lambda: self.Change_Voice_Speaker('baya'))
        self.kseniya_tButton.clicked.connect(lambda : self.Change_Voice_Speaker('kseniya'))
        self.xenia_tButton.clicked.connect(lambda:self.Change_Voice_Speaker('xenia'))
        self.aidar_tButton.clicked.connect(lambda:self.Change_Voice_Speaker('aidar'))
        self.eugene_tButton.clicked.connect(lambda:self.Change_Voice_Speaker('eugene'))


        self.Side_Menu_Num = 0
        self.Side_Menu_Num_2 = 0
        self.ASF_Pers_TE = 0
        self.ASF_History_TE = 0
        self.ASF_Manner_TE = 0

        self.frame_6_max_width = 720
        self.frame_6_min_width = 480
        self.frame_6_main_width = 720
        self.animation_block = 0
        self.duration_anim_sideMenu = 250

        self.path_to_browser.clicked.connect(self.open_browser_file)
        self.browser_close_1.clicked.connect(self.delete_save_browser_default)

        if not self.initialized_loadfile:
            self.load_save_file()
            self.initialized_loadfile = True

        # таймер
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.execute_command)
        self.timer_interval_set()
        self.timer.start(self.interval)

        self.thread = None
        self.Sub_Button.clicked.connect(self.on_btn)

    def Send_Message_Sub(self,response):
        response_1 = ''
        response_2 = ''
        for i in range(1, (len(response) // 50) + 1):
            response_1 = response[:50 * i]
            response_2 = response[50 * i + 1:]
            response = response_1 + '\n' + response_2

        if self.thread:
            self.thread.send_param.emit(response)

    def on_btn(self):
        if self.thread is None:
            self.thread = ThreadWindow()
            self.thread.threadSignal.connect(self.on_threadSignal)
            self.thread.start()

            self.SubWin = Sub_Win(self.thread)
            self.SubWin.show()
        else:
            self.thread.stop()
            self.thread.quit()
            self.thread.wait()
            self.thread = None

    def on_threadSignal(self, value):
        print(f"Received from thread: {value}")

    def Change_Voice_Speaker(self,speaker):
        global Speaker_Voice
        Style_Sheet_act = ('QToolButton {'
                           'background: rgb(20, 20, 20);'
                           'color: white;'
                           'border-radius: 15px;'
                           'font-family:System;'
                           'font-size:12px;}'

                           'QToolButton :hover {'
                           'background: rgb(20, 20, 20);'
                           'color: white;'
                           'border-radius: 15px;'
                           'font-family:System;'
                           'font-size:12px;}'

                           'QToolButton :pressed {'
                           'background: rgb(10, 10, 10);}')
        Style_Sheet_norm = ('QToolButton {'
                            'background: rgb(40, 40, 40);'
                            'color: white;'
                            'border-radius: 15px;'
                            'font-family:System;'
                            'font-size:12px;}'

                            'QToolButton :hover {'
                            'background: rgb(20, 20, 20);'
                            'color: white;'
                            'border-radius: 15px;'
                            'font-family:System;'
                            'font-size:12px;}'

                            'QToolButton :pressed {'
                            'background: rgb(10, 10, 10);}')

        buttons = {
            'baya': self.baya_tButton,
            'kseniya': self.kseniya_tButton,
            'xenia': self.xenia_tButton,
            'eugene': self.eugene_tButton,
            'aidar': self.aidar_tButton
        }

        for btn in buttons.values():
            btn.setStyleSheet(Style_Sheet_norm)

        if speaker in buttons:
            buttons[speaker].setStyleSheet(Style_Sheet_act)

        parameter_save_file['Speaker_Voice'] = speaker
        Speaker_Voice= speaker
        self.save_savefile()

    def off_or_on_sint_voice(self,checked):
        if checked:
            print('> voice is turned off')
            self.deactivate_voice.setIcon(self.icon_voice_active)
            self.check_activate_sint_voice = False
        else:
            print('> voice is turned on')
            self.deactivate_voice.setIcon(self.icon_voice_normal)
            self.check_activate_sint_voice=True

    def fifteens_times_history_gen(self):
        global History_Mem_CP
        chat_history = self.memory.get_messages()
        chat_string = "\n".join(f"{entry['role']}: {entry['content']}" for entry in chat_history)
        text = ('выдели информацию из всего текста (в частности у пользователя) такую что может пригодиться на долгое время, что можно вcпомнить на будущее.'
                'и то что попросил пользователь у ассистента. сделать все очень кратко по возможности в одного предложения. пиши словно идет обращение к ассистенту. при отсутствии важной инфорvации вывести пустоту.'
                'нужен только текст о том какой ассистент должен быть с тем, что должен помнить')
        sys_message  =f"'{chat_string}' - {text}"
        messages_with_system = [{"role": "system", "content": sys_message}]
        response = generate_response(messages_with_system)
        print(">>>",response, "<<<")
        messages_with_system = [{"role": "system", "content": (f"'{response}' - добавь текст из первого текста в этот '{History_Mem_CP}' адаптируя первый текст под стиль написании второго, но не меняя второй текст просто добавь из первого. пиши словно идет обращение к ассистенту. текст должен быть написано к ассистенту."
                                                               f"должно быть все написано обезличено без упоминания пользвателя и ассистента. выведи только в один текст.")}]
        response = generate_response(messages_with_system)
        print("<<<",response,">>>" )
        History_Mem_CP = response
        parameter_save_file['History_Mem_CP'] = History_Mem_CP
        self.History_Sett_TE.setText()
        self.Save_OpenAI_settings()

    def timer_interval_set(self):
        self.interval = random.randint(Min_STime_Question*1000, Max_STime_Question*1000)
        print(self.interval//1000,'сек. осталось до вопроса')

    def execute_command(self):
        print("случайный вопрос!")

        user_input = ("*задай краткий любой глупый вопрос или скажи что-нибуль утвердительнон НО не вопрос. связанный с историей чата и его темой, как мой друг,"
                      "обязательно не повторяйся в вопросах. совмещай утверждения или говори только про одно. пиши краткр в одно предложение максимум! если до тебе не ответили, то веди себя агрессивно и молчи в ответ*")
        self.memory.add_message("user", user_input)
        messages_with_system = [{"role": "system", "content": self.system_message}] + self.memory.get_messages()
        try:
            response = generate_response(messages_with_system)
            self.memory.add_message("assistant", response)
            self.textBrowser.append(f"Bob: {response}")
            self.textBrowser.moveCursor(self.textBrowser.textCursor().End)
            self.history_edit_check +=1
            if self.history_edit_check >= 3:
                print(self.history_edit_check)
                self.fifteens_times_history_gen()
                self.history_edit_check = 0
            print(response)
            if self.check_activate_sint_voice:
                self.voice_massage_ask(response)
        except Exception as error:
            print(f'error - {error}')

        parameter_save_file["Chat_history"] = self.memory.get_messages()

        print(self.memory, parameter_save_file)
        self.save_savefile()

        self.timer_interval_set()
        self.timer.start(self.interval)

    def voice_adoptation(self):
        self.synthesize_and_play('о')
        print('> Прогрузка синтеза голоса, тест:', 1)
        self.synthesize_and_play('завершён...')
        print('> Прогрузка синтеза голоса завершена...')

    def load_save_file(self): # Initialization/Инициализация

        last_backslash_index = self.file_path.rfind('/')
        last_part = self.file_path[last_backslash_index + 1:]
        if last_part in self.browsers_executables:
            self.temp_browser_set = self.file_path
            print('> загрузка .exe файла браузера temp_browser_set:', self.temp_browser_set)

        # set info API tokens and temperature
        self.Num_tokens_LineE.setText(str(Number_of_tokens))
        self.Temperature_LineE.setText(str(Temperature))

        # set info min/max question interval
        self.Question_Interval_min_LE.setText(str(Min_STime_Question))
        self.Question_Interval_max_LE.setText(str(Max_STime_Question))

        # set Prompt's - Personality, History, Manner speech
        self.Personality_Sett_TE.setText(Personality_CP)
        self.History_Sett_TE.setText(History_Mem_CP)
        self.Manner_Sett_TE.setText(Manner_Voice_CP)
        print(f'> system prompts - {self.system_message}')

        self.Change_Voice_Speaker(Speaker_Voice)

        """self.voice_adoptation()"""
        self.click_browser_1.setText(self.file_path)
        print('> Загрузка API ключа...')
        if OpenAi_ApiKey:
            self.settings_apikey.setText(OpenAi_ApiKey)
            print('> Загрузка API ключа завершена')
        else:
            self.textBrowser.setText('Загрузка API-ключа не удалась.')

    def Save_Ttaaq(self): # save Timer
        global Min_STime_Question,Max_STime_Question
        parameter_save_file['Question_Interval_min'] = int(self.Question_Interval_min_LE.text())
        parameter_save_file['Question_Interval_max'] = int(self.Question_Interval_max_LE.text())
        Min_STime_Question = int(self.Question_Interval_min_LE.text())
        Max_STime_Question = int(self.Question_Interval_max_LE.text())
        self.save_savefile()
        self.timer_interval_set()
        self.timer.start(self.interval)

    def Save_OpenAI_settings(self):
        global Manner_Voice_CP,History_Mem_CP,Personality_CP
        try:
            api_key_text = self.settings_apikey.text()
            Manner_Voice_CP = str(self.Manner_Sett_TE.toPlainText())
            History_Mem_CP = str(self.History_Sett_TE.toPlainText())
            Personality_CP = str(self.Personality_Sett_TE.toPlainText())
            parameter_save_file['Number_of_tokens']=int(self.Num_tokens_LineE.text())
            parameter_save_file['Temperature'] = float(self.Temperature_LineE.text())
            parameter_save_file['Manner_Voice_CP'] = Manner_Voice_CP
            parameter_save_file['History_Mem_CP'] = History_Mem_CP
            parameter_save_file['Personality_CP'] = Personality_CP
            self.save_savefile()

            with open("OpenAiApiKey.txt", "w", encoding="utf-8") as file:
                file.write(api_key_text)
        except Exception as f:
            print(f)

    def Set_Default_Settings(self):
        self.Num_tokens_LineE.setText(str(parameter_save_file['Number_of_tokens']))
        self.Temperature_LineE.setText(str(parameter_save_file['Temperature']))

        self.Question_Interval_min_LE.setText(str(parameter_save_file['Question_Interval_min']))
        self.Question_Interval_max_LE.setText(str(parameter_save_file['Question_Interval_max']))

    def handle_input(self):
        user_input = self.lineEdit_2.text()
        try:
            if user_input:
                self.memory.add_message("user", user_input)
                messages_with_system = [{"role": "system", "content": self.system_message}] + self.memory.get_messages()
                try:
                    response = generate_response(messages_with_system)
                    self.memory.add_message("assistant", response)
                    self.textBrowser.append(f"User: {user_input}")
                    self.textBrowser.append(f"Bob: {response}")

                    self.history_edit_check += 1
                    if self.history_edit_check >= 15:
                        print(self.history_edit_check)
                        self.fifteens_times_history_gen()
                        self.history_edit_check = 0

                    self.textBrowser.moveCursor(self.textBrowser.textCursor().End)
                except Exception as error:
                    print(f'error - {error}')
                    return

                self.lineEdit_2.clear()

                self.Send_Message_Sub(response)

                if self.check_activate_sint_voice:
                    self.voice_massage_ask(response)
                self.out_text = user_input
                self.conv_text_to_func()

                parameter_save_file["Chat_history"]=self.memory.get_messages()
                print(self.memory,parameter_save_file)
                self.save_savefile()
            self.timer_interval_set()
            self.timer.start(self.interval)


        except Exception as p:
            print(f'Error: {p}')

    def open_browser_file(self):
        file_dialog = QFileDialog()
        self.browser_var = ['']
        self.file_path, _ = file_dialog.getOpenFileName()

        self.load_save_file()

        parameter_save_file["Browser_directory"] = self.file_path
        self.save_savefile()
        self.default_browser_state = 1
        self.voice_massage_ask(
            f"{self.dict_word_used_browser[random.randint(0, len(self.dict_word_used_browser) - 1)]}"
            f" {self.file_path}"
        )

    def save_savefile(self):
        with open('savefile.json', 'w',encoding='utf-8') as json_file:
            json.dump(parameter_save_file, json_file,ensure_ascii=False,indent=len(parameter_save_file))
        print('savefile.json saved in folder')

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

    def Anim_Slide_Frame_Manner_TE(self):
        if self.animation_block:
            return
        self.animation_block = True
        if self.ASF_Manner_TE == 0: #открытие окна
            self.ASF_Manner_TE = 1
            self.Manner_Sett_TE_Button.setText(" < ")
            self.animation10 = QtCore.QPropertyAnimation(self.Manner_Sett_TE, b"minimumHeight")
            self.animation10.setDuration(self.duration_anim_sideMenu)
            self.animation10.setStartValue(0)
            self.animation10.setEndValue(170)
            self.animation10.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation10.finished.connect(self.on_animation_finished)
            self.animation10.start()
        else:                     #закрытие окна
            self.ASF_Manner_TE = 0
            self.Manner_Sett_TE_Button.setText(". . .")
            self.animation10 = QtCore.QPropertyAnimation(self.Manner_Sett_TE, b"minimumHeight")
            self.animation10.setDuration(self.duration_anim_sideMenu)
            self.animation10.setStartValue(170)
            self.animation10.setEndValue(0)
            self.animation10.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation10.finished.connect(self.on_animation_finished)
            self.animation10.start()


    def Anim_Slide_Frame_History_TE(self):
        if self.animation_block:
            return
        self.animation_block = True
        if self.ASF_History_TE == 0: #открытие окна
            self.ASF_History_TE = 1
            self.History_Sett_TE_Button.setText(" < ")
            self.animation10 = QtCore.QPropertyAnimation(self.History_Sett_TE, b"minimumHeight")
            self.animation10.setDuration(self.duration_anim_sideMenu)
            self.animation10.setStartValue(0)
            self.animation10.setEndValue(170)
            self.animation10.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation10.finished.connect(self.on_animation_finished)
            self.animation10.start()
        else:                     #закрытие окна
            self.ASF_History_TE = 0
            self.History_Sett_TE_Button.setText(". . .")
            self.animation10 = QtCore.QPropertyAnimation(self.History_Sett_TE, b"minimumHeight")
            self.animation10.setDuration(self.duration_anim_sideMenu)
            self.animation10.setStartValue(170)
            self.animation10.setEndValue(0)
            self.animation10.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation10.finished.connect(self.on_animation_finished)
            self.animation10.start()

    def Anim_Slide_Frame_Pers_TE(self):
        if self.animation_block:
            return
        self.animation_block = True
        if self.ASF_Pers_TE == 0: #открытие окна
            self.ASF_Pers_TE = 1
            self.Personality_Sett_TE_Button.setText(" < ")
            self.animation9 = QtCore.QPropertyAnimation(self.Personality_Sett_TE, b"minimumHeight")
            self.animation9.setDuration(self.duration_anim_sideMenu)
            self.animation9.setStartValue(0)
            self.animation9.setEndValue(170)
            self.animation9.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation9.finished.connect(self.on_animation_finished)
            self.animation9.start()
        else:                     #закрытие окна
            self.ASF_Pers_TE = 0
            self.Personality_Sett_TE_Button.setText(". . .")
            self.animation9 = QtCore.QPropertyAnimation(self.Personality_Sett_TE, b"minimumHeight")
            self.animation9.setDuration(self.duration_anim_sideMenu)
            self.animation9.setStartValue(170)
            self.animation9.setEndValue(0)
            self.animation9.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation9.finished.connect(self.on_animation_finished)
            self.animation9.start()

    def Slide_Frame_Options(self):
        if self.animation_block:
            return
        self.animation_block = True

        if self.Side_Menu_Num == 0:
            self.Side_Menu_Num = 1
            self.animation2 = QtCore.QPropertyAnimation(self.Consol, b"minimumWidth")
            self.animation2.setDuration(self.duration_anim_sideMenu)
            self.animation2.setStartValue(self.frame_6_min_width)
            self.animation2.setEndValue(0)
            self.animation2.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation2.finished.connect(self.on_animation_finished)
            self.animation2.start()
            self.animation22 = QtCore.QPropertyAnimation(self.Consol, b"maximumWidth")
            self.animation22.setDuration(self.duration_anim_sideMenu)
            self.animation22.setStartValue(self.frame_6_max_width)
            self.animation22.setEndValue(0)
            self.animation22.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation22.finished.connect(self.on_animation_finished)
            self.animation22.start()

            self.animation41 = QtCore.QPropertyAnimation(self.frame_4, b"minimumWidth")
            self.animation41.setDuration(self.duration_anim_sideMenu)
            self.animation41.setStartValue(0)
            self.animation41.setEndValue(self.frame_6_min_width)
            self.animation41.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation41.finished.connect(self.on_animation_finished)
            self.animation41.start()
            self.animation42 = QtCore.QPropertyAnimation(self.frame_4, b"maximumWidth")
            self.animation42.setDuration(self.duration_anim_sideMenu)
            self.animation42.setStartValue(0)
            self.animation42.setEndValue(self.frame_6_max_width)
            self.animation42.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation42.finished.connect(self.on_animation_finished)
            self.animation42.start()

            self.Set_Default_Settings()
        else:
            self.Side_Menu_Num = 0
            self.animation2 = QtCore.QPropertyAnimation(self.frame_4, b"maximumWidth")
            self.animation2.setDuration(self.duration_anim_sideMenu)
            self.animation2.setStartValue(self.frame_6_max_width)
            self.animation2.setEndValue(0)
            self.animation2.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation2.finished.connect(self.on_animation_finished)
            self.animation2.start()
            self.animation21 = QtCore.QPropertyAnimation(self.frame_4, b"minimumWidth")
            self.animation21.setDuration(self.duration_anim_sideMenu)
            self.animation21.setStartValue(self.frame_6_min_width)
            self.animation21.setEndValue(0)
            self.animation21.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation21.finished.connect(self.on_animation_finished)
            self.animation21.start()

            self.animation4 = QtCore.QPropertyAnimation(self.Consol, b"minimumWidth")
            self.animation4.setDuration(self.duration_anim_sideMenu)
            self.animation4.setStartValue(0)
            self.animation4.setEndValue(self.frame_6_min_width)
            self.animation4.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation4.finished.connect(self.on_animation_finished)
            self.animation4.start()
            self.animation41 = QtCore.QPropertyAnimation(self.Consol, b"maximumWidth")
            self.animation41.setDuration(self.duration_anim_sideMenu)
            self.animation41.setStartValue(0)
            self.animation41.setEndValue(self.frame_6_max_width)
            self.animation41.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation41.finished.connect(self.on_animation_finished)
            self.animation41.start()



    def Slide_Frame_Main(self):
        if self.animation_block:
            return
        self.animation_block = True

        if self.Side_Menu_Num_2 == 0:
            self.animation2 = QtCore.QPropertyAnimation(self.Menu, b"minimumWidth")
            self.animation2.setDuration(self.duration_anim_sideMenu)
            self.animation2.setStartValue(80)
            self.animation2.setEndValue(160)
            self.animation2.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation2.finished.connect(self.on_animation_finished)
            self.animation2.start()

            self.Side_Menu_Num_2 = 1
        else:
            self.animation2 = QtCore.QPropertyAnimation(self.Menu, b"minimumWidth")
            self.animation2.setDuration(self.duration_anim_sideMenu)
            self.animation2.setStartValue(160)
            self.animation2.setEndValue(80)
            self.animation2.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.animation2.finished.connect(self.on_animation_finished)
            self.animation2.start()

            self.Side_Menu_Num_2 = 0

    def on_animation_finished(self):
        self.animation_block = False

    def voice_massage_ask(self, massage):
        print(massage)

        self.synthesize_and_play(massage,Speaker_Voice)


    def synthesize_and_play(self,text, speaker='baya', sample_rate=48000):

        text = text+'....ъъъъ'
        audio_path = self.model.save_wav(text=text, speaker=speaker, sample_rate=sample_rate)

        audio, sr = sf.read(audio_path)

        sd.play(audio, samplerate=sr)
        sd.wait()
        self.timer_interval_set()
        self.timer.start(self.interval)


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

            elif word in conv_num_file: # открытие проводника
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
                self.default_browser_state = 1
            return
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
            'выключи звук': lambda: pyautogui.press('volumedown', presses=int(50))
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
    root.show()
    sys.exit(app.exec_())
