import math
import pyxel
from model.world import TILE_SIZE, SPRITE_BANK, WorldItem

# ── State machine ──────────────────────────────────────────────────── #
PATROL = 0   # jalan bolak-balik sesuai patrol_points
ALERT  = 1   # tanda tanya — musuh curiga, berjalan ke last-seen pos
CHASE  = 2   # seru — musuh tahu posisi player, kejar

# ── Konstanta vision ──────────────────────────────────────────────── #
VISION_RANGE      = 80    # px — seberapa jauh musuh bisa lihat
VISION_HALF_ANGLE = 45    # derajat setengah FOV (total FOV = 90°)
NOISE_RANGE       = 40    # px — radius dengar suara langkah

# ── Konstanta timer ──────────────────────────────────────────────── #
ALERT_DURATION    = 120   # frame sebelum balik ke PATROL (2 detik @60fps)

# ── Warna ────────────────────────────────────────────────────────── #
COLOR_VISION_CONE = 10    # kuning
COLOR_ALERT_CONE  = 8     # merah


def _raycast_hit_wall(world, x0: float, y0: float, x1: float, y1: float) -> bool:
    """
    DDA raycasting: jalan dari (x0,y0) ke (x1,y1) tile per tile.
    Return True kalau ada wall di antara keduanya (sebelum sampai tujuan).
    Koordinat dalam pixel.
    """
    tx0 = int(x0) // TILE_SIZE
    ty0 = int(y0) // TILE_SIZE
    tx1 = int(x1) // TILE_SIZE
    ty1 = int(y1) // TILE_SIZE

    dx = abs(tx1 - tx0)
    dy = abs(ty1 - ty0)
    sx = 1 if tx0 < tx1 else -1
    sy = 1 if ty0 < ty1 else -1
    err = dx - dy

    tx, ty = tx0, ty0

    while True:
        # Kalau sudah sampai tile tujuan, tidak ada wall di antaranya
        if tx == tx1 and ty == ty1:
            return False

        # Cek tile saat ini (skip tile asal musuh sendiri)
        if not (tx == tx0 and ty == ty0):
            if world.is_solid(tx, ty):
                return True  # kena wall

        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            tx  += sx
        if e2 < dx:
            err += dx
            ty  += sy


