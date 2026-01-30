# CHIP-8 Python 模拟器

## 简介
本仓库实现了一个遵循经典 CHIP-8 指令集的解释器，采用 Python + Pygame 负责图形和输入，直接运行 `games` 文件夹内的 ROM 就能体验 1970 年代风格的小游戏。解释器支持完整的定时器、键盘扫描以及标准的绘制、内存和子程序行为，是学习 CHIP-8 架构或制作轻量模拟器的起点。

## 依赖
- Python 3.7 及以上
- [pygame](https://www.pygame.org/)（用于渲染、输入、定时）

安装依赖：
```
pip install pygame
```

## 如何运行
1. 复制或编写一个 ROM 到 `games/` 目录。已有 ROM 包含 `TETRIS`、`PONG`、`INVADERS` 等经典小游戏。
2. 编辑 `run.py` 中的 `game.load_from_file('games/TETRIS')`，改成你要运行的 ROM 文件。
3. 运行模拟器：
```
python run.py
```
窗口会以 64×32 逻辑像素打开，模拟器内部会将画面放大到默认的 12 倍。

如果你想调节渲染参数，直接在 `chip8.Chip8.run(scale=...)` 中传入其他缩放值，也可以调整 `Chip8.cpu_hz` 或 `Chip8.fps` 控制速度。

## 键盘映射
CHIP-8 使用的 16 键键盘映射为：
```
1 2 3 4    -> HEX 1 2 3 C
Q W E R    -> HEX 4 5 6 D
A S D F    -> HEX 7 8 9 E
Z X C V    -> HEX A 0 B F
```
按下/松开对应按键会立即更新内部按键状态，FX0A 指令会自动等待有效键入。

## 可用 ROM
`games/` 目录里预置：
15PUZZLE、BLINKY、BLITZ、BRIX、CONNECT4、GUESS、HIDDEN、INVADERS、KALEID、MAZE、MERLIN、MISSILE、PONG、PONG2、PUZZLE、SYZYGY、TANK、TETRIS、TICTAC、UFO、VBRIX、VERS、WIPEOFF 等多个 ROM，直接传入对应文件名即可启动。


## 贡献与探索
- 想追踪声音？可在 `Chip8.run()` 中观察 `sound_timer`，结合 Pygame 播放短促的告警。
- 想写自动测试？可直接调用 `Chip8.execute()` 和 `fetch_opcode()`，向内存写入固定指令，验证寄存器/定时器行为。
- 欢迎提交更多 ROM、调色皮肤、或者键盘映射配置。
