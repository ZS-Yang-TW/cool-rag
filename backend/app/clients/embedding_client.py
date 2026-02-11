import logging
import math
import time
from typing import List

from openai import OpenAI, OpenAIError

from app.core import settings

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """Client for generating embeddings using OpenAI-compatible API"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_embedding_model
        self.batch_size = settings.embedding_batch_size

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            return response.data[0].embedding
        except OpenAIError as e:
            logger.exception("Embedding API error")
            raise

    def _clean_texts(self, texts: List[str]) -> List[str]:
        """
        Clean and validate input texts

        Args:
            texts: Raw input texts

        Returns:
            Cleaned texts with empty/invalid entries replaced by space
        """
        return [t.strip() if isinstance(t, str) and t.strip() else " " for t in texts]

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        cleaned_texts = self._clean_texts(texts)
        embeddings = []
        total_batches = math.ceil(len(cleaned_texts) / self.batch_size)

        for i in range(0, len(cleaned_texts), self.batch_size):
            batch = cleaned_texts[i : i + self.batch_size]
            batch_num = (i // self.batch_size) + 1

            start_time = time.time()

            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                )

                batch_embeddings = [d.embedding for d in response.data]
                embeddings.extend(batch_embeddings)

                duration = time.time() - start_time
                logger.info(
                    "Batch %d/%d done (%d texts, %.2fs)",
                    batch_num,
                    total_batches,
                    len(batch),
                    duration,
                )

                # Small delay to avoid rate limits
                if i + self.batch_size < len(cleaned_texts):
                    time.sleep(0.2)

            except OpenAIError as e:
                logger.exception(
                    "Error generating embeddings for batch %d/%d",
                    batch_num,
                    total_batches,
                )
                raise

        return embeddings
