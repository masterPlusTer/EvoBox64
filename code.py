import board
import displayio
import framebufferio
import rgbmatrix
import random
import time

# ================================================================
# EVOBOX 64x64 - terrario digital en un solo archivo
# CircuitPython + Raspberry Pi Pico + matriz HUB75 64x64
# No necesita librerias externas ni imagenes.
# ================================================================

WIDTH = 64
HEIGHT = 64
TOP = 6
FPS = 10
FRAME_TIME = 1.0 / FPS
BIT_DEPTH = 5

INITIAL_GRAZERS = 6
INITIAL_HUNTERS = 1
MAX_GRAZERS = 12
MAX_HUNTERS = 3

# Limites ecologicos para evitar explosiones y colapsos bruscos.
TARGET_FOOD = 120
MAX_FOOD_CELLS = 190
CONSOLE_EVERY = 100

# Indices de paleta
BLACK = 0
GROUND_A = 1
GROUND_B = 2
FOOD_SMALL = 3
FOOD_BIG = 4
GRAZER_BODY = 5
GRAZER_LIGHT = 6
HUNTER_BODY = 7
HUNTER_LIGHT = 8
EGG = 9
CORPSE = 10
TRAIL_GRAZER = 11
TRAIL_HUNTER = 12
UI_DIM = 13
UI_WHITE = 14
UI_GREEN = 15
UI_RED = 16
UI_YELLOW = 17
DANGER = 18
RAIN = 19

COLORS = (
    0x000000,
    0x020805,
    0x04130A,
    0x167A28,
    0x8CFF4D,
    0x00A9D6,
    0xD8FFFF,
    0xE51645,
    0xFFD2A8,
    0xFFD84A,
    0x58311F,
    0x003B49,
    0x4B0718,
    0x0A1218,
    0xFFFFFF,
    0x36E35C,
    0xFF315D,
    0xFFD84A,
    0xFF7A00,
    0x258CFF,
)

# --------------------------- DISPLAY -----------------------------
displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=WIDTH,
    height=HEIGHT,
    bit_depth=BIT_DEPTH,
    rgb_pins=[board.GP2, board.GP3, board.GP4, board.GP5, board.GP8, board.GP9],
    addr_pins=[board.GP10, board.GP16, board.GP18, board.GP20, board.GP22],
    clock_pin=board.GP11,
    latch_pin=board.GP12,
    output_enable_pin=board.GP13,
    tile=1,
    serpentine=True,
    doublebuffer=True,
)
DISPLAY = framebufferio.FramebufferDisplay(matrix, auto_refresh=True, rotation=180)
BITMAP = displayio.Bitmap(WIDTH, HEIGHT, len(COLORS))
PALETTE = displayio.Palette(len(COLORS))
for i, color in enumerate(COLORS):
    PALETTE[i] = color
ROOT = displayio.Group()
ROOT.append(displayio.TileGrid(BITMAP, pixel_shader=PALETTE))
try:
    DISPLAY.root_group = ROOT
except AttributeError:
    DISPLAY.show(ROOT)

# ----------------------------- WORLD -----------------------------
SIZE = WIDTH * HEIGHT
food = bytearray(SIZE)       # 0..3
trails = bytearray(SIZE)     # 0..15, high bit marks hunter trail
corpses = bytearray(SIZE)    # decay timer
rain_ticks = 0
frame = 0
world_births = 0
world_deaths = 0
world_kills = 0
last_event = "inicio"
cached_food = 0
cached_mature = 0


def index(x, y):
    return y * WIDTH + x


def wrap_x(x):
    return x % WIDTH


def wrap_y(y):
    if y < TOP:
        return HEIGHT - 1
    if y >= HEIGHT:
        return TOP
    return y


def delta_wrap(a, b, size):
    d = b - a
    half = size // 2
    if d > half:
        d -= size
    elif d < -half:
        d += size
    return d


def sgn(v):
    if v < 0:
        return -1
    if v > 0:
        return 1
    return 0


def pixel(x, y, color):
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        BITMAP[x, y] = color


def rect(x, y, w, h, color):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if 0 <= xx < WIDTH and 0 <= yy < HEIGHT:
                BITMAP[xx, yy] = color


def clear_world_arrays():
    for i in range(SIZE):
        food[i] = 0
        trails[i] = 0
        corpses[i] = 0


