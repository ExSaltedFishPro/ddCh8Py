from chip8 import Chip8

game = Chip8()
game.load_from_file('games/TETRIS')
game.run()