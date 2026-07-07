# Story mode — the nightly poem minigame.
#
# Ported from the original script-poemgame.rpy with the Act-1 path only.
# The original built its word grid with the ui.* widget functions, which
# Ren'Py 8 removed — the grid is rebuilt as a screen. New for this mod: the
# player may instead write their own poem and have the AI judge which girl
# it appeals to (with deterministic word-list scoring as the fallback).
#
# Scoring/routing is identical to the original: 20 picks accumulate hidden
# per-girl points; the highest total wins poemwinner[chapter] and +1 appeal;
# per-girl poemappeal is -1/0/+1 against the 29/45 thresholds.

init python:
    import random
    import re
    import threading


    class PoemWord:
        def __init__(self, word, sPoint, nPoint, yPoint):
            self.word = word
            self.sPoint = sPoint
            self.nPoint = nPoint
            self.yPoint = yPoint


    POEM_DISLIKE_THRESHOLD = 29
    POEM_LIKE_THRESHOLD = 45

    full_wordlist = []
    with renpy.open_file("assets/configs/poemwords.txt", encoding="utf-8") as wordfile:
        for line in wordfile:
            line = line.strip()
            if line == "" or line[0] == "#":
                continue
            x = line.split(",")
            full_wordlist.append(PoemWord(x[0], float(x[1]), float(x[2]), float(x[3])))


    # Sticker (chibi) wander-animation state, driven by the ATL functions below
    sayoriTime = renpy.random.random() * 4 + 4
    natsukiTime = renpy.random.random() * 4 + 4
    yuriTime = renpy.random.random() * 4 + 4
    sayoriPos = 0
    natsukiPos = 0
    yuriPos = 0
    sayoriOffset = 0
    natsukiOffset = 0
    yuriOffset = 0
    sayoriZoom = 1
    natsukiZoom = 1
    yuriZoom = 1


    def randomPauseSayori(trans, st, at):
        global sayoriTime
        if st > sayoriTime:
            sayoriTime = renpy.random.random() * 4 + 4
            return None
        return 0


    def randomPauseNatsuki(trans, st, at):
        global natsukiTime
        if st > natsukiTime:
            natsukiTime = renpy.random.random() * 4 + 4
            return None
        return 0


    def randomPauseYuri(trans, st, at):
        global yuriTime
        if st > yuriTime:
            yuriTime = renpy.random.random() * 4 + 4
            return None
        return 0


    def randomMoveSayori(trans, st, at):
        global sayoriPos
        global sayoriOffset
        global sayoriZoom
        if st > 0.16:
            if sayoriPos > 0:
                sayoriPos = renpy.random.randint(-1, 0)
            elif sayoriPos < 0:
                sayoriPos = renpy.random.randint(0, 1)
            else:
                sayoriPos = renpy.random.randint(-1, 1)
            if trans.xoffset * sayoriPos > 5:
                sayoriPos *= -1
            return None
        if sayoriPos > 0:
            trans.xzoom = -1
        elif sayoriPos < 0:
            trans.xzoom = 1
        trans.xoffset += 0.16 * 10 * sayoriPos
        sayoriOffset = trans.xoffset
        sayoriZoom = trans.xzoom
        return 0


    def randomMoveNatsuki(trans, st, at):
        global natsukiPos
        global natsukiOffset
        global natsukiZoom
        if st > 0.16:
            if natsukiPos > 0:
                natsukiPos = renpy.random.randint(-1, 0)
            elif natsukiPos < 0:
                natsukiPos = renpy.random.randint(0, 1)
            else:
                natsukiPos = renpy.random.randint(-1, 1)
            if trans.xoffset * natsukiPos > 5:
                natsukiPos *= -1
            return None
        if natsukiPos > 0:
            trans.xzoom = -1
        elif natsukiPos < 0:
            trans.xzoom = 1
        trans.xoffset += 0.16 * 10 * natsukiPos
        natsukiOffset = trans.xoffset
        natsukiZoom = trans.xzoom
        return 0


    def randomMoveYuri(trans, st, at):
        global yuriPos
        global yuriOffset
        global yuriZoom
        if st > 0.16:
            if yuriPos > 0:
                yuriPos = renpy.random.randint(-1, 0)
            elif yuriPos < 0:
                yuriPos = renpy.random.randint(0, 1)
            else:
                yuriPos = renpy.random.randint(-1, 1)
            if trans.xoffset * yuriPos > 5:
                yuriPos *= -1
            return None
        if yuriPos > 0:
            trans.xzoom = -1
        elif yuriPos < 0:
            trans.xzoom = 1
        trans.xoffset += 0.16 * 10 * yuriPos
        yuriOffset = trans.xoffset
        yuriZoom = trans.xzoom
        return 0


    def poem_word_score(text):
        """Deterministic fallback: score a written poem against the word
        list. Returns (sTotal, nTotal, yTotal)."""
        tokens = re.findall(r"[a-zA-Z']+", text.lower())
        s = n = y = 0.0
        for pw in full_wordlist:
            if pw.word.lower() in tokens:
                s += pw.sPoint
                n += pw.nPoint
                y += pw.yPoint
        return s, n, y


    def poem_judge_worker(text):
        """Worker thread: ask the model which girl the poem appeals to.
        Leaves the winner name (or None) in store.poem_judge_result."""
        winner = None
        try:
            reply = TextModel().getLLM([
                {"role": "system", "content": game_configs.story_prompts["judge"]},
                {"role": "user", "content": text},
            ])
            if isinstance(reply, tuple):  # (False, "<|Error|> ...")
                reply = ""
            reply = reply.lower()
            winner = next((g for g in ("sayori", "natsuki", "yuri") if g in reply), None)
        except Exception as e:
            renpy.log(f">>> poem judge failed: {e}")
        finally:
            poem_judge_result["winner"] = winner
            poem_judge_result["done"] = True


    def apply_poem_scores(sPointTotal, nPointTotal, yPointTotal):
        """The original post-game scoring: winner, appeal, per-girl reactions."""
        totals = {"sayori": sPointTotal, "natsuki": nPointTotal, "yuri": yPointTotal}

        # Siding with a girl in the ch1 fight nudges her next poem score
        if chapter == 1:
            initial_map = {"s": "sayori", "n": "natsuki", "y": "yuri"}
            totals[initial_map[ch1_choice[0]]] += 5

        winner = sorted(totals, key=totals.get)[-1]
        poemwinner[chapter] = winner
        setattr(store, winner[0] + "_appeal", getattr(store, winner[0] + "_appeal") + 1)

        for girl, total in totals.items():
            appeal = getattr(store, girl[0] + "_poemappeal")
            if total < POEM_DISLIKE_THRESHOLD:
                appeal[chapter] = -1
            elif total > POEM_LIKE_THRESHOLD:
                appeal[chapter] = 1

        getattr(store, winner[0] + "_poemappeal")[chapter] = 1


