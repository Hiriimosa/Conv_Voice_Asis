if output in ['включи браузер', 'включи браузеров', 'включи браузера',
              'включи браузеры', 'открой браузеров', 'открой браузер', 'открой браузеры', 'открой браузера']:
    os.system('"C:/Program Files/Mozilla Firefox/firefox.exe"')
if 'поиск' in output or 'поиске' in output:
    if 'найди' in output or 'введи' in output or 'види' in output:
        text = output
        print(text)
        text = '+'.join(text[text.find('поиск') + 6:].split())
        final_text = "start" + " " + " https://ya.ru/search/?text=" + text
        os.system(final_text)

        time.sleep(1)
        for _ in range(10):
            keyboard.press_and_release('Up')
        while self.place_sma !=place_sma_act:
            time.sleep(0.2)
            keyboard.press_and_release('Down')
            self.place_sma +=1
        if self.place_sma == place_sma_act:
            keyboard.press_and_release('Enter')

import openai

openai.api_key = ''

def generate_response(prompt):
    response = openai.Completion.create(
        engine='gpt-3.5-turbo',
        prompt=prompt,
        max_tokens=3796,  # Максимальное количество токенов в каждом запросе
        temperature=0.8,
        n=1,
        stop=None,
        timeout=50  # Опционально: установите таймаут на запрос
    )
    print()
    return response.choices[0].text.strip()

while True:
    vopros = 'твое имя'
    if vopros == "no":
        break
    else:
        otvet = generate_response(vopros)
        print(otvet)

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QLCDNumber, QScrollArea


class Prog(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.label = QLabel(self)
        self.label.setText("text")

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.label)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = Prog()
    win.show()
    sys.exit(app.exec())



import openai

# Задайте API ключ через переменные окружения или другой безопасный метод


class ChatMemory:
    def __init__(self, max_messages=10):
        self.max_messages = max_messages
        self.messages = []

    def add_message(self, role, content):
        # Добавляем новое сообщение в память
        self.messages.append({"role": role, "content": content})
        # Если превышен лимит сообщений, удаляем старые
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def get_messages(self):
        return self.messages


def generate_response(messages):
    response = openai.ChatCompletion.create(
        model='gpt-4o',
        messages=messages,
        max_tokens=50,  # Установлено для ограничения длины ответов
        temperature=0.8
    )
    return response.choices[0].message['content'].strip()


def main():
    memory = ChatMemory()

    # Запрашиваем системное сообщение в каждой итерации
    system_message = "будь застенчивым человеком по имени Боб. Ты необщителен и можешь делиться личным."

    while True:
        user_input = input('Введите ваш вопрос (или "no" для выхода): ')
        if user_input.lower() == "no":
            break

        # Добавляем системное сообщение, чтобы напомнить правило
        messages_with_system = [{"role": "system", "content": system_message}] + memory.get_messages()

        # Добавляем сообщение пользователя в память
        memory.add_message("user", user_input)

        # Генерируем ответ
        response = generate_response(messages_with_system)

        # Добавляем ответ модели в память
        memory.add_message("assistant", response)

        # Выводим ответ
        print("Ответ:", response)


if __name__ == "__main__":
    main()