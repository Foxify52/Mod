# The space classroom ("purgatory") — entered fresh via init_end_sim, or by
# loading a previously saved space realm.
# Entry: fresh purgatory, jumped to from label start when persistent.purgatory is set
label space_zone:
    $ space_resume = False
    jump space_zone_main
# Entry: a saved space realm, jumped to from AICharacter after it loaded the
# realm's chat/scene data (pathSetup, chatSetup, memory, scene_state are set)

label space_zone_resume:
    $ space_resume = True
    jump space_zone_main

label space_zone_main:
    scene white
    play music "bgm/monika-start.ogg" noloop
    $ renpy.pause(0.5, hard=True)
    show splash_glitch2 with Dissolve(0.5, alpha=True)
    $ renpy.pause(2.0, hard=True)
    hide splash_glitch2 with Dissolve(0.5, alpha=True)
    stop music

    if persistent.first_space == False:
        show mask_2
        show mask_3
        show monika_bg
        show monika_bg_highlight
    else:
        show mask_2 at zm_out
        show mask_3 at zm_out
        show monika_bg at zm_out
        show monika_bg_highlight at zm_out

    play music m1
    $ persistent.in_game = True
    $ renpy.save_persistent()

    if space_resume:
        $ purg_title = scene_state.character_title
    else:
        $ purg_name = persistent.purgatory_name
        $ purg_title = purg_name.title()
        $ persistent.purgatory = False
        $ persistent.purgatory_name = ""
        $ renpy.save_persistent()
    ###########################
    # Monologue
    ###########################

    $ Configs().create_from_hex("assets/audio/sfx/space.mp3", f"{config.gamedir}/assets/audio/sfx/_space-lines.mp3")
    $ space_line = Info().getSpaceLines[1]["file"]
    $ space_line_time = Info().getSpaceLines[1]["time"]
    $ hard_pause = False

    if persistent.first_space == True:
        $ renpy.sound.play(f"{space_line}", channel="sound", loop=None)
        $ persistent.first_space = False
        $ renpy.save_persistent()
        $ hard_pause = True
    else:
        $ rnd_line = renpy.random.randint(0, 4)
        $ rnd_line = rnd_line if rnd_line != 3 else 0
        $ space_line = Info().getSpaceLines[rnd_line]["file"]
        $ space_line_time = Info().getSpaceLines[rnd_line]["time"]
        $ renpy.sound.play(f"{space_line}", channel="sound", loop=None)

    if hard_pause:
        $ renpy.pause(space_line_time, hard=hard_pause)
    else:
        "click to skip"

        stop sound

    $ Configs().delete_egg(f"{config.gamedir}/assets/audio/sfx/_space-lines.mp3")
    show screen home_icon_screen

    if space_resume:
        $ last_msg = Data(path_to_user_dir=pathSetup).getLastMessageClean
        call say_reply(purg_title, last_msg)
    else:
        $ chatFolderName = f"{purg_name}_purgatory"
        $ chatSetup = SetupChat(chat_name=chatFolderName, character_name=purg_name)
        $ pathSetup = chatSetup.setup(purgatory=True)
        $ renpy.log(f">>> pathSetup is: {pathSetup}")
        $ DataSetup = Data(path_to_user_dir=pathSetup)
        $ DataSetup.updateSceneData("zone", "true")
        $ DataSetup.updateSceneData("character", purg_name)
        $ default_history = Info().getExamplePrompts[f"{purg_name}_purgatory"]
        call ai_generate(default_history, "umm...")
        $ renpy.log(">>> starting new ")
        $ convo = chatSetup.generated_text
        # An Error happened, so stop the current session and return to lobby

        if convo.startswith("<|Error|>"):
            $ convo = convo.replace("<|Error|>", "")
            show screen error_popup(message=convo)
            "Returning to main menu..."

            return

        call say_reply(purg_title, convo)

    $ memory = Data(path_to_user_dir=pathSetup).getChathistory
    $ counter = 0
    $ special_check = False
    ###########################
    # Main Event Loop
    ###########################

    while True:
        $ user_msg = ""

        while user_msg.strip() == "":
            $ user_msg = renpy.input("Enter a message: ")

        $ counter += 1

        if counter >= 6 and persistent.first_scare == False:
            hide monika_bg
            hide monika_bg_highlight
            show monika_scare
            play sound "sfx/mscare.ogg"
            $ persistent.first_scare = True
            $ renpy.save_persistent()
            $ special_check = True
            $ user_msg = user_msg + " *I also suddenly scream really loudly because you just scared me*"

        call ai_generate(memory, user_msg)
        $ final_msg = chatSetup.generated_text

        if final_msg.startswith("<|Error|>"):
            $ final_msg = final_msg.replace("<|Error|>", "")
            show screen error_popup(message=final_msg)
        else:
            if special_check:
                $ renpy.pause(10, hard=True)
                "..."

                $ special_check = False

            hide monika_scare
            show monika_bg
            show monika_bg_highlight
            call say_reply(purg_title, final_msg)

    return
