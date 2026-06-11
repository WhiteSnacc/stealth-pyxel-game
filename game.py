import pyxel
from model.player import Player
from model.enemy  import Enemy
from model.world  import World, WorldItem, world_item_draw, MapTrigger, TILE_SIZE

# ── Layar ────────────────────────────────────────────────────────────── #
SCREEN_W = World.WIDTH  * TILE_SIZE   # 128 px
SCREEN_H = World.HEIGHT * TILE_SIZE   # 128 px

# ── State game ───────────────────────────────────────────────────────── #
STATE_TUTORIAL  = -1  # layar tutorial sebelum main
STATE_PLAY      =  0
STATE_ALERT     =  1  # minimal 1 enemy sedang chase
STATE_GAME_OVER =  2
STATE_WIN       =  3

# ── Tilemap index per map ────────────────────────────────────────────── #
TILEMAP_IDX = {
    "outdoor" : 0,
    "building": 1,
    "basement": 2,
}

# ════════════════════════════════════════════════════════════════════════ #
#  TUTORIAL SLIDES                                                         #
#  Tiap slide = { "title": str, "lines": [str, ...] }                     #
#  Pyxel font 4×6 px per karakter, SCREEN_W=128 → maks ~31 char per baris #
# ════════════════════════════════════════════════════════════════════════ #
TUTORIAL_SLIDES = [
    {
        "title": "=  OPERATION: DEMON CORE  =",
        "lines": [
            " Tahun 2033. Sebuah organisasi",
            "militer gelap berhasil mencuri",
            "inti nuklir 'Demon Core' yang",
            "mampu menghancurkan kota.",
            "",
            " Kamu adalah agen infiltrasi",
            "terakhir yang dikirim untuk",
            "mengamankan senjata itu",
            "sebelum terlambat.",
        ],
    },
    {
        "title": "---  KONTROL  ---",
        "lines": [
            " W / Arrow Up   : Jalan atas",
            " S / Arrow Down : Jalan bawah",
            " A / Arrow Left : Jalan kiri",
            " D / Arrow Right: Jalan kanan",
            "",
            "",
            " CTRL / Z  : Toggle CROUCH",
            " ESC       : Keluar game",
        ],
    },
    {
        "title": "---  STEALTH  ---",
        "lines": [
            " Musuh punya VISION CONE.",
            "Jangan masuk ke dalam cone",
            "kuning mereka!",
            "",
            "Cone MERAH = musuh mengejar.",
            "",
            " Gunakan CROUCH untuk bergerak",
            "lebih pelan & senyap.",
            "Bar NOISE di pojok kanan atas",
            "menunjukkan seberapa berisik",
            "langkah kakimu.",
        ],
    },
    {
        "title": "---  MISI  ---",
        "lines": [
            "Rute: ",
            "OUTDOOR-BUILDING-BASEMENT.",
            "Cari pintu masuk gedung di",
            "sisi kanan peta outdoor.",
            "Di basement, cari dan sentuh",
            "kotak [CORE] untuk mengambil",
            "Demon Core dan menyelesaikan",
            "misi.",
            "",
            "Jangan sampai tertangkap!",
        ],
    },
]


# ════════════════════════════════════════════════════════════════════════ #
#  MAP FACTORIES                                                           #
# ════════════════════════════════════════════════════════════════════════ #

def _make_outdoor_world(tilemap) -> tuple:
    triggers = [
        MapTrigger(grid_x=15, grid_y=5,
                   target_map="building", target_x=8, target_y=40),
    ]
    world = World(tilemap, triggers, default_floor=WorldItem.GRASS)
    enemies = [
        Enemy(x=32,  y=40,  world=world,
              patrol_points=[(32, 40),  (88, 40)]),
        Enemy(x=104, y=56,  world=world,
              patrol_points=[(104, 56), (104, 104)]),
    ]
    return world, enemies


