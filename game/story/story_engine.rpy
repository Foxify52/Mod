# Story mode — engine.
#
# The AI chat window (label story_chat), day checkpoints, and the Act 1
# driver. Scripted scenes call story_chat at one-on-one moments: the player
# types as the protagonist, the girl replies through the local Ollama model
# (protocol: [FACE] emotion [CONTENT] text [END]) while steering toward the
# scene's goal. When AI is unavailable the window is skipped entirely, so
# the story is always completable fully scripted.

init python:
    import copy
    import re
    import threading

    # Original say characters, defined in game/definitions.rpy
    STORY_SPEAKERS = {"sayori": "s", "natsuki": "n", "yuri": "y", "monika": "m"}

    # Routing state snapshotted by day checkpoints. Values are plain
    # lists/strings/bools/None — safe to deep-copy and pickle.
    STORY_VARS = (
        "chapter",
        "poemwinner",
        "s_appeal", "n_appeal", "y_appeal", "m_appeal",
        "s_poemappeal", "n_poemappeal", "y_poemappeal", "m_poemappeal",
        "ch1_choice", "ch2_winner",
        "help_sayori", "help_monika",
        "ch4_scene", "ch4_name",
        "sayori_confess",
        "n_exclusivewatched", "y_exclusivewatched",
        "y_gave", "y_ranaway",
        "n_read3", "y_read3", "n_poemearly",
    )

    STORY_VAR_DEFAULTS = {
        "chapter": 0,
        "poemwinner": ["sayori", "sayori", "sayori"],
        "s_appeal": 0, "n_appeal": 0, "y_appeal": 0, "m_appeal": 0,
        "s_poemappeal": [0, 0, 0], "n_poemappeal": [0, 0, 0],
        "y_poemappeal": [0, 0, 0], "m_poemappeal": [0, 0, 0],
        "ch1_choice": "sayori",
        "ch2_winner": "Yuri",
        "help_sayori": None, "help_monika": None,
        "ch4_scene": "yuri", "ch4_name": "Yuri",
        "sayori_confess": True,
        "n_exclusivewatched": False, "y_exclusivewatched": False,
        "y_gave": False, "y_ranaway": False,
        "n_read3": False, "y_read3": False, "n_poemearly": False,
    }


    def story_ai_available():
        """True when Ollama is reachable and a chat model is configured."""
        if not persistent.chatModel or persistent.chatModel == "None":
            return False
        return ollama_list_models() != "off"


    def story_reset_vars():
        for key, value in STORY_VAR_DEFAULTS.items():
            setattr(store, key, copy.deepcopy(value))


    def story_checkpoint(day):
        """Snapshot routing state at the start of a story day."""
        snap = {k: copy.deepcopy(getattr(store, k)) for k in STORY_VARS}
        # Always assign a fresh dict: Ren'Py only reliably notices persistent
        # changes on attribute assignment, not in-place mutation
        persistent.story_checkpoint = {"day": day, "vars": snap}
        renpy.save_persistent()


    def story_restore_checkpoint():
        checkpoint = persistent.story_checkpoint or {}
        for key, value in checkpoint.get("vars", {}).items():
            setattr(store, key, copy.deepcopy(value))


    class StoryChat:
        """One AI conversation window: builds the prompt, runs generations on
        a worker thread, and parses [FACE]/[CONTENT] replies."""

        def __init__(self, girl, context, goal):
            self.girl = girl
            self.goal = goal
            self.is_generating = False
            self.raw_result = None

            emotes = ", ".join(game_configs.story_sprites.get(girl, {}))
            persona = game_configs.story_prompts[girl]
            rules = game_configs.story_prompts["format"]

            system = persona
            if context:
                system += "\nCURRENT SCENE\n" + context
            system += "\nYOUR GOAL\n" + goal
            system += rules
            system = system.replace("{{user}}", persistent.playername)
            system = system.replace("{{emotes}}", emotes)

            self.messages = [{"role": "system", "content": system}]

        def generate(self, user_msg):
            """Worker-thread entry: one chat completion for user_msg."""
            self.raw_result = None
            try:
                reply = TextModel().getLLM(
                    self.messages + [{"role": "user", "content": user_msg}]
                )
                if isinstance(reply, tuple):  # (False, "<|Error|> ...")
                    reply = reply[1]
                self.raw_result = reply
            except Exception as e:
                self.raw_result = f"<|Error|> {e}"
            finally:
                self.is_generating = False

        def parse(self):
            """Returns (ok, emotion_or_None, text). ok=False means the reply
            broke the format (text then holds a cleaned-up fallback)."""
            raw = (self.raw_result or "").strip()

            if raw.startswith("<|Error|>"):
                raise OllamaError(raw.replace("<|Error|>", "").strip())

            emotion = None
            match = re.search(r"\[FACE\]\s*(.+?)\s*\[CONTENT\]", raw, re.S)
            if match:
                emotion = match.group(1).strip().lower()

            if "[CONTENT]" in raw:
                text = raw.split("[CONTENT]", 1)[1]
            else:
                text = raw

            text = text.split("[END]")[0]
            text = re.sub(r"\[.*?\]", "", text)
            text = re.sub(r"\*.*?\*", "", text).strip()

            ok = "[CONTENT]" in raw and bool(text)
            return ok, emotion, text

        def commit_turn(self, user_msg):
            """Store the finished exchange so later turns keep the context.
            The assistant side keeps its tags — models hold the format better
            when the history demonstrates it."""
            self.messages.append({"role": "user", "content": user_msg})
            self.messages.append({"role": "assistant", "content": self.raw_result or ""})


    def story_opinion_phrase(opinion):
        """Turns a poemresponse opinion into prompt text for the chat window."""
        return {
            "bad": "you didn't really care for it",
            "good": "you genuinely loved it",
        }.get(opinion, "you thought it was a decent effort")


    def story_show_emotion(girl, emotion, position="t11", outfit=""):
        """Switch the girl's sprite to the tag mapped for `emotion`.
        `outfit` is a letter spliced in after the pose digit ("b" turns
        sayori 1a into sayori 1ba for the casual/bedroom set)."""
        sprites = game_configs.story_sprites.get(girl, {})
        tag = sprites.get(emotion) or sprites.get("neutral")
        if tag and outfit:
            for candidate_emotion in (emotion, "neutral"):
                base = sprites.get(candidate_emotion)
                if not base:
                    continue
                candidate = re.sub(r"^(\d+)", r"\g<1>" + outfit, base)
                if renpy.has_image(f"{girl} {candidate}", exact=True):
                    tag = candidate
                    break
            else:
                return  # nothing in this outfit; keep the current sprite
        if tag:
            renpy.show(f"{girl} {tag}", at_list=[getattr(store, position)], zorder=2)


    def story_speak(girl, text):
        """Say a (possibly long) reply as the girl, via the original
        say characters, in textbox-sized chunks."""
        character = getattr(store, STORY_SPEAKERS[girl])
        # Escape interpolation/tag characters the model may emit
        text = text.replace("[", "[[").replace("{", "{{")
        chunks = string_splitter(text, 255)
        while chunks:
            message = chunks.pop()
            if chunks:
                message += "..."
            character(message)


