"""Markdown formatting utilities for Telegram."""

import re


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram markdown."""
    escape_chars = r"\_*[]()~`>#+-=|{}.!"
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
    return text


def format_markdown(text: str) -> str:
    """
    Basic markdown formatting for Telegram messages.

    Supports:
    - **bold**
    - *italic*
    - `code`
    - [text](url)
    """
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)

    return text


def split_into_chunks(text: str, chunk_size: int = 4096) -> list[str]:
    """Split text into chunks for Telegram message limit."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    current_chunk = ""

    lines = text.split("\n")
    for line in lines:
        if len(current_chunk) + len(line) + 1 <= chunk_size:
            current_chunk += line + "\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            if len(line) <= chunk_size:
                current_chunk = line + "\n"
            else:
                words = line.split(" ")
                current_chunk = ""
                for word in words:
                    if len(current_chunk) + len(word) + 1 <= chunk_size:
                        current_chunk += word + " "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = word + " "
                current_chunk += "\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks