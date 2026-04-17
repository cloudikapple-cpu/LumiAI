"""Text utilities."""

import re


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)].rstrip() + suffix


def split_text(text: str, max_length: int = 4096) -> list[str]:
    """
    Split text into chunks of maximum length.

    Args:
        text: Text to split
        max_length: Maximum chunk length

    Returns:
        List of text chunks
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = ""

    lines = text.split("\n")
    for line in lines:
        if len(current_chunk) + len(line) + 1 <= max_length:
            current_chunk += line + "\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            if len(line) <= max_length:
                current_chunk = line + "\n"
            else:
                words = line.split(" ")
                current_chunk = ""
                for word in words:
                    if len(current_chunk) + len(word) + 1 <= max_length:
                        current_chunk += word + " "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = word + " "
                current_chunk += "\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def clean_whitespace(text: str) -> str:
    """Clean excessive whitespace from text."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    text = text.strip()
    return text


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text."""
    url_pattern = re.compile(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    )
    return url_pattern.findall(text)


def count_tokens_approximate(text: str) -> int:
    """
    Approximate token count for text.

    Note: This is a rough approximation. For accurate counts,
    use tiktoken or similar.
    """
    words = text.split()
    return int(len(words) * 1.3)


def strip_markdown(text: str) -> str:
    """Remove markdown formatting from text."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"~~(.+?)~~", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    return text