# =========================================================
# Dgt game 2026 — Code
# =========================================================
#   1. CONFIG          - window/tile settings
#   2. ASSETS          - images, sounds, fonts
#   3. LEVELS          - the level maps + code that turns them into
#                        platforms / enemies / a boss
#   4. PLAYER STATE    - starting position, health, movement constants
#   5. UI RECTS        - clickable button positions
#   6. GAME STATE       - which screen we're on (menu, playing, etc.)
#   7. LEADERBOARD     - loading/saving/sorting speedrun scores
#   8. MAIN LOOP       - event handling, physics, drawing, per screen
#
# =========================================================

# ---- Imports ----
# sys / os      -> quitting the program cleanly and building file paths
# math          -> used for the boss's floating motion (sin) and fireball angles
# wave / struct / tempfile -> not actually used for sound generation here, but
#                              were left available in case sounds need to be
#                              built on the fly instead of loaded from disk
# pygame        -> the game engine: window, drawing, input, sound, timing
import sys
import os
import math
import wave
import struct
import tempfile
import pygame

# pygame must be initialised before any other pygame calls are made.
pygame.init()

# -------------------------
# 1. CONFIG
# -------------------------
# Basic window and grid settings used everywhere else in the file.
SCREEN_WIDTH = 1250          # width of the game window, in pixels
SCREEN_HEIGHT = 700          # height of the game window, in pixels
TILE_SIZE = 50               # every level tile (platform/enemy/etc.) is a 50x50 square

# Create the actual window the game will be drawn to.
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Ruatepupuke’s wood carvings")   # text shown in the window title bar
clock = pygame.time.Clock()  # used later to lock the game to 60 frames per second

# -------------------------
# 2. ASSETS
# -------------------------
# This section loads every image, sound and font the game needs, once,
# at the very start. Loading them once (instead of during the main loop)
# keeps the game running smoothly.

# --- Images ---
# Always load assets from the same folder as this Python file. This fixes
# problems caused by running the game from a different working directory.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # folder this .py file lives in

def asset_path(filename):
    """Turn a plain filename (e.g. 'Enemy.png') into a full path next to this script."""
    return os.path.join(BASE_DIR, filename)

def load_image(filename):
    """Load an image reliably, including PNG files Pygame cannot decode directly."""
    path = asset_path(filename)
    try:
        # Normal case: pygame can read the image directly.
        return pygame.image.load(path)
    except pygame.error:
        # Some PNG files are saved with an encoding that SDL/Pygame cannot read.
        # Pillow can decode those and convert them into a normal RGBA surface.
        try:
            from PIL import Image
            with Image.open(path) as img:
                img = img.convert("RGBA")                 # make sure it has transparency info
                data = img.tobytes()                       # raw pixel bytes
                return pygame.image.fromstring(data, img.size, "RGBA").convert_alpha()
        except Exception as exc:
            # If even Pillow can't open it, stop the game with a clear error
            # instead of a confusing crash somewhere else.
            raise pygame.error(
                f"Could not load image '{filename}'. Make sure the file is a valid image "
                f"and is in the same folder as the game. Details: {exc}"
            )

# Load every raw image used in the game. Left/Right facing versions of the
# player, enemy and blocks are created by flipping the original horizontally.
grass_img = load_image("Ocean Platform.png")          # texture used for platforms
ocean_img = load_image("Background v2.png")           # background image
characterRight_img = load_image("CharacterV2.png")    # player sprite, facing right
characterLeft_img = pygame.transform.flip(characterRight_img, True, False)  # flipped -> facing left
enemyRight_img = load_image("Enemy.png")
enemyLeft_img = pygame.transform.flip(enemyRight_img, True, False)
boss_img = load_image("Dragon Boss.png")
blockright_img = load_image("Wave block.png")         # the "punch effect" graphic
blockleft_img = pygame.transform.flip(blockright_img, True, False)
block_img = blockright_img  # default punch-effect sprite before facing is known
characterWalking_img = load_image("character v2 walking.png")     # walk-cycle frame 1
characterwalking_img = load_image("character v2 walking walking.png")  # walk-cycle frame 2
menuscreen_img = load_image("Menu screen.png")
Fragments_img = load_image("Fragments.png")           # collectible fragment icon


# Player/enemy sprite sizes (in pixels) used for scaling and for collision boxes.
player_width = 40
player_height = 60
character_img = pygame.transform.scale(characterLeft_img, (player_width, player_height))
enemy_img = pygame.transform.scale(enemyLeft_img, (TILE_SIZE, TILE_SIZE))

# The boss image is loaded again and scaled up to 6 tiles wide/tall, since the
# boss is meant to look much bigger than a normal enemy.
boss_img = load_image("Dragon Boss.png")
boss_img = pygame.transform.scale(boss_img, (TILE_SIZE * 6, TILE_SIZE * 6))

# Boss faces right by default; flip it for when it's moving/facing left
boss_right_img = boss_img
boss_left_img = pygame.transform.flip(boss_img, True, False)

# Small icons used on the tutorial screen (smaller than the in-game sprites).
character_icon = pygame.transform.scale(characterRight_img, (32, 48))
enemy_icon = pygame.transform.scale(enemyRight_img, (40, 40))

# --- Player animation frames ---
# Idle frames (standing still / in the air)
idle_right_img = pygame.transform.scale(characterRight_img, (player_width, player_height))
idle_left_img = pygame.transform.scale(characterLeft_img, (player_width, player_height))

# Walk-cycle frames, built from the two walking sprites. The idle frame is
# reused as the "middle" contact frame so the cycle reads as idle -> step -> idle -> step.
_walk_step1_right = pygame.transform.scale(characterWalking_img, (player_width, player_height))
_walk_step2_right = pygame.transform.scale(characterwalking_img, (player_width, player_height))
_walk_step1_left = pygame.transform.flip(_walk_step1_right, True, False)
_walk_step2_left = pygame.transform.flip(_walk_step2_right, True, False)

# Each list is a 4-frame walking animation cycled through while the player moves.
walk_frames_right = [idle_right_img, _walk_step1_right, idle_right_img, _walk_step2_right]
walk_frames_left = [idle_left_img, _walk_step1_left, idle_left_img, _walk_step2_left]

ANIMATION_FRAME_DURATION = 6  # game frames each walk-cycle frame is shown for
# (Lower = faster-looking walk animation, higher = slower.)

# --- Music ---
pygame.mixer.init()  # start up the sound system
pygame.mixer.music.load(asset_path("background music.mp3"))
pygame.mixer.music.play(-1, 0.0)  # -1 means "loop forever", starting at position 0.0 seconds

# --- Sound effects ---
# Loaded defensively: if a sound file is missing put into silent.
# no-op instead of crashing the whole game.
def load_sound(path):
    """Try to load a sound effect; return None (silently) if it can't be loaded."""
    try:
        return pygame.mixer.Sound(asset_path(path))
    except Exception:
        return None

hit_sound = load_sound("hit.wav")
punch_sound = load_sound("punch.wav")
enemy_death_sound = load_sound("enemy death.wav")
boss_defeat_sound = load_sound("boss defeat.wav")

muted = False  # global mute flag, toggled with the M key while playing

def play_sound(sound):
    """Play a sound effect, but only if it loaded successfully and the game isn't muted."""
    if sound is not None and not muted:
        sound.play()

# --- Fonts ---
font = pygame.font.SysFont("Arial", 50)        # large font, used for titles/headings
small_font = pygame.font.SysFont("Arial", 28)  # smaller font, used for body text/buttons



# -------------------------
# 3. LEVELS
# -------------------------
# Each level is a list of strings ("rows"). Each character is one tile:
#   "."  -> empty space
#   "#"  -> platform
#   "E"  -> a enemy spawn point
#   "B"  -> the boss spawn point (only used in the final level)
#   "F"  ->  collectible fragment
# The row/column position of each character in these strings is later
# multiplied by TILE_SIZE (in build_level) to work out its real pixel position.
levels = []

# --- Level 1: a gentle introduction level with one fragment, no enemies ---
level_1 = [
        ".........................",
        ".........................",
        ".........................",
        ".........................",
        ".........................",
        ".........................",
        ".........................",
        ".........................",
        ".......................#############",
        ".....................#..............",
        "..................##.............",
        "................##............F.####",
        "...............#..............#",
        "##################..#...#....#...",
]

