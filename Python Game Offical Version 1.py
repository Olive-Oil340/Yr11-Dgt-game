import sys
import pygame

pygame.init()

SCREEN_WIDTH = 1250
SCREEN_HEIGHT = 700
TILE_SIZE = 50

grass_img = pygame.image.load()

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Epic game cool")

clock = pygame.time.Clock()

# -------------------------
# LEVELS
levels = []

level_1 = [
    ".........................",
    ".........................",
    ".............#####.....##",
    "...................#.....",
    "......#####..............",
    "..........E...............",
    "##############............",
    "..........................",
]

level_2 = [
    ".........................",
    "....E....................",
    "#####....................",
    ".........................",
    "..............#####......",
    ".........................",
    "...........##############",
    ".........................",
]

level_3 = [
    "........................",
    "....................#####",
    "...............#.........",
    ".........................",
    "...........#.............",
    "..............#####......",
    ".........................",
    "##############......E....",
]

level_4 = [
    "........................",
    "#####....................",
    ".........................",
    "........#................",
    "..............#####......",
    ".........................",
    "#########........E.......",
    ".........................",
    ".........................",
    ".........................",
    ".............#....#...#..",
]

level_5 = [
    "........................",
    "........................",
    "......###################",
    "........................",
    "............E............",
    "......###################",
    "...###..................",
    "###.....................",
]

levels.extend([level_1, level_2, level_3, level_4, level_5])

# -------------------------
# BUILD PLATFORMS & ENEMIES
def build_level(level_map):
    platforms = []
    enemies = []
    for row_index, row in enumerate(level_map):
        for col_index, tile in enumerate(row):
            x = col_index * TILE_SIZE
            y = row_index * TILE_SIZE

            if tile == "#":
                platforms.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))

            if tile == "E":
                enemies.append({
                    "rect": pygame.Rect(x, y, TILE_SIZE, TILE_SIZE),
                    "speed": 5
                })

    return platforms, enemies

# -------------------------
# PLAYER
player_width = 40
player_height = 60
player_x = 100
player_y = 100
player_speed = 5

gravity = 0.5
jump_strength = -12
y_velocity = 0
on_ground = False

# Punch system
punching = False
punch_timer = 0
PUNCH_DURATION = 8

# -------------------------
# LEVEL & CHECKPOINT SYSTEM
current_level = 0
platforms, enemies = build_level(levels[current_level])

checkpoint_level = 0
checkpoint_pos = (player_x, player_y)

# -------------------------
# GAME LOOP
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()

    # Movement input
    x_velocity = 0
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        x_velocity = -player_speed
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        x_velocity = player_speed

    # Punch input
    if keys[pygame.K_f] and not punching:
        punching = True
        punch_timer = PUNCH_DURATION

    # Jump
    if (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]) and on_ground:
        y_velocity = jump_strength
        on_ground = False

    # Gravity
    y_velocity += gravity

    # Axis-separated movement
    player_rect = pygame.Rect(player_x, player_y, player_width, player_height)

    # Horizontal
    player_rect.x += x_velocity
    for platform in platforms:
        if player_rect.colliderect(platform):
            if x_velocity > 0:
                player_rect.right = platform.left
            elif x_velocity < 0:
                player_rect.left = platform.right

    # Vertical
    player_rect.y += y_velocity
    on_ground = False
    for platform in platforms:
        if player_rect.colliderect(platform):
            if y_velocity > 0:
                player_rect.bottom = platform.top
                y_velocity = 0
                on_ground = True
            elif y_velocity < 0:
                player_rect.top = platform.bottom
                y_velocity = 0

    player_x, player_y = player_rect.x, player_rect.y

    # -------------------------
    # Punch hitbox
    punch_rect = None
    if punching:
        facing_right = x_velocity >= 0
        if facing_right:
            punch_rect = pygame.Rect(player_rect.right, player_rect.y + 10, 30, 40)
        else:
            punch_rect = pygame.Rect(player_rect.left - 30, player_rect.y + 10, 30, 40)

        punch_timer -= 1
        if punch_timer <= 0:
            punching = False

    # -------------------------
    # ENEMY MOVEMENT + PUNCH DAMAGE
    for enemy in enemies[:]:
        enemy_rect = enemy["rect"]
        speed = enemy["speed"]

        enemy_rect.x += speed

        # Turn around on platform collision
        for platform in platforms:
            if enemy_rect.colliderect(platform):
                enemy_rect.x -= speed
                enemy["speed"] *= -1

        # Turn around at screen edges
        if enemy_rect.left < 0 or enemy_rect.right > SCREEN_WIDTH:
            enemy["speed"] *= -1

        # Punch kills enemy
        if punching and punch_rect and punch_rect.colliderect(enemy_rect):
            enemies.remove(enemy)
            continue

        # Player collision → respawn
        if player_rect.colliderect(enemy_rect):
            print("Hit enemy! Respawning at checkpoint...")
            current_level = checkpoint_level
            platforms, enemies = build_level(levels[current_level])
            player_x, player_y = checkpoint_pos
            y_velocity = 0

    # -------------------------
    # LEVEL SWITCHING
    if player_rect.right >= SCREEN_WIDTH:
        if current_level < len(levels) - 1:
            current_level += 1
            platforms, enemies = build_level(levels[current_level])
            player_x = 15
            player_y = 10
            player_rect.x = player_x
            player_rect.y = player_y

            # Checkpoint every 5 levels
            if current_level % 5 == 0:
                checkpoint_level = current_level
                checkpoint_pos = (player_x, player_y)
                print("Checkpoint reached at Level", current_level + 1)

    # -------------------------
    # DEATH / FALL CHECK
    if player_rect.top > SCREEN_HEIGHT:
        print("Respawning at checkpoint...")
        current_level = checkpoint_level
        platforms, enemies = build_level(levels[current_level])
        player_x, player_y = checkpoint_pos
        y_velocity = 0

    # -------------------------
    # DRAW
    screen.fill((30, 30, 40))

    for platform in platforms:
        pygame.draw.rect(screen, (100, 200, 255), platform)

    for enemy in enemies:
        pygame.draw.rect(screen, (255, 50, 50), enemy["rect"])

    pygame.draw.rect(screen, (255, 80, 80), player_rect)

    if punching and punch_rect:
        pygame.draw.rect(screen, (255, 200, 0), punch_rect)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
