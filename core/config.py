
#-- Импорт
import os
import sys

import pygame

import screen_setting as SS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False):
    ROOT_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    ROOT_DIR = os.path.dirname(BASE_DIR)


def res(*parts):
    return os.path.join(BASE_DIR, *parts)


def root(*parts):
    return os.path.join(ROOT_DIR, *parts)


TITLE = "Geometry Rhythm"
VERSION = "0.2"
WIDTH, HEIGHT = SS.apply_name(SS.read_saved(root("data", "settings.json")))
UI_FONT_SCALE = 1.2
FPS = 60

BG_DARK = (10, 10, 20)
GRID_COL = (25, 25, 50)
WHITE = (255, 255, 255)
GREY = (160, 160, 180)
DIM = (70, 70, 110)
GREEN = (50, 220, 100)
PURPLE = (160, 80, 255)
PURPLE_LIGHT = (200, 130, 255)
RED = (220, 50, 60)
RED_LIGHT = (255, 100, 110)
GOLD = (255, 210, 60)
CYAN = (80, 220, 255)

LANE_KEYS = (pygame.K_d, pygame.K_f, pygame.K_j, pygame.K_k)
LANE_LABELS = ("D", "F", "J", "K")
LANE_COLORS = (CYAN, GREEN, PURPLE_LIGHT, GOLD)
LANE_SHAPES = ("square", "triangle", "hexagon", "rhombus")

#-- Размеры поля: значения ниже расчётные (1280 × 720), в пиксели переводит screen_setting
_D_LANE_W, _D_LANE_GAP, _D_HIT_Y, _D_TRAVEL_EXTRA = 104, 16, 600, 40
SCROLL_MS = 900


def refresh_derived():
    """Пересчитывает пиксельные размеры поля под текущий режим (вызывает screen_setting.set_mode)."""
    global LANE_W, LANE_GAP, FIELD_W, FIELD_X, HIT_Y, TRAVEL_PX
    LANE_W = SS.U(_D_LANE_W)
    LANE_GAP = SS.U(_D_LANE_GAP)
    FIELD_W = 4 * LANE_W + 3 * LANE_GAP
    FIELD_X = (WIDTH - FIELD_W) // 2
    HIT_Y = SS.U(_D_HIT_Y)
    TRAVEL_PX = HIT_Y + SS.U(_D_TRAVEL_EXTRA)


refresh_derived()

WIN_PERFECT = 45
WIN_GREAT = 90
WIN_GOOD = 135

MAX_HP = 5
LATENCY_MS = 0