class Vector2:
    def __init__(self, x: float = 0, y: float = 0):
        self.x = x
        self.y = y

    def __add__(self, other):  return Vector2(self.x + other.x, self.y + other.y)
    def __sub__(self, other):  return Vector2(self.x - other.x, self.y - other.y)
    def __mul__(self, s):      return Vector2(self.x * s, self.y * s)

    def magnitude(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def normalize(self):
        m = self.magnitude()
        return Vector2(self.x / m, self.y / m) if m > 0 else Vector2(0, 0)

    def dot(self, other) -> float:
        return self.x * other.x + self.y * other.y

    def distance_to(self, other) -> float:
        return (self - other).magnitude()


class Enemy:
    IMG    = 0
    WIDTH  = 8
    HEIGHT = 8

    SPEED_PATROL = 0.4
    SPEED_ALERT  = 0.5
    SPEED_CHASE  = 0.5

    def __init__(self, x: float, y: float, world,
                 patrol_points: list[tuple] | None = None):
        """
        x, y          — posisi awal dalam pixel
        world         — referensi World, untuk raycasting wall check
        patrol_points — list of (px, py) dalam pixel.
                        Kalau None, musuh diam di tempat.
        """
        self.pos   = Vector2(x, y)
        self.world = world   # dipakai oleh _can_see & _draw_vision_cone

        # Patrol
        self.patrol_points = patrol_points or [(x, y)]
        self.patrol_index  = 0
        self._goto_next_patrol()

        # State
        self.state       = PATROL
        self.alert_timer = 0
        self.last_seen   = Vector2(x, y)  # posisi terakhir player terlihat

        # Facing (arah hadap, untuk vision cone)
        self.facing = Vector2(1, 0)

    # ─────────────────────────────────────────────────────────────────── #
    #  UPDATE UTAMA                                                        #
    # ─────────────────────────────────────────────────────────────────── #
    def update(self, player_fx: float, player_fy: float, player_noise: float):
        """Dipanggil tiap frame dari App.update()."""
        player_pos = Vector2(player_fx, player_fy)

        can_see  = self._can_see(player_pos)
        can_hear = self._can_hear(player_pos, player_noise)

        # ── Transisi state ─────────────────────────────────────────── #
        if can_see or can_hear:
            self.state       = CHASE if can_see else ALERT
            self.last_seen   = Vector2(player_fx, player_fy)
            self.alert_timer = ALERT_DURATION
        else:
            if self.state == CHASE:
                self.state       = ALERT     # baru kehilangan pandangan
                self.alert_timer = ALERT_DURATION
            elif self.state == ALERT:
                self.alert_timer -= 1
                if self.alert_timer <= 0:
                    self.state = PATROL
                    self._goto_next_patrol()

        # ── Gerakan sesuai state ───────────────────────────────────── #
        if self.state == PATROL:
            self._do_patrol()
        elif self.state == ALERT:
            self._move_toward(self.last_seen, self.SPEED_ALERT)
        elif self.state == CHASE:
            self._move_toward(player_pos, self.SPEED_CHASE)

    # ─────────────────────────────────────────────────────────────────── #
    #  DETECTION                                                           #
    # ─────────────────────────────────────────────────────────────────── #
    def _can_see(self, player_pos: Vector2) -> bool:
        """
        Vision cone check + raycasting.
        1. Cek apakah player dalam range & sudut FOV
        2. Tembak ray — kalau ada wall di antaranya, tidak bisa lihat
        """
        to_player = player_pos - self.pos
        dist = to_player.magnitude()
        if dist > VISION_RANGE or dist == 0:
            return False

        # Sudut FOV check
        cos_angle = self.facing.normalize().dot(to_player.normalize())
        threshold = math.cos(math.radians(VISION_HALF_ANGLE))
        if cos_angle < threshold:
            return False

        # Raycasting — ada wall di antara enemy dan player?
        cx = self.pos.x + self.WIDTH  // 2
        cy = self.pos.y + self.HEIGHT // 2
        px = player_pos.x + self.WIDTH  // 2
        py = player_pos.y + self.HEIGHT // 2
        if _raycast_hit_wall(self.world, cx, cy, px, py):
            return False

        return True

    def _can_hear(self, player_pos: Vector2, noise: float) -> bool:
        """Noise detection — radius proporsional dengan noise level player."""
        if noise <= 0:
            return False
        dist = self.pos.distance_to(player_pos)
        return dist <= NOISE_RANGE * noise

    # ─────────────────────────────────────────────────────────────────── #
    #  MOVEMENT                                                            #
    # ─────────────────────────────────────────────────────────────────── #
    def _can_move_to(self, x: float, y: float) -> bool:
        """Return True kalau enemy bisa bergerak ke posisi pixel (x, y)."""
        corners = [
            (x, y),
            (x + self.WIDTH - 1, y),
            (x, y + self.HEIGHT - 1),
            (x + self.WIDTH - 1, y + self.HEIGHT - 1),
        ]
        for cx, cy in corners:
            tx = int(cx) // TILE_SIZE
            ty = int(cy) // TILE_SIZE
            if self.world.is_solid(tx, ty):
                return False
        return True

    def _move_toward(self, target: Vector2, speed: float):
        direction = (target - self.pos).normalize()
        if direction.magnitude() > 0:
            self.facing = direction

        new_x = self.pos.x + direction.x * speed
        new_y = self.pos.y + direction.y * speed

        # Gerakannya dicek per sumbu agar tidak tembus wall/pohon
        if self._can_move_to(new_x, self.pos.y):
            self.pos.x = new_x
        if self._can_move_to(self.pos.x, new_y):
            self.pos.y = new_y

    def _do_patrol(self):
        if not self.patrol_points:
            return
        target = Vector2(*self.patrol_points[self.patrol_index])
        dist   = self.pos.distance_to(target)

        if dist < self.SPEED_PATROL + 0.5:
            # Sampai di waypoint, ke waypoint berikutnya
            self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)
            self._goto_next_patrol()
        else:
            self._move_toward(target, self.SPEED_PATROL)

    def _goto_next_patrol(self):
        """Update target patrol index (tidak gerakkan, hanya set index)."""
        # Target sudah di-set di _do_patrol; method ini hanya placeholder
        # agar bisa di-override di subclass jika perlu.
        pass

    # ─────────────────────────────────────────────────────────────────── #
    #  DRAW                                                                #
    # ─────────────────────────────────────────────────────────────────── #
    def draw(self, pyxel_ref):
        # ── Vision cone ────────────────────────────────────────────── #
        cone_color = COLOR_ALERT_CONE if self.state in (ALERT, CHASE) else COLOR_VISION_CONE
        self._draw_vision_cone(pyxel_ref, cone_color)

        # ── Sprite musuh ───────────────────────────────────────────── #
        pyxel_ref.blt(
            int(self.pos.x),
            int(self.pos.y),
            self.IMG,
            WorldItem.ENEMY[0] * TILE_SIZE,
            WorldItem.ENEMY[1] * TILE_SIZE,
            self.WIDTH,
            self.HEIGHT,
        )

        # ── Indikator state (! / ?) ─────────────────────────────────── #
        if self.state == ALERT:
            pyxel_ref.text(int(self.pos.x) + 1, int(self.pos.y) - 7, "?", 10)
        elif self.state == CHASE:
            pyxel_ref.text(int(self.pos.x) + 1, int(self.pos.y) - 7, "!", 8)

    def _draw_vision_cone(self, pyxel_ref, color: int):
        """
        Gambar vision cone — tiap ray berhenti di wall pertama yang ditemui,
        jadi cone tidak tembus tembok.
        """
        cx = int(self.pos.x) + self.WIDTH  // 2
        cy = int(self.pos.y) + self.HEIGHT // 2

        facing_angle = math.atan2(self.facing.y, self.facing.x)
        steps = 16  # lebih banyak ray = cone lebih rapat

        for i in range(steps + 1):
            t     = -1.0 + (2.0 * i / steps)
            angle = facing_angle + t * math.radians(VISION_HALF_ANGLE)
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            # Jalan step kecil sepanjang ray, berhenti di wall
            draw_len = VISION_RANGE
            for step in range(1, VISION_RANGE, TILE_SIZE // 2):
                rx = cx + cos_a * step
                ry = cy + sin_a * step
                tx = int(rx) // TILE_SIZE
                ty = int(ry) // TILE_SIZE
                if self.world.is_solid(tx, ty):
                    # Berhenti tepat di depan wall
                    draw_len = step - TILE_SIZE // 2
                    break

            ex = int(cx + cos_a * draw_len)
            ey = int(cy + sin_a * draw_len)
            pyxel_ref.line(cx, cy, ex, ey, color)

    # ─────────────────────────────────────────────────────────────────── #
    #  PROPERTIES                                                          #
    # ─────────────────────────────────────────────────────────────────── #
    @property
    def x(self) -> int:
        return int(self.pos.x)

    @property
    def y(self) -> int:
        return int(self.pos.y)

    def is_chasing(self) -> bool:
        return self.state == CHASE

    def player_caught(self, player_fx: float, player_fy: float) -> bool:
        """Return True kalau musuh menyentuh player (untuk game over)."""
        dist = self.pos.distance_to(Vector2(player_fx, player_fy))
        return dist < TILE_SIZE