################################################################################
## The AI chat window
################################################################################

# Free-form conversation with one girl. The caller has already staged the
# scene (background, sprite, music); this label runs `turns` player inputs,
# then lets the player keep the conversation going for as long as they like
# before returning to the scripted closer. No-ops when AI is off.

label story_chat(girl, goal, context="", turns=3, position="t11", outfit=""):
    if not story_ai_enabled:
        return

    $ config.skipping = False
    $ story_chat_obj = StoryChat(girl, context, goal)
    $ story_turn = 0

    while True:
        $ story_turn += 1

        # Past the scene's planned exchanges the player sets the pace
        if story_turn > turns:
            menu:
                "Keep talking.":
                    pass
                "Let the story continue.":
                    return

        $ story_user_msg = ""

        while story_user_msg.strip() == "":
            $ story_user_msg = renpy.input("What do you say?")

        $ mc("[story_user_msg!q] {fast} {nw}")

        # From the planned final exchange onward, nudge the model to keep
        # steering toward the scene's beat
        $ story_sent_msg = story_user_msg
        if story_turn >= turns:
            $ story_sent_msg += game_configs.story_prompts["wrapup"].replace("{{goal}}", story_chat_obj.goal)

        $ story_reply = None

        # Two attempts: plain, then with a format reminder appended
        $ story_attempt = 0
        while story_attempt < 2 and story_reply is None:
            $ story_attempt += 1
            $ story_attempt_msg = story_sent_msg if story_attempt == 1 else story_sent_msg + game_configs.story_prompts["reminder"]

            $ story_chat_obj.is_generating = True
            $ threading.Thread(target=story_chat_obj.generate, args=(story_attempt_msg,)).start()
            $ story_wait = ""
            while story_chat_obj.is_generating:
                $ story_wait = story_wait + "." if len(story_wait) < 3 else "."
                "Loading[story_wait] {fast} {w=0.7}{nw}"

            python:
                try:
                    story_parse_ok, story_emotion, story_text = story_chat_obj.parse()
                except OllamaError as e:
                    # Connection/model trouble mid-scene: drop back to the script
                    story_ai_enabled = False
                    renpy.notify("Connection to the AI was lost — continuing the story.")
                    renpy.log(f">>> story_chat aborted: {e}")
                    story_parse_ok, story_emotion, story_text = False, None, None

                if story_text and (story_parse_ok or story_attempt == 2):
                    story_reply = story_text
                elif story_parse_ok is False and story_text:
                    renpy.log(f">>> story_chat retrying, bad format: {story_chat_obj.raw_result!r}")

            if not story_ai_enabled:
                return

        if story_reply is None:
            # Both attempts produced nothing usable; bow out gracefully
            $ story_ai_enabled = False
            $ renpy.notify("The AI stopped responding — continuing the story.")
            return

        $ story_chat_obj.commit_turn(story_user_msg)
        $ story_show_emotion(girl, story_emotion, position, outfit)
        $ story_speak(girl, story_reply)
        $ renpy.block_rollback()

    return


