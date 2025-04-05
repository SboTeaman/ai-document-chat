import logging
from dataclasses import dataclass
from functools import lru_cache

import tiktoken

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_encoder() -> tiktoken.Encoding:
    """Return a lazily-initialised, process-wide tiktoken encoder."""
    return tiktoken.get_encoding("cl100k_base")


@dataclass
class Chunk:
    content: str
    chunk_index: int
    token_count: int


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[Chunk]:
    """Split text into token-bounded, overlapping chunks for embedding.

    Tokenises with tiktoken and emits ``Chunk`` objects of at most
    ``chunk_size`` tokens, each overlapping the previous by ``overlap`` tokens.
    """
    encoder = _get_encoder()
    tokens = encoder.encode(text)

    if not tokens:
        return []

    chunks = []
    start = 0
    index = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text_str = encoder.decode(chunk_tokens).strip()

        if chunk_text_str:
            chunks.append(
                Chunk(
                    content=chunk_text_str,
                    chunk_index=index,
                    token_count=len(chunk_tokens),
                )
            )
            index += 1

        if end >= len(tokens):
            break

        start = end - overlap

    logger.debug("Text chunked", extra={"total_tokens": len(tokens), "chunks": len(chunks)})
    return chunks