def seed_food(count):
    for _ in range(count):
        x = random.randrange(WIDTH)
        y = random.randrange(TOP, HEIGHT)
        food[index(x, y)] = random.choice((1, 1, 2, 2, 3))


def food_cells():
    count = 0
    mature = 0
    for value in food:
        if value:
            count += 1
        if value >= 2:
            mature += 1
    return count, mature


def log_event(text):
    global last_event
    last_event = text
    print("EVENT", frame, text)


class Creature:
    next_id = 1

    def __init__(self, species, x=None, y=None, genes=None, parent_id=0):
        self.id = Creature.next_id
        Creature.next_id += 1
        self.species = species  # 0 grazer, 1 hunter
        self.parent_id = parent_id
        self.x = random.randrange(2, WIDTH - 2) if x is None else wrap_x(x)
        self.y = random.randrange(TOP + 2, HEIGHT - 2) if y is None else wrap_y(y)
        self.old_x = self.x
        self.old_y = self.y
        self.age = 0
        self.energy = 95 if species == 0 else 135
        self.alive = True
        self.facing = random.randrange(4)
        self.move_delay = random.randrange(1, 4)
        self.birth_flash = 18
        self.attack_flash = 0

        if genes is None:
            if species == 0:
                self.speed = random.randrange(2, 5)
                self.vision = random.randrange(5, 9)
                self.metabolism = random.randrange(1, 3)
                self.fertility = random.randrange(3, 6)
                self.courage = random.randrange(2, 7)
            else:
                self.speed = random.randrange(2, 5)
                self.vision = random.randrange(7, 11)
                self.metabolism = random.randrange(2, 4)
                self.fertility = random.randrange(2, 5)
                self.courage = random.randrange(6, 10)
        else:
            self.speed, self.vision, self.metabolism, self.fertility, self.courage = genes

    def mutated_genes(self):
        def mut(value, low, high):
            value += random.choice((-1, 0, 0, 0, 0, 1))
            return max(low, min(high, value))
        return (
            mut(self.speed, 1, 5),
            mut(self.vision, 3, 12),
            mut(self.metabolism, 1, 4),
            mut(self.fertility, 1, 7),
            mut(self.courage, 1, 10),
        )


grazers = []
hunters = []
eggs = []  # [species, x, y, timer, genes, parent_id]


def distance(a, b):
    dx = delta_wrap(a.x, b.x, WIDTH)
    dy = delta_wrap(a.y, b.y, HEIGHT - TOP)
    return abs(dx) + abs(dy)


def nearest_creature(source, creatures, max_dist):
    best = None
    best_dist = max_dist + 1
    for other in creatures:
        if other.alive and other is not source:
            d = distance(source, other)
            if d < best_dist:
                best = other
                best_dist = d
    return best, best_dist


def nearest_food(creature):
    for radius in range(1, creature.vision + 1):
        for offset in range(-radius, radius + 1):
            candidates = (
                (creature.x + offset, creature.y - radius),
                (creature.x + offset, creature.y + radius),
                (creature.x - radius, creature.y + offset),
                (creature.x + radius, creature.y + offset),
            )
            for x, y in candidates:
                x = wrap_x(x)
                y = wrap_y(y)
                if food[index(x, y)] >= 2:
                    return x, y
    return None


def choose_step(creature, target=None, away=False):
    if target is None:
        if random.randrange(100) < 65:
            creature.facing = (creature.facing + random.choice((-1, 0, 0, 0, 1))) % 4
        directions = ((1, 0), (0, 1), (-1, 0), (0, -1))
        return directions[creature.facing]

    tx, ty = target
    dx = sgn(delta_wrap(creature.x, tx, WIDTH))
    dy = sgn(delta_wrap(creature.y, ty, HEIGHT - TOP))
    if away:
        dx = -dx
        dy = -dy
    if dx and dy:
        if random.randrange(2):
            dy = 0
        else:
            dx = 0
    return dx, dy


def move_creature(creature, dx, dy):
    creature.old_x = creature.x
    creature.old_y = creature.y
    creature.x = wrap_x(creature.x + dx)
    creature.y = wrap_y(creature.y + dy)
    if dx > 0:
        creature.facing = 0
    elif dy > 0:
        creature.facing = 1
    elif dx < 0:
        creature.facing = 2
    elif dy < 0:
        creature.facing = 3

    ti = index(creature.old_x, creature.old_y)
    trails[ti] = 0x80 | 12 if creature.species else 12


