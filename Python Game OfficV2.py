import sys
import pygame

pygame.init()

SCREEN_WIDTH = 1250
SCREEN_HEIGHT = 700
TILE_SIZE = 50

grass_img = pygame.image.load("Grass.png")
ocean_img = pygame.image.load("Background v2.png")
character_img = pygame.image.load("Character.png")

# Scale player sprite
player_width = 40
player_height = 60
character_img = pygame.transform.scale(character_img, (player_width, player_height))

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
    "...............E..........",
    "...........#.............",
    "..............#####......",
    ".........................",
    "##############..........",
]

level_4 = [
    "........................",
    "#####....................",
    ".........................",
    "........#................",
    "..............#####......",
    "...........E..............",
    "#########...............",
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

level_6 = [
    "........................",
    "........................",
    "........................",
    "........................",
    "............E............",
    "......###################",
    "...###..................",
    "###.....................",
]
level_7 = [
    "........................",
    "........................",
    "........................",
    "........................",
    "............B............",
    "........................",
    "#########################",
    "........................",
]

levels.extend([level_1, level_2, level_3, level_4, level_5, level_6, level_7])

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
# GAME STATES
game_state = "menu"  # menu, playing, paused
font = pygame.font.SysFont("Arial", 50)

# -------------------------
# GAME LOOP
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # START MENU INPUT
        if game_state == "menu":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                game_state = "playing"

        # PAUSE MENU INPUT
        if game_state == "playing":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                game_state = "paused"

        elif game_state == "paused":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                game_state = "playing"

    # -------------------------
    # START MENU
    if game_state == "menu":
        screen.fill((0, 0, 0))
        title = font.render("EPIC GAME COOL", True, (255, 255, 255))
        start_text = font.render("Press ENTER to Start", True, (200, 200, 200))
        screen.blit(title, (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 - 100))
        screen.blit(start_text, (SCREEN_WIDTH//2 - 250, SCREEN_HEIGHT//2 + 20))
        pygame.display.flip()
        clock.tick(60)
        continue

    # -------------------------
    # PAUSE MENU
    if game_state == "paused":
        pause_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        pause_overlay.set_alpha(180)
        pause_overlay.fill((0, 0, 0))
        screen.blit(pause_overlay, (0, 0))

        pause_text = font.render("PAUSED", True, (255, 255, 255))
        resume_text = font.render("Press ESC to Resume", True, (200, 200, 200))
        screen.blit(pause_text, (SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2 - 50))
        screen.blit(resume_text, (SCREEN_WIDTH//2 - 250, SCREEN_HEIGHT//2 + 20))

        pygame.display.flip()
        clock.tick(60)
        continue

    # -------------------------
    # GAMEPLAY
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

    # Punch hitbox
    punch_rect = None
    if punching:
        facing_right = x_velocity >= 0
        if facing_right:
            punch_rect = pygame.Rect(player_rect.right, player_rect.y + 10, 30, 40)
        else:
            punch_rect = pygame.Rect(player_rect.left - 30, player_rect.y + 10, 30, 40)

        punch_timer -= 1
        if punch_timer <= 5:
            punching = False

    # ENEMY MOVEMENT + PUNCH DAMAGE
    for enemy in enemies[:]:
        enemy_rect = enemy["rect"]
        speed = enemy["speed"]

        enemy_rect.x += speed

        for platform in platforms:
            if enemy_rect.colliderect(platform):
                enemy_rect.x -= speed
                enemy["speed"] *= -1

        if enemy_rect.left < 0 or enemy_rect.right > SCREEN_WIDTH:
            enemy["speed"] *= -1

        if punching and punch_rect and punch_rect.colliderect(enemy_rect):
            enemies.remove(enemy)
            continue

        if player_rect.colliderect(enemy_rect):
            current_level = checkpoint_level
            platforms, enemies = build_level(levels[current_level])
            player_x, player_y = checkpoint_pos
            y_velocity = 0

    # LEVEL SWITCHING
    if player_rect.right >= SCREEN_WIDTH:
        if current_level < len(levels) - 1:
            current_level += 1
            platforms, enemies = build_level(levels[current_level])
            player_x = 15
            player_y = 10

            if current_level % 5 == 0:
                checkpoint_level = current_level
                checkpoint_pos = (player_x, player_y)

    # DEATH CHECK
    if player_rect.top > SCREEN_HEIGHT:
        current_level = checkpoint_level
        platforms, enemies = build_level(levels[current_level])
        player_x, player_y = checkpoint_pos
        y_velocity = 0

    # -------------------------
    # DRAW
    background_img = pygame.transform.scale(ocean_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(background_img, (0, 0))

    for platform in platforms:
        platform_img = pygame.transform.scale(grass_img, (platform.width, platform.height))
        screen.blit(platform_img, platform.topleft)

    for enemy in enemies:
        pygame.draw.rect(screen, (255, 50, 50), enemy["rect"])

    screen.blit(character_img, (player_x, player_y))

    if punching and punch_rect:
        pygame.draw.rect(screen, (255, 200, 0), punch_rect)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
