init -5 python:
    class OllamaImages:
        def __init__(self, image, desc):
            self.image = image
            self.desc = desc


    def image_list():
        return [
            OllamaImages(step["image"], step["desc"])
            for step in game_configs.tutorials["ollama"]
        ]

define tutorial_images = image_list()
default tutorial_index = 0
default current_tutorial_image = tutorial_images[0]

init -4 python:
    def update_image(new_index):
        store.tutorial_index = new_index
        store.current_tutorial_image = tutorial_images[new_index]

screen tutorial_screen():
    tag menu
    add "menu_bg"
    vbox:
        xalign 0.4
        yalign 0.5
        add current_tutorial_image.image:
            xalign 0.0
            yalign 0.6
            zoom 0.75
        hbox:
            style_prefix "arrows"
            xalign 0.5
            yalign 0.97
            spacing 20
            textbutton "<":
                action If(
                tutorial_index > 0,
                true=Function(update_image, tutorial_index - 1),
                false=Function(update_image, len(tutorial_images) - 1)
            )
            text "Page [tutorial_index]":
                style "character_name_style"
            textbutton ">":
                action If(
                tutorial_index < len(tutorial_images) - 1,
                true=Function(update_image, tutorial_index + 1),
                false=Function(update_image, 0)
            )
    null:
        width 30
    frame:
        background "assets/imgs/gui/bio_box.png"
        xalign 1
        yalign 0.4
        padding (790, 130, 160, 220)
        vbox:
            xfill True
            box_wrap True
            viewport:
                scrollbars "vertical"
                mousewheel True
                draggable True
                text "[current_tutorial_image.desc]":
                    size 22
                    justify True
    textbutton _("Return"):
        style "return_button"
        action Return()
# Main Image and arrows underneath
# Nav buttons
# Description section
# Image info