def update_grazer(g):
    global world_births, world_deaths
    g.age += 1
    g.energy -= g.metabolism
    if g.birth_flash:
        g.birth_flash -= 1
    if g.attack_flash:
        g.attack_flash -= 1

    predator, pd = nearest_creature(g, hunters, g.vision)
    if predator is not None and pd <= g.vision:
        step = choose_step(g, (predator.x, predator.y), away=True)
    else:
        target = nearest_food(g)
        step = choose_step(g, target)

    g.move_delay -= 1
    if g.move_delay <= 0:
        move_creature(g, step[0], step[1])
        g.move_delay = max(1, 6 - g.speed)

    i = index(g.x, g.y)
    if food[i]:
        g.energy = min(180, g.energy + 18 + food[i] * 8)
        food[i] = 0

    population_pressure = len(grazers) + len(hunters) * 2
    can_breed = cached_mature > 35 + population_pressure * 4
    if can_breed and g.energy > 155 and len(grazers) + sum(1 for e in eggs if e[0] == 0) < MAX_GRAZERS:
        chance = 340 - g.fertility * 24 + len(grazers) * 20
        if random.randrange(max(80, chance)) == 0:
            eggs.append([0, g.x, g.y, random.randrange(34, 58), g.mutated_genes(), g.id])
            g.energy -= 65
            world_births += 1
            log_event("huevo herbivoro padre=" + str(g.id))

    if g.energy <= 0 or g.age > 3000 + g.courage * 120:
        g.alive = False
        world_deaths += 1
        corpses[i] = 90
        log_event("muere herbivoro id=" + str(g.id) + " energia=" + str(g.energy))


