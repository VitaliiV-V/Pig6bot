from __future__ import annotations

import json
import secrets
from config.config import *
from bot.settings import *
from io import BytesIO
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, User, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

SUPERSAMPLE = 4

BG_COLOR = (27, 37, 50, 255)
NAME_FONT_SIZE = 24
TEXT_FONT_SIZE = 22
LINE_SPACING = 8

OUTER_MARGIN = 30
AVATAR_SIZE = 50
AVATAR_GAP = 5
BUBBLE_PADDING_X = 10
BUBBLE_PADDING_TOP = 10
BUBBLE_PADDING_BOTTOM = 20
NAME_TEXT_GAP = 10
MAX_TEXT_WIDTH = 420
BUBBLE_RADIUS = 20

STICKER_MAX_SIDE = 512

FONT_NAME_PATH = "assets/fonts/Roboto-Bold.ttf"
FONT_TEXT_PATH = "assets/fonts/Roboto-Regular.ttf"

NAME_COLORS = [
    (0xFC, 0x5C, 0x5C),
    (0xFF, 0x93, 0x4A),
    (0xE0, 0xA2, 0xF3),
    (0x65, 0xC8, 0x6A),
    (0x33, 0xC7, 0xC1),
    (0x54, 0x9C, 0xF6),
    (0xE8, 0x6C, 0xA6),
]

import emoji


def remove_emojis(text: str) -> str:
    return emoji.replace_emoji(text, replace="")


def get_name_color(user_id: int) -> tuple[int, int, int]:
    return NAME_COLORS[user_id % len(NAME_COLORS)]


def _load_fonts() -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    name_font = ImageFont.truetype(FONT_NAME_PATH, NAME_FONT_SIZE * SUPERSAMPLE)
    text_font = ImageFont.truetype(FONT_TEXT_PATH, TEXT_FONT_SIZE * SUPERSAMPLE)
    return name_font, text_font


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []

    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue

        words = paragraph.split(" ")
        current = ""

        for word in words:
            if draw.textlength(word, font=font) > max_width:
                if current:
                    lines.append(current)
                    current = ""
                chunk = ""
                for ch in word:
                    candidate_chunk = chunk + ch
                    if (
                        draw.textlength(candidate_chunk, font=font) <= max_width
                        or not chunk
                    ):
                        chunk = candidate_chunk
                    else:
                        lines.append(chunk)
                        chunk = ch
                current = chunk
                continue

            candidate = f"{current} {word}".strip()
            width = draw.textlength(candidate, font=font)

            if width <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word

        lines.append(current)

    return lines


async def _get_avatar_image(
    context: ContextTypes.DEFAULT_TYPE,
    author: User,
    msg,
    size: int,
) -> Image.Image:
    avatar: Optional[Image.Image] = None

    file_id = None
    try:
        photos = await context.bot.get_user_profile_photos(author.id, limit=1)
        if photos and photos.photos:
            file_id = photos.photos[0][-1].file_id
            tg_file = await context.bot.get_file(file_id)
            raw = await tg_file.download_as_bytearray()
            avatar = Image.open(BytesIO(bytes(raw))).convert("RGBA")
    except Exception:
        file_id = None

    if not file_id:
        try:
            chat = await context.bot.get_chat(MAIN_CHANNEL_ID)
            if chat.photo:
                file_id = chat.photo.big_file_id
        except Exception:
            pass

    if file_id:
        try:
            tg_file = await context.bot.get_file(file_id)
            raw = await tg_file.download_as_bytearray()
            avatar = Image.open(BytesIO(bytes(raw))).convert("RGBA")
        except Exception:
            avatar = None

    if avatar is None:
        name = author.first_name or author.username or "?"
        color = get_name_color(author.id)
        avatar = Image.new("RGBA", (size, size), (*color, 255))
        draw = ImageDraw.Draw(avatar)
        font = ImageFont.truetype(FONT_NAME_PATH, int(size * 0.5))
        letter = name[0].upper()
        bbox = draw.textbbox((0, 0), letter, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            ((size - w) / 2 - bbox[0], (size - h) / 2 - bbox[1]),
            letter,
            font=font,
            fill="white",
        )
    else:
        avatar = _fit_square(avatar, size)

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    avatar.putalpha(mask)

    return avatar


def _fit_square(image: Image.Image, size: int) -> Image.Image:
    """Кроп по центру + ресайз до квадрата size x size."""
    w, h = image.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    image = image.crop((left, top, left + side, top + side))
    return image.resize((size, size), Image.LANCZOS)


def _rounded_rectangle_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255
    )
    return mask