def _make_building_world(tilemap) -> tuple:
    triggers = [
        MapTrigger(grid_x=8, grid_y=14,
                   target_map="basement", target_x=64, target_y=16),
        MapTrigger(grid_x=0, grid_y=5,
                   target_map="outdoor",  target_x=112, target_y=40),
    ]
    world = World(tilemap, triggers, default_floor=WorldItem.CERAMIC)
    enemies = [
        Enemy(x=96, y=80, world=world,
              patrol_points=[(96, 80), (48, 80), (48, 32), (96, 32)]),
        Enemy(x=112, y=64, world=world,
              patrol_points=[(112, 64), (16, 64)]),
    ]
    return world, enemies


def _make_basement_world(tilemap) -> tuple:
    triggers = [
        MapTrigger(grid_x=8, grid_y=1,
                   target_map="building", target_x=64, target_y=16),
    ]
    world = World(tilemap, triggers, default_floor=WorldItem.SILICON)
    enemies = [
        Enemy(x=80, y=96, world=world,
              patrol_points=[(80, 96), (40, 96), (40, 56), (80, 56)]),
    ]
    return world, enemies


# ════════════════════════════════════════════════════════════════════════ #
#  APP                                                                     #
# ════════════════════════════════════════════════════════════════════════ #

class App:
    DEMON_CORE_TILE = (7, 7)

    # ── Warna tombol ─────────────────────────────────────────────────── #
    BTN_NEXT_COL   = 6   # abu-abu terang  — tombol Next aktif
    BTN_NEXT_DIM   = 5   # abu-abu gelap   — tombol Next nonaktif (slide akhir)
    BTN_START_COL  = 11  # hijau           — tombol Start aktif (slide akhir)
    BTN_START_DIM  = 1   # biru gelap      — tombol Start nonaktif

    def __init__(self):
        pyxel.init(SCREEN_W, SCREEN_H, title="Operation: Demon Core", fps=60)
        pyxel.load("mygame.pyxres")

        # Tutorial state
        self.tutorial_slide   = 0
        self.tutorial_read    = False   # True kalau sudah sampai slide terakhir

        self.state       = STATE_TUTORIAL
        self.current_map = "outdoor"
        self._load_map("outdoor")

        pyxel.run(self.update, self.draw)

    # ── Map loading ──────────────────────────────────────────────────── #
    def _load_map(self, map_name: str,
                  spawn_x: int | None = None,
                  spawn_y: int | None = None):
        tilemap = pyxel.tilemap(TILEMAP_IDX.get(map_name, 0))

        if map_name == "outdoor":
            self.world, self.enemies = _make_outdoor_world(tilemap)
        elif map_name == "building":
            self.world, self.enemies = _make_building_world(tilemap)
        elif map_name == "basement":
            self.world, self.enemies = _make_basement_world(tilemap)
        else:
            self.world, self.enemies = _make_outdoor_world(tilemap)

        self.player = Player(self.world)

        if spawn_x is not None:
            self.player._Player__x = float(spawn_x)
        if spawn_y is not None:
            self.player._Player__y = float(spawn_y)

        self.current_map = map_name

    # ════════════════════════════════════════════════════════════════════ #
    #  UPDATE                                                              #
    # ════════════════════════════════════════════════════════════════════ #
    def update(self):
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            pyxel.quit()

        # ── Tutorial ─────────────────────────────────────────────────── #
        if self.state == STATE_TUTORIAL:
            self._update_tutorial()
            return

        # ── Game over / win ──────────────────────────────────────────── #
        if self.state in (STATE_GAME_OVER, STATE_WIN):
            if pyxel.btnp(pyxel.KEY_R):
                # Balik ke tutorial dari awal
                self.tutorial_slide = 0
                self.tutorial_read  = False
                self.state          = STATE_TUTORIAL
                self._load_map("outdoor")
            return

        # ── Player ───────────────────────────────────────────────────── #
        self.player.handle_input(pyxel)

        # ── Trigger transisi map ─────────────────────────────────────── #
        trigger = self.world.check_trigger(self.player.x, self.player.y)
        if trigger:
            self._load_map(trigger.target_map, trigger.target_x, trigger.target_y)
            return

        # ── Demon core pickup ────────────────────────────────────────── #
        if self.current_map == "basement":
            ptx = self.player.x // TILE_SIZE
            pty = self.player.y // TILE_SIZE
            if (ptx, pty) == self.DEMON_CORE_TILE:
                self.state = STATE_WIN
                return

        # ── Enemy ────────────────────────────────────────────────────── #
        for enemy in self.enemies:
            enemy.update(self.player.fx, self.player.fy, self.player.noise_level)
            if enemy.player_caught(self.player.fx, self.player.fy):
                self.state = STATE_GAME_OVER
                return

        self.state = STATE_ALERT if any(e.is_chasing() for e in self.enemies) \
                     else STATE_PLAY

    def _update_tutorial(self):
        last_slide = len(TUTORIAL_SLIDES) - 1

        # Tombol Next (→ atau N) — hanya kalau bukan slide terakhir
        if pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_N):
            if self.tutorial_slide < last_slide:
                self.tutorial_slide += 1

        # Tombol Prev (← atau B) — kembali ke slide sebelumnya
        if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_B):
            if self.tutorial_slide > 0:
                self.tutorial_slide -= 1

        # Sudah sampai slide terakhir → unlock Start
        if self.tutorial_slide == last_slide:
            self.tutorial_read = True

        # Tombol Start (SPACE atau RETURN) — hanya kalau sudah baca semua
        if self.tutorial_read:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.state = STATE_PLAY

    # ════════════════════════════════════════════════════════════════════ #
    #  DRAW                                                                #
    # ════════════════════════════════════════════════════════════════════ #
    def draw(self):
        pyxel.cls(0)

        if self.state == STATE_TUTORIAL:
            self._draw_tutorial()
            return

        # ── Tiles ────────────────────────────────────────────────────── #
        for y in range(self.world.HEIGHT):
            for x in range(self.world.WIDTH):
                world_item_draw(pyxel, x, y, self.world.world_map[y][x])

        # ── Demon core marker ────────────────────────────────────────── #
        if self.current_map == "basement":
            cx, cy = self.DEMON_CORE_TILE
            pyxel.rectb(cx * TILE_SIZE, cy * TILE_SIZE, TILE_SIZE, TILE_SIZE, 10)
            pyxel.text(cx * TILE_SIZE, cy * TILE_SIZE - 6, "CORE", 10)

        # ── Enemy ────────────────────────────────────────────────────── #
        for enemy in self.enemies:
            enemy.draw(pyxel)

        # ── Player ───────────────────────────────────────────────────── #
        pyxel.blt(
            self.player.x, self.player.y,
            self.player.IMG,
            WorldItem.PLAYER[0] * TILE_SIZE,
            WorldItem.PLAYER[1] * TILE_SIZE,
            self.player.WIDTH,
            self.player.HEIGHT,
        )

        # ── HUD ──────────────────────────────────────────────────────── #
        self._draw_hud()

        # ── Overlay ──────────────────────────────────────────────────── #
        if self.state == STATE_GAME_OVER:
            self._draw_overlay("GAME OVER", "Tertangkap!\nTekan R untuk ulang", 8)
        elif self.state == STATE_WIN:
            self._draw_overlay("MISI SELESAI!", "Demon Core diamankan :D.\nTekan R untuk ulang", 11)
        elif self.state == STATE_ALERT:
            if (pyxel.frame_count // 15) % 2 == 0:
                pyxel.text(2, 2, "!  ALERT  !", 8)

    # ── Tutorial renderer ────────────────────────────────────────────── #
    def _draw_tutorial(self):
        slide      = TUTORIAL_SLIDES[self.tutorial_slide]
        last_slide = len(TUTORIAL_SLIDES) - 1
        is_last    = (self.tutorial_slide == last_slide)
        y_off      = -8

        # Background gelap penuh
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, 0)

        # ── Border luar ───────────────────────────────────────────────── #
        pyxel.rectb(2, 2, SCREEN_W - 4, SCREEN_H - 4, 13)

        # ── Slide indicator titik (●/○) di bawah judul ───────────────── #
        total = len(TUTORIAL_SLIDES)
        dot_total_w = total * 6 - 1       # 5px per titik + 1px gap
        dot_x = (SCREEN_W - dot_total_w) // 2
        dot_y = 18 + y_off
        for i in range(total):
            col = 7 if i == self.tutorial_slide else 5
            pyxel.rect(dot_x + i * 6, dot_y, 4, 4, col)

        # ── Judul slide ───────────────────────────────────────────────── #
        title     = slide["title"]
        title_col = 10 if is_last else 11
        tx = (SCREEN_W - len(title) * 4) // 2
        pyxel.text(tx, 26 + y_off, title, title_col)

        # ── Garis pemisah ─────────────────────────────────────────────── #
        pyxel.line(8, 33 + y_off, SCREEN_W - 9, 33 + y_off, 13)

        # ── Isi slide ─────────────────────────────────────────────────── #
        for i, line in enumerate(slide["lines"]):
            pyxel.text(8, 37 + i * 7 + y_off, line, 7)

        # ── Tombol navigasi (bawah) ───────────────────────────────────── #
        # [ < PREV ]  halaman x/n  [ NEXT > ]  [ START ]
        nav_y = SCREEN_H - 14

        # Halaman x / n
        page_str = f"{self.tutorial_slide + 1}/{total}"
        px = (SCREEN_W - len(page_str) * 4) // 2
        pyxel.text(px, nav_y + 3, page_str, 6)

        # Tombol PREV — selalu ada kecuali di slide pertama
        if self.tutorial_slide > 0:
            self._draw_button(4, nav_y, "< PREV", 6)
        else:
            self._draw_button(4, nav_y, "< PREV", 1)  # dim

        # Tombol NEXT — hanya aktif kalau bukan slide terakhir
        if not is_last:
            self._draw_button(SCREEN_W - 38, nav_y, "NEXT >", self.BTN_NEXT_COL)
        else:
            self._draw_button(SCREEN_W - 38, nav_y, "NEXT >", self.BTN_NEXT_DIM)

        # Tombol START — aktif hanya kalau sudah baca semua (= is_last)
        # Digambar lebih menonjol kalau aktif (berkedip)
        if self.tutorial_read:
            # Berkedip tiap 20 frame agar menarik perhatian
            start_col = self.BTN_START_COL if (pyxel.frame_count // 20) % 2 == 0 \
                        else 3
            self._draw_button(SCREEN_W - 38, nav_y - 12, " START", start_col,
                              border_col=start_col)
            # pyxel.text(SCREEN_W - 50, nav_y - 9, "SPACE/", 5)
        else:
            self._draw_button(SCREEN_W - 38, nav_y - 12, " START", self.BTN_START_DIM,
                              border_col=1)
            # Petunjuk kecil: baca semua slide dulu
            # hint = "baca semua dulu"
            # pyxel.text((SCREEN_W - len(hint) * 4) // 2,
            #            nav_y - 9, hint, 5)

    def _draw_button(self, x: int, y: int, label: str,
                     text_col: int, border_col: int | None = None):
        """Gambar tombol kecil dengan border dan label."""
        w = len(label) * 4 + 4
        h = 9
        bc = border_col if border_col is not None else text_col
        pyxel.rect (x, y, w, h, 0)
        pyxel.rectb(x, y, w, h, bc)
        pyxel.text (x + 2, y + 2, label, text_col)

    # ── HUD ──────────────────────────────────────────────────────────── #
    def _draw_hud(self):
        pyxel.text(2, SCREEN_H - 8, self.current_map.upper(), 7)

        if self.player.crouching:
            pyxel.text(SCREEN_W - 30, SCREEN_H - 8, "[CROUCH]", 11)

        noise = self.player.noise_level
        bar_w = int(noise * 30)
        pyxel.text(SCREEN_W - 36, 2, "NOISE", 7)
        if bar_w > 0:
            pyxel.rect(SCREEN_W - 36, 8, bar_w, 3, 8 if noise > 0.5 else 10)

    # ── Overlay game over / win ───────────────────────────────────────── #
    def _draw_overlay(self, title: str, subtitle: str, color: int):
        bx, by, bw, bh = 16, 40, SCREEN_W - 32, 48
        pyxel.rect (bx, by, bw, bh, 0)
        pyxel.rectb(bx, by, bw, bh, color)

        tx = (SCREEN_W - len(title) * 4) // 2
        pyxel.text(tx, by + 8, title, color)

        lines = subtitle.split("\n")
        for i, line in enumerate(lines):
            sx = (SCREEN_W - len(line) * 4) // 2
            pyxel.text(sx, by + 20 + i * 10, line, 7)


App()