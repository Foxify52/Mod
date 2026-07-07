# Minimal stdlib client for the local Ollama REST API.
# No third-party packages (ollama/httpx/requests/tqdm) — everything the mod
# ships must run on Ren'Py's bundled Python alone.
init -5 python:
    import json
    import random
    import urllib.request
    import urllib.error

    OLLAMA_URL = "http://127.0.0.1:11434"
    OLLAMA_OFFLINE_MSG = "You don't have ollama running."


    class OllamaError(Exception):
        """The Ollama server answered with an error."""

        def __init__(self, message, status=None):
            super().__init__(message)
            self.message = message
            self.status = status


    class OllamaOffline(OllamaError):
        """The Ollama server is unreachable."""

        def __init__(self):
            super().__init__(OLLAMA_OFFLINE_MSG, None)


    def ollama_request(path, payload=None, timeout=600, stream=False, method=None):
        """Send one request to the local Ollama server.

        Returns parsed JSON, or the raw response object when stream=True
        (iterate it for newline-delimited JSON progress lines).
        """
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        if method is None:
            method = "POST" if data is not None else "GET"
        req = urllib.request.Request(
            OLLAMA_URL + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            try:
                detail = json.loads(body).get("error", body)
            except ValueError:
                detail = body
            raise OllamaError(detail, e.code)
        except (urllib.error.URLError, OSError):
            raise OllamaOffline()

        if stream:
            return resp
        return json.loads(resp.read().decode("utf-8"))


    def ollama_list_models():
        """Names of locally installed models, or "off" when the server is unreachable."""
        try:
            data = ollama_request("/api/tags", timeout=10)
        except OllamaError:
            return "off"
        return [m["name"] for m in data.get("models", [])]


    def ollama_delete_model(model):
        # Both keys: newer servers read "model", older ones read "name"
        ollama_request(
            "/api/delete", {"model": model, "name": model}, timeout=30, method="DELETE"
        )


    def ollama_pull(model, on_progress):
        """Download a model, reporting human-readable progress via on_progress(text)."""
        resp = ollama_request(
            "/api/pull", {"model": model, "name": model}, timeout=3600, stream=True
        )
        for line in resp:
            info = json.loads(line.decode("utf-8"))
            if "error" in info:
                raise OllamaError(info["error"])
            status = info.get("status", "")
            total = info.get("total")
            completed = info.get("completed")
            if total and completed is not None:
                mb = 1024 * 1024
                on_progress(
                    f"{status} {completed * 100 // total}% ({completed // mb}MB of {total // mb}MB)"
                )
            elif status:
                on_progress(status)


    class TextModel:
        def getLLM(self, prompt):
            if not persistent.chatModel or persistent.chatModel == "None":
                return (
                    False,
                    "<|Error|> No model selected! Go to settings and pick a model first.",
                )

            if persistent.seed == "random":
                seed = random.randint(0, 2**31 - 1)
            else:
                try:
                    seed = int(persistent.seed)
                except ValueError:
                    seed = random.randint(0, 2**31 - 1)

            payload = {  # "thinking" and return an empty reply
                "model": persistent.chatModel,
                "messages": prompt,
                "stream": False,
                "think": False,
                "options": {
                    "temperature": float(f".{persistent.temp}"),
                    "stop": ["[INST", "[/INST", "[END]"],
                    "num_ctx": int(persistent.context_window),
                    "seed": seed,
                    "num_predict": 200,
                },
            }

            try:
                try:
                    response = ollama_request("/api/chat", payload)
                except OllamaError as e:
                    # Models without a reasoning mode may reject the think flag
                    if e.status == 400 and "think" in str(e.message).lower():
                        del payload["think"]
                        response = ollama_request("/api/chat", payload)
                    else:
                        raise
            except OllamaOffline:
                return False, f"<|Error|> {OLLAMA_OFFLINE_MSG}"
            except OllamaError as e:
                if e.status == 404:
                    return (
                        False,
                        f'<|Error|> You dont have the model "{persistent.chatModel}" installed! Go to settings and install this model (if it exists).',
                    )
                return False, f"<|Error|> {e.message}"

            result = response["message"]["content"]
            renpy.log(f"RAW RESPONSE: {result}")

            result = result.strip()
            if "[END]" not in result:
                result += " [END]"
            return result