################################################################################
## Entry points and the Act 1 driver
################################################################################

label story_start:
    if not renpy.has_label("ch0_main"):
        # Chapters land in a later phase; keep the button safe until then
        show screen basic_popup(title="Original Story", message="The story content is still under construction. Check back in the next update!", ok_action=Hide("basic_popup"))
        return

    $ story_reset_vars()
    $ persistent.story_checkpoint = None
    $ renpy.save_persistent()
    call story_session_setup
    call story_day(0)
    return


label story_continue:
    if persistent.story_checkpoint is None or not renpy.has_label("ch0_main"):
        jump story_start

    $ story_restore_checkpoint()
    $ story_resume_day = persistent.story_checkpoint["day"]
    call story_session_setup
    call story_day(story_resume_day)
    return


label story_session_setup:
    $ persistent.in_game = True
    $ renpy.save_persistent()
    stop music fadeout 0.5
    $ story_ai_enabled = story_ai_available()
    if not story_ai_enabled:
        $ renpy.notify("AI chat is offline — the story will play fully scripted.")
    return


# One pass through Act 1 from the given day. Chapters/poem labels are called
# by name (call expression) — they arrive in later phases.
label story_day(day=0):
    if day <= 0:
        $ chapter = 0
        $ story_checkpoint(0)
        call expression "ch0_main"
        call expression "poem"

    if day <= 1:
        $ chapter = 1
        $ story_checkpoint(1)
        call expression "ch1_main"
        call expression "poemresponse_start"
        call expression "ch1_end"
        call expression "poem"

    if day <= 2:
        $ chapter = 2
        $ story_checkpoint(2)
        call expression "ch2_main"
        call expression "poemresponse_start"
        call expression "ch2_end"
        call expression "poem"

    if day <= 3:
        $ chapter = 3
        $ story_checkpoint(3)
        call expression "ch3_main"
        call expression "poemresponse_start"
        call expression "ch3_end"

    if day <= 4:
        $ chapter = 4
        $ story_checkpoint(4)
        call expression "ch4_main"

    if day <= 5:
        $ chapter = 5
        $ story_checkpoint(5)
        call expression "ch5_main"

    jump story_act1_outro


label story_act1_outro:
    $ persistent.story_checkpoint = None
    $ persistent.story_act1_done = True
    $ renpy.save_persistent()

    stop music fadeout 2.0
    scene black with dissolve_scene_full
    $ renpy.pause(1.5, hard=True)

    "To be continued..."

    call endgame
    $ renpy.full_restart()
    return