# --- Level 2: introduces two enemies and a fragment ---
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
    "..................F...E..",
    "..............#####......",
    "................E.........",
    "...........##############",
]

# --- Level 3: more platforming, one enemy, one fragment ---
level_3 = [
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    "....................###########",
    "...............#.........",
    "..............E.........",
    "..........#.............",
    "..............#####........",
    ".........................F",
    "##############.........#########",
]

# --- Level 4: one enemy, one fragment, trickier platform layout ---
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
    "...................................######",
    ".....F...................######.....",
    ".....#...#...#....#...#..#",
]

# --- Level 5: one enemy, long open corridor, no fragment break ---
level_5 = [
    "........................",
    "........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    "........................",
    "......########################",
    "........................",
    "............E............",
    "......#######################",
    "...###..................",
    "###.....................",
]

# --- Level 6:  - four enemies and the final fragment ---
level_6 = [
    "........................",
    "........................",
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    "..................E.....",
    ".........E........#.....",
    "...............#....E...",
    "..............#.........",
    "........E...####.....F..",
    "......##########.....#..",
    "...###..................",
    "###.....................",
]

# --- Level 7: the boss arena. Flat floor, single "B" spawns the boss ---
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

# Put all the levels together, in play order, into a single list the rest
# of the game can index into using current_level.
levels.extend([level_1, level_2, level_3, level_4, level_5, level_6, level_7])


# -------------------------
# LEVEL BUILDING
# -------------------------
# Fragment positions that have already been collected.
# Stored as (level_number, row, column), so collected fragments stay collected
# even if the player dies or reloads a level.
collected_fragment_positions = set()
fragments_collected = 0      # running total of fragments collected across the whole game
TOTAL_FRAGMENTS = 5          # number of fragments needed to unlock the secret ending


def build_level(level_map):
    """Turn a level map (list of strings) into actual game objects.

    Reads every character in the map and creates the matching object:
      '#' -> a platform Rect the player/enemies can stand on / collide with
      'E' -> a dictionary describing one enemy (position, speed, health)
      'F' -> a dictionary describing one collectible fragment (skipped if
             that exact fragment was already collected earlier)
      'B' -> a dictionary describing the boss (only appears in level 7)

    Returns a tuple: (platforms, enemies, fragments, boss)
    """
    platforms = []
    enemies = []
    fragments = []
    boss = None

    # Walk through every row and every character in that row.
    for row_index, row in enumerate(level_map):
        for col_index, tile in enumerate(row):
            # Convert the tile's grid position into real pixel coordinates.
            x = col_index * TILE_SIZE
            y = row_index * TILE_SIZE

            if tile == "#":
                # Solid ground/wall tile -> just a rectangle used for collision.
                platforms.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))

            elif tile == "E":
                # A basic patrolling enemy. "speed" also doubles as its
                # patrol direction (positive = moving right, negative = left).
                enemies.append({
                    "rect": pygame.Rect(x, y, TILE_SIZE, TILE_SIZE),
                    "speed": 3,
                    "health": 3
                })

            elif tile == "F":
                # "F" in the level map places a collectible fragment.
                # It is centered inside the tile and disappears when collected.
                fragment_key = (current_level, row_index, col_index)
                # Only add the fragment back into the level if the player
                # hasn't already picked it up previously (e.g. after dying).
                if fragment_key not in collected_fragment_positions:
                    fragments.append({
                        "rect": pygame.Rect(
                            x + TILE_SIZE // 4,      # shrink the box so it sits
                            y + TILE_SIZE // 4,      # centered inside the tile
                            TILE_SIZE // 2,
                            TILE_SIZE // 2
                        ),
                        "row": row_index,
                        "col": col_index
                    })

            elif tile == "B":
                # The boss sprite is much bigger than one tile, so it's
                # spawned above and to the left of its "B" marker so its
                # feet roughly line up with the marker. The hitbox matches
                # the full sprite. The boss floats above the ground and
                # bobs up and down rather than walking on platforms.
                boss_size = TILE_SIZE * 6
                boss_max_health = 300
                float_base_y = y - boss_size - TILE_SIZE  # closer to the ground than before
                boss = {
                    "rect": pygame.Rect(x, float_base_y, boss_size, boss_size),
                    "health": boss_max_health,
                    "max_health": boss_max_health,
                    "speed": 6,                # horizontal patrol speed (and direction)
                    "attack_timer": 0,         # counts up while patrolling, toward next attack
                    "state": "patrol",         # "patrol"
                    "telegraph_timer": 0,      # counts down during the warning flash before attacking
                    "float_base_y": float_base_y,   # the "resting" height the bob motion is centred on
                    "float_timer": 0,          # feeds the sine wave used for the floating bob
                    "attack_cycle": ["geyser", "fireball", "geyser", "meteor"],  # order of attacks
                    "attack_index": 0,         # which attack in attack_cycle is next
                    "phase": 1,                # phase 2 kicks in at half health, attacks faster
                }

    return platforms, enemies, fragments, boss


def get_level_width(level_map):
    """Work out how wide a level is in pixels (levels can be wider than the screen).

    The camera needs to know this so it knows how far it's allowed to scroll.
    If every row is shorter than the screen, the level width is just the
    screen width (no need to scroll).
    """
    if not level_map:
        return SCREEN_WIDTH
    return max(SCREEN_WIDTH, max(len(row) for row in level_map) * TILE_SIZE)


# -------------------------
# 4. PLAYER STATE
# -------------------------
# Starting position and movement-related constants/variables for the player.
player_x = 100
player_y = 100
player_speed = 5          # horizontal movement speed, in pixels per frame

gravity = 0.5              # the amount of gravity 
jump_strength = -12        # instant upward velocity applied when jumping (negative = up)
y_velocity = 0             # current vertical speed (changes constantly due to gravity/jumping)
on_ground = False          # whether the player is currently standing on a platform

punching = False                       # true while a punch animation/hitbox is active
punch_timer = 0                        # counts down while a punch is in progress
PUNCH_DURATION = 8                     # how many frames a punch lasts
PUNCH_COOLDOWN_DURATION = 20  # frames after a punch finishes before you can punch again
punch_cooldown_timer = 0               # counts down during the cooldown after punching

player_health = 5
max_player_health = 5

# Invincibility frames: player can't take damage again for a short time after being hit
PLAYER_INVINCIBLE_DURATION = 60  # ~1 second at 60 fps
player_invincible_timer = 0      # counts down; while > 0 the player can't be hurt again

player_anim_timer = 0            # increases every frame; used to pick the current walk frame

# -------------------------
# LEVEL & CHECKPOINT
# -------------------------
current_level = 0
# Build the very first level into actual game objects before the main loop starts.
platforms, enemies, fragments, boss = build_level(levels[current_level])
level_width = get_level_width(levels[current_level])
camera_x = 0   # how far the "camera" (view of the level) has scrolled to the right

# Checkpoints let the player respawn partway through the game instead of
# always going back to level 1 after dying.
checkpoint_level = 0
checkpoint_pos = (player_x, player_y)

