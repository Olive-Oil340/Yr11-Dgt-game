# Dgt game 2026 — Full combined script (Part 1)
import sys
import os
import pygame

pygame.init()

# -------------------------
# CONFIG
SCREEN_WIDTH = 1250
SCREEN_HEIGHT = 700
TILE_SIZE = 50

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Dgt game 2026")
clock = pygame.time.Clock()

# -------------------------
# ASSETS
grass_img = pygame.image.load("Ocean Platform.png")
ocean_img = pygame.image.load("Background v2.png")
characterRight_img = pygame.image.load("CharacterV2.png")
characterLeft_img = pygame.transform.flip(characterRight_img, True, False)
enemyRight_img = pygame.image.load("Enemy.png")
enemyLeft_img = pygame.transform.flip(enemyRight_img, True, False)
boss_img = pygame.image.load("Dragon Boss.png")
blockright_img = pygame.image.load("Wave block.png")
blockleft_img = pygame.transform.flip(blockright_img, True, False)
block_img = blockright_img

player_width = 40
player_height = 60
character_img = pygame.transform.scale(characterLeft_img, (player_width, player_height))
enemy_img = pygame.transform.scale(enemyLeft_img, (TILE_SIZE, TILE_SIZE))
boss_img = pygame.transform.scale(boss_img, (TILE_SIZE * 6, TILE_SIZE * 6 ))

pygame.mixer.init()
pygame.mixer.music.load("background music.mp3")
pygame.mixer.music.play(-1,0.0)

font = pygame.font.SysFont("Arial", 50)
small_font = pygame.font.SysFont("Arial", 28)

# -------------------------
# LEVELS
levels = []

level_1 = [
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".......................####",
    ".....................#.....",
    "..................##.......",
    "................##.........",
    "..............##..........",
    "##############............",
]

level_2 = [
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    "#####....................",
    "......................E..",
    "..............#####......",
    "................E.........",
    "...........##############",
]

level_3 = [
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    "....................#####",
    "...............#.........",
    "...............E.........",
    "...........#.............",
    "..............#####......",
    ".........................",
    "##############..........",
]

level_4 = [
    "........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    "........#................",
    "..............#####......",
    "...........E.............",
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
    "..................E.....",
    ".........E........#.....",
    "...............#....E...",
    "..............#.........",
    "........E...####........",
    "......##########........",
    "...###..................",
    "###.....................",
]

level_7 = [
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    "..............B..........",
    "#########################",
]

levels.extend([level_1, level_2, level_3, level_4, level_5, level_6, level_7])

# -------------------------
# LEVEL BUILDING
def build_level(level_map):
    platforms = []
    enemies = []
    boss = None

    for row_index, row in enumerate(level_map):
        for col_index, tile in enumerate(row):
            x = col_index * TILE_SIZE
            y = row_index * TILE_SIZE

            if tile == "#":
                platforms.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))

            elif tile == "E":
                enemies.append({
                    "rect": pygame.Rect(x, y, TILE_SIZE, TILE_SIZE),
                    "speed": 3,
                    "health": 3
                })

            elif tile == "B":
                boss = {
                    "rect": pygame.Rect(x, y - TILE_SIZE * 5, TILE_SIZE * 5, TILE_SIZE * 5),
                    "health": 10,
                    "speed": 2,
                    "attack_timer": 0
                }

    return platforms, enemies, boss

# -------------------------
# PLAYER
player_x = 100
player_y = 100
player_speed = 5

gravity = 0.5
jump_strength = -12
y_velocity = 0
on_ground = False

punching = False
punch_timer = 0
PUNCH_DURATION = 8

player_health = 5
max_player_health = 5

# ENEMIES
# enemy_facing_right = True
# enemy_facing_left = False
# -------------------------
# LEVEL & CHECKPOINT
current_level = 0
platforms, enemies, boss = build_level(levels[current_level])

checkpoint_level = 0
checkpoint_pos = (player_x, player_y)

# -------------------------
# GAME STATE & SPEEDRUN
game_state = "menu"  # menu, playing, paused, enter_username, scoreboard
geysers = []

speedrun_mode = False
username = ""
timer_start = None
timer_time = 0
scoreboard = []

