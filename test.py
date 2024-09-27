from PyQt5 import QtWidgets, QtCore
import random
import sys


class Window(QtWidgets.QMainWindow):
    # Определение сигнала для передачи строки
    text_signal = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.temp_vol = -1
        self.initialized_loadfile = False

        # Создаем таймер
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.execute_command)

        # Устанавливаем случайный интервал от 1 до 10 секунд
        self.set_random_timer_interval()

        # Запускаем таймер
        self.timer.start(self.interval)

    def set_random_timer_interval(self):
        # Устанавливаем случайный интервал (в миллисекундах)
        self.interval = random.randint(1000, 10000)  # от 1 до 10 секунд

    def execute_command(self):
        # Выполняем вашу команду здесь
        print("Команда выполнена!")
        # Устанавливаем новый случайный интервал
        self.set_random_timer_interval()
        # Перезапускаем таймер с новым интервалом
        self.timer.start(self.interval)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())
