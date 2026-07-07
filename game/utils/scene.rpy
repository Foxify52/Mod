# Shared presentation layer for the AI chat: scene-state snapshots,
# background/sprite rendering, speaker dispatch, message splitting, and the
# generation-wait loop. Used by both the sandbox realm (script.rpy) and the
# space zone (space_zone.rpy).
init python:
    import json
    import re
    import threading

    # Content that ships with base DDLC (found inside images.rpa)
    DDLC_DEFAULT_BGS = {
        "bedroom.png",
        "club.png",
        "class.png",
        "closet.png",
        "corridor.png",
        "house.png",
        "kitchen.png",
        "sayori_bedroom.png",
        "residential.png",
    }
    DDLC_DEFAULT_CHARS = {"monika", "sayori", "natsuki", "yuri"}


    class SceneState:
        """One-shot snapshot of a realm's scenedata.json.
        Reads the file once; call refresh() to re-read after the AI updates it."""

        FIELDS = (
            "gamemode",
            "music",
            "background",
            "character",
            "head_sprite",
            "left_sprite",
            "right_sprite",
            "zone",
        )

        def __init__(self, realm_path):
            self.realm_path = realm_path
            self.refresh()

        def refresh(self):
            try:
                with open(self.realm_path + "/scenedata.json", "r") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                data = {}
            for field in self.FIELDS:
                setattr(self, field, data.get(field, ""))
            return self

        @property
        def character_title(self):
            return self.character.title()


    def show_chat_scene(state):
        """Rebuild the visible background and character sprite from a SceneState."""
        if state.background in DDLC_DEFAULT_BGS:
            bg_path = f"bg/{state.background}"
        else:
            bg_path = f"assets/imgs/bg/{state.background}"

        renpy.scene()
        renpy.show("chat_bg", what=Composite((1280, 720), (0, 0), bg_path))

        if state.character in DDLC_DEFAULT_CHARS:
            sprite_dir = state.character
        else:
            sprite_dir = f"assets/imgs/characters/{state.character_title}"

        if Info().full_sprites_check(state.character_title, state.head_sprite):
            # The head sprite is a full-body image on its own
            sprite = Composite((960, 960), (0, 0), f"{sprite_dir}/{state.head_sprite}")
        else:
            sprite = Composite(
                (960, 960),
                (0, 0),
                f"{sprite_dir}/{state.left_sprite}",
                (0, 0),
                f"{sprite_dir}/{state.right_sprite}",
                (0, 0),
                f"{sprite_dir}/{state.head_sprite}",
            )
        renpy.show("chat_sprite", what=sprite, at_list=[uppies, t11])


    def string_splitter(text, length):
        """Split text into chunks of at most `length` chars along sentence
        boundaries, returned in reverse order (pop() yields them in order)."""
        sentences = re.split(r"(?<=[.!?]) +", text)

        wrapped_sentences = []
        current_part = ""

        for sentence in sentences:
            if len(current_part) + len(sentence) < length:
                current_part += sentence + " "
            else:
                if current_part:
                    wrapped_sentences.append(current_part.strip())
                current_part = sentence + " "

        if current_part.strip():
            wrapped_sentences.append(current_part.strip())

        wrapped_sentences.reverse()
        return wrapped_sentences


    def speak(current_char_title, message):
        """Say a line as the given character, updating cur_speaker so the say
        screen picks the matching textbox. Use in place of renpy.say()."""
        global cur_speaker
        speakers = {
            "Monika": ("m", monika),
            "Sayori": ("s", sayori),
            "Natsuki": ("n", natsuki),
            "Yuri": ("y", yuri),
        }
        cur_speaker, character = speakers.get(current_char_title, ("n_default", None))
        if character is None:
            renpy.say(current_char_title, message)
        else:
            character(message)
        renpy.log(cur_speaker)
# Runs the AI generation on a worker thread while showing a Loading prompt.
# The result is left in chatSetup.generated_text for the caller.

label ai_generate(gen_memory, gen_user_msg):
    $ chatSetup.is_generating = True
    $ threading.Thread(target=chatSetup.chat, args=(pathSetup, gen_memory, gen_user_msg)).start()
    $ _history = False
    $ wait_msg = ""

    while chatSetup.is_generating == True:
        $ wait_msg = wait_msg + "." if len(wait_msg) < 3 else "."
        "Loading[wait_msg] {fast} {w=0.7}{nw}"

    $ _history = True
    return
# Says a (possibly long) AI reply in textbox-sized chunks.

label say_reply(speaker_title, reply):
    $ messages = string_splitter(reply, 255)

    while messages:
        $ message = messages.pop()

        if len(messages) > 0:
            $ message += '...'

        $ speak(speaker_title, message)

    return
