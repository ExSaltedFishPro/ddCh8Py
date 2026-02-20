import random
import pygame,time
import math
import array
class Chip8:
    def make_beep_sound(self, freq=440, duration=0.1, volume=0.2, sample_rate=44100):
        n_samples = int(duration * sample_rate)
        buf = array.array("h")
        amp = int(32767 * volume)
        half_period = sample_rate // (2 * freq)
        if half_period <= 0:
            half_period = 1

        v = amp
        count = 0
        for _ in range(n_samples):
            buf.append(v)
            count += 1
            if count >= half_period:
                v = -v
                count = 0

        return pygame.mixer.Sound(buffer=buf.tobytes())

    def __init__(self):
        self.memory = bytearray(4096)
        self.V = [0] * 16
        self.stack = [0] * 16
        self.sp = -1
        self.I = 0
        self.pc = 0x200
        self.delay_timer = 0
        self.sound_timer = 0
        self.display_raw = [[0] * 64 for _ in range(32)]
        self.fps = 60
        self.cpu_hz = 500
        self.draw_flag = True
        self.waiting_for_key = False
        self.wait_reg = 0
        self.keys = [0] * 16
        self.increment_i_quirk = False  # Some interpreters advance I on FX55/FX65; default off
        FONTSET = bytearray([
        0xF0, 0x90, 0x90, 0x90, 0xF0,  # 0
        0x20, 0x60, 0x20, 0x20, 0x70,  # 1
        0xF0, 0x10, 0xF0, 0x80, 0xF0,  # 2
        0xF0, 0x10, 0xF0, 0x10, 0xF0,  # 3
        0x90, 0x90, 0xF0, 0x10, 0x10,  # 4
        0xF0, 0x80, 0xF0, 0x10, 0xF0,  # 5
        0xF0, 0x80, 0xF0, 0x90, 0xF0,  # 6
        0xF0, 0x10, 0x20, 0x40, 0x40,  # 7
        0xF0, 0x90, 0xF0, 0x90, 0xF0,  # 8
        0xF0, 0x90, 0xF0, 0x10, 0xF0,  # 9
        0xF0, 0x90, 0xF0, 0x90, 0x90,  # A
        0xE0, 0x90, 0xE0, 0x90, 0xE0,  # B
        0xF0, 0x80, 0x80, 0x80, 0xF0,  # C
        0xE0, 0x90, 0x90, 0x90, 0xE0,  # D
        0xF0, 0x80, 0xF0, 0x80, 0xF0,  # E
        0xF0, 0x80, 0xF0, 0x80, 0x80   # F
        ])
        self.memory[0:len(FONTSET)] = FONTSET

    def load_from_file(self, filename):
        with open(filename, 'rb') as f:
            self.load_program(f.read())
    def load_program(self, program_bytes):
        if len(program_bytes) + 0x200 > len(self.memory):
            raise ValueError("Program size exceeds memory limits.")
        self.memory[0x200:0x200 + len(program_bytes)] = program_bytes

    def fetch_opcode(self):
        high_byte = self.memory[self.pc]
        low_byte = self.memory[self.pc + 1]
        return (high_byte << 8) | low_byte
    
    def _cls(self):
        self.display_raw = [[0] * 64 for _ in range(32)]
        self.draw_flag = True

    def _draw_sprite_DXYN(self, x, y, height):
        collision = 0
        for row in range(height):
            sprite_byte = self.memory[self.I + row]
            for col in range(8):
                sprite_pixel = (sprite_byte >> (7 - col)) & 0x1
                if sprite_pixel == 1:
                    screen_x = (x + col) % 64
                    screen_y = (y + row) % 32
                    if self.display_raw[screen_y][screen_x] == 1:
                        collision = 1
                    self.display_raw[screen_y][screen_x] ^= 1
        self.draw_flag = True
        return collision

    def _store_bcd(self, x):
        value = self.V[x]
        self.memory[self.I] = value // 100
        self.memory[self.I + 1] = (value // 10) % 10
        self.memory[self.I + 2] = value % 10

    def execute(self, opcode):
        nibbles = [(opcode & 0xF000) >> 12,
                  (opcode & 0x0F00) >> 8,
                  (opcode & 0x00F0) >> 4,
                  (opcode & 0x000F)]
        self.pc += 2
        if nibbles[0] == 0x0:
            if nibbles[1] == 0x0 and nibbles[2] == 0xE and nibbles[3] == 0x0:
                "00E0 - CLS: Clear the display."
                self._cls()
            elif nibbles[1] == 0x0 and nibbles[2] == 0xE and nibbles[3] == 0xE:
                "00EE - RET: Return from a subroutine."
                if self.sp<0:
                    raise ValueError("Stack underflow on RET.")
                self.pc = self.stack[self.sp]
                self.sp -= 1
            else:
                "0NNN - Calls machine code routine (RCA 1802 for COSMAC VIP) at address NNN. Not necessary for most ROMs."
        elif nibbles[0] == 0x1:
            "1NNN - JP addr: Jump to location NNN."
            address = opcode & 0x0FFF
            self.pc = address
        elif nibbles[0] == 0x2:
            "2NNN - CALL addr: Call subroutine at NNN."
            address = opcode & 0x0FFF
            self.sp += 1
            if self.sp >= len(self.stack):
                raise RuntimeError("Stack overflow on CALL")
            self.stack[self.sp] = self.pc
            self.pc = address
        elif nibbles[0] == 0x3:
            "3XNN - Skips the next instruction if VX equals NN. (Usually the next instruction is a jump to skip a code block)"
            x = nibbles[1]
            nn = opcode & 0x00FF
            if self.V[x] == nn:
                self.pc += 2
        elif nibbles[0] == 0x4:
            "4XNN - Skips the next instruction if VX doesn't equal NN. (Usually the next instruction is a jump to skip a code block)"
            x = nibbles[1]
            nn = opcode & 0x00FF
            if self.V[x] != nn:
                self.pc += 2
        elif nibbles[0] == 0x5:
            "5XY0 - Skips the next instruction if VX equals VY. (Usually the next instruction is a jump to skip a code block)"
            if nibbles[3] != 0:
                raise ValueError(f"Unknown opcode: {opcode:04X}")
            x = nibbles[1]
            y = nibbles[2]
            if self.V[x] == self.V[y]:
                self.pc += 2
        elif nibbles[0] == 0x6:
            "6XNN - Sets VX to NN."
            x = nibbles[1]
            nn = opcode & 0x00FF
            self.V[x] = nn
        elif nibbles[0] == 0x7:
            "7XNN - Adds NN to VX. (Carry flag is not changed)"
            x = nibbles[1]
            nn = opcode & 0x00FF
            self.V[x] = (self.V[x] + nn) & 0xFF
        elif nibbles[0] == 0x8:
            x = nibbles[1]
            y = nibbles[2]
            if nibbles[3] == 0:
                "8XY0 - Sets VX to the value of VY."
                self.V[x] = self.V[y]
            elif nibbles[3] == 1:
                "8XY1 - Sets VX to VX or VY. (Bitwise OR operation)"
                self.V[x] |= self.V[y]
            elif nibbles[3] == 2:
                "8XY2 - Sets VX to VX and VY. (Bitwise AND operation)"
                self.V[x] &= self.V[y]
            elif nibbles[3] == 3:
                "8XY3 - Sets VX to VX xor VY."
                self.V[x] ^= self.V[y]
            elif nibbles[3] == 4:
                "8XY4 - Adds VY to VX. VF is set to 1 when there's a carry, and to 0 when there isn't."
                total = self.V[x] + self.V[y]
                self.V[0xF] = 1 if total > 0xFF else 0
                self.V[x] = total & 0xFF
            elif nibbles[3] == 5:
                "8XY5 - VY is subtracted from VX. VF is set to 0 when there's a borrow, and 1 when there isn't."
                self.V[0xF] = 1 if self.V[x] >= self.V[y] else 0
                self.V[x] = (self.V[x] - self.V[y]) & 0xFF
            elif nibbles[3] == 6:
                "8XY6 - Stores the least significant bit of VX in VF and then shifts VX to the right by 1."
                self.V[0xF] = self.V[x] & 0x1
                self.V[x] = (self.V[x] >> 1) & 0xFF
            elif nibbles[3] == 7:
                "8XY7 - Sets VX to VY minus VX. VF is set to 0 when there's a borrow, and 1 when there isn't."
                self.V[0xF] = 1 if self.V[y] >= self.V[x] else 0
                self.V[x] = (self.V[y] - self.V[x]) & 0xFF
            elif nibbles[3] == 0xE:
                "8XYE - Stores the most significant bit of VX in VF and then shifts VX to the left by 1."
                self.V[0xF] = (self.V[x] & 0b10000000) >> 7
                self.V[x] = (self.V[x] << 1) & 0xFF
            else:
                raise ValueError(f"Unknown opcode: {opcode:04X}")
        elif nibbles[0] == 0x9:
            "9XY0 - Skips the next instruction if VX doesn't equal VY. (Usually the next instruction is a jump to skip a code block)"
            if nibbles[3] != 0:
                raise ValueError(f"Unknown opcode: {opcode:04X}")
            x = nibbles[1]
            y = nibbles[2]
            if self.V[x] != self.V[y]:
                self.pc += 2
        elif nibbles[0] == 0xA:
            "ANNN - Sets I to the address NNN."
            address = opcode & 0x0FFF
            self.I = address
        elif nibbles[0] == 0xB:
            "BNNN - Jumps to the address NNN plus V0."
            addr = opcode & 0x0FFF
            self.pc = addr + self.V[0]
        elif nibbles[0] == 0xC:
            "CXNN - Sets VX to the result of a bitwise and operation on a random number (Typically: 0 to 255) and NN."
            random_number = random.randint(0, 255)
            x = nibbles[1]
            self.V[x] = random_number & (opcode & 0x00FF)
        elif nibbles[0] == 0xD:
            "DXYN - Draws a sprite at coordinate (VX, VY) that has a width of 8 pixels and a height of N pixels. Each row of 8 pixels is read as bit-coded starting from memory location I; I value doesn’t change after the execution of this instruction. As described above, VF is set to 1 if any screen pixels are flipped from set to unset when the sprite is drawn, and to 0 if that doesn’t happen"
            x = self.V[nibbles[1]]
            y = self.V[nibbles[2]]
            height = nibbles[3]
            self.V[0xF] = self._draw_sprite_DXYN(x, y, height)
        elif nibbles[0] == 0xE:
            if nibbles[2] == 0x9 and nibbles[3] == 0xE:
                "EX9E - Skips the next instruction if the key stored in VX is pressed. (Usually the next instruction is a jump to skip a code block)"
                x = nibbles[1]
                key = self.V[x] & 0xF
                if self.keys[key] == 1:
                    self.pc += 2
            elif nibbles[2] == 0xA and nibbles[3] == 0x1:
                "EXA1 - Skips the next instruction if the key stored in VX isn't pressed. (Usually the next instruction is a jump to skip a code block)"
                x = nibbles[1]
                key = self.V[x] & 0xF
                if self.keys[key] == 0:
                    self.pc += 2
        elif nibbles[0] == 0xF:
            if nibbles[2] == 0x0 and nibbles[3] == 0x7:
                "FX07 - Sets VX to the value of the delay timer."
                x = nibbles[1]
                self.V[x] = self.delay_timer
            elif nibbles[2] == 0x0 and nibbles[3] == 0xA:
                "FX0A - A key press is awaited, and then stored in VX. (Blocking Operation. All instruction halted until next key event)"
                x = nibbles[1]
                self.waiting_for_key = True
                self.wait_reg = x
                #self.pc -= 2
            elif nibbles[2] == 0x1 and nibbles[3] == 0x5:
                "FX15 - Sets the delay timer to VX."
                x = nibbles[1]
                self.delay_timer = self.V[x]
            elif nibbles[2] == 0x1 and nibbles[3] == 0x8:
                "FX18 - Sets the sound timer to VX."
                x = nibbles[1]
                self.sound_timer = self.V[x]
            elif nibbles[2] == 0x1 and nibbles[3] == 0xE:
                "FX1E - Adds VX to I. VF is not affected."
                self.I = (self.I + self.V[nibbles[1]]) & 0xFFFF
            elif nibbles[2] == 0x2 and nibbles[3] == 0x9:
                "FX29 - Sets I to the location of the sprite for the character in VX. Characters 0-F (in hexadecimal) are represented by a 4x5 font."
                x = nibbles[1]
                self.I = self.V[x] * 5
            elif nibbles[2] == 0x3 and nibbles[3] == 0x3:
                "FX33 - Stores the binary-coded decimal representation of VX, with the most significant of three digits at the address in I, the middle digit at I plus 1, and the least significant digit at I plus 2."
                self._store_bcd(nibbles[1])
            elif nibbles[2] == 0x5 and nibbles[3] == 0x5:
                "FX55 - Stores V0 to VX (including VX) in memory starting at address I. The offset from I is increased by 1 for each value written, but I itself is left unmodified."
                x = nibbles[1]
                for i in range(x + 1):
                    self.memory[self.I + i] = self.V[i]
                if self.increment_i_quirk:
                    self.I = (self.I + x + 1) & 0xFFFF
            elif nibbles[2] == 0x6 and nibbles[3] == 0x5:
                "FX65 - Fills V0 to VX (including VX) with values from memory starting at address I. The offset from I is increased by 1 for each value read, but I itself is left unmodified."
                x = nibbles[1]
                for i in range(x + 1):
                    self.V[i] = self.memory[self.I + i]
                if self.increment_i_quirk:
                    self.I = (self.I + x + 1) & 0xFFFF
        else:
            raise ValueError(f"Unknown opcode: {opcode:04X}")
        
    def update_timers(self):
        if self.delay_timer > 0:
            self.delay_timer -= 1
        if self.sound_timer > 0:
            self.sound_timer -= 1

    def render_display(self):
        for y in range(32):
            for x in range(64):
                color = (255, 255, 255) if self.display_raw[y][x] == 1 else (0, 0, 0)
                self.display.set_at((x, y), color)
        return self.display

    def run(self, scale=12):
        self.display = pygame.Surface((64, 32))
        KEYMAP = {
        pygame.K_1: 0x1, pygame.K_2: 0x2, pygame.K_3: 0x3, pygame.K_4: 0xC,
        pygame.K_q: 0x4, pygame.K_w: 0x5, pygame.K_e: 0x6, pygame.K_r: 0xD,
        pygame.K_a: 0x7, pygame.K_s: 0x8, pygame.K_d: 0x9, pygame.K_f: 0xE,
        pygame.K_z: 0xA, pygame.K_x: 0x0, pygame.K_c: 0xB, pygame.K_v: 0xF,
        }
        chip8 = self
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.init()
        pygame.mixer.init()
        beep = self.make_beep_sound(freq=440, duration=0.1, volume=0.2)
        channel = pygame.mixer.Channel(0)
        beeping = False
        pygame.display.set_caption("CHIP-8")
        window = pygame.display.set_mode((64 * scale, 32 * scale))
        clock = pygame.time.Clock()

        cpu_step = 1.0 / chip8.cpu_hz
        timer_step = 1.0 / 60.0  # CHIP-8 timers are 60Hz

        cpu_acc = 0.0
        timer_acc = 0.0

        running = True
        last = time.perf_counter()

        while running:
            now = time.perf_counter()
            dt = now - last
            last = now

            # 避免切到后台回来 dt 巨大导致“狂追帧”
            if dt > 0.25:
                dt = 0.25

            cpu_acc += dt
            timer_acc += dt

            # 防止后台切回来 CPU "狂追帧"
            cpu_acc = min(cpu_acc, cpu_step * 20)
            if self.sound_timer > 0:
                if not beeping:
                    channel.play(beep, loops=-1)  # 一直循环
                    beeping = True
            else:
                if beeping:
                    channel.stop()
                    beeping = False
            # 事件 + 键盘
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key in KEYMAP:
                        k = KEYMAP[event.key]
                        chip8.keys[k] = 1

                        # 处理 FX0A：如果正在等键，按下任意有效键就写入并解除等待
                        if chip8.waiting_for_key:
                            chip8.V[chip8.wait_reg] = k
                            chip8.waiting_for_key = False

                elif event.type == pygame.KEYUP:
                    if event.key in KEYMAP:
                        chip8.keys[KEYMAP[event.key]] = 0

            # 如果 FX0A 在等待，允许直接使用当前已按下的键（无需额外再按一次）
            if chip8.waiting_for_key:
                for idx, state in enumerate(chip8.keys):
                    if state:
                        chip8.V[chip8.wait_reg] = idx
                        chip8.waiting_for_key = False
                        break

            # CPU：如果 FX0A 阻塞，就不继续执行指令（但定时器/渲染仍然走）
            while cpu_acc >= cpu_step and not chip8.waiting_for_key:
                opcode = chip8.fetch_opcode()
                chip8.execute(opcode)
                cpu_acc -= cpu_step

            # Timers：严格 60Hz
            while timer_acc >= timer_step:
                chip8.update_timers()
                timer_acc -= timer_step

            # Render：60FPS（用 tick 控制）
            if chip8.draw_flag:
                surface_64x32 = chip8.render_display()  # 你已有：把 display_raw 写到 self.display
                scaled = pygame.transform.scale(surface_64x32, (64 * scale, 32 * scale))
                window.blit(scaled, (0, 0))
                pygame.display.flip()
                chip8.draw_flag = False

            clock.tick(chip8.fps)

        pygame.quit()
        
