import json

params = {'Browser_directory': 'C:/Program Files/Mozilla Firefox/firefox.exe', 'Chat_history': [{'role': 'user', 'content': 'gпривет'}, {'role': 'assistant', 'content': 'Добрый день, сэр. Как ваши дела?'}]}

combined_chat = ' '.join(f"{entry['role']}: {entry['content']}" for entry in params['Chat_history'])
print(combined_chat)