SCOREBOARD_FILE = "speedrun_scores.txt"

# Load scoreboard
if os.path.exists(SCOREBOARD_FILE):
    with open(SCOREBOARD_FILE, "r") as f:
        scoreboard = [line.strip() for line in f.readlines()]
else:
    scoreboard = []

# Helper to save a score
def save_score(name, time_seconds):
    entry = f"{name} - {time_seconds:.2f}s"
    scoreboard.append(entry)
    with open(SCOREBOARD_FILE, "a") as f:
        f.write(entry + "\n")
# Dgt game 2026 — Full combined script (Part 2)
running = True
while running:
    # Event handling (top-level)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Menu input handling
        if game_state == "menu":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    speedrun_mode = False
                    timer_start = None
                    timer_time = 0
                    game_state = "playing"
                    current_level = 0
                    platforms, enemies, boss = build_level(levels[current_level])
                    player_x, player_y = 100, 100
                    y_velocity = 0
                if event.key == pygame.K_s:
                    game_state = "enter_username"
                    username = ""

        # Enter username screen events handled below in that block
        elif game_state == "enter_username":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if username.strip() == "":
                        username = "Player"
                    speedrun_mode = True
                    timer_start = pygame.time.get_ticks()
                    timer_time = 0
                    current_level = 0
                    platforms, enemies, boss = build_level(levels[current_level])
                    player_x, player_y = 100, 100
                    y_velocity = 0
                    game_state = "playing"
                elif event.key == pygame.K_BACKSPACE:
                    username = username[:-1]
                else:
                    # Only accept printable characters
                    if event.unicode.isprintable():
                        username += event.unicode

        # Pause toggle
        elif game_state == "playing":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                game_state = "paused"

        elif game_state == "paused":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                game_state = "playing"

        elif game_state == "scoreboard":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                game_state = "menu"
                speedrun_mode = False
                timer_start = None
                timer_time = 0

    # -------------------------
    # MENU
    if game_state == "menu":
        screen.fill((0, 0, 0))
        title = font.render("Dgt Game 2026", True, (255, 255, 255))
        start_text = font.render("Press ENTER to Start", True, (200, 200, 200))
        speedrun_text = font.render("Press S for Speedrun Mode", True, (200, 200, 0))
        screen.blit(title, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 100))
        screen.blit(start_text, (SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2 + 20))
        screen.blit(speedrun_text, (SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT // 2 + 100))

        # show top 3 scores on menu
        menu_scores = scoreboard[-3:]
        y = SCREEN_HEIGHT // 2 + 180
        header = small_font.render("Recent Speedrun Scores:", True, (180, 180, 180))
        screen.blit(header, (SCREEN_WIDTH // 2 - 200, y))
        y += 30
        for s in reversed(menu_scores):
            txt = small_font.render(s, True, (0, 255, 0))
            screen.blit(txt, (SCREEN_WIDTH // 2 - 200, y))
            y += 26

        pygame.display.flip()
        clock.tick(60)
        continue

    # -------------------------
    # ENTER USERNAME SCREEN
    if game_state == "enter_username":
        screen.fill((0, 0, 0))
        prompt = font.render("Enter Username:", True, (255, 255, 255))
        name_display = font.render(username, True, (0, 255, 0))
        hint = small_font.render("Press ENTER to start speedrun", True, (180, 180, 180))
        screen.blit(prompt, (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 - 50))
        screen.blit(name_display, (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 + 20))
        screen.blit(hint, (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 + 90))
        pygame.display.flip()
        clock.tick(60)
        continue

    # -------------------------
    # PAUSE
    if game_state == "paused":
        pause_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        pause_overlay.set_alpha(180)
        pause_overlay.fill((0, 0, 0))
        screen.blit(pause_overlay, (0, 0))

        pause_text = font.render("PAUSED", True, (255, 255, 255))
        resume_text = font.render("Press ESC to Resume", True, (200, 200, 200))
        screen.blit(pause_text, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 50))
        screen.blit(resume_text, (SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2 + 20))

        pygame.display.flip()
        clock.tick(60)
        continue

    # -------------------------
    # GAMEPLAY
    keys = pygame.key.get_pressed()

    # DEV TELEPORT
    if keys[pygame.K_6]:
        current_level = 6
        platforms, enemies, boss = build_level(levels[current_level])
        player_x, player_y = 100, 100
        y_velocity = 0
        checkpoint_level = current_level
        checkpoint_pos = (player_x, player_y)

    # Movement
    x_velocity = 0
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        x_velocity = -player_speed
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        x_velocity = player_speed

    # Punch
    if keys[pygame.K_f] and not punching:
        punching = True
        punch_timer = PUNCH_DURATION

    # Jump
    if (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]) and on_ground:
        y_velocity = jump_strength
        on_ground = False

    # Gravity
    y_velocity += gravity

    # Movement & collisions
    player_facing_right = x_velocity >= 0
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
            punch_rect = pygame.Rect(player_rect.left -30, player_rect.y + 10, 30, 40)

        punch_timer -= 1
        if punch_timer <= 0:
            punching = False

    # -------------------------
    # ENEMIES
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
            '''if enemy_facing_right:
                enemy_facing_right = False
                enemy_facing_left = True
            elif enemy_facing_left:
                enemy_facing_left = False
                enemy_facing_right = True'''

        # Punch damage
        if punching and punch_rect and punch_rect.colliderect(enemy_rect):
            enemy["health"] -= 1
            if enemy["health"] <= 0:
                enemies.remove(enemy)
            continue

        # Player damage
        if player_rect.colliderect(enemy_rect):
            player_health -= 1
            if player_health <= 0:
                current_level = checkpoint_level
                platforms, enemies, boss = build_level(levels[current_level])
                player_x, player_y = checkpoint_pos
                y_velocity = 0
                player_health = max_player_health

    # -------------------------
    # BOSS + GEYSERS
    if boss:
        boss_rect = boss["rect"]

        boss_rect.x += boss["speed"]
        if boss_rect.left < 0 or boss_rect.right > SCREEN_WIDTH:
            boss["speed"] *= -1

        for platform in platforms:
            if boss_rect.colliderect(platform):
                boss_rect.x -= boss["speed"]
                boss["speed"] *= -1

        boss["attack_timer"] += 1

        if boss["attack_timer"] >= 60:
            boss["attack_timer"] = 0
            GEYSER_Y = 370
            GEYSER_HEIGHT = 300

            geysers = [
                {"rect": pygame.Rect(player_x - 20, GEYSER_Y, 20, GEYSER_HEIGHT), "warning": 40, "active": 30},
                {"rect": pygame.Rect(player_x + 20, GEYSER_Y, 20, GEYSER_HEIGHT), "warning": 40, "active": 30},
            ]

        for geyser in geysers[:]:
            if geyser["warning"] > 0:
                geyser["warning"] -= 1
                continue

            geyser["active"] -= 1
            if geyser["active"] <= 0:
                geysers.remove(geyser)
                continue

            if player_rect.colliderect(geyser["rect"]):
                player_health -= 1
                if player_health <= 0:
                    current_level = checkpoint_level
                    platforms, enemies, boss = build_level(levels[current_level])
                    player_x, player_y = checkpoint_pos
                    y_velocity = 0
                    player_health = max_player_health

        # Punch boss
        if punching and punch_rect and punch_rect.colliderect(boss_rect):
            boss["health"] -= 1
            if boss["health"] <= 0:
                # Speedrun finish handling
                if speedrun_mode and timer_start is not None:
                    final_time = (pygame.time.get_ticks() - timer_start) / 1000.0
                    save_score(username if username.strip() != "" else "Player", final_time)
                    game_state = "scoreboard"
                    speedrun_mode = False
                    timer_start = None
                    timer_time = final_time

                boss = None
                current_level += 1
                if current_level < len(levels):
                    platforms, enemies, boss = build_level(levels[current_level])
                player_x, player_y = 15, 10

    # -------------------------
    # LEVEL SWITCH
    if player_rect.right >= SCREEN_WIDTH:
        if current_level < len(levels) - 1:
            current_level += 1
            platforms, enemies, boss = build_level(levels[current_level])
            player_x, player_y = 15, 10
            y_velocity = 0

            if current_level % 5 == 0:
                checkpoint_level = current_level
                checkpoint_pos = (player_x, player_y)

    # -------------------------
    # DEATH
    if player_rect.top > SCREEN_HEIGHT:
        current_level = checkpoint_level
        platforms, enemies, boss = build_level(levels[current_level])
        player_x, player_y = checkpoint_pos
        y_velocity = 0

    # -------------------------
    # DRAW
    bg = pygame.transform.scale(ocean_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(bg, (0, 0))

    for platform in platforms:
        tile = pygame.transform.scale(grass_img, (platform.width, platform.height))
        screen.blit(tile, platform.topleft)

    for enemy in enemies:
        if enemy["speed"]> 0:
            enemy_img = pygame.transform.scale(enemyLeft_img, (TILE_SIZE, TILE_SIZE))
        else:
            enemy_img = pygame.transform.scale(enemyRight_img, (TILE_SIZE, TILE_SIZE))
        screen.blit(enemy_img, enemy["rect"])
        # Enemy health bar
        pygame.draw.rect(screen, (255,0,0), (enemy["rect"].x, enemy["rect"].y - 10, TILE_SIZE, 5))
        pygame.draw.rect(screen, (0,255,0), (enemy["rect"].x, enemy["rect"].y - 10, TILE_SIZE * max(0, enemy["health"] / 3), 5))

    if boss:
        screen.blit(boss_img, boss["rect"])
        for geyser in geysers:
            if geyser["warning"] > 0:
                pygame.draw.circle(screen,(255,0,0),(geyser["rect"].x + geyser["rect"].width//2, 650),12)
            else:
                surf = pygame.Surface((geyser["rect"].width, geyser["rect"].height), pygame.SRCALPHA)
                surf.fill((0,150,255,200))
                screen.blit(surf, (geyser["rect"].x, 370))

        # Boss health bar
        max_boss_health = 10
        boss_health_ratio = max(0, boss["health"] / max_boss_health)
        pygame.draw.rect(screen, (255,0,0), (SCREEN_WIDTH//2 - 200, 20, 400, 25))
        pygame.draw.rect(screen, (0,255,0), (SCREEN_WIDTH//2 - 200, 20, 400 * boss_health_ratio, 25))

    # Player sprite
    if player_facing_right:
        character_img = characterRight_img
    else:
        character_img = characterLeft_img
    screen.blit(character_img, (player_rect.x, player_rect.y))

    if punching and punch_rect:
        if facing_right:
            block_img = blockright_img
        else:
            block_img = blockleft_img
        screen.blit(block_img, punch_rect)

    # Player health bar
    pygame.draw.rect(screen, (255,0,0), (20, 20, 200, 20))
    pygame.draw.rect(screen, (0,255,0), (20, 20, 200 * max(0, player_health / max_player_health), 20))

    # Speedrun timer display
    if speedrun_mode and timer_start is not None:
        timer_time = (pygame.time.get_ticks() - timer_start) / 1000.0
        timer_text = small_font.render(f"Time: {timer_time:.2f}s", True, (255, 255, 0))
        screen.blit(timer_text, (SCREEN_WIDTH - 260, 20))

    pygame.display.flip()
    clock.tick(60)

    # -------------------------
    # SCOREBOARD SCREEN (handled after frame to avoid nested event loops)
    if game_state == "scoreboard":
        screen.fill((0, 0, 0))
        title = font.render("Speedrun Scores", True, (255, 255, 255))
        screen.blit(title, (SCREEN_WIDTH//2 - 200, 50))

        y_offset = 150
        # show last 10 scores, newest first
        for entry in reversed(scoreboard[-10:]):
            score_text = small_font.render(entry, True, (0, 255, 0))
            screen.blit(score_text, (SCREEN_WIDTH//2 - 200, y_offset))
            y_offset += 30

        back_text = small_font.render("Press ENTER to return to menu", True, (200, 200, 200))
        screen.blit(back_text, (SCREEN_WIDTH//2 - 300, SCREEN_HEIGHT - 100))

        pygame.display.flip()

        # Wait here until user presses ENTER or quits
        waiting = True
        while waiting:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    waiting = False
                    running = False
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
                    waiting = False
                    game_state = "menu"
                    speedrun_mode = False
                    timer_start = None
                    timer_time = 0
            clock.tick(30)

pygame.quit()
sys.exit()