def update_hunter(h):
    global world_births, world_deaths, world_kills
    h.age += 1
    h.energy -= h.metabolism
    if h.birth_flash:
        h.birth_flash -= 1
    if h.attack_flash:
        h.attack_flash -= 1

    prey, pd = nearest_creature(h, grazers, h.vision)
    target = None if prey is None else (prey.x, prey.y)
    step = choose_step(h, target)

    h.move_delay -= 1
    if h.move_delay <= 0:
        move_creature(h, step[0], step[1])
        h.move_delay = max(1, 6 - h.speed)

    prey, pd = nearest_creature(h, grazers, 2)
    if prey is not None and pd <= 2:
        prey.alive = False
        world_kills += 1
        world_deaths += 1
        corpses[index(prey.x, prey.y)] = 70
        h.energy = min(220, h.energy + 95)
        h.attack_flash = 8
        log_event("caza depredador=" + str(h.id) + " presa=" + str(prey.id))

    can_breed = len(grazers) >= 7 and len(hunters) < max(1, len(grazers) // 4)
    if can_breed and h.energy > 205 and len(hunters) + sum(1 for e in eggs if e[0] == 1) < MAX_HUNTERS:
        chance = 520 - h.fertility * 30 + len(hunters) * 80
        if random.randrange(max(150, chance)) == 0:
            eggs.append([1, h.x, h.y, random.randrange(48, 76), h.mutated_genes(), h.id])
            h.energy -= 100
            world_births += 1
            log_event("huevo depredador padre=" + str(h.id))

    if h.energy <= 0 or h.age > 2600 + h.courage * 100:
        h.alive = False
        world_deaths += 1
        corpses[index(h.x, h.y)] = 100
        log_event("muere depredador id=" + str(h.id) + " energia=" + str(h.energy))


def update_eggs():
    global eggs
    remaining = []
    for egg in eggs:
        egg[3] -= 1
        if egg[3] <= 0:
            species, x, y, _, genes, parent_id = egg
            baby = Creature(species, x, y, genes, parent_id)
            if species == 0 and len(grazers) < MAX_GRAZERS:
                grazers.append(baby)
                log_event("nace herbivoro id=" + str(baby.id) + " padre=" + str(parent_id))
            elif species == 1 and len(hunters) < MAX_HUNTERS:
                hunters.append(baby)
                log_event("nace depredador id=" + str(baby.id) + " padre=" + str(parent_id))
        else:
            remaining.append(egg)
    eggs = remaining


def update_environment():
    global rain_ticks, cached_food, cached_mature

    total_food, mature_food = food_cells()
    cached_food = total_food
    cached_mature = mature_food

    if rain_ticks > 0:
        rain_ticks -= 1
        growth_attempts = 10
    else:
        growth_attempts = 5
        if total_food < 65 and random.randrange(260) == 0:
            rain_ticks = random.randrange(70, 130)
            log_event("comienza lluvia")

    # Regulacion dependiente de densidad. Cuanta mas comida hay, mas lento crece.
    shortage = max(0, TARGET_FOOD - total_food)
    for _ in range(growth_attempts + shortage // 18):
        x = random.randrange(WIDTH)
        y = random.randrange(TOP, HEIGHT)
        i = index(x, y)
        if food[i] == 0 and total_food < MAX_FOOD_CELLS:
            chance = 42 if rain_ticks else 18
            if random.randrange(100) < chance:
                food[i] = 1
                total_food += 1
        elif 0 < food[i] < 3:
            chance = 34 if rain_ticks else 13
            if random.randrange(100) < chance:
                food[i] += 1

    # Si sobra muchisima comida, parte envejece y desaparece. Evita la pantalla toda verde.
    if total_food > TARGET_FOOD + 35:
        for _ in range(8):
            x = random.randrange(WIDTH)
            y = random.randrange(TOP, HEIGHT)
            i = index(x, y)
            if food[i] and random.randrange(100) < 35:
                food[i] -= 1

    cached_food, cached_mature = food_cells()

    # Procesamiento distribuido: no recorre 4096 posiciones en cada frame.
    for _ in range(180):
        i = random.randrange(TOP * WIDTH, SIZE)
        if trails[i]:
            marker = trails[i] & 0x80
            life = (trails[i] & 0x7F) - 1
            trails[i] = marker | life if life > 0 else 0
        if corpses[i]:
            corpses[i] -= 1
            if corpses[i] == 0 and random.randrange(100) < 75:
                food[i] = max(food[i], 2)


def revive_if_needed():
    # Reintroduccion lenta, no una explosion instantanea de poblacion.
    if not grazers and not any(e[0] == 0 for e in eggs):
        if frame % 80 == 0:
            baby = Creature(0)
            grazers.append(baby)
            log_event("reintroduccion herbivoro id=" + str(baby.id))
    if not hunters and len(grazers) >= 8 and not any(e[0] == 1 for e in eggs):
        if frame % 240 == 0:
            baby = Creature(1)
            hunters.append(baby)
            log_event("reintroduccion depredador id=" + str(baby.id))


def draw_background():
    for y in range(TOP, HEIGHT):
        for x in range(WIDTH):
            # Fondo casi negro. Las entidades deben dominar la lectura visual.
            BITMAP[x, y] = GROUND_B if ((x + y) % 17 == 0) else GROUND_A


def draw_environment():
    for y in range(TOP, HEIGHT):
        row = y * WIDTH
        for x in range(WIDTH):
            i = row + x
            if trails[i]:
                BITMAP[x, y] = TRAIL_HUNTER if trails[i] & 0x80 else TRAIL_GRAZER
            if corpses[i]:
                BITMAP[x, y] = CORPSE
            elif food[i] == 1:
                BITMAP[x, y] = FOOD_SMALL
            elif food[i] >= 2:
                BITMAP[x, y] = FOOD_BIG


def draw_egg(egg):
    _, x, y, timer, _, _ = egg
    color = EGG if (timer // 4) & 1 else UI_WHITE
    pixel(x, y, color)
    pixel(wrap_x(x - 1), y, EGG)
    pixel(wrap_x(x + 1), y, EGG)
    pixel(x, wrap_y(y - 1), EGG)
    pixel(x, wrap_y(y + 1), EGG)


def draw_creature(c):
    # Sprite 4x4. Mucho mas facil de reconocer que un punto perdido.
    body = GRAZER_BODY if c.species == 0 else HUNTER_BODY
    light = GRAZER_LIGHT if c.species == 0 else HUNTER_LIGHT
    if c.attack_flash or c.birth_flash:
        body = UI_WHITE if ((frame // 2) & 1) else body

    x = c.x - 1
    y = c.y - 1
    rect(x, y, 4, 4, body)

    # Dos ojos orientados hacia la direccion de movimiento.
    if c.facing == 0:
        pixel(x + 3, y + 1, light)
        pixel(x + 3, y + 2, light)
    elif c.facing == 1:
        pixel(x + 1, y + 3, light)
        pixel(x + 2, y + 3, light)
    elif c.facing == 2:
        pixel(x, y + 1, light)
        pixel(x, y + 2, light)
    else:
        pixel(x + 1, y, light)
        pixel(x + 2, y, light)

    # Una diminuta barra de energia encima.
    energy_max = 180 if c.species == 0 else 220
    filled = max(0, min(4, (c.energy * 4) // energy_max))
    for n in range(4):
        pixel(x + n, y - 1, light if n < filled else UI_DIM)


def draw_ui():
    rect(0, 0, WIDTH, TOP, BLACK)

    # Poblacion: lineas faciles de leer.
    grazer_len = min(20, len(grazers) * 2)
    hunter_len = min(20, len(hunters) * 4)
    rect(1, 1, 20, 2, UI_DIM)
    rect(1, 1, grazer_len, 2, UI_GREEN)
    rect(43, 1, 20, 2, UI_DIM)
    rect(63 - hunter_len, 1, hunter_len, 2, UI_RED)

    # Latido blanco.
    pixel(frame % WIDTH, 4, UI_WHITE)

    # Estado del clima.
    pixel(31, 1, RAIN if rain_ticks else UI_DIM)
    pixel(32, 1, RAIN if rain_ticks else UI_DIM)

    # Generacion aproximada: puntos amarillos, uno por cada 1000 frames.
    generations = min(8, frame // 1000)
    for n in range(8):
        pixel(27 + n, 3, UI_YELLOW if n < generations else UI_DIM)


def draw_rain():
    if rain_ticks:
        for n in range(7):
            x = (frame * 3 + n * 11) % WIDTH
            y = TOP + ((frame * 2 + n * 17) % (HEIGHT - TOP))
            pixel(x, y, RAIN)
            pixel(x, wrap_y(y + 1), RAIN)


def draw():
    draw_background()
    draw_environment()
    for egg in eggs:
        draw_egg(egg)
    for g in grazers:
        if g.alive:
            draw_creature(g)
    for h in hunters:
        if h.alive:
            draw_creature(h)
    draw_rain()
    draw_ui()


def setup():
    clear_world_arrays()
    seed_food(105)
    for _ in range(INITIAL_GRAZERS):
        grazers.append(Creature(0))
    for _ in range(INITIAL_HUNTERS):
        hunters.append(Creature(1))


setup()
print("EVOBOX64 v4 estable")
print("Un archivo, sin librerias externas")
print("Celeste=herbivoro Rojo=depredador Verde=comida Amarillo=huevo")
print("La consola muestra STATUS periodico y EVENT cuando ocurre algo importante")
next_frame = time.monotonic()

while True:
    frame += 1

    update_environment()
    for creature in grazers[:]:
        if creature.alive:
            update_grazer(creature)
    for creature in hunters[:]:
        if creature.alive:
            update_hunter(creature)

    grazers[:] = [g for g in grazers if g.alive]
    hunters[:] = [h for h in hunters if h.alive]
    update_eggs()
    revive_if_needed()
    draw()

    if frame % CONSOLE_EVERY == 0:
        total_food, mature_food = food_cells()
        avg_grazer_energy = (sum(g.energy for g in grazers) // len(grazers)) if grazers else 0
        avg_hunter_energy = (sum(h.energy for h in hunters) // len(hunters)) if hunters else 0
        print(
            "STATUS",
            "frame=" + str(frame),
            "herbivoros=" + str(len(grazers)),
            "depredadores=" + str(len(hunters)),
            "huevos=" + str(len(eggs)),
            "comida=" + str(total_food),
            "madura=" + str(mature_food),
            "energiaH=" + str(avg_grazer_energy),
            "energiaD=" + str(avg_hunter_energy),
            "lluvia=" + str(rain_ticks),
            "nacimientos=" + str(world_births),
            "muertes=" + str(world_deaths),
            "cazas=" + str(world_kills),
            "ultimo=" + last_event,
        )

    next_frame += FRAME_TIME
    delay = next_frame - time.monotonic()
    if delay > 0:
        time.sleep(delay)
    else:
        next_frame = time.monotonic()