default poem_judge_result = {"done": True, "winner": None}


# The word grid: two columns of five picks, replacing the original's
# removed ui.* construction. Returns the chosen PoemWord.
screen poemgame_screen(progress, numwords, page_words):
    text "[progress]/[numwords]" style "poemgame_text" xpos 810 ypos 80 color "#000"

    for j, column in enumerate((page_words[:5], page_words[5:])):
        for i, w in enumerate(column):
            textbutton "[w.word]":
                action Return(w)
                text_style "poemgame_text"
                background None
                xpos (440 if j == 0 else 680)
                ypos (i * 56 + 160)


label poem(transition=True):
    stop music fadeout 2.0

    scene bg notebook
    show s_sticker at sticker_left
    show n_sticker at sticker_mid
    show y_sticker at sticker_right

    if transition:
        with dissolve_scene_full

    play music t4

    $ config.skipping = False
    $ config.allow_skipping = False
    $ allow_skipping = False

    if chapter == 0:
        call screen dialog("It's time to write a poem!\n\nPick words you think your favorite club member\nwill like. Something good might happen with\nwhoever likes your poem the most!", ok_action=Return())

label poem_mode_menu:
    menu:
        "How should I write tonight's poem?"

        "Pick the words for it.":
            jump poem_words

        "Write it in my own words.":
            jump poem_freeform


################################################################################
## Original word-picker
################################################################################

label poem_words:
    python:
        progress = 1
        numWords = 20
        sPointTotal = 0
        nPointTotal = 0
        yPointTotal = 0
        wordlist = list(full_wordlist)

        sayoriTime = renpy.random.random() * 4 + 4
        natsukiTime = renpy.random.random() * 4 + 4
        yuriTime = renpy.random.random() * 4 + 4
        sayoriPos = renpy.random.randint(-1, 1)
        natsukiPos = renpy.random.randint(-1, 1)
        yuriPos = renpy.random.randint(-1, 1)
        sayoriOffset = 0
        natsukiOffset = 0
        yuriOffset = 0
        sayoriZoom = 1
        natsukiZoom = 1
        yuriZoom = 1

        while True:
            page_words = []
            for i in range(10):
                word = random.choice(wordlist)
                wordlist.remove(word)
                page_words.append(word)

            t = renpy.call_screen(
                "poemgame_screen",
                progress=progress,
                numwords=numWords,
                page_words=page_words,
            )

            renpy.play(gui.activate_sound)
            if t.sPoint >= 3:
                renpy.show("s_sticker hop")
            if t.nPoint >= 3:
                renpy.show("n_sticker hop")
            if t.yPoint >= 3:
                renpy.show("y_sticker hop")

            sPointTotal += t.sPoint
            nPointTotal += t.nPoint
            yPointTotal += t.yPoint
            progress += 1
            if progress > numWords:
                break

        apply_poem_scores(sPointTotal, nPointTotal, yPointTotal)

    jump poem_done


