# Data access for realms (chat folders) and game configuration.
#
# Shipped JSON is read through Ren'Py's loader so it keeps working when the
# mod is packed into .rpa archives. User-content folders (custom characters,
# custom prompts) are loose on disk by design and are enumerated with os.
init -6 python:
    import os
    import json
    import re
    import copy
    import binascii


    def _read_game_json(path):
        """Read a shipped JSON file through Ren'Py's loader (works from .rpa
        archives and loose files alike)."""
        with renpy.open_file(path) as f:
            return json.load(f)


    def _read_user_json_dir(dir_path):
        """Merge every *.json in a loose user-content folder into one dict."""
        combined = {}
        try:
            filenames = sorted(os.listdir(dir_path))
        except OSError:
            return combined

        for filename in filenames:
            if not filename.endswith(".json"):
                continue
            try:
                with open(os.path.join(dir_path, filename), "r", encoding="utf-8") as f:
                    combined.update(json.load(f))
            except (OSError, ValueError):
                renpy.log(f">>> ignored invalid user config: {filename}")
        return combined


    class ConfigCache:
        """Every shipped + user JSON config, loaded once at startup.
        Call reload() after anything writes to the user config folders."""

        CUSTOM_CHARS_DIR = "assets/configs/custom_characters"
        CUSTOM_PROMPTS_DIR = "assets/prompts/custom_prompts"

        def __init__(self):
            self.reload()

        def reload(self):
            self.bg_scenes = _read_game_json("assets/configs/bg_scenes.json")
            self.purgatory_lines = _read_game_json("assets/configs/purgatory_lines.json")
            self.tutorials = _read_game_json("assets/configs/tutorials.json")
            self.reminder = _read_game_json("assets/prompts/reminder.json")
            self.prompt_format = _read_game_json("assets/prompts/prompt_format.json")
            self.example_prompts = _read_game_json("assets/prompts/prompt_templates.json")

            # Story mode: Act-1 personas and emotion -> sprite-tag maps
            self.story_prompts = _read_game_json("assets/prompts/story_prompts.json")
            self.story_sprites = _read_game_json("assets/prompts/story_sprites.json")

            # Shipped characters load first so user files can override them
            self.characters = _read_game_json("assets/configs/characters.json")
            self.characters.update(
                _read_user_json_dir(os.path.join(config.gamedir, self.CUSTOM_CHARS_DIR))
            )

            self.custom_prompts = _read_user_json_dir(
                os.path.join(config.gamedir, self.CUSTOM_PROMPTS_DIR)
            )


    game_configs = ConfigCache()


    def reload_configs():
        game_configs.reload()

init python:
    class Data:
        """File-backed access to one realm's chat history and scene data."""

        def __init__(self, path_to_user_dir):
            self.path_to_user_dir = path_to_user_dir

        @property
        def getLastMessage(self):
            with open(self.path_to_user_dir + "/chathistory.json", "r") as f:
                last_msg = json.load(f)[-1]["content"]

            try:
                last_msg = "[SCENE]" + last_msg.split("[SCENE]")[1]
            except IndexError:
                pass

            return last_msg

        @property
        def getChathistory(self):
            with open(self.path_to_user_dir + "/chathistory.json", "r") as f:
                return json.load(f)

        @property
        def getLastMessageClean(self):
            with open(self.path_to_user_dir + "/chathistory.json", "r") as f:
                reply = json.load(f)[-1]["content"]

            reply = reply.replace("[END]", "")
            if "[CONTENT]" in reply:
                reply = reply.split("[CONTENT]", 1)[1]

            # Strip any leftover [tags] / *actions* a model may have emitted
            reply = re.sub(r"\[.*?\]", "", reply)
            reply = re.sub(r"\*.*?\*", "", reply)
            return reply.strip()

        def getSceneData(self, key):
            try:
                with open(self.path_to_user_dir + "/scenedata.json", "r") as f:
                    return json.load(f).get(key)
            except (TypeError, FileNotFoundError, json.JSONDecodeError):
                return None

        def updateSceneData(self, key, value):
            with open(self.path_to_user_dir + "/scenedata.json", "r") as f:
                scenedata = json.load(f)

            scenedata[key] = value

            with open(self.path_to_user_dir + "/scenedata.json", "w") as f:
                json.dump(scenedata, f, indent=2)
            return value


    class Configs:
        @property
        def bg_scenes(self):
            return game_configs.bg_scenes

        @property
        def characters(self):
            return game_configs.characters

        def body_types(self, name):
            char_conf = game_configs.characters.get(name.title(), {})
            raw_bodies = list(char_conf.get("left", {})) + list(char_conf.get("right", {}))
            body_descriptions = game_configs.reminder.get("bodies", {})

            seen = []
            body_examples = []
            for part in raw_bodies:
                if part not in seen:
                    seen.append(part)
                    example = body_descriptions.get(part, "").replace(
                        "{{char}}", name.title()
                    )
                    body_examples.append(part + example)

            return " and ".join(body_examples)

        def listCharEmotes(self, name):
            return ", ".join(game_configs.characters.get(name, {}).get("head", {}))

        def create_from_hex(self, game_relative_input, output_path):
            """Decode a hex-encoded shipped asset into a loose runtime file.
            The input is read through the loader so it can live in an .rpa."""
            with renpy.open_file(game_relative_input) as hex_file:
                hex_data = hex_file.read().strip()

            binary_data = binascii.unhexlify(hex_data)

            with open(output_path, "wb") as output_file:
                output_file.write(binary_data)

        def delete_egg(self, path):
            try:
                os.remove(path)
            except OSError:
                pass

        def update_character_backstory(self, character, backstory):
            """Save a backstory edit as a user override in the loose
            custom-prompts folder. Shipped templates are never modified."""
            dir_path = os.path.join(config.gamedir, ConfigCache.CUSTOM_PROMPTS_DIR)
            os.makedirs(dir_path, exist_ok=True)
            path = os.path.join(dir_path, f"{character}.json")

            # Keep whatever else the user already has in that file
            existing = {}
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (OSError, ValueError):
                pass

            entry = existing.get(character) or [{"role": "system", "content": ""}]
            entry[0]["content"] = f"BACKSTORY {backstory}\n" + "{{format}}"
            existing[character] = entry

            with open(path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)

            renpy.log(f">>> backstory override saved: {path}")
            reload_configs()


    class Info:
        @property
        def getExamplePrompts(self):
            # Deep copy: callers fill in placeholders on the returned template
            return copy.deepcopy(game_configs.example_prompts)

        @property
        def getCustomPrompts(self):
            return copy.deepcopy(game_configs.custom_prompts)

        def get_prompt(self, character_name):
            """Prompt template for a character — user overrides beat shipped."""
            if character_name in game_configs.custom_prompts:
                return copy.deepcopy(game_configs.custom_prompts[character_name])
            return copy.deepcopy(game_configs.example_prompts[character_name])

        @property
        def getReminder(self):
            return game_configs.reminder

        @property
        def getSpaceLines(self):
            return game_configs.purgatory_lines

        @property
        def format(self):
            return game_configs.prompt_format

        @property
        def whitelist_purgatory(self):
            return ["monika"]

        def full_sprites_check(self, name, current_head_sprite):
            char_conf = game_configs.characters.get(name, {})
            heads = char_conf.get("head", {})
            full_sprites = [
                heads[s] for s in char_conf.get("full_sprites", []) if s in heads
            ]
            return current_head_sprite in full_sprites
