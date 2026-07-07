# Story mode — shared definitions.
#
# Routing state, helpers, and classes the ported original-game scripts rely
# on. Everything here was part of the original DDLC definitions and was
# removed from the mod while story content was absent; story mode brings the
# needed subset back. Values match reference/scripts/definitions.rpy.
#
# Deliberately NOT ported: the .chr file machinery (delete_character /
# restore_all_characters), anticheat, delete_all_saves, and the playthrough
# autoload branching — story mode has its own entry points and never touches
# files on disk.

init python:
    import random

    def get_pos(channel="music"):
        pos = renpy.music.get_pos(channel=channel)
        if pos:
            return pos
        return 0

    def pause(time=None):
        global _windows_hidden
        if not time:
            _windows_hidden = True
            renpy.ui.saybehavior(afm=" ")
            renpy.ui.interact(mouse='pause', type='pause', roll_forward=None)
            _windows_hidden = False
            return
        if time <= 0:
            return
        _windows_hidden = True
        renpy.pause(time)
        _windows_hidden = False

    # Also referenced (lazily) by n_rects_mouth in game/definitions.rpy —
    # having this class defined fixes that latent NameError as well.
    class RectCluster(object):
        def __init__(self, theDisplayable, numRects=12, areaWidth=30, areaHeight=30):
            self.sm = SpriteManager(update=self.update)
            self.rects = []
            self.displayable = theDisplayable
            self.numRects = numRects
            self.areaWidth = areaWidth
            self.areaHeight = areaHeight

            for i in range(self.numRects):
                self.add(self.displayable)

        def add(self, d):
            s = self.sm.create(d)
            s.x = (random.random() - 0.5) * self.areaWidth * 2
            s.y = (random.random() - 0.5) * self.areaHeight * 2
            s.width = random.random() * self.areaWidth / 2
            s.height = random.random() * self.areaHeight / 2
            self.rects.append(s)

        def update(self, st):
            for s in self.rects:
                s.x = (random.random() - 0.5) * self.areaWidth * 2
                s.y = (random.random() - 0.5) * self.areaHeight * 2
                s.width = random.random() * self.areaWidth / 2
                s.height = random.random() * self.areaHeight / 2
            return 0

    nonunicode = "¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿĀāĂăĄąĆćĈĉĊċČčĎďĐđĒēĔĕĖėĘęĚěĜĝĞğĠġĢģĤĥĦħĨĩĪīĬĭĮįİıĲĳĴĵĶķĸĹĺĻļĽľĿŀŁłŃńŅņŇňŉŊŋŌōŎŏŐőŒœŔŕŖŗŘřŚśŜŝŞşŠšŢţŤťŦŧŨũŪūŬŭŮůŰűŲųŴŵŶŷŸŹźŻżŽž"

    def glitchtext(length):
        output = ""
        for x in range(length):
            output += random.choice(nonunicode)
        return output


################################################################################
## Original-game routing state (per-playthrough; snapshotted by checkpoints)
################################################################################

default chapter = 0
default currentpos = 0
default allow_skipping = True

# Poem game results
default poemwinner = ['sayori', 'sayori', 'sayori']
default s_poemappeal = [0, 0, 0]
default n_poemappeal = [0, 0, 0]
default y_poemappeal = [0, 0, 0]
default m_poemappeal = [0, 0, 0]
default s_appeal = 0
default n_appeal = 0
default y_appeal = 0
default m_appeal = 0

# Poem-sharing bookkeeping
default s_readpoem = False
default n_readpoem = False
default y_readpoem = False
default m_readpoem = False
default n_read3 = False
default y_read3 = False
default n_poemearly = False
default poemsread = 0
default skip_poem = False
default skip_transition = False
default pt = ""

# Choice outcomes
default ch1_choice = "sayori"
default ch2_winner = "Yuri"
default help_sayori = None
default help_monika = None
default ch4_scene = "yuri"
default ch4_name = "Yuri"
default sayori_confess = True

# One-shot scene guards
default n_exclusivewatched = False
default y_exclusivewatched = False
default y_gave = False
default y_ranaway = False
default in_sayori_kill = None
default seen_eyes_this_chapter = False

################################################################################
## Story-mode state (mod-specific)
################################################################################

# Whether AI chat windows are active this session (Ollama reachable + model set)
default story_ai_enabled = False

# Day checkpoint: {"day": int, "vars": {...}} — always assigned a fresh dict
default persistent.story_checkpoint = None
default persistent.story_act1_done = False

# Poem/gallery persistence from the original game
default persistent.yuri_kill = 0
default persistent.clear = [False, False, False, False, False, False, False, False, False, False]
default persistent.clearall = None
default persistent.special_poems = None
default persistent.first_poem = None
