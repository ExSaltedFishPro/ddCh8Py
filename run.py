import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
from chip8 import Chip8
import pathlib

banner = """-------------------------------------------------
ddCh8Py - A Simple CHIP-8 Emulator in Python
-------------------------------------------------
LICENSE: MIT License
Games are free software downloaded from the 
Internet, and are included in this repository.
Please note that the games are not created by me,
and I do not claim any ownership over them.
--------------------------------------------------"""
print(banner)
games = pathlib.Path('games').glob('*')
print("0. Exit")
games = list(games)
# split games into pages of 7 games each
# 0: exit,9: next page, 8: previous page
pages = [len(games[i:i + 7]) for i in range(0, len(games), 7)]
current_page = 0
while True:
    print(f"Page {current_page + 1}/{len(pages)}")
    for i, game in enumerate(games[current_page * 7:(current_page + 1) * 7]):
        print(f"{i + 1}. {game.name}")
    if current_page > 0:
        print("8. Previous Page")
    if current_page < len(pages) - 1:
        print("9. Next Page")
    choice = input("Select a game to play: ")
    if choice == '0':
        break
    elif choice == '8' and current_page > 0:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(banner)
        current_page -= 1
    elif choice == '9' and current_page < len(pages) - 1:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(banner)
        current_page += 1
    elif choice.isdigit() and 1 <= int(choice) <= pages[current_page]:
        game_path = games[current_page * 7 + int(choice) - 1]
        print(f"Loading {game_path.name}...")
        chip8 = Chip8()
        chip8.load_from_file(game_path)
        chip8.run()
        os.system('cls' if os.name == 'nt' else 'clear')
        print(banner)
    else:
        print("Invalid choice. Please try again.")

