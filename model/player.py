import math
from model.pyxel_utils import PyxelSounds
from model.utils import round_float_if_close
from model.world import TILE_SIZE, WorldItem, sprites_collide

# Konstanta arah facing (untuk animasi & vision cone nanti)
DIR_RIGHT      = 0
DIR_DOWN_RIGHT = 1
DIR_DOWN       = 2
DIR_DOWN_LEFT  = 3
DIR_LEFT       = 4
DIR_UP_LEFT    = 5
DIR_UP         = 6
DIR_UP_RIGHT   = 7


class Player:
    IMG    = 0
    WIDTH  = 8
    HEIGHT = 8

    SPEED_NORMAL   = 1.0          # px per frame saat jalan normal
    SPEED_DIAGONAL = 1.0 / math.sqrt(2)  # dinormalisasi biar kecepatan sama
    SPEED_CROUCH   = 0.5          # px per frame saat jongkok (stealth)

    ROUNDING_ERROR_DELTA = 0.1

    def __init__(self, world):
        self.__x: float = world.player_grid_x * TILE_SIZE
        self.__y: float = world.player_grid_y * TILE_SIZE
        self.world = world
        self.pyxel_sounds = PyxelSounds()

        self.facing   = DIR_RIGHT   # arah hadap sekarang
        self.crouching = False      # tombol crouch (akan dipakai di noise system)
        self.moving    = False      # apakah sedang bergerak

    # ------------------------------------------------------------------ #
    #  MOVEMENT UTAMA — dipanggil dari game.py setiap frame               #
    # ------------------------------------------------------------------ #
    def handle_input(self, pyxel):
        """
        Baca input 8-arah dari pyxel, hitung dx/dy, lalu gerakkan player.
        Dipanggil dari App.update().
        """
        dx = 0
        dy = 0

        if pyxel.btn(pyxel.KEY_A) or pyxel.btn(pyxel.KEY_LEFT):
            dx -= 1
        if pyxel.btn(pyxel.KEY_D) or pyxel.btn(pyxel.KEY_RIGHT):
            dx += 1
        if pyxel.btn(pyxel.KEY_W) or pyxel.btn(pyxel.KEY_UP):
            dy -= 1
        if pyxel.btn(pyxel.KEY_S) or pyxel.btn(pyxel.KEY_DOWN):
            dy += 1

        # Crouch toggle — tombol Left Ctrl atau Z
        if pyxel.btnp(pyxel.KEY_LCTRL) or pyxel.btnp(pyxel.KEY_Z):
            self.crouching = not self.crouching

        self.moving = (dx != 0 or dy != 0)

        if not self.moving:
            self._snap_to_grid()
            return

        # Update facing berdasarkan arah input
        self._update_facing(dx, dy)

        # Hitung speed: diagonal dinormalisasi, crouch lebih lambat
        if dx != 0 and dy != 0:
            speed = self.SPEED_DIAGONAL
        else:
            speed = self.SPEED_NORMAL

        if self.crouching:
            speed *= self.SPEED_CROUCH

        # Gerakkan horizontal & vertikal secara terpisah
        # (agar bisa sliding sepanjang tembok)
        if dx != 0:
            self._move_axis(dx * speed, 0)
        if dy != 0:
            self._move_axis(0, dy * speed)

    # ------------------------------------------------------------------ #
    #  INTERNAL MOVEMENT                                                   #
    # ------------------------------------------------------------------ #
    def _move_axis(self, ddx: float, ddy: float):
        """Gerakkan player 1 sumbu, cek collision."""
        new_x = self.__x + ddx
        new_y = self.__y + ddy

        # Empat sudut bounding-box player (8×8 px)
        corners = [
            (new_x,              new_y),               # kiri atas
            (new_x + self.WIDTH - 1, new_y),           # kanan atas
            (new_x,              new_y + self.HEIGHT - 1),  # kiri bawah
            (new_x + self.WIDTH - 1, new_y + self.HEIGHT - 1),  # kanan bawah
        ]

        for cx, cy in corners:
            tx = int(cx) // TILE_SIZE
            ty = int(cy) // TILE_SIZE
            if self.world.is_solid(tx, ty):
                self.pyxel_sounds.play_hit_wall_sound()
                return  # batalkan gerakan sumbu ini

        self.__x = new_x
        self.__y = new_y

    def _snap_to_grid(self):
        """Bulatkan posisi ke pixel bulat saat berhenti."""
        self.__x = round_float_if_close(self.__x, self.ROUNDING_ERROR_DELTA)
        self.__y = round_float_if_close(self.__y, self.ROUNDING_ERROR_DELTA)

    def _update_facing(self, dx: int, dy: int):
        """Ubah self.facing berdasarkan dx/dy input."""
        if   dx == 1  and dy == 0:  self.facing = DIR_RIGHT
        elif dx == 1  and dy == 1:  self.facing = DIR_DOWN_RIGHT
        elif dx == 0  and dy == 1:  self.facing = DIR_DOWN
        elif dx == -1 and dy == 1:  self.facing = DIR_DOWN_LEFT
        elif dx == -1 and dy == 0:  self.facing = DIR_LEFT
        elif dx == -1 and dy == -1: self.facing = DIR_UP_LEFT
        elif dx == 0  and dy == -1: self.facing = DIR_UP
        elif dx == 1  and dy == -1: self.facing = DIR_UP_RIGHT

    # ------------------------------------------------------------------ #
    #  PROPERTIES                                                          #
    # ------------------------------------------------------------------ #
    @property
    def x(self) -> int:
        return int(self.__x)

    @property
    def y(self) -> int:
        return int(self.__y)

    @property
    def fx(self) -> float:
        """Posisi X sebagai float (untuk kalkulasi AI)."""
        return self.__x

    @property
    def fy(self) -> float:
        return self.__y

    @property
    def noise_level(self) -> float:
        """
        0.0 = diam, 1.0 = lari.
        Dipakai oleh enemy noise-detection nanti.
        """
        if not self.moving:
            return 0.0
        if self.crouching:
            return 0.3
        return 1.0

    # Tetap ada untuk kompatibilitas (tidak dipakai lagi, tapi aman)
    def stop_moving(self):
        self._snap_to_grid()

    def move_left(self):
        self._move_axis(-self.SPEED_NORMAL, 0)
        self.facing = DIR_LEFT

    def move_right(self):
        self._move_axis(self.SPEED_NORMAL, 0)
        self.facing = DIR_RIGHT

    def move_up(self):
        self._move_axis(0, -self.SPEED_NORMAL)
        self.facing = DIR_UP

    def move_down(self):
        self._move_axis(0, self.SPEED_NORMAL)
        self.facing = DIR_DOWN