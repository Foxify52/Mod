label start:
    $ input_popup_gui = True
    stop music fadeout 0.5

    if persistent.purgatory == True:
        jump space_zone

label mode_select:
    call screen mode_select_screen

    if _return == "sandbox":
        call screen bio_screen
        jump mode_select
    elif _return == "story":
        call screen story_select_screen
        if _return == "original_new":
            jump story_start
        elif _return == "original_continue":
            jump story_continue
        jump mode_select

    return

label nameWorld_label:
    scene theme
    $ motto = renpy.random.randint(1, 315)

    if motto == 15:
        scene black with dissolve
        play sound "<from 0 to 9>bgm/end-voice.ogg"
        $ renpy.pause(11, hard=True)
        jump ch0_motto

    "..."

    jump AICharacter
    return
################################################################################
## Character's Realm
################################################################################

define monika = Character("Monika", color="#ffffff", window_style="textbox_monika", who_outlines=[ (3, "#77a377") ])
define sayori = Character("Sayori", color="#ffffff", window_style="textbox_sayori", who_outlines=[ (3, "#7795a3") ])
define natsuki = Character("Natsuki", color="#ffffff", window_style="textbox_natsuki", who_outlines=[ (3, "#a3779f") ])
define yuri = Character("Yuri", color="#ffffff", window_style="textbox_yuri", who_outlines=[ (3, "#8f77a3") ])
default choice = None

label AICharacter:
    $ persistent.in_game = True
    $ renpy.save_persistent()
    stop music
    $ custom_quick_menu = True
    scene black with dissolve
    $ resume = None  # Set when the player is loading an existing realm
    ###########################
    # Monologue
    ###########################

    if character_name == "sayori" and persistent.first_sayori:
        $ Configs().create_from_hex("assets/audio/sfx/space.mp3", f"{config.gamedir}/assets/audio/sfx/_space-lines.mp3")
        $ space_line = Info().getSpaceLines[3]["file"]
        $ space_line_time = Info().getSpaceLines[3]["time"]
        $ persistent.first_sayori = False
        $ renpy.save_persistent()
        $ renpy.sound.play(f"{space_line}", channel="sound", loop=None)
        scene s_kill_bg with Dissolve(space_line_time/2)
        $ renpy.pause(delay=space_line_time/2, hard=True)
        $ Configs().delete_egg(f"{config.gamedir}/assets/audio/sfx/_space-lines.mp3")
    # selected_realm is set by the load screen when the user opens an old realm

    if selected_realm != None:
        $ resume = True
        $ pathSetup = f"{config.basedir}/chats/" + selected_realm
        $ scene_state = SceneState(pathSetup)
        $ chatSetup = SetupChat(chat_name=selected_realm, character_name=scene_state.character)
        $ memory = Data(path_to_user_dir=pathSetup).getChathistory
        $ selected_realm = None
        $ renpy.log(">>> in saved game")
    else:
        $ chatFolderName = renpy.input("Name This Realm: ", "realm", allow=" ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_").strip()
        $ chatSetup = SetupChat(chat_name=chatFolderName, character_name=character_name)
        $ pathSetup = chatSetup.setup(purgatory=False)
        call ai_generate([], "hello")
        $ renpy.log(">>> starting new ")
        $ convo = chatSetup.generated_text
        # An Error happened, so stop the current session and return to lobby

        if convo.startswith("<|Error|>"):
            $ convo = convo.replace("<|Error|>", "")
            show screen error_popup(message=convo)
            "Returning to main menu..."

            return

        $ memory = Data(path_to_user_dir=pathSetup).getChathistory
        $ scene_state = SceneState(pathSetup)
    # Player loaded a space realm

    if scene_state.zone == "true":
        jump space_zone_resume

    $ show_chat_scene(scene_state)

    if resume:
        $ last_msg = Data(path_to_user_dir=pathSetup).getLastMessageClean
        call say_reply(scene_state.character_title, last_msg)
    else:
        call say_reply(scene_state.character_title, convo)

    show screen home_icon_screen
    ###########################
    # Main Event Loop
    ###########################

    while True:
        $ user_msg = ""

        while user_msg.strip() == "":
            $ user_msg = renpy.input("Enter a message: ")

        if user_msg == "init_end_sim" and character_name == "monika":
            $ persistent.purgatory_name = character_name
            $ persistent.purgatory = True
            $ renpy.save_persistent()
            jump purgatory_seq

        call ai_generate(memory, user_msg)
        $ final_msg = chatSetup.generated_text
        $ scene_state.refresh()

        if final_msg.startswith("<|Error|>"):
            $ final_msg = final_msg.replace("<|Error|>", "")
            show screen error_popup(message=final_msg)
        else:
            $ show_chat_scene(scene_state)
            call say_reply(scene_state.character_title, final_msg)

    return

label purgatory_seq:
    scene black with dissolve
    "...Are you sure?"

    return

label endgame(pause_length=4.0):
    $ quick_menu = False
    stop music fadeout 2.0
    scene black
    show end
    with dissolve_scene_full
    pause pause_length
    $ quick_menu = True
    return