async def quote(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> Optional[Path]:
    msg = update.message

    message = update.message.reply_to_message

    if message is None or not message.text:
        return None

    author = message.from_user
    name = author.first_name or author.username or "Unknown"
    if author.first_name == "Telegram":
        author = await context.bot.get_chat(MAIN_CHANNEL_ID)
        name = author.title
    text = message.text

    name = remove_emojis(name)
    text = remove_emojis(text)

    ss = SUPERSAMPLE
    name_font, text_font = _load_fonts()

    outer_margin = OUTER_MARGIN * ss
    avatar_size = AVATAR_SIZE * ss
    avatar_gap = AVATAR_GAP * ss
    bubble_padding_x = BUBBLE_PADDING_X * ss
    bubble_padding_top = BUBBLE_PADDING_TOP * ss
    bubble_padding_bottom = BUBBLE_PADDING_BOTTOM * ss
    name_text_gap = NAME_TEXT_GAP * ss
    max_text_width = MAX_TEXT_WIDTH * ss
    bubble_radius = BUBBLE_RADIUS * ss
    line_spacing = LINE_SPACING * ss

    measure_img = Image.new("RGBA", (10, 10))
    measure_draw = ImageDraw.Draw(measure_img)

    name_lines = _wrap_text(measure_draw, name, name_font, max_text_width)
    name_line_heights = []
    name_line_widths = []
    for line in name_lines:
        bbox = measure_draw.textbbox((0, 0), line if line else " ", font=name_font)
        name_line_widths.append(bbox[2] - bbox[0])
        name_line_heights.append(bbox[3] - bbox[1])
    name_block_width = max(name_line_widths) if name_line_widths else 0
    name_block_height = sum(name_line_heights) + line_spacing * max(
        len(name_lines) - 1, 0
    )

    lines = _wrap_text(measure_draw, text, text_font, max_text_width)
    line_heights = []
    line_widths = []
    for line in lines:
        bbox = measure_draw.textbbox((0, 0), line if line else " ", font=text_font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])
    text_block_width = (
        max([name_block_width] + line_widths) if lines else name_block_width
    )
    text_block_width = min(text_block_width, max_text_width)
    text_block_height = sum(line_heights) + line_spacing * max(len(lines) - 1, 0)

    text_column_height = name_block_height + name_text_gap + text_block_height

    bubble_width = int(text_block_width + bubble_padding_x * 2)
    bubble_height = int(text_column_height + bubble_padding_top + bubble_padding_bottom)

    content_height = max(avatar_size, bubble_height)
    canvas_width = int(outer_margin * 2 + avatar_size + avatar_gap + bubble_width)
    canvas_height = int(outer_margin * 2 + content_height)

    image = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))

    bubble_x = outer_margin + avatar_size + avatar_gap
    bubble_y = outer_margin
    bubble = Image.new("RGBA", (bubble_width, bubble_height), BG_COLOR)
    bubble.putalpha(
        _rounded_rectangle_mask((bubble_width, bubble_height), bubble_radius)
    )
    image.alpha_composite(bubble, dest=(bubble_x, bubble_y))

    draw = ImageDraw.Draw(image)
    avatar = await _get_avatar_image(context, author, message, avatar_size)
    avatar_pos = (outer_margin, outer_margin)
    image.alpha_composite(avatar, dest=avatar_pos)

    text_x = bubble_x + bubble_padding_x
    text_y = bubble_y + bubble_padding_top

    name_color = get_name_color(author.id)
    y = text_y
    for line, h in zip(name_lines, name_line_heights):
        draw.text((text_x, y), line, font=name_font, fill=name_color)
        y += h + line_spacing

    y = text_y + name_block_height + name_text_gap
    for line, h in zip(lines, line_heights):
        draw.text((text_x, y), line, font=text_font, fill="white")
        y += h + line_spacing

    final_size = (canvas_width // ss, canvas_height // ss)
    image = image.resize(final_size, Image.LANCZOS)

    w, h = image.size
    scale = STICKER_MAX_SIDE / max(w, h)
    if scale < 1:
        image = image.resize(
            (max(int(w * scale), 1), max(int(h * scale), 1)), Image.LANCZOS
        )

    output_dir = Path("stickers")
    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = output_dir / f"quote_{message.message_id}.webp"
    image.save(file_path, format="WEBP", lossless=True)

    code = secrets.token_hex(8)

    os.makedirs("tmp", exist_ok=True)

    path = f"tmp/.quote_{code}.json"

    data = {
        "user_id": msg.from_user.id,
        "id": str(msg.chat_id) + str(msg.reply_to_message.message_id),
        "sticker_path": str(file_path),
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    with open("tmp/allowed_messages.json", "r", encoding="utf-8") as f:
        allowed_messages = json.load(f)
    config = load_config()
    if msg.from_user.id in config["root_users"]:
        alpha = True
    elif msg.from_user.id == OWNER_ID:
        alpha = True
    else:
        alpha = False
    if (data["id"] in allowed_messages["messages"]) or alpha:
        await context.bot.send_sticker(
            chat_id=data["user_id"], sticker=data["sticker_path"]
        )

        await msg.reply_text("🟢 Стикер отправлен Вам в личные сообщения.")
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"approveq^{path}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rejectq^{path}"),
            ]
        ]
    )

    await msg.reply_text(text=(f"{OWNER_USERNAME}"), reply_markup=keyboard)
