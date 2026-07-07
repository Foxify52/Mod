define config.name = "Doki Doki AI Edition"
define config.version = "1.3.1-demo"
define gui.about = _("")
define build.name = "DDAE"
define config.has_sound = True
define config.has_music = True
define config.has_voice = False
define config.debug_sound = True
define config.main_menu_music = audio.t1
define config.enter_transition = Dissolve(.2)
define config.exit_transition = Dissolve(.2)
define config.after_load_transition = None
define config.end_game_transition = Dissolve(.5)
define config.window = "auto"
define config.window_show_transition = Dissolve(.2)
define config.window_hide_transition = Dissolve(.2)
default preferences.text_cps = 50
default preferences.afm_time = 15
default preferences.music_volume = 0.75
default preferences.sfx_volume = 0.6
define config.save_directory = "DDAE-1454445547"
define config.window_icon = "assets/imgs/gui/window_icon.png"
define config.allow_skipping = False
define config.has_autosave = False
define config.has_quicksave = False
define config.autosave_on_quit = False
define config.autosave_on_choice = False
define config.autosave_slots = 0
define config.layers = [ 'master', 'transient', 'screens', 'overlay', 'front' ]
define config.image_cache_size = 64
define config.predict_statements = 50
define config.rollback_enabled = config.developer
define config.check_conflicting_properties = True
define config.menu_clear_layers = ["front"]
# DDLC-era engine behavior: without this, Ren'Py 8 initializes fresh shows
# from the "default" transform (bottom-center, zoom 1.0), so the original
# scripts' bare `show girl` statements flash a huge centered sprite before
# the t11/t2x transforms ease it into its slot.
define config.default_transform = None
define config.gl_test_image = "white"
define config.log = "log.txt"
# init python:
#     if len(renpy.loadsave.location.locations) > 1: del(renpy.loadsave.location.locations[1])
#     renpy.game.preferences.pad_enabled = False
#     def replace_text(s):
#         s = s.replace('--', u'\u2014') 
#         s = s.replace(' - ', u'\u2014') 
#         return s
#     config.replace_text = replace_text
#     def game_menu_check():
#         if quick_menu: renpy.call_in_new_context('_game_menu')
#     config.game_menu_action = game_menu_check
#     def force_integer_multiplier(width, height):
#         if float(width) / float(height) < float(config.screen_width) / float(config.screen_height):
#             return (width, float(width) / (float(config.screen_width) / float(config.screen_height)))
#         else:
#             return (float(height) * (float(config.screen_width) / float(config.screen_height)), height)

init python:
    ## Everything the mod ships is packed into .rpa archives, EXCEPT the
    ## user-accessible custom-content folders, which must stay loose so
    ## players can drop their own files in (see GUIDES.md):
    ##   game/assets/configs/**          - bg_scenes.json etc. are user-editable,
    ##                                     custom_characters/ is a drop zone
    ##   game/assets/prompts/**          - custom_prompts/ holds backstory edits
    ##   game/assets/imgs/characters/**  - custom character sprites
    ##   game/assets/imgs/bg/**          - custom backgrounds

    build.archive("scripts", "all")
    build.archive("mod_assets", "all")

    # Junk and dev files first (first matching pattern wins)
    build.classify("/reference/**", None)  # decompiled original scripts, dev-only
    build.classify("/reference/", None)
    build.classify("**~", None)
    build.classify("**.bak", None)
    build.classify("**/.**", None)
    build.classify("**/#**", None)
    build.classify("**/thumbs.db", None)
    build.classify("**.rpy", None)
    build.classify("**.psd", None)
    build.classify("/game/cache/**", None)
    build.classify("/game/saves/**", None)
    build.classify("/game/firstrun", None)
    build.classify("/game/log.txt", None)

    # Never ship the base-DDLC archives that get copied in for testing
    build.classify("game/audio.rpa", None)
    build.classify("game/images.rpa", None)
    build.classify("game/fonts.rpa", None)
    build.classify("game/scripts.rpa", None)

    # Compiled scripts go into the scripts archive
    build.classify("game/**.rpyc", "scripts")

    # Loose user-content folders ship as plain files
    build.classify("game/assets/configs/**", "all")
    build.classify("game/assets/prompts/**", "all")
    build.classify("game/assets/imgs/characters/**", "all")
    build.classify("game/assets/imgs/bg/**", "all")

    # Everything else the mod ships is archived
    build.classify("game/assets/**", "mod_assets")

    build.documentation("*.html")
    build.documentation("*.txt")

    build.include_old_themes = False
