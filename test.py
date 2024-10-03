import os

file_name = 'OpenAiApiKey.txt'
if not os.path.exists(file_name):
    open(file_name, 'w',encoding='utf-8').close()
with open(file_name, 'r',encoding='utf-8') as file:
    OpenAi_ApiKey = file.read()

print("Ваш OpenAI API ключ: ", OpenAi_ApiKey)