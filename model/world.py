TILE_SIZE   = 8
SPRITE_BANK = 0

# Tiap tilemap di pyxres berukuran 256×256 tiles.
# Map outdoor  → tilemap 0, offset tile (0,0)
# Map building → tilemap 1, offset tile (0,0)
# Map basement → tilemap 2, offset tile (0,0)
# Pyxel menyimpan semua tilemap dalam satu "sheet" raksasa per bank,
# tapi pyxel.tilemap(n) sudah mengembalikan objek tilemap yang benar,
# jadi pget(x, y) dengan x,y 0–15 sudah tepat — tidak perlu offset manual.


class WorldItem:
    # ── Walls ──────────────────────────────────────────────────────── #
    TREE    = (2, 0)   # solid — outdoor
    WALL    = (3, 0)   # solid — building
    WALLC    = (2, 1)   # solid — basement

    # ── Peluncur nuklir (16 tile, 4×4) ────────────────────────────── #
    LAUNCH1  = (0, 6);  LAUNCH2  = (1, 6);  LAUNCH3  = (2, 6);  LAUNCH4  = (3, 6)
    LAUNCH5  = (0, 7);  LAUNCH6  = (1, 7);  LAUNCH7  = (2, 7);  LAUNCH8  = (3, 7)
    LAUNCH9  = (0, 8);  LAUNCH10 = (1, 8);  LAUNCH11 = (2, 8);  LAUNCH12 = (3, 8)
    LAUNCH13 = (0, 9);  LAUNCH14 = (1, 9);  LAUNCH15 = (2, 9);  LAUNCH16 = (3, 9)

    # ── Floors / corridors ─────────────────────────────────────────── #
    CORRIDOR = (4, 0)   # fallback / alias
    GRASS    = (4, 0)   # outdoor floor
    CERAMIC  = (5, 0)   # building floor
    SILICON  = (4, 1)   # basement floor

    # ── Sprites / interactables ────────────────────────────────────── #
    PLAYER = (0, 0)
    ENEMY  = (6, 0)
    DOOROUTDOOR   = (0, 3)
    DOORBUILDING  = (1, 3)
    DOORBASEMENT  = (1, 2)
    TRIGGER1= (4, 0)   # invisible — tampak seperti corridor GRASS
    TRIGGER2= (5, 0)   # invisible — tampak seperti corridor CERAMIC
    TRIGGER3= (4, 1)   # invisible — tampak seperti corridor SILICON

    # Diisi setelah definisi class (butuh referensi ke nilai di atas)
    SOLID_TILES = None


# Semua tile yang tidak bisa dilewati player maupun enemy
WorldItem.SOLID_TILES = frozenset({
    WorldItem.TREE,
    WorldItem.WALL,
    WorldItem.WALLC,
})

# Semua tile LAUNCH juga solid (badan mesin peluncur)
for _attr in dir(WorldItem):
    if _attr.startswith("LAUNCH"):
        WorldItem.SOLID_TILES = WorldItem.SOLID_TILES | frozenset({getattr(WorldItem, _attr)})


class MapTrigger:
    """Tile yang kalau diinjak player memicu transisi map."""
    def __init__(self, grid_x: int, grid_y: int,
                 target_map: str, target_x: int, target_y: int):
        self.grid_x     = grid_x
        self.grid_y     = grid_y
        self.target_map = target_map
        self.target_x   = target_x   # pixel spawn di map tujuan
        self.target_y   = target_y


class World:
    HEIGHT = 16
    WIDTH  = 16

    def __init__(self, tilemap, triggers: list | None = None,
                 default_floor: tuple = WorldItem.GRASS):
        self.tilemap  = tilemap
        self.triggers = triggers or []
        self.world_map: list[list] = []
        self.default_floor = default_floor

        # Default spawn — di-override kalau ada tile PLAYER di tilemap
        self.player_grid_x = 1
        self.player_grid_y = 13

        for y in range(self.HEIGHT):
            row = []
            for x in range(self.WIDTH):
                tile = self.tilemap.pget(x, y)

                if tile in WorldItem.SOLID_TILES:
                    row.append(tile)
                elif tile == WorldItem.PLAYER:
                    row.append(WorldItem.CORRIDOR)
                    self.player_grid_x = x
                    self.player_grid_y = y
                elif tile in (WorldItem.DOOROUTDOOR,
                              WorldItem.DOORBUILDING, WorldItem.DOORBASEMENT):
                    row.append(tile)
                elif tile in (WorldItem.GRASS, WorldItem.CERAMIC,
                              WorldItem.SILICON, WorldItem.CORRIDOR):
                    row.append(tile)
                elif tile in (WorldItem.TRIGGER1, WorldItem.TRIGGER2,
                              WorldItem.TRIGGER3):
                    row.append(self.default_floor)
                else:
                    # Unknown walkable tile → gunakan floor map saat ini
                    row.append(self.default_floor)
            self.world_map.append(row)

    # ── Query ────────────────────────────────────────────────────── #
    def is_solid(self, tile_x: int, tile_y: int) -> bool:
        if tile_x < 0 or tile_x >= self.WIDTH or tile_y < 0 or tile_y >= self.HEIGHT:
            return True   # out of bounds = solid
        return self.world_map[tile_y][tile_x] in WorldItem.SOLID_TILES

    def check_trigger(self, pixel_x: int, pixel_y: int) -> "MapTrigger | None":
        gx = pixel_x // TILE_SIZE
        gy = pixel_y // TILE_SIZE
        for t in self.triggers:
            if t.grid_x == gx and t.grid_y == gy:
                return t
        return None


# ── Rendering ───────────────────────────────────────────────────────── #
def world_item_draw(pyxel, x: int, y: int, world_item: tuple):
    pyxel.blt(
        x * TILE_SIZE,
        y * TILE_SIZE,
        SPRITE_BANK,
        world_item[0] * TILE_SIZE,
        world_item[1] * TILE_SIZE,
        TILE_SIZE,
        TILE_SIZE,
    )


def sprites_collide(x1: int, y1: int, x2: int, y2: int) -> bool:
    if x1 + TILE_SIZE <= x2 or x2 + TILE_SIZE <= x1:
        return False
    if y1 + TILE_SIZE <= y2 or y2 + TILE_SIZE <= y1:
        return False
    return True