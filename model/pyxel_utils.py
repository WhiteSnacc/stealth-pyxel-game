import pyxel

class PyxelSounds:

    # in frames (60 frames per second)
    HIT_WALL_SOUND_TIMEOUT = 60

    def __init__(self):
        self.__hit_wall_sound_framestamp = 0
        pyxel.playm(0, loop=True)

    def play_hit_wall_sound(self):
        current_frame = pyxel.frame_count
        if current_frame - self.__hit_wall_sound_framestamp < self.HIT_WALL_SOUND_TIMEOUT:
            return
        self.__hit_wall_sound_framestamp = current_frame
        pyxel.play(0, 0)