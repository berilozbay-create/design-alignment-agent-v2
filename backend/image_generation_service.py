import mimetypes
import time
from pathlib import Path
from urllib.request import urlopen

EMPTY_ROOM_PATH = "static/room/empty_room.png"


def ensure_session_folder(session_id: str):
    folder = Path(f"static/generated/session_{session_id}")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def save_generated_image(image_bytes: bytes, path: Path):
    with open(path, "wb") as f:
        f.write(image_bytes)


def guess_mime_type(path_or_name: str) -> str:
    mime_type, _ = mimetypes.guess_type(path_or_name)
    return mime_type or "image/png"


def load_local_image_part(types_module, file_path: str):
    with open(file_path, "rb") as f:
        data = f.read()

    return types_module.Part.from_bytes(
        data=data,
        mime_type=guess_mime_type(file_path),
    )


def static_url_to_local_path(image_url: str) -> str:
    if not image_url.startswith("/static/"):
        raise ValueError(f"Not a local static URL: {image_url}")

    return image_url.lstrip("/")


def load_image_part_from_reference(types_module, image_reference: str):
    if not image_reference:
        raise ValueError("image_reference is missing")

    if image_reference.startswith("/static/"):
        local_path = static_url_to_local_path(image_reference)
        return load_local_image_part(types_module, local_path)

    if image_reference.startswith("http://") or image_reference.startswith("https://"):
        with urlopen(image_reference) as response:
            data = response.read()

        return types_module.Part.from_bytes(
            data=data,
            mime_type=guess_mime_type(image_reference),
        )

    return load_local_image_part(types_module, image_reference)


def extract_image_bytes_from_response(response):
    candidates = getattr(response, "candidates", None) or []

    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue

        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline_data = getattr(part, "inline_data", None)
            if inline_data and getattr(inline_data, "data", None):
                return inline_data.data

    return None


def generate_image_with_gemini(
    gemini_client,
    session_id: str,
    round_number: int,
    option_id: str,
    prompt: str,
    style_image_path: str = None,
    direction_image_url: str = None,
):
    from google.genai import types

    parts = []
    parts.append(types.Part.from_text(text=prompt))

    if direction_image_url:
        parts.append(load_image_part_from_reference(types, direction_image_url))
    else:
        parts.append(load_local_image_part(types, EMPTY_ROOM_PATH))

    if style_image_path:
        parts.append(load_image_part_from_reference(types, style_image_path))

    max_attempts = 4
    delay_seconds = 10
    response = None
    last_error = None

    for attempt in range(max_attempts):
        try:
            print(f"[image_generation] option={option_id} attempt={attempt + 1}/{max_attempts}")
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=parts,
            )
            print(f"[image_generation] option={option_id} success")
            break
        except Exception as e:
            last_error = e
            error_text = str(e)
            print(f"[image_generation] option={option_id} error: {error_text}")

            if "RESOURCE_EXHAUSTED" in error_text or "429" in error_text:
                if attempt < max_attempts - 1:
                    print(f"[image_generation] option={option_id} waiting {delay_seconds}s before retry")
                    time.sleep(delay_seconds)
                    delay_seconds *= 2
                    continue

            raise

    if response is None:
        raise last_error

    image_bytes = extract_image_bytes_from_response(response)

    if image_bytes is None:
        raise ValueError("Gemini did not return image bytes")

    folder = ensure_session_folder(session_id)
    filename = f"round{round_number}_{option_id}.png"
    file_path = folder / filename

    save_generated_image(image_bytes, file_path)

    return f"/static/generated/session_{session_id}/{filename}"