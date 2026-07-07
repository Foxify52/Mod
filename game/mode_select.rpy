# Game-mode selection, shown after pressing New Game.
#
# Sandbox    -> the existing free-form AI chat (character select first)
# Story Mode -> Original Story: the original plot + horror, AI-guided so the
#               player speaks freely but the story stays on track. A Continue
#               button appears when a day checkpoint exists.
#               Traditional VN: revised horror-free romance routes for any of
#               the four club members. Placeholder for now.
screen mode_select_screen():
    tag menu
    add "menu_bg"
    vbox:
        xalign 0.5
        yalign 0.4
        spacing 30
        text _("How do you want to play?"):
            style "mode_title"
            xalign 0.5
        null:
            height 20
        textbutton _("Sandbox"):
            action Return("sandbox")
            xalign 0.5
            style "mode_button"
        textbutton _("Story Mode"):
            action Return("story")
            xalign 0.5
            style "mode_button"
    textbutton _("Return"):
        style "return_button"
        action Return("back")

screen story_select_screen():
    tag menu
    add "menu_bg"
    vbox:
        xalign 0.5
        yalign 0.4
        spacing 30
        text _("Story Mode"):
            style "mode_title"
            xalign 0.5
        null:
            height 20
        textbutton _("Original Story (Experimental)"):
            xalign 0.5
            style "mode_button"
            action Return("original_new")
        if persistent.story_checkpoint:
            textbutton _("Continue (Day [persistent.story_checkpoint['day'] + 1])"):
                xalign 0.5
                style "mode_button"
                action Return("original_continue")
        textbutton _("Traditional VN (Coming Soon)"):
            xalign 0.5
            style "mode_button"
            action Show(screen="basic_popup", title="Traditional VN", message="A revised, horror-free take on the story. A classic romance visual novel where you can pursue any of the four club members. Coming soon!", ok_action=Hide("basic_popup"))
    textbutton _("Back"):
        style "return_button"
        action Return("back")

style mode_title:
    color "#fff"
    font "gui/font/RifficFree-Bold.ttf"
    outlines [(4, "#000", 0, 0), (2, "#000", 2, 2)]
    size 45
style mode_button is gui_button
style mode_button_text is gui_button_text
style mode_button:
    activate_sound "gui/sfx/select.ogg"
    hover_sound "gui/sfx/hover.ogg"
    properties gui.button_properties("mode_button")
style mode_button_text:
    color "#fff"
    font "gui/font/RifficFree-Bold.ttf"
    hover_outlines [(4, "#fac", 0, 0), (2, "#fac", 2, 2)]
    outlines [(4, "#000", 0, 0), (2, "#000", 2, 2)]
    properties gui.button_text_properties("mode_button")
    size 36