# -------------------------
# 5. UI RECTS (clickable buttons)
# -------------------------
# Rect = pygame's rectangle type: (x, y, width, height). These are the
# clickable areas for buttons on the pause and victory/rescue screens.
BUTTON_WIDTH = 260
BUTTON_HEIGHT = 60
pause_resume_rect = pygame.Rect(SCREEN_WIDTH // 2 - BUTTON_WIDTH // 2, SCREEN_HEIGHT // 2 - 90, BUTTON_WIDTH, BUTTON_HEIGHT)
pause_restart_rect = pygame.Rect(SCREEN_WIDTH // 2 - BUTTON_WIDTH // 2, SCREEN_HEIGHT // 2 - 10, BUTTON_WIDTH, BUTTON_HEIGHT)
pause_menu_rect = pygame.Rect(SCREEN_WIDTH // 2 - BUTTON_WIDTH // 2, SCREEN_HEIGHT // 2 + 70, BUTTON_WIDTH, BUTTON_HEIGHT)
victory_menu_rect = pygame.Rect(SCREEN_WIDTH // 2 - BUTTON_WIDTH // 2, SCREEN_HEIGHT // 2 + 120, BUTTON_WIDTH, BUTTON_HEIGHT)

# Menu buttons are rebuilt every frame the menu is drawn (list length varies with Continue)
menu_buttons = []

scoreboard_clear_rect = pygame.Rect(SCREEN_WIDTH // 2 - 130, SCREEN_HEIGHT - 150, 260, 50)

# -------------------------
# 6. GAME STATE & SPEEDRUN
# -------------------------
# game_state controls which "screen" is currently active. The main loop
# checks this value to decide what to draw and how to respond to input.
game_state = "menu"  # menu, playing, paused, enter_username, scoreboard, tutorial, victory, rescue
boss_projectiles = []   # list of fireballs currently flying toward the player
boss_hazards = []       # list of active/warning geysers and meteors

speedrun_mode = False    # true if the player chose "Speedrun Mode" from the menu
username = ""            # name typed in on the "enter username" screen
timer_start = None       # tick count (ms) when the speedrun timer started, or None if not running
timer_time = 0           # most recently calculated elapsed speedrun time, in seconds

SCOREBOARD_FILE = "speedrun_scoresv2.txt"   # text file the leaderboard is saved to/loaded from



# -------------------------
# 7. LEADERBOARD
# -------------------------
# Scores are stored on disk as plain text lines: "name - 12.34s"
# In memory we keep them as a list of (name, time_seconds) tuples,
# which makes sorting by time trivial and avoids re-parsing the
# string every time we want to display or sort the scores.

def parse_score_line(line):
    """Turn a saved 'name - 12.34s' line back into (name, time_seconds).
    Returns None if the line is malformed (so a corrupted file line
    doesn't crash the game)."""
    line = line.strip()
    if not line or " - " not in line:
        return None
    name, time_part = line.rsplit(" - ", 1)   # split on the LAST " - " (names could contain spaces)
    time_part = time_part.strip()
    if time_part.endswith("s"):
        time_part = time_part[:-1]            # drop the trailing "s" from e.g. "12.34s"
    try:
        return (name, float(time_part))
    except ValueError:
        # The number after the dash wasn't actually a valid number.
        return None


def format_score_line(name, time_seconds):
    """The inverse of parse_score_line: turn (name, time) into the
    text line we save to disk / show on screen."""
    return f"{name} - {time_seconds:.2f}s"


def load_scoreboard():
    """Load all saved scores from disk as a list of (name, time_seconds)."""
    if not os.path.exists(SCOREBOARD_FILE):
        return []  # no file yet -> no scores yet
    scores = []
    with open(SCOREBOARD_FILE, "r") as f:
        for line in f.readlines():
            parsed = parse_score_line(line)
            if parsed is not None:
                scores.append(parsed)
    return scores


def save_score(name, time_seconds):
    """Add a new score to the in-memory list and append it to disk."""
    scoreboard.append((name, time_seconds))
    with open(SCOREBOARD_FILE, "a") as f:   # "a" = append, so old scores aren't lost
        f.write(format_score_line(name, time_seconds) + "\n")


def clear_scoreboard():
    """Wipe every saved score, both in memory and on disk."""
    global scoreboard
    scoreboard = []
    if os.path.exists(SCOREBOARD_FILE):
        os.remove(SCOREBOARD_FILE)


def get_fastest_scores(limit=None):
    """Return scores sorted fastest-first (lowest time = best).
    Pass a limit to get just the top N, e.g. get_fastest_scores(3)."""
    fastest_first = sorted(scoreboard, key=lambda entry: entry[1])
    if limit is not None:
        return fastest_first[:limit]
    return fastest_first


# Load whatever scores already exist on disk as soon as the game starts,
# so the menu/leaderboard screens have data to show straight away.
scoreboard = load_scoreboard()


def apply_player_damage():
    """Take one health point away from the player, unless they are
    currently invincible (just been hit). If health reaches zero, the
    player "dies" and is respawned back at their last checkpoint with
    full health.

    This function is shared by every damage source (enemies, fireballs,
    boss hazards) so the damage/death rules only have to be written once.
    """
    # These variables are changed inside the function, so they need to be
    # declared global or the changes wouldn't be seen outside this function.
    global player_health, player_invincible_timer, current_level, platforms, enemies, boss
    global player_x, player_y, y_velocity, level_width

    if player_invincible_timer > 0:
        # Still flashing/invincible from the last hit -> ignore this hit.
        return

    player_health -= 1
    player_invincible_timer = PLAYER_INVINCIBLE_DURATION
    play_sound(hit_sound)

    if player_health <= 0:
        # Player died: send them back to the last checkpoint and reset health.
        current_level = checkpoint_level
        platforms, enemies, fragments, boss = build_level(levels[current_level])
        level_width = get_level_width(levels[current_level])
        player_x, player_y = checkpoint_pos
        y_velocity = 0
        player_health = max_player_health
        player_invincible_timer = 0


# =========================================================
# 8. MAIN LOOP the main loop  
# =========================================================
# Everything from here down runs once per frame (60 times per second),
# for as long as `running` stays True. Each pass through the loop:
#   1. Handles input events (key presses, mouse clicks, quitting)
#   2. Depending on game_state, either draws a menu-style screen and
#      `continue`s straight to the next frame, or runs the full gameplay
#      update (movement, physics, enemies, boss) and draws the game world.
running = True
while running:
    # ---- Event handling (top-level) ----
    # pygame.event.get() returns every input event that happened since the
    # last time we checked (key presses, mouse clicks, closing the window).
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False   # user clicked the window's close button

        # ---- Main menu input ----
        if game_state == "menu":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    # ENTER -> start a brand new game from level 1.
                    speedrun_mode = False
                    timer_start = None
                    timer_time = 0
                    game_state = "playing"
                    current_level = 0
                    collected_fragment_positions.clear()
                    fragments_collected = 0
                    platforms, enemies, fragments, boss = build_level(levels[current_level])
                    level_width = get_level_width(levels[current_level])
                    player_x, player_y = 100, 100
                    y_velocity = 0
                    player_health = max_player_health
                    checkpoint_level = 0
                    checkpoint_pos = (player_x, player_y)
                if event.key == pygame.K_c and checkpoint_level > 0:
                    # C -> continue from the last checkpoint (only shown/usable
                    # once the player has actually reached a checkpoint).
                    speedrun_mode = False
                    timer_start = None
                    timer_time = 0
                    game_state = "playing"
                    current_level = checkpoint_level
                    platforms, enemies, fragments, boss = build_level(levels[current_level])
                    level_width = get_level_width(levels[current_level])
                    player_x, player_y = checkpoint_pos
                    y_velocity = 0
                    player_health = max_player_health
                if event.key == pygame.K_s:
                    # S -> go to the username entry screen to start a speedrun.
                    game_state = "enter_username"
                    username = ""
                if event.key == pygame.K_t:
                    # T -> open the tutorial / how to play screen.
                    game_state = "tutorial"
                if event.key == pygame.K_q:
                    # Q -> quit the game entirely.
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Left mouse click: check if it landed on one of the menu buttons.
                # (menu_buttons is rebuilt every frame while drawing the menu, below.)
                for btn in menu_buttons:
                    if btn["rect"].collidepoint(event.pos):
                        action = btn["action"]
                        # Each button's action does the same thing its keyboard
                        # shortcut would do above.
                        if action == "start":
                            speedrun_mode = False
                            timer_start = None
                            timer_time = 0
                            game_state = "playing"
                            current_level = 0
                            collected_fragment_positions.clear()
                            fragments_collected = 0
                            platforms, enemies, fragments, boss = build_level(levels[current_level])
                            level_width = get_level_width(levels[current_level])
                            player_x, player_y = 100, 100
                            y_velocity = 0
                            player_health = max_player_health
                            checkpoint_level = 0
                            checkpoint_pos = (player_x, player_y)
                        elif action == "continue":
                            speedrun_mode = False
                            timer_start = None
                            timer_time = 0
                            game_state = "playing"
                            current_level = checkpoint_level
                            platforms, enemies, fragments, boss = build_level(levels[current_level])
                            level_width = get_level_width(levels[current_level])
                            player_x, player_y = checkpoint_pos
                            y_velocity = 0
                            player_health = max_player_health
                        elif action == "speedrun":
                            game_state = "enter_username"
                            username = ""
                        elif action == "tutorial":
                            game_state = "tutorial"
                        elif action == "quit":
                            running = False
                        break  # only one button can be clicked at a time

        # ---- Username entry screen ----
        elif game_state == "enter_username":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    # ENTER confirms the name and starts the speedrun timer.
                    if username.strip() == "":
                        username = "Player"   # fallback name if nothing was typed
                    speedrun_mode = True
                    timer_start = pygame.time.get_ticks()   # record the start time (ms since pygame started)
                    timer_time = 0
                    current_level = 0
                    collected_fragment_positions.clear()
                    fragments_collected = 0
                    platforms, enemies, fragments, boss = build_level(levels[current_level])
                    level_width = get_level_width(levels[current_level])
                    player_x, player_y = 100, 100
                    y_velocity = 0
                    player_health = max_player_health
                    checkpoint_level = 0
                    checkpoint_pos = (player_x, player_y)
                    game_state = "playing"
                elif event.key == pygame.K_BACKSPACE:
                    username = username[:-1]   # delete the last typed character
                else:
                    # Only accept printable characters
                    if event.unicode.isprintable():
                        username += event.unicode   # add the typed character to the name

        # ---- Tutorial / how-to-play screen ----
        elif game_state == "tutorial":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                    game_state = "menu"   # either key takes the player back to the menu

        # ---- Pause toggle + mute toggle (while playing) ----
        elif game_state == "playing":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state = "paused"
                elif event.key == pygame.K_m:
                    # Toggle mute: flip the flag and set the music volume to match.
                    muted = not muted
                    pygame.mixer.music.set_volume(0.0 if muted else 1.0)

        # ---- Pause menu ----
        elif game_state == "paused":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                game_state = "playing"   # ESC again unpauses
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = event.pos
                if pause_resume_rect.collidepoint(mouse_pos):
                    game_state = "playing"
                elif pause_restart_rect.collidepoint(mouse_pos):
                    # Restart the game from the beginning
                    current_level = 0
                    collected_fragment_positions.clear()
                    fragments_collected = 0
                    platforms, enemies, fragments, boss = build_level(levels[current_level])
                    level_width = get_level_width(levels[current_level])
                    player_x, player_y = 100, 100
                    y_velocity = 0
                    player_health = max_player_health
                    player_invincible_timer = 0
                    checkpoint_level = 0
                    checkpoint_pos = (player_x, player_y)
                    if speedrun_mode:
                        # Restarting mid-speedrun resets the clock too.
                        timer_start = pygame.time.get_ticks()
                        timer_time = 0
                    game_state = "playing"
                elif pause_menu_rect.collidepoint(mouse_pos):
                    # Return to main menu
                    speedrun_mode = False
                    timer_start = None
                    timer_time = 0
                    game_state = "menu"

        # ---- Leaderboard screen ----
        elif game_state == "scoreboard":
            # NOTE: in practice the scoreboard screen is drawn and handled in
            # its own little loop further down (see "SCREEN: LEADERBOARD"),
            # so this branch mostly exists as a safety net.
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                game_state = "menu"
                speedrun_mode = False
                timer_start = None
                timer_time = 0

        # ---- Victory screen (normal mode boss defeat) ----
        elif game_state == "victory":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                # If the player collected every fragment, ENTER unlocks the
                # secret ending; otherwise it just returns to the menu.
                if fragments_collected >= 5:
                    game_state = "rescue"
                else:
                    game_state = "menu"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if victory_menu_rect.collidepoint(event.pos):
                    if fragments_collected >= 5:
                        game_state = "rescue"
                    else:
                        game_state = "menu"

        # ---- Rescue / fragment ending screen ----
        elif game_state == "rescue":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE:
                    game_state = "menu"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if victory_menu_rect.collidepoint(event.pos):
                    game_state = "menu"

    # =====================================================
    # SCREEN: MENU (Improved Title Screen)
    # =====================================================
    # Each of these "SCREEN" blocks below draws one non-gameplay screen and
    # then immediately `continue`s, skipping the gameplay/physics code that
    # comes later in the loop (that code should only run for game_state == "playing").
    if game_state == "menu":
        screen.blit(ocean_img, (0, 0))  # background image instead of black

        # --- Title ---
        title_text = "Ruatepupuke’s wood carvings"
        title_surf = font.render(title_text, True, (255, 255, 255))   # white text
        title_outline = font.render(title_text, True, (0, 0, 0))       # black "shadow" copy

        # Center title
        tx = SCREEN_WIDTH // 2 - title_surf.get_width() // 2
        ty = 40

        # Outline effect: draw the black copy slightly offset first, then the
        # white text on top, so the title is easier to read against any background.
        screen.blit(title_outline, (tx + 3, ty + 3))
        screen.blit(title_surf, (tx, ty))

        # --- Shortcuts hint ---
        hint = small_font.render("ENTER / C / S / T / Q", True, (230, 230, 230))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 110))

        # --- Buttons ---
        # Rebuild the button list every frame (its contents depend on whether
        # a checkpoint exists yet), then draw each one and remember its Rect
        # so mouse clicks can be matched against it (see event handling above).
        mouse_pos = pygame.mouse.get_pos()
        menu_buttons = []
        btn_w, btn_h = 300, 55
        btn_x = SCREEN_WIDTH // 2 - btn_w // 2
        btn_y = 170
        spacing = 70   # vertical gap between buttons

        # (action_id, label text, base RGB colour)
        button_defs = [("start", "Start Game", (0, 120, 60))]
        if checkpoint_level >0 :
            # Only show "Continue" once the player has actually reached a checkpoint.
            button_defs.append(("continue", f"Continue (Level {checkpoint_level + 1})", (0, 90, 160)))
        button_defs.append(("speedrun", "Speedrun Mode", (150, 110, 0)))
        button_defs.append(("tutorial", "How to Play", (80, 80, 180)))
        button_defs.append(("quit", "Quit", (150, 0, 0)))

        for action, label, base_color in button_defs:
            rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
            hover = rect.collidepoint(mouse_pos)
            # Lighten the button colour slightly when the mouse is over it,
            # capped at 255 so the colour never overflows.
            color = tuple(min(255, c + 40) for c in base_color) if hover else base_color

            pygame.draw.rect(screen, color, rect, border_radius=10)
            pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=10)   # white outline

            label_surf = small_font.render(label, True, (255, 255, 255))
            screen.blit(label_surf, label_surf.get_rect(center=rect.center))   # center text in button

            menu_buttons.append({"rect": rect, "action": action})
            btn_y += spacing   # move down for the next button

        # --- Fastest Speedrun Times ---
        y = btn_y + 20
        header = small_font.render("Fastest Speedrun Times:", True, (255, 255, 255))
        screen.blit(header, (SCREEN_WIDTH // 2 - header.get_width() // 2, y))
        y += 30

        # Show the top 3 fastest saved speedrun times on the menu itself.
        for rank, (name, time_seconds) in enumerate(get_fastest_scores(3), start=1):
            txt = small_font.render(f"{rank}. {format_score_line(name, time_seconds)}", True, (0, 255, 0))
            screen.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, y))
            y += 26

        pygame.display.flip()   # show everything drawn this frame
        clock.tick(60)          # wait so the loop runs at ~60 frames per second
        continue                # skip the gameplay code below - this frame is done

    # =====================================================
    # SCREEN: VICTORY (normal mode boss defeat)
    # =====================================================
    if game_state == "victory":
        screen.fill((5, 20, 15))   # dark green/black background

        win_title = font.render("Boss Slain!", True, (255, 215, 0))
        win_sub = font.render("You Win!", True, (255, 255, 255))
        screen.blit(win_title, (SCREEN_WIDTH // 2 - win_title.get_width() // 2, SCREEN_HEIGHT // 2 - 160))
        screen.blit(win_sub, (SCREEN_WIDTH // 2 - win_sub.get_width() // 2, SCREEN_HEIGHT // 2 - 90))

        if fragments_collected >= 5:
            # Player found every fragment -> tease the secret ending.
            congrats = small_font.render("You collected all 5 fragments!", True, (255, 255, 255))
            screen.blit(congrats, (SCREEN_WIDTH // 2 - congrats.get_width() // 2, SCREEN_HEIGHT // 2 - 20))
            button_label = "Secret Ending"
            hint_text = "Press ENTER or click Continue to see what happens next"
        else:
            # Otherwise just acknowledge finishing the normal game.
            congrats = small_font.render("You made it through all the levels and defeated the Taniwha.", True, (200, 200, 200))
            screen.blit(congrats, (SCREEN_WIDTH // 2 - congrats.get_width() // 2, SCREEN_HEIGHT // 2 - 20))
            button_label = "Main Menu"
            hint_text = "Press ENTER or click Main Menu to continue"

        # Draw the single button on this screen (its label/behaviour changes
        # depending on whether the secret ending was unlocked, above).
        mouse_pos = pygame.mouse.get_pos()
        color = (0, 130, 210) if victory_menu_rect.collidepoint(mouse_pos) else (0, 90, 160)
        pygame.draw.rect(screen, color, victory_menu_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), victory_menu_rect, 2, border_radius=8)
        label_surf = small_font.render(button_label, True, (255, 255, 255))
        label_rect = label_surf.get_rect(center=victory_menu_rect.center)
        screen.blit(label_surf, label_rect)

        hint = small_font.render(hint_text, True, (180, 180, 180))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 60))

        pygame.display.flip()
        clock.tick(60)
        continue

    # =====================================================
    # SCREEN: SECRET RESCUE ENDING
    # =====================================================
    if game_state == "rescue":
        screen.blit(ocean_img, (0, 0))

        # Dark overlay so the ending text is easy to read.
        # A separate transparent Surface is drawn on top of the background
        # so the background image is still visible but darkened.
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 145))   # black, with alpha (transparency) of 145/255
        screen.blit(overlay, (0, 0))

        title = font.render("CONGRATULATIONS!", True, (255, 215, 0))
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 45))

        rescue_title = font.render("You rescued my son!", True, (255, 255, 255))
        screen.blit(rescue_title, (SCREEN_WIDTH // 2 - rescue_title.get_width() // 2, 125))

        # The supplied Māori tradition text is displayed as a short lore section.
        lore_header = small_font.render("A piece of the story:", True, (255, 220, 120))
        screen.blit(lore_header, (SCREEN_WIDTH // 2 - lore_header.get_width() // 2, 210))

        lore_lines = [
            "Te Manuhauturuki is a central figure in Māori tradition whose",
            "capture by the sea god Tangaroa led to the discovery of",
            "whakairo (the art of wood carving)"
        ]

        # Draw each line of the lore text, one below the other.
        lore_y = 255
        for line in lore_lines:
            text = small_font.render(line, True, (245, 245, 245))
            screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, lore_y))
            lore_y += 38

        final_text = small_font.render("The five fragments have unlocked the secret ending.", True, (180, 255, 180))
        screen.blit(final_text, (SCREEN_WIDTH // 2 - final_text.get_width() // 2, 405))

        mouse_pos = pygame.mouse.get_pos()
        color = (0, 130, 210) if victory_menu_rect.collidepoint(mouse_pos) else (0, 90, 160)
        pygame.draw.rect(screen, color, victory_menu_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), victory_menu_rect, 2, border_radius=8)
        label_surf = small_font.render("Main Menu", True, (255, 255, 255))
        screen.blit(label_surf, label_surf.get_rect(center=victory_menu_rect.center))

        hint = small_font.render("Press ENTER, ESC, or click Main Menu to continue", True, (190, 190, 190))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 60))

        pygame.display.flip()
        clock.tick(60)
        continue

    # =====================================================
    # SCREEN: TUTORIAL / HOW TO PLAY
    # =====================================================
    if game_state == "tutorial":
        screen.fill((10, 10, 30))   # dark navy background

        title = font.render("How to Play", True, (255, 255, 255))
        screen.blit(title, (SCREEN_WIDTH // 2 - 150, 30))

        # --- Controls section ---
        screen.blit(character_icon, (30, 108))
        controls_header = font.render("Controls", True, (0, 200, 255))
        screen.blit(controls_header, (80, 110))

        # Plain list of control explanations, drawn one line at a time below.
        controls_list = [
            "LEFT / A       -  Move left",
            "RIGHT / D      -  Move right",
            "UP / W / SPACE -  Jump (only while on the ground)",
            "F              -  Punch (attack enemies in front of you, short cooldown between punches)",
            "ESC            -  Pause / Resume game",
            "M              -  Mute / unmute sound (while playing)",
            "For Mr lier - Press 6 for last level",
        ]

        y = 160
        for line in controls_list:
            txt = small_font.render(line, True, (230, 230, 230))
            screen.blit(txt, (100, y))
            y += 30

        # --- Enemies section (regular enemies only, not the boss) ---
        screen.blit(enemy_icon, (30, y + 28))
        enemies_header = font.render("Enemies", True, (255, 120, 0))
        screen.blit(enemies_header, (80, y + 30))

        enemies_list = [
            "Enemies patrol back and forth and turn around at walls or platform edges.",
            "If you get close and are on roughly the same level, an enemy will lunge toward you.",
            "Touching an enemy deals  damage to you (you're briefly invincible right after).",
            "Punch (F) an enemy to damage it - each hit removes its health.",
            "An enemy is defeated once its health bar reaches zero.",
            "Collect 5 Fragements for Secret.",
        ]

        y2 = y + 80
        for line in enemies_list:
            txt = small_font.render(line, True, (230, 230, 230))
            screen.blit(txt, (100, y2))
            y2 += 34

        back_text = small_font.render("Press ENTER or ESC to return to menu", True, (200, 200, 200))
        screen.blit(back_text, (SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT - 60))

        pygame.display.flip()
        clock.tick(60)
        continue

    # =====================================================
    # SCREEN: ENTER USERNAME
    # =====================================================
    if game_state == "enter_username":
        screen.fill((0, 0, 0))
        prompt = font.render("Enter Username:", True, (255, 255, 255))
        name_display = font.render(username, True, (0, 255, 0))   # shows what's typed so far
        hint = small_font.render("Press ENTER to start speedrun", True, (180, 180, 180))
        screen.blit(prompt, (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 - 50))
        screen.blit(name_display, (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 + 20))
        screen.blit(hint, (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 + 90))
        pygame.display.flip()
        clock.tick(60)
        continue

    # =====================================================
    # SCREEN: PAUSE
    # =====================================================
    if game_state == "paused":
        # Draw a semi-transparent black rectangle over the whole screen so
        # the game underneath is still faintly visible but clearly paused.
        pause_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        pause_overlay.set_alpha(180)   # 0 = fully see-through, 255 = fully solid
        pause_overlay.fill((0, 0, 0))
        screen.blit(pause_overlay, (0, 0))

        pause_text = font.render("PAUSED", True, (255, 255, 255))
        screen.blit(pause_text, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 170))

        mouse_pos = pygame.mouse.get_pos()

        def draw_pause_button(rect, label, base_color, hover_color):
            """Small helper (only used on the pause screen) that draws one
            button, highlighting it if the mouse is currently over it."""
            color = hover_color if rect.collidepoint(mouse_pos) else base_color
            pygame.draw.rect(screen, color, rect, border_radius=8)
            pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=8)
            label_surf = small_font.render(label, True, (255, 255, 255))
            label_rect = label_surf.get_rect(center=rect.center)
            screen.blit(label_surf, label_rect)

        draw_pause_button(pause_resume_rect, "Resume", (0, 120, 60), (0, 170, 90))
        draw_pause_button(pause_restart_rect, "Restart", (150, 110, 0), (200, 150, 0))
        draw_pause_button(pause_menu_rect, "Main Menu", (0, 90, 160), (0, 130, 210))

        pygame.display.flip()
        clock.tick(60)
        continue

    # =====================================================
    # GAMEPLAY (movement, combat, physics)
    # =====================================================
    # Everything below this point only runs while game_state == "playing"
    # (every other state already hit a `continue` above and skipped this).

    # keys is a list-like object where keys[SOME_KEY_CONSTANT] is True if
    # that key is currently held down (not just pressed once).
    keys = pygame.key.get_pressed()

    player_anim_timer += 1
    if player_invincible_timer > 0:
        player_invincible_timer -= 1   # count down the "just got hit" timer

    # DEV TELEPORT (disabled during speedrun mode to keep times legitimate)
    # Pressing 6 jumps straight to the final boss level - handy for testing.
    if keys[pygame.K_6] and not speedrun_mode:
        current_level = 6
        platforms, enemies, fragments, boss = build_level(levels[current_level])
        level_width = get_level_width(levels[current_level])
        player_x, player_y = 100, 100
        y_velocity = 0
        checkpoint_level = current_level
        checkpoint_pos = (player_x, player_y)

    # --- Movement input ---
    x_velocity = 0
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        x_velocity = -player_speed
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        x_velocity = player_speed
    # (If both left and right are held, right wins because it's checked last.)

    # --- Punch (with a short cooldown so it can't be spammed) ---
    if punch_cooldown_timer > 0:
        punch_cooldown_timer -= 1

    if keys[pygame.K_f] and not punching and punch_cooldown_timer <= 0:
        punching = True
        punch_timer = PUNCH_DURATION
        play_sound(punch_sound)

    # --- Jump ---
    # Only allowed while on_ground is True, so the player can't jump mid-air.
    if (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]) and on_ground:
        y_velocity = jump_strength
        on_ground = False

    # --- Gravity ---
    # Constantly pulls the player downward; jumping just gives a big
    # negative (upward) velocity that gravity then gradually cancels out.
    y_velocity += gravity

    # --- Movement & collisions ---
    player_facing_right = x_velocity >= 0
    player_rect = pygame.Rect(player_x, player_y, player_width, player_height)

    # Horizontal movement is resolved first... iD
    # Move sideways, then push the player back out of any platform it
    # ended up overlapping (this stops the player walking through walls).
    player_rect.x += x_velocity
    for platform in platforms:
        if player_rect.colliderect(platform):
            if x_velocity > 0:
                player_rect.right = platform.left   # hit a wall while moving right
            elif x_velocity < 0:
                player_rect.left = platform.right   # hit a wall while moving left

    # ...then vertical movement, so the player can't clip through corners.
    # Doing horizontal and vertical movement as two separate steps (rather
    # than diagonally in one go) is what stops the player getting stuck
    # inside the corner of a platform.
    player_rect.y += y_velocity
    on_ground = False
    for platform in platforms:
        if player_rect.colliderect(platform):
            if y_velocity > 0:
                # Falling onto the top of a platform -> stop and stand on it.
                player_rect.bottom = platform.top
                y_velocity = 0
                on_ground = True
            elif y_velocity < 0:
                # Jumping up into the underside of a platform -> stop rising.
                player_rect.top = platform.bottom
                y_velocity = 0

    # Copy the resolved rectangle position back into the plain x/y variables
    # used elsewhere in the game (e.g. by the boss's attack aiming code).
    player_x, player_y = player_rect.x, player_rect.y

    # --- Fragment collection ---
    # Check every fragment still on screen; if the player is touching it,
    # remember it as collected (so it won't reappear) and remove it from
    # the current level's fragment list.
    for fragment in fragments[:]:   # [:] makes a copy so we can safely remove while looping
        if player_rect.colliderect(fragment["rect"]):
            fragment_key = (current_level, fragment["row"], fragment["col"])
            collected_fragment_positions.add(fragment_key)
            fragments.remove(fragment)
            fragments_collected += 1

    # --- Punch hitbox ---
    # A small rectangle in front of the player, only while punching.
    punch_rect = None
    facing_right = x_velocity >= 0
    if punching:
        if facing_right:
            punch_rect = pygame.Rect(player_rect.right, player_rect.y + 10, 30, 40)
        else:
            punch_rect = pygame.Rect(player_rect.left - 30, player_rect.y + 10, 30, 40)

        punch_timer -= 1
        if punch_timer <= 0:
            # Punch animation/hitbox has finished -> start the cooldown
            # before the player is allowed to punch again.
            punching = False
            punch_cooldown_timer = PUNCH_COOLDOWN_DURATION

    # --- Camera ---
    # Follows the player horizontally, clamped so it never scrolls past
    # the edges of the level.
    camera_x = player_rect.centerx - SCREEN_WIDTH // 2
    camera_x = max(0, min(camera_x, max(0, level_width - SCREEN_WIDTH)))
    # (Everything is drawn later at "real position - camera_x" so the world
    #  appears to scroll as the player moves.)

    # --- Enemies ---
    LUNGE_RANGE_X = 220              # how close (horizontally) before an enemy notices the player
    LUNGE_RANGE_Y = TILE_SIZE        # must be roughly at the same height to give chase
    LUNGE_SPEED = 6                  # how fast an enemy moves once it starts lunging

    for enemy in enemies[:]:   # copy the list so enemies can be removed mid-loop
        enemy_rect = enemy["rect"]

        dx = player_rect.centerx - enemy_rect.centerx
        dy = player_rect.centery - enemy_rect.centery
        same_level = abs(dy) < LUNGE_RANGE_Y
        lunging = same_level and abs(dx) < LUNGE_RANGE_X

        # If the player is close and at roughly the same height, the enemy
        # charges toward them; otherwise it just patrols back and forth.
        move = (LUNGE_SPEED if dx > 0 else -LUNGE_SPEED) if lunging else enemy["speed"]
        enemy["facing"] = move   # remembered so the correct left/right sprite can be drawn later

        enemy_rect.x += move
        for platform in platforms:
            if enemy_rect.colliderect(platform):
                enemy_rect.x -= move   # undo the move, it hit something solid
                if not lunging:
                    enemy["speed"] *= -1  # hit a wall while patrolling -> turn around

        # Also turn around / stop at the edges of the level itself.
        if enemy_rect.left < 0 or enemy_rect.right > level_width:
            enemy_rect.x -= move
            if not lunging:
                enemy["speed"] *= -1

        # Did the player's punch land on this enemy?
        if punching and punch_rect and punch_rect.colliderect(enemy_rect):
            enemy["health"] -= 1
            if enemy["health"] <= 0:
                enemies.remove(enemy)
                play_sound(enemy_death_sound)
            continue   # an enemy that was just hit doesn't also damage the player this frame

        # Did this enemy touch the player?
        if player_rect.colliderect(enemy_rect):
            apply_player_damage()

    # --- Boss + fireballs + hazards (final level only) ---
    # `boss` is None on every level except the final one, so this whole
    # block is skipped entirely until the player reaches level 7.
    if boss:
        boss_rect = boss["rect"]

        # At half health the boss enters phase 2: attacks come noticeably
        # more often (shorter patrol windows and a snappier telegraph).
        if boss["phase"] == 1 and boss["health"] <= boss["max_health"] / 2:
            boss["phase"] = 2

        if boss["phase"] == 2:
            BOSS_ATTACK_INTERVAL = 70      # frames of patrol between attacks (~1.2s)
            BOSS_TELEGRAPH_DURATION = 30   # warning flash before an attack fires
        else:
            BOSS_ATTACK_INTERVAL = 150     # frames of patrol between attacks (~2.5s)
            BOSS_TELEGRAPH_DURATION = 45   # warning flash before an attack fires
        BOSS_PROJECTILE_SPEED = 7
        BOSS_FLOAT_AMPLITUDE = 34      # how far it bobs up/down while floating

        # The boss always floats and bobs, regardless of state.
        # math.sin() produces a smooth wave between -1 and 1, which is
        # scaled by BOSS_FLOAT_AMPLITUDE to create the up/down bobbing motion.
        boss["float_timer"] += 1
        boss_rect.y = boss["float_base_y"] + int(math.sin(boss["float_timer"] * 0.05) * BOSS_FLOAT_AMPLITUDE)

        if boss["state"] == "telegraph":
            # Boss holds still and flashes red before unleashing its next attack.
            boss["telegraph_timer"] -= 1
            if boss["telegraph_timer"] <= 0:
                # Telegraph warning is over -> actually fire the next attack.
                boss["state"] = "patrol"
                boss["attack_timer"] = 0

                attack_type = boss["attack_cycle"][boss["attack_index"]]
                boss["attack_index"] = (boss["attack_index"] + 1) % len(boss["attack_cycle"])

                if attack_type == "geyser":
                    # Two narrow water spouts erupt right next to the player.
                    GEYSER_Y = 370
                    GEYSER_HEIGHT = 300
                    boss_hazards.append({"rect": pygame.Rect(player_x - 20, GEYSER_Y, 20, GEYSER_HEIGHT), "warning": 40, "active": 30, "kind": "geyser"})
                    boss_hazards.append({"rect": pygame.Rect(player_x + 20, GEYSER_Y, 20, GEYSER_HEIGHT), "warning": 40, "active": 30, "kind": "geyser"})

                elif attack_type == "meteor":
                    # Fiery meteors fall from the sky near the player,
                    # forcing them to find the gaps between impact zones.
                    METEOR_WIDTH = 40
                    METEOR_WARNING = 50
                    for offset in (-150, -50, 50, 150):
                        mx = player_x + offset
                        boss_hazards.append({
                            "rect": pygame.Rect(mx, 550, METEOR_WIDTH, 150),
                            "warning": METEOR_WARNING,
                            "warning_total": METEOR_WARNING,   # kept so drawing can work out % progress
                            "active": 20,
                            "kind": "meteor",
                        })

                else:  # "fireball"
                    # Work out the direction (as a unit vector) from the boss
                    # to the player, then fire three fireballs: one straight
                    # at the player and two slightly angled either side, so
                    # dodging isn't as simple as stepping to one side.
                    dx = player_rect.centerx - boss_rect.centerx
                    dy = player_rect.centery - boss_rect.centery
                    distance = max(1.0, math.hypot(dx, dy))   # avoid dividing by zero
                    base_vx = dx / distance * BOSS_PROJECTILE_SPEED
                    base_vy = dy / distance * BOSS_PROJECTILE_SPEED

                    # Fire a small spread of three fireballs toward the player.
                    for angle_offset in (-0.2, 0.0, 0.2):
                        # Standard 2D rotation formula, used to angle the
                        # straight-line velocity slightly left/right.
                        vx = base_vx * math.cos(angle_offset) - base_vy * math.sin(angle_offset)
                        vy = base_vx * math.sin(angle_offset) + base_vy * math.cos(angle_offset)
                        boss_projectiles.append({
                            "x": float(boss_rect.centerx),
                            "y": float(boss_rect.centery),
                            "vx": vx,
                            "vy": vy,
                        })

                play_sound(punch_sound)

        else:  # "patrol" - drifts side to side while floating
            boss_rect.x += boss["speed"]
            if boss_rect.left < 0 or boss_rect.right > level_width:
                boss["speed"] *= -1   # bounce off the edges of the arena

            boss["attack_timer"] += 1
            if boss["attack_timer"] >= BOSS_ATTACK_INTERVAL:
                # Enough time has passed patrolling -> start warning the
                # player that an attack is about to happen.
                boss["attack_timer"] = 0
                boss["state"] = "telegraph"
                boss["telegraph_timer"] = BOSS_TELEGRAPH_DURATION

        # Move fireballs and check for hits
        for proj in boss_projectiles[:]:
            proj["x"] += proj["vx"]
            proj["y"] += proj["vy"]
            proj_rect = pygame.Rect(int(proj["x"]) - 8, int(proj["y"]) - 8, 16, 16)

            if player_rect.colliderect(proj_rect):
                apply_player_damage()
                boss_projectiles.remove(proj)
                continue

            # Remove fireballs once they've flown well off-screen, so the
            # list of projectiles doesn't grow forever.
            if proj["x"] < -50 or proj["x"] > level_width + 50 or proj["y"] < -50 or proj["y"] > SCREEN_HEIGHT + 50:
                boss_projectiles.remove(proj)

        # Update geyser / meteor hazards (warning period, then a damaging window)
        for hazard in boss_hazards[:]:
            if hazard["warning"] > 0:
                # Still in the "about to happen" warning phase -> not
                # dangerous yet, just counting down.
                hazard["warning"] -= 1
                continue

            hazard["active"] -= 1
            if hazard["active"] <= 0:
                boss_hazards.remove(hazard)
                continue

            # Hazard is currently "live" -> hurts the player on contact.
            if player_rect.colliderect(hazard["rect"]):
                apply_player_damage()

        # Did the player's punch land on the boss? The hitbox is now the
        # boss's full sprite rather than a box smaller than what's drawn.
        if punching and punch_rect and punch_rect.colliderect(boss_rect):
            boss["health"] -= 1
            if boss["health"] <= 0:
                play_sound(boss_defeat_sound)
                if speedrun_mode and timer_start is not None:
                    # Speedrun finish: record the time and show the leaderboard.
                    final_time = (pygame.time.get_ticks() - timer_start) / 1000.0
                    save_score(username if username.strip() != "" else "Player", final_time)
                    game_state = "scoreboard"
                    speedrun_mode = False
                    timer_start = None
                    timer_time = final_time
                    boss = None
                else:
                    # Normal mode: just show a victory screen.
                    boss = None
                    game_state = "victory"

    # --- Level switch (reached the right edge of the level) ---
    if player_rect.right >= level_width:
        if current_level < len(levels) - 1:
            current_level += 1
            platforms, enemies, fragments, boss = build_level(levels[current_level])
            level_width = get_level_width(levels[current_level])
            player_x, player_y = 15, 10   # spawn near the top-left of the new level
            y_velocity = 0

            if current_level % 5 == 0:
                # Every 5th level becomes a new checkpoint.
                checkpoint_level = current_level
                checkpoint_pos = (player_x, player_y)

    # --- Fell off the bottom of the screen ---
    #-- When the player falls off the screen health is set to 0 and player invicible timer also set to 0--#
    #so it spawns to the last checkpoint and for tis player x and y cords--#
    # (In practice this resets health to full rather than to 0 - the player
    #  is simply sent back to their last checkpoint, same as dying normally.)
    if player_rect.top > SCREEN_HEIGHT:
        current_level = checkpoint_level
        platforms, enemies, fragments, boss = build_level(levels[current_level])
        level_width = get_level_width(levels[current_level])
        player_x, player_y = checkpoint_pos
        y_velocity = 0
        player_health = max_player_health
        player_invincible_timer = 0


    # =====================================================
    # DRAW (gameplay screen)
    # =====================================================
    # Everything drawn here uses "world position - camera_x" for its X
    # coordinate, which is what makes the level appear to scroll as the
    # camera follows the player.
    bg = pygame.transform.scale(ocean_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(bg, (0, 0))

    # Draw every platform tile, scaled to match its Rect's size.
    for platform in platforms:
        tile = pygame.transform.scale(grass_img, (platform.width, platform.height))
        screen.blit(tile, (platform.x - camera_x, platform.y))

    # Draw collectible fragments
    fragment_draw_img = pygame.transform.scale(
        Fragments_img, (TILE_SIZE, TILE_SIZE)
    )
    for fragment in fragments:
        screen.blit(
            fragment_draw_img,
            (fragment["rect"].centerx - TILE_SIZE // 2 - camera_x,
             fragment["rect"].centery - TILE_SIZE // 2)
        )

    # Draw each enemy, picking the sprite that faces the direction it's
    # currently moving, plus a red/green health bar above its head.
    for enemy in enemies:
        facing = enemy.get("facing", enemy["speed"])
        if facing > 0:
            enemy_img = pygame.transform.scale(enemyLeft_img, (TILE_SIZE, TILE_SIZE))
        else:
            enemy_img = pygame.transform.scale(enemyRight_img, (TILE_SIZE, TILE_SIZE))
        draw_x = enemy["rect"].x - camera_x
        screen.blit(enemy_img, (draw_x, enemy["rect"].y))
        # Enemy health bar: red background bar, green foreground bar scaled
        # to the fraction of health remaining (enemies start with 3 health).
        pygame.draw.rect(screen, (255, 0, 0), (draw_x, enemy["rect"].y - 10, TILE_SIZE, 5))
        pygame.draw.rect(screen, (0, 255, 0), (draw_x, enemy["rect"].y - 10, TILE_SIZE * max(0, enemy["health"] / 3), 5))

    if boss:
        boss_facing_right = boss["speed"] > 0
        boss_draw_img = boss_right_img if boss_facing_right else boss_left_img
        tint_alpha = 55 if boss["phase"] == 2 else 0  # faint permanent red tint once enraged
        if boss["state"] == "telegraph" and (boss["telegraph_timer"] // 5) % 2 == 0:
            # Flash brighter red to warn the player it's about to fire.
            tint_alpha = 130
        if tint_alpha:
            # Overlay a semi-transparent red rectangle on top of a copy of
            # the boss sprite to create the red "tint"/flash effect.
            boss_draw_img = boss_draw_img.copy()
            flash = pygame.Surface(boss_draw_img.get_size(), pygame.SRCALPHA)
            flash.fill((255, 0, 0, tint_alpha))
            boss_draw_img.blit(flash, (0, 0))
        screen.blit(boss_draw_img, (boss["rect"].x - camera_x, boss["rect"].y))

        # Draw each fireball as a small orange/yellow circle.
        for proj in boss_projectiles:
            draw_px = int(proj["x"]) - camera_x
            draw_py = int(proj["y"])
            pygame.draw.circle(screen, (255, 100, 0), (draw_px, draw_py), 9)
            pygame.draw.circle(screen, (255, 220, 0), (draw_px, draw_py), 4)

        # Draw each hazard differently depending on its kind and whether
        # it's still in its warning countdown or actually active/dangerous.
        for hazard in boss_hazards:
            draw_hx = hazard["rect"].x - camera_x
            if hazard["kind"] == "geyser":
                if hazard["warning"] > 0:
                    # Still warming up: show a small warning dot on the ground.
                    pygame.draw.circle(screen, (255, 0, 0), (draw_hx + hazard["rect"].width // 2, 650), 12)
                else:
                    # Active: show the actual water spout.
                    surf = pygame.Surface((hazard["rect"].width, hazard["rect"].height), pygame.SRCALPHA)
                    surf.fill((0, 150, 255, 200))
                    screen.blit(surf, (draw_hx, 370))
            else:  # "meteor"
                center_x = draw_hx + hazard["rect"].width // 2
                if hazard["warning"] > 0:
                    # Falls from off-screen at the top down to its impact point.
                    # progress goes from 0 (just started warning) to 1 (about to land).
                    progress = 1 - (hazard["warning"] / hazard["warning_total"])
                    meteor_y = -40 + progress * 630
                    pygame.draw.circle(screen, (255, 90, 0), (center_x, int(meteor_y)), 10)
                    pygame.draw.circle(screen, (255, 200, 0), (center_x, int(meteor_y)), 5)
                    # Ground shadow grows as the meteor gets closer.
                    shadow_w = int(hazard["rect"].width * (0.4 + 0.6 * progress))
                    pygame.draw.ellipse(screen, (150, 30, 0), (center_x - shadow_w // 2, 640, shadow_w, 18))
                else:
                    # Active: show the fiery impact zone.
                    surf = pygame.Surface((hazard["rect"].width, hazard["rect"].height), pygame.SRCALPHA)
                    surf.fill((255, 90, 0, 200))
                    screen.blit(surf, (draw_hx, 550))

        # Boss health bar (drawn at the top-centre of the screen, not
        # following the boss around, since it should always be visible).
        boss_health_ratio = max(0, boss["health"] / boss["max_health"])
        pygame.draw.rect(screen, (255, 0, 0), (SCREEN_WIDTH // 2 - 200, 20, 400, 25))
        pygame.draw.rect(screen, (0, 255, 0), (SCREEN_WIDTH // 2 - 200, 20, 400 * boss_health_ratio, 25))
        if boss["phase"] == 2:
            enraged_text = small_font.render("ENRAGED", True, (255, 60, 60))
            screen.blit(enraged_text, (SCREEN_WIDTH // 2 - enraged_text.get_width() // 2, 48))

    # Player sprite (walking animation while moving on the ground, idle
    # frame otherwise, plus invincibility flicker)
    is_walking = x_velocity != 0 and on_ground
    if is_walking:
        # Cycle through the 4 walk frames, changing frame every
        # ANIMATION_FRAME_DURATION game frames.
        frame_index = (player_anim_timer // ANIMATION_FRAME_DURATION) % len(walk_frames_right)
        character_img = walk_frames_right[frame_index] if player_facing_right else walk_frames_left[frame_index]
    else:
        character_img = idle_right_img if player_facing_right else idle_left_img

    draw_player = True
    if player_invincible_timer > 0 and (player_invincible_timer // 4) % 2 == 0:
        draw_player = False  # flicker every few frames while invincible

    if draw_player:
        screen.blit(character_img, (player_rect.x - camera_x, player_rect.y))

    # Draw the punch effect graphic over the punch hitbox, if currently punching.
    if punching and punch_rect:
        if facing_right:
            block_img = blockright_img
        else:
            block_img = blockleft_img
        screen.blit(block_img, (punch_rect.x - camera_x, punch_rect.y))

    # Player health bar (fixed in the top-left corner of the screen).
    pygame.draw.rect(screen, (255, 0, 0), (20, 20, 200, 20))
    pygame.draw.rect(screen, (0, 255, 0), (20, 20, 200 * max(0, player_health / max_player_health), 20))

    # Fragment counter
    fragment_text = small_font.render(
        f"Fragments: {fragments_collected} / {TOTAL_FRAGMENTS}",
        True,
        (255, 255, 255)
    )
    screen.blit(fragment_text, (20, 50))

    # Level indicator
    level_text = small_font.render(f"Level {current_level + 1} / {len(levels)}", True, (255, 255, 255))
    screen.blit(level_text, (SCREEN_WIDTH // 2 - level_text.get_width() // 2, 20))

    # Mute indicator
    if muted:
        mute_text = small_font.render("Muted (M)", True, (255, 120, 120))
        screen.blit(mute_text, (20, SCREEN_HEIGHT - 40))

    # Speedrun timer display
    if speedrun_mode and timer_start is not None:
        timer_time = (pygame.time.get_ticks() - timer_start) / 1000.0
        timer_text = small_font.render(f"Time: {timer_time:.2f}s", True, (255, 255, 0))
        screen.blit(timer_text, (SCREEN_WIDTH - 260, 20))

    pygame.display.flip()   # show this frame
    clock.tick(60)          # limit to 60 frames per second

    # =====================================================
    # SCREEN: LEADERBOARD
    # =====================================================
    # (Handled here, right after a normal frame, so it doesn't need its
    # own branch up in the main event-handling section.)
    if game_state == "scoreboard":
        redraw_scoreboard = True
        while redraw_scoreboard:
            redraw_scoreboard = False

            screen.fill((0, 0, 0))
            title = font.render("Speedrun Leaderboard", True, (255, 255, 255))
            screen.blit(title, (SCREEN_WIDTH // 2 - 220, 50))

            # Show the top 10 fastest times, ranked #1 (fastest) downward.
            y_offset = 150
            for rank, (name, time_seconds) in enumerate(get_fastest_scores(10), start=1):
                # Highlight the podium (top 3) in gold/silver/bronze-ish colors.
                if rank == 1:
                    color = (255, 215, 0)
                elif rank == 2:
                    color = (200, 200, 200)
                elif rank == 3:
                    color = (205, 140, 80)
                else:
                    color = (0, 255, 0)
                    #--- it changes the color

                entry_text = f"{rank}. {format_score_line(name, time_seconds)}"
                score_text = small_font.render(entry_text, True, color)
                screen.blit(score_text, (SCREEN_WIDTH // 2 - 200, y_offset))
                y_offset += 30

            if not scoreboard:
                empty_text = small_font.render("No speedrun times yet - be the first!", True, (150, 150, 150))
                screen.blit(empty_text, (SCREEN_WIDTH // 2 - empty_text.get_width() // 2, y_offset))

            # Draw the "Clear Scores" button.
            mouse_pos = pygame.mouse.get_pos()
            clear_hover = scoreboard_clear_rect.collidepoint(mouse_pos)
            clear_color = (170, 0, 0) if clear_hover else (110, 0, 0)
            pygame.draw.rect(screen, clear_color, scoreboard_clear_rect, border_radius=8)
            pygame.draw.rect(screen, (255, 255, 255), scoreboard_clear_rect, 2, border_radius=8)
            clear_label = small_font.render("Clear Scores", True, (255, 255, 255))
            screen.blit(clear_label, clear_label.get_rect(center=scoreboard_clear_rect.center))

            back_text = small_font.render("Press ENTER to return to menu", True, (200, 200, 200))
            screen.blit(back_text, (SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT - 100))

            pygame.display.flip()

            # Wait here until the user presses ENTER, clicks Clear, or quits.
        
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
                    if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        if scoreboard_clear_rect.collidepoint(ev.pos):
                            clear_scoreboard()
                            waiting = False
                            redraw_scoreboard = True   # go round and redraw the now-empty board
                clock.tick(30)


# The window was closed or Q/QUIT was triggered - shut pygame down

pygame.quit()
sys.exit()