################################################################################
## Write-your-own poem (AI-judged, word-list fallback)
################################################################################

label poem_freeform:
    $ poem_text = renpy.input(prompt="Write tonight's poem:", default="", exclude="{[", screen="input_long", multiline=True).strip()

    if poem_text == "":
        "I stare at the blank page for a while, but nothing comes out..."
        jump poem_mode_menu

    $ poem_winner_name = None

    if story_ai_enabled:
        $ poem_judge_result = {"done": False, "winner": None}
        $ threading.Thread(target=poem_judge_worker, args=(poem_text,)).start()
        $ poem_wait = ""
        while not poem_judge_result["done"]:
            $ poem_wait = poem_wait + "." if len(poem_wait) < 3 else "."
            "Reading it back to myself[poem_wait] {fast} {w=0.7}{nw}"
        $ poem_winner_name = poem_judge_result["winner"]

    if poem_winner_name == None:
        # AI off or unparseable verdict: score the poem's own words instead
        python:
            ws, wn, wy = poem_word_score(poem_text)
            word_totals = {"sayori": ws, "natsuki": wn, "yuri": wy}
            poem_winner_name = sorted(word_totals, key=word_totals.get)[-1]

    # Map the verdict onto totals the original thresholds understand:
    # the winner clearly likes it, the others find it just okay
    python:
        judged = {"sayori": 36, "natsuki": 36, "yuri": 36}
        judged[poem_winner_name] = 60
        renpy.show(poem_winner_name[0] + "_sticker hop")
        renpy.play(gui.activate_sound)
        apply_poem_scores(judged["sayori"], judged["natsuki"], judged["yuri"])

    "There. It's not much, but it's honest."

    jump poem_done


label poem_done:
    $ config.allow_skipping = True
    $ allow_skipping = True
    stop music fadeout 2.0

    show black as fadeout:
        alpha 0
        linear 1.0 alpha 1.0

    $ pause(1.0)
    return


################################################################################
## Stickers (chibi word-reaction sprites) — art lives in base images.rpa
################################################################################

image s_sticker:
    "gui/poemgame/s_sticker_1.png"
    xoffset sayoriOffset xzoom sayoriZoom
    block:
        function randomPauseSayori
        parallel:
            sticker_move_n
        parallel:
            function randomMoveSayori
        repeat
image n_sticker:
    "gui/poemgame/n_sticker_1.png"
    xoffset natsukiOffset xzoom natsukiZoom
    block:
        function randomPauseNatsuki
        parallel:
            sticker_move_n
        parallel:
            function randomMoveNatsuki
        repeat
image y_sticker:
    "gui/poemgame/y_sticker_1.png"
    xoffset yuriOffset xzoom yuriZoom
    block:
        function randomPauseYuri
        parallel:
            sticker_move_n
        parallel:
            function randomMoveYuri
        repeat
image s_sticker hop:
    "gui/poemgame/s_sticker_2.png"
    xoffset sayoriOffset xzoom sayoriZoom
    sticker_hop
    xoffset 0 xzoom 1
    "s_sticker"
image n_sticker hop:
    "gui/poemgame/n_sticker_2.png"
    xoffset natsukiOffset xzoom natsukiZoom
    sticker_hop
    xoffset 0 xzoom 1
    "n_sticker"
image y_sticker hop:
    "gui/poemgame/y_sticker_2.png"
    xoffset yuriOffset xzoom yuriZoom
    sticker_hop
    xoffset 0 xzoom 1
    "y_sticker"

transform sticker_left:
    subpixel True xcenter 100 yalign 0.9
transform sticker_mid:
    subpixel True xcenter 220 yalign 0.9
transform sticker_right:
    subpixel True xcenter 340 yalign 0.9
transform sticker_move_n:
    easein_quad .08 yoffset -15
    easeout_quad .08 yoffset 0
transform sticker_hop:
    easein_quad .18 yoffset -80
    easeout_quad .18 yoffset 0
    easein_quad .18 yoffset -80
    easeout_quad .18 yoffset 0
