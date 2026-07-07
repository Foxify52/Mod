init python:
    import json
    import os
    import random
    import re


    class AIManager:
        def __init__(self, character_name, chathistory, full_path, resume=False):
            self.character_name = character_name
            self.chathistory = chathistory
            self.full_path = full_path
            self.resume = resume
            self.NARRATION = False
            self.rnd = random.randint(1, 7)
            self.retrying = False
            self.dbase = Data(path_to_user_dir=self.full_path)

        def get_char_name(self, aireply):
            # WIP method that should be used when multiple
            # characters are speaking
            if "[CHAR]" in aireply:
                pass
            return self.character_name

        def controlMood(self, face, body):
            """Display different facial expressions"""
            spacezone = self.dbase.getSceneData("zone")
            if spacezone == "true":
                return self.dbase.updateSceneData("character", self.character_name)

            if not face or not body:
                return

            char_conf = Configs().characters.get(self.character_name.title())
            if char_conf is None:
                return

            full_sprite_emotions = char_conf[
                "full_sprites"
            ]  # dont render "left" or "right" body sprites if the face is one of these
            head_sprites = char_conf["head"]
            leftside_sprites = char_conf["left"]
            rightside_sprites = char_conf["right"]

            self.dbase.updateSceneData("character", self.character_name)

            face = face.lower()
            body = body.lower()

            if face in head_sprites:
                self.dbase.updateSceneData("head_sprite", head_sprites[face])

            # A full sprite already includes the body, so leave the side sprites alone
            if face in full_sprite_emotions:
                return

            if body in leftside_sprites:
                self.dbase.updateSceneData("left_sprite", leftside_sprites[body])

            if body in rightside_sprites:
                self.dbase.updateSceneData("right_sprite", rightside_sprites[body])

        def controlBackground(self, scene):
            """Display different background image"""
            if not scene:
                return

            bg_scenes = Configs().bg_scenes
            for key in ("default", "checks"):
                if scene in bg_scenes[key]:
                    return self.dbase.updateSceneData("background", bg_scenes[key][scene])

            return self.dbase.updateSceneData("background", bg_scenes["checks"]["clubroom"])

        def safeResponse(self, raw_response):
            """A response that's not entirely raw. If the AI
            speaks out of character but still returns the correct
            format, only capture the format it outputs"""
            clean_response = raw_response
            spacezone = self.dbase.getSceneData("zone")
            if "[SCENE]" in clean_response:
                clean_response = "[SCENE]" + clean_response.split("[SCENE]", 1)[1]
                # Some models emit a second full tag block in one reply;
                # keep only the first so history stays one block per turn
                second = clean_response.find("[SCENE]", 1)
                if second != -1:
                    clean_response = clean_response[:second]

            elif spacezone == "true" and "[CONTENT]" in clean_response:
                clean_response = (
                    "[CONTENT]" + clean_response.split("[CONTENT]", 1)[1].strip()
                )
                second = clean_response.find("[CONTENT]", 1)
                if second != -1:
                    clean_response = clean_response[:second]

            if "[CONTENT]" in clean_response:
                clean_response = re.sub(
                    r"\*.*?\*", "", clean_response
                )  # gets rid of anything in asterisks

            return clean_response

        def removeKeywords(self, reply):
            """Get rid of keywords and return a clean string"""

            def getContent(start, end, reply=reply):
                try:
                    content = reply.split(start)[1].split(end)[0].strip()
                    return content
                except IndexError:
                    return None
                except AttributeError:
                    return None

            char = getContent(
                "[CHAR]", "[CONTENT]"
            )  # Currently unused, just a placeholder once the usage of multiple chars is implemented
            face = getContent("[FACE]", "[BODY]")
            body = getContent("[BODY]", "[CONTENT]")
            scene = getContent("[SCENE]", "[FACE]")

            reply = reply.split("[END]")[0]  # remove anything after [END]
            if scene:
                # Sometimes a model responds w/ text before [SCENE]
                # This removes any text before and only keeps [SCENE] and
                # everything that comes after it
                reply = "[SCENE] " + reply.split("[SCENE]")[1]

            if "[CONTENT]" in reply:
                reply = reply.split("[CONTENT]")[1].strip()

                # If the character replies with smthing like *giggles* remove it.
                # (and yes im using regex here)
                reply = re.sub(r"\*.*?\*", "", reply)
                # If the character replies with smthing like [silence] remove it.
                reply = re.sub(r"\[.*?\]", "", reply)
            else:
                # Typically this means that the model didnt return a proper content field
                reply = "ERROR"

            return reply, char, face, body, scene

        def removePlaceholders(self):
            """Fill in the {{placeholders}} of the character's prompt template"""
            spacezone = self.dbase.getSceneData("zone")
            renpy.log(f">>> rmvPlace func: spacezone is {spacezone}")

            if spacezone == "true":
                raw_examples = Info().getExamplePrompts[f"{self.character_name}_purgatory"]
                format_rules = Info().format["purgatory"]
                emotions = ""
            else:
                raw_examples = Info().get_prompt(self.character_name)
                format_rules = Info().format["roleplay"]
                emotions = ", ".join(
                    Configs()
                    .characters.get(self.character_name.title(), {})
                    .get("head", {})
                )

            backgrounds = ", ".join(Configs().bg_scenes["default"])

            string = raw_examples[0]["content"].replace("{{format}}", format_rules)
            string = string.replace("{{char}}", self.character_name)
            string = string.replace("{{emotes}}", emotions)
            string = string.replace("{{scenes}}", backgrounds)
            string = string.replace("{{user}}", persistent.playername)
            string = string.replace(
                "{{body}}", Configs().body_types(self.character_name.title())
            )

            raw_examples[0]["content"] = string

            if spacezone != "true":
                with open(self.full_path + "/full_history.json", "w") as f:
                    json.dump(raw_examples + self.chathistory, f, indent=2)

            return raw_examples

        def checkForContextLimit(self, range=120, contains_system_prompt=False):
            """Estimates the amount of tokens in the chathistory.
            If the max context window for an LLM is set to (for eg.) 1024 then if the tokens
            exceed that amount, the start of the chathistory will be deleted.

            Both the user message and the assistant message.

            Args:
                range -- the amount of words it will take before clearing up the chat. eg.
                        if the max context window is 1024, with a range of 40 and the current
                        context of the chathistory is >= 984 then it will delete the chat (first 2 msgs or more)
                        once the current tokens reach 984 or higher.

                contains_system_prompt -- Determines if the first index should be deleted or skipped
                                        (which would typically be the system prompt)
            """

            max_tokens = int(persistent.context_window)
            delete_pos = 0 if contains_system_prompt == False else 1
            current_tokens = self.count_tokens()

            # Continues to delete the chat from the top if
            # the current_tokens is still greater than max_tokens.
            # Removes the oldest user/assistant pair each round; always keeps
            # the newest message so the model has something to respond to.
            popped = False
            while (
                current_tokens >= max_tokens - range
                and len(self.chathistory) - delete_pos >= 3
            ):
                self.chathistory.pop(delete_pos)
                self.chathistory.pop(delete_pos)
                popped = True
                current_tokens = self.count_tokens()

            if popped:
                with open(f"{self.full_path}/chathistory.json", "w") as f:
                    json.dump(self.chathistory, f, indent=2)

        def count_tokens(self):
            current_tokens = 0
            for content in self.chathistory:
                words_amnt = len(content["content"].split())
                current_tokens += words_amnt
            return current_tokens

        def checkForError(self, reply):
            """If An error happened with the API, return the Error"""
            try:
                if reply[0] == False:
                    false_return = reply[0]
                    error_message = reply[1]
                    return false_return, error_message
            except TypeError:
                return False

        def checkForPurgatory(self):
            """This puts the prompt template into the
            chathistory file instead of having it be empty."""
            spacezone = self.dbase.getSceneData("zone")
            if spacezone == "true":
                with open(f"{self.full_path}/chathistory.json", "w") as f:
                    json.dump(self.chathistory, f, indent=2)

        def checkForBadFormat(self, response):
            """attempts to fix incorrectly formatted responses"""
            spacezone = self.dbase.getSceneData("zone")
            if spacezone == "true":
                if not response.startswith("[CONTENT]"):
                    return "[CONTENT] Hmm..."
                return response

            if (
                "[SCENE]" not in response
                or "[FACE]" not in response
                or "[BODY]" not in response
                or "[CONTENT]" not in response
            ):
                return "[SCENE] clubroom [FACE] happy [BODY] relaxed [CONTENT] ... [END]"

            char_conf = Configs().characters.get(self.character_name.title(), {})
            valid_bodies = set(char_conf.get("left", {})) | set(char_conf.get("right", {}))
            valid_faces = char_conf.get("head", {})

            body = response.split("[BODY]")[1].split("[CONTENT]")[0].strip()
            if body and body.lower() not in valid_bodies:
                response = response.replace(body, "relaxed", 1)

            face = response.split("[FACE]")[1].split("[BODY]")[0].strip()
            if face and valid_faces and face.lower() not in valid_faces:
                response = response.replace(face, random.choice(list(valid_faces)), 1)
            return response

        def modelChoices(self, prompt):
            return TextModel().getLLM(prompt=prompt)

        def ai_response(self, userInput):
            """Gets ai generated text based off given prompt"""

            reminder = ""
            spacezone = self.dbase.getSceneData("zone")

            renpy.log(f">>> ai response func: spacezone is {spacezone}")
            if spacezone != "true" and self.retrying:
                char_conf = Configs().characters.get(self.character_name.title(), {})
                emotions = ", ".join(char_conf.get("head", {}))
                parts = Configs().body_types(self.character_name.title())
                reminder = (
                    Info()
                    .getReminder["emotes"]
                    .replace("{{emotes}}", emotions)
                    .replace("{{body}}", parts)
                    .replace("{{char}}", self.character_name)
                )

            self.checkForPurgatory()

            # Log user input (the retry reminder is only sent to the model,
            # never saved into the chat history)
            self.chathistory.append({"role": "user", "content": userInput})

            # Make sure the user's msg doesn't go over the context window
            self.checkForContextLimit()
            examples = self.removePlaceholders()
            contextAndUserMsg = (
                examples + self.chathistory
                if spacezone != "true"
                else list(self.chathistory)
            )
            if reminder:
                contextAndUserMsg = contextAndUserMsg[:-1] + [
                    {"role": "user", "content": userInput + reminder}
                ]

            response = self.modelChoices(contextAndUserMsg)

            # If An error happened with the API, return the Error
            check_error = self.checkForError(response)
            if check_error:
                return check_error[1]

            response = " ".join(response.split())  # Get rid of any extra spaces
            response = self.checkForBadFormat(response)

            reply, _, face, body, scene = self.removeKeywords(response)

            # Log AI input
            response = self.safeResponse(response)
            response = response.split("[END]")[0] + " [END]"

            if response.startswith("[FACE]") and "[BODY]" not in response:
                response = Info().getReminder["generic_response"]

            self.chathistory.append({"role": "assistant", "content": response})

            self.controlMood(face, body)
            self.controlBackground(scene)

            with open(f"{self.full_path}/chathistory.json", "w") as f:
                json.dump(self.chathistory, f, indent=2)
            return reply
