label apikey_label:
    $ apikey = renpy.input("Enter API Key", f"{persistent.chatToken}").strip()
    $ persistent.chatToken = apikey
    $ renpy.save_persistent()
    return

label custom_chat_model_label:
    "Enter a model from your ollama list"

    "You can check what models you have available by typing \\"

    $ model = renpy.input("Enter a model", f"{persistent.chatModel}").strip()
    $ persistent.chatModel = model
    $ renpy.save_persistent()
    return

label custom_backstory_label:
    "Enter your own backstory for this character. Your edit is saved to \\"

    $ raw_prompt = Info().get_prompt(character_name)[0]["content"].split("{{format}}")[0].replace("BACKSTORY", "").strip()
    $ player_prompt = renpy.input(prompt=" ", default=f"{raw_prompt}", exclude="}{", screen="input_long").strip()
    $ Configs().update_character_backstory(character=character_name, backstory=player_prompt)
    "Successfully changed backstory!"

    return

label setup_model_label:
    menu:
        "Would you like a tutorial on how to download a model? Or simply download a model now?"
        "Tutorial":
            jump tutorial_label
        "Download Model":
            jump download_model_label

label tutorial_label:
    call screen tutorial_screen
    return

init python:
    def download_model(model_name):
        global is_downloading
        global download_progress
        global download_text

        is_downloading = True
        download_progress = ""
        download_text = ""

        def on_progress(text):
            global download_progress
            download_progress = text

        try:
            ollama_pull(model_name, on_progress)
            download_text = "done"
        except OllamaError as e:
            download_text = f"<|Error|> {e.message}"

        is_downloading = False

label download_model_label:
    "Enter the name of an AI model you want to download from ollama.com/library"

    $ model = renpy.input("Install a model").strip()
    $ renpy.invoke_in_thread(download_model, model)
    $ _history = False
    # Wait for download to finish

    while is_downloading == True:
        "[download_progress!q] {fast} {w=0.7}{nw}"

    # An Error happened, so stop the current session and return to lobby

    if download_text.startswith("<|Error|>"):
        $ download_text = download_text.replace("<|Error|>", "")
        show screen error_popup(message=download_text)
        "Returning to main menu..."

        return

    if download_text == "done":
        "Download Complete! Restart the game and select the model"

    return
