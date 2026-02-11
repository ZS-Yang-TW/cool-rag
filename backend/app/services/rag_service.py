"""
RAG Service - Consolidates all RAG-related logic including chunking, retrieval, and context formatting
"""

import base64
import logging
import re
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import tiktoken
from sqlalchemy.orm import Session

from app.clients import EmbeddingClient
from app.core import settings
from app.repositories import VectorRepository

logger = logging.getLogger(__name__)

# ============================================================================
# Image Preprocessing
# ============================================================================


class ImagePreprocessor:
    """Extract base64 images from markdown and replace with local file references"""

    # Pattern to match base64 image references in markdown
    # Example: [image1]: <data:image/png;base64,iVBORw0KGgoAAAANS...>
    IMAGE_REF_PATTERN = re.compile(
        r"\[(image\d+)\]:\s*<data:image\/(png|jpeg|jpg|gif|webp);base64,([A-Za-z0-9+/=\s]+)>",
        re.MULTILINE,
    )

    # Pattern to match image usage in markdown
    # Example: ![][image1]
    IMAGE_USAGE_PATTERN = re.compile(r"!\[\]\[(image\d+)\]")

    def __init__(self, base_dir: str = "uploaded_images"):
        """
        Initialize image preprocessor
        
        Args:
            base_dir: Base directory for storing extracted images
        """
        self.base_dir = base_dir

    def preprocess_markdown(self, markdown: str, document_id: str) -> str:
        """
        Extract base64 images from markdown, save as local files, and update references.
        
        Args:
            markdown: Raw markdown content with base64 images
            document_id: Unique identifier for the document (used for folder organization)
            
        Returns:
            Cleaned markdown with local image URLs
            
        Example:
            Input markdown:
                ![][image1]
                [image1]: data:image/png;base64,iVBORw0KG...
                
            Output markdown:
                ![image1](/images/doc123/abc-def.png)
        """
        if not markdown or not document_id:
            logger.warning("Empty markdown or document_id provided")
            return markdown

        image_map: Dict[str, str] = {}

        # Create document-specific image directory
        doc_image_dir = Path(self.base_dir) / str(document_id)
        doc_image_dir.mkdir(parents=True, exist_ok=True)

        # Extract and save all base64 images
        image_count = 0
        for match in self.IMAGE_REF_PATTERN.finditer(markdown):
            image_id, ext, base64_str = match.groups()

            try:
                # Remove whitespace from base64 string
                base64_str = re.sub(r"\s+", "", base64_str)

                # Decode base64 to bytes
                image_bytes = base64.b64decode(base64_str)

                # Generate unique filename
                filename = f"{uuid.uuid4()}.{ext}"
                filepath = doc_image_dir / filename

                # Save image to disk
                with open(filepath, "wb") as f:
                    f.write(image_bytes)

                # Store mapping from image_id to URL
                image_url = f"/images/{document_id}/{filename}"
                image_map[image_id] = image_url
                image_count += 1

                logger.info(
                    f"Saved image {image_id} as {filename} ({len(image_bytes)} bytes)"
                )

            except Exception as e:
                logger.error(f"Failed to process image {image_id}: {e}")
                # Skip this image but continue processing others
                continue

        # Remove all base64 reference definitions from markdown
        markdown = self.IMAGE_REF_PATTERN.sub("", markdown)

        # Replace image usage syntax with proper markdown image links
        def replace_image(match):
            image_id = match.group(1)
            url = image_map.get(image_id, "")
            if url:
                return f"![{image_id}]({url})"
            else:
                # If image wasn't found/processed, keep original
                logger.warning(f"Image reference {image_id} not found in map")
                return match.group(0)

        markdown = self.IMAGE_USAGE_PATTERN.sub(replace_image, markdown)

        # Clean up extra blank lines
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)

        logger.info(
            f"Preprocessed markdown: extracted {image_count} images for document {document_id}"
        )

        return markdown.strip()

    @staticmethod
    def is_image_only_chunk(chunk_text: str) -> bool:
        """
        Check if a chunk contains only an image reference (no meaningful text).
        
        Args:
            chunk_text: Text chunk to check
            
        Returns:
            True if chunk is image-only, False otherwise
        """
        if not chunk_text:
            return False

        # Strip whitespace
        text = chunk_text.strip()

        # Check if chunk starts with image markdown
        if text.startswith("!["):
            # Check if there's substantial text after the image
            # Allow for image + caption, but reject standalone images
            lines = [line.strip() for line in text.split("\n") if line.strip()]

            # If only one line and it's an image, reject
            if len(lines) == 1:
                return True

            # If all lines are images, reject
            if all(line.startswith("![") for line in lines):
                return True

        return False


# ============================================================================
# Chunking Logic
# ============================================================================


class MarkdownChunker:
    """Chunk Markdown documents while preserving structure"""

    def __init__(
        self, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None
    ):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(self, text: str) -> int:
        """Count the number of tokens in text"""
        return len(self.tokenizer.encode(text))

    def chunk_document(self, content: str, source_file: str) -> List[Dict]:
        """
        Chunk a markdown document into smaller pieces

        Args:
            content: Markdown document content
            source_file: Name of the source file

        Returns:
            List of chunks with metadata
        """
        # Parse document structure
        sections = self._parse_markdown_structure(content)

        # Create chunks
        chunks = []
        chunk_index = 0

        for section in sections:
            section_chunks = self._chunk_section(
                section["content"], section["heading_path"], source_file, chunk_index
            )
            chunks.extend(section_chunks)
            chunk_index += len(section_chunks)

        return chunks

    def _parse_markdown_structure(self, content: str) -> List[Dict]:
        """Parse markdown into hierarchical sections"""
        lines = content.split("\n")
        sections = []
        current_section = {"heading_path": "", "content": "", "level": 0}
        heading_stack = []

        for line in lines:
            # Check if line is a heading
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)

            if heading_match:
                # Save previous section if it has content
                if current_section["content"].strip():
                    sections.append(current_section.copy())

                # Parse new heading
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()

                # Update heading stack
                heading_stack = heading_stack[: level - 1]
                heading_stack.append(heading_text)

                # Start new section
                current_section = {
                    "heading_path": " > ".join(heading_stack),
                    "content": f"{'#' * level} {heading_text}\n\n",
                    "level": level,
                }
            else:
                # Add line to current section
                current_section["content"] += line + "\n"

        # Add last section
        if current_section["content"].strip():
            sections.append(current_section)

        return sections

    def _chunk_section(
        self, content: str, heading_path: str, source_file: str, start_index: int
    ) -> List[Dict]:
        """Chunk a section into smaller pieces"""
        cleaned_content = self._clean_content(content)
        content_token_count = self._count_tokens(cleaned_content)

        # If section is small enough, return as single chunk
        if content_token_count <= self.chunk_size:
            return [
                {
                    "content": cleaned_content,
                    "source_file": source_file,
                    "heading_path": heading_path,
                    "chunk_index": start_index,
                    "metadata": {
                        "token_count": content_token_count,
                        "is_complete_section": True,
                    },
                }
            ]

        # Split into chunks with overlap
        chunks = []
        paragraphs = self._split_into_paragraphs(cleaned_content)

        current_chunk = ""
        current_index = start_index

        for para in paragraphs:
            # Calculate token counts
            current_tokens = self._count_tokens(current_chunk)
            para_tokens = self._count_tokens(para)

            # If paragraph itself is larger than chunk_size, force split it
            if para_tokens > self.chunk_size:
                # Save current chunk if it has content
                if current_chunk.strip():
                    chunks.append(
                        {
                            "content": current_chunk.strip(),
                            "source_file": source_file,
                            "heading_path": heading_path,
                            "chunk_index": current_index,
                            "metadata": {
                                "token_count": self._count_tokens(
                                    current_chunk.strip()
                                ),
                                "is_complete_section": False,
                            },
                        }
                    )
                    current_index += 1
                    current_chunk = ""

                # Split the large paragraph into multiple chunks
                tokens = self.tokenizer.encode(para)
                for i in range(0, len(tokens), self.chunk_size - self.chunk_overlap):
                    sub_tokens = tokens[i : i + self.chunk_size]
                    sub_text = self.tokenizer.decode(sub_tokens)

                    chunks.append(
                        {
                            "content": sub_text.strip(),
                            "source_file": source_file,
                            "heading_path": heading_path,
                            "chunk_index": current_index,
                            "metadata": {
                                "token_count": len(sub_tokens),
                                "is_complete_section": False,
                                "is_forced_split": True,
                            },
                        }
                    )
                    current_index += 1
                continue

            # If adding this paragraph exceeds chunk size
            if current_tokens + para_tokens > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(
                    {
                        "content": current_chunk.strip(),
                        "source_file": source_file,
                        "heading_path": heading_path,
                        "chunk_index": current_index,
                        "metadata": {
                            "token_count": self._count_tokens(current_chunk.strip()),
                            "is_complete_section": False,
                        },
                    }
                )

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text + para + "\n\n"
                current_index += 1
            else:
                current_chunk += para + "\n\n"

        # Add last chunk
        if current_chunk.strip():
            chunks.append(
                {
                    "content": current_chunk.strip(),
                    "source_file": source_file,
                    "heading_path": heading_path,
                    "chunk_index": current_index,
                    "metadata": {
                        "token_count": self._count_tokens(current_chunk.strip()),
                        "is_complete_section": False,
                    },
                }
            )

        return chunks

    def _clean_content(self, content: str) -> str:
        """Clean and normalize content"""
        # Remove TOC markers
        content = re.sub(r"\[\[_TOC_\]\]", "", content)

        # Normalize whitespace
        content = re.sub(r"\n{3,}", "\n\n", content)

        # Remove leading/trailing whitespace
        content = content.strip()

        return content

    def _split_into_paragraphs(self, content: str) -> List[str]:
        """Split content into paragraphs"""
        # Split by double newlines
        paragraphs = re.split(r"\n\n+", content)

        # Filter out empty paragraphs
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        return paragraphs

    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from the end of current chunk using token-based extraction"""
        tokens = self.tokenizer.encode(text)

        # If text is shorter than overlap, return entire text
        if len(tokens) <= self.chunk_overlap:
            return text

        # Extract last N tokens for overlap
        overlap_tokens = tokens[-self.chunk_overlap :]
        overlap_text = self.tokenizer.decode(overlap_tokens)

        return overlap_text + "\n\n"


def chunk_documents(
    documents: List[Tuple[str, str]], document_id_map: Optional[Dict[str, str]] = None
) -> List[Dict]:
    """
    Chunk multiple documents with image preprocessing

    Args:
        documents: List of (filename, content) tuples
        document_id_map: Optional mapping of filename to document_id for image storage

    Returns:
        List of all chunks from all documents
    """
    chunker = MarkdownChunker()
    image_preprocessor = ImagePreprocessor()
    all_chunks = []

    for filename, content in documents:
        # Preprocess markdown to extract base64 images
        if document_id_map and filename in document_id_map:
            document_id = document_id_map[filename]
            content = image_preprocessor.preprocess_markdown(content, document_id)

        chunks = chunker.chunk_document(content, filename)

        # Filter out image-only chunks
        chunks = [
            chunk
            for chunk in chunks
            if not ImagePreprocessor.is_image_only_chunk(chunk["content"])
        ]

        all_chunks.extend(chunks)
        print(f"✓ Chunked {filename}: {len(chunks)} chunks")

    return all_chunks


# ============================================================================
# Retrieval Logic
# ============================================================================


class VectorRetriever:
    """Retrieve relevant document chunks using vector similarity"""

    def __init__(
        self,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        use_mmr: Optional[bool] = None,
        mmr_lambda: Optional[float] = None,
        mmr_fetch_k: Optional[int] = None,
    ):
        self.embedding_client = EmbeddingClient()
        self.vector_repo = VectorRepository(
            top_k if top_k is not None else settings.top_k_results,
            (
                similarity_threshold
                if similarity_threshold is not None
                else settings.similarity_threshold
            ),
        )
        self.use_mmr = use_mmr if use_mmr is not None else settings.use_mmr
        self.mmr_lambda = mmr_lambda if mmr_lambda is not None else settings.mmr_lambda
        self.mmr_fetch_k = (
            mmr_fetch_k if mmr_fetch_k is not None else settings.mmr_fetch_k
        )

    def retrieve(self, query: str, db: Session) -> List[Dict]:
        """
        Retrieve most relevant chunks for a query

        Args:
            query: Search query
            db: Database session

        Returns:
            List of chunk dictionaries with similarity scores
        """
        # Generate query embedding
        query_embedding = self.embedding_client.generate_embedding(query)

        if self.use_mmr:
            return self._retrieve_with_mmr(query_embedding, db)
        else:
            return self._retrieve_direct(query_embedding, db)

    def _retrieve_direct(self, query_embedding: List[float], db: Session) -> List[Dict]:
        """Direct vector similarity retrieval without MMR"""
        # Search similar chunks
        chunks_with_scores = self.vector_repo.search_similar_chunks(query_embedding, db)

        # Convert to dictionaries
        results = []
        for chunk, score in chunks_with_scores:
            result = {
                "content": chunk.content,
                "source_file": chunk.source_file,
                "heading_path": chunk.heading_path,
                "chunk_index": chunk.chunk_index,
                "similarity_score": score,
                "chunk_metadata": chunk.chunk_metadata,
            }
            results.append(result)

        return results

    def _retrieve_with_mmr(
        self, query_embedding: List[float], db: Session
    ) -> List[Dict]:
        """
        Retrieve chunks using Maximal Marginal Relevance (MMR) algorithm

        MMR balances relevance to query with diversity among results.

        Process:
        1. Fetch top_n candidates (e.g., 20) using vector similarity
        2. Select top_k results (e.g., 5) using MMR:
           - First: Select chunk most similar to query
           - Then iteratively:
             a. For each remaining candidate:
                - Calculate similarity to query
                - Calculate max similarity to already selected chunks
                - Apply MMR formula: λ * sim(query) - (1-λ) * max_sim(selected)
             b. Select candidate with highest MMR score

        Args:
            query_embedding: Query vector embedding
            db: Database session

        Returns:
            List of chunk dictionaries selected by MMR
        """
        # Step 1: Fetch more candidates than we need (fetch_k candidates)
        # Temporarily override top_k to fetch more candidates
        original_top_k = self.vector_repo.top_k
        self.vector_repo.top_k = self.mmr_fetch_k

        candidates_with_scores = self.vector_repo.search_similar_chunks(
            query_embedding, db
        )

        # Restore original top_k
        self.vector_repo.top_k = original_top_k

        if not candidates_with_scores:
            return []

        # Convert to list for easier manipulation
        candidates = []
        query_similarities = []
        embeddings = []

        for chunk, score in candidates_with_scores:
            # Skip chunks without embeddings
            if chunk.embedding is None:
                continue

            candidates.append(
                {
                    "content": chunk.content,
                    "source_file": chunk.source_file,
                    "heading_path": chunk.heading_path,
                    "chunk_index": chunk.chunk_index,
                    "similarity_score": score,
                    "chunk_metadata": chunk.chunk_metadata,
                }
            )
            query_similarities.append(score)
            embeddings.append(chunk.embedding)

        # Check if we have any valid candidates
        if not candidates:
            return []

        # Convert to numpy arrays for efficient computation
        candidate_embeddings = np.array(embeddings)
        query_sims = np.array(query_similarities)

        # Cosine similarity computation
        # Pre-compute similarity matrix: similarity_matrix[i][j] = similarity between candidate i and j
        norms = np.linalg.norm(candidate_embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        normalized_embeddings = candidate_embeddings / norms
        similarity_matrix = normalized_embeddings @ normalized_embeddings.T

        # Step 2: Apply MMR selection
        selected_indices = []
        remaining_indices = list(range(len(candidates)))

        # Select first chunk: most similar to query
        first_idx = int(np.argmax(query_sims))
        selected_indices.append(first_idx)
        remaining_indices.remove(first_idx)

        # Step 3: Iteratively select remaining chunks
        target_k = min(original_top_k, len(candidates))

        while len(selected_indices) < target_k and remaining_indices:
            mmr_scores = []

            for idx in remaining_indices:
                similarity_to_query = query_sims[idx]

                # Get maximum similarity to any selected chunk
                max_sim_to_selected = np.max(similarity_matrix[idx, selected_indices])

                # Calculate MMR score
                mmr_score = self._calculate_mmr_score(
                    similarity_to_query, max_sim_to_selected
                )
                mmr_scores.append((idx, mmr_score))

            # Select chunk with highest MMR score
            best_idx, best_score = max(mmr_scores, key=lambda x: x[1])
            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)

        # Return selected chunks in order of selection
        results = [candidates[idx] for idx in selected_indices]

        return results

    def _calculate_mmr_score(
        self, similarity_to_query: float, max_sim_to_selected: float
    ) -> float:
        """
        Calculate MMR (Maximal Marginal Relevance) score

        MMR formula: λ * relevance - (1-λ) * redundancy
        - λ (lambda): Trade-off parameter (0 to 1)
          - Higher λ: Prioritize relevance to query
          - Lower λ: Prioritize diversity from selected chunks

        Args:
            similarity_to_query: Cosine similarity to the query
            max_sim_to_selected: Maximum similarity to already selected chunks

        Returns:
            MMR score
        """
        return (
            self.mmr_lambda * similarity_to_query
            - (1 - self.mmr_lambda) * max_sim_to_selected
        )

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0 to 1)
        """
        # Handle None or empty vectors
        if vec1 is None or vec2 is None:
            return 0.0

        # Convert to numpy arrays if needed
        if not isinstance(vec1, np.ndarray):
            vec1 = np.array(vec1)
        if not isinstance(vec2, np.ndarray):
            vec2 = np.array(vec2)

        # Check for zero vectors
        if vec1.size == 0 or vec2.size == 0:
            return 0.0

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def retrieve_with_context(
        self, query: str, db: Session, include_adjacent: bool = False
    ) -> List[Dict]:
        """
        Retrieve chunks with additional context

        Args:
            query: Search query
            db: Database session
            include_adjacent: Whether to include adjacent chunks (future enhancement)

        Returns:
            List of chunk dictionaries with metadata
        """
        return self.retrieve(query, db)


# ============================================================================
# Context Formatting
# ============================================================================


def format_context_for_llm(chunks: List[Dict]) -> str:
    """
    Format retrieved chunks into context for LLM

    Args:
        chunks: List of retrieved chunk dictionaries

    Returns:
        Formatted context string
    """
    if not chunks:
        return "沒有找到相關文件。"

    context_parts = []

    for i, chunk in enumerate(chunks, 1):
        source = chunk["source_file"]
        heading = chunk.get("heading_path", "").strip()
        content = chunk["content"]
        score = chunk["similarity_score"]

        context_part = f"[來源 {i}] {source}"
        if heading:
            context_part += f" - {heading}"
        context_part += f" (相似度: {score:.2f})\n{content}\n"

        context_parts.append(context_part)

    return "\n---\n\n".join(context_parts)


def extract_sources(chunks: List[Dict]) -> List[Dict]:
    """
    Extract source information from chunks

    Args:
        chunks: List of retrieved chunk dictionaries

    Returns:
        List of source dictionaries
    """
    sources = []
    seen_sources = set()

    for chunk in chunks:
        source_key = f"{chunk['source_file']}::{chunk.get('heading_path', '')}"

        if source_key not in seen_sources:
            # Get a preview of the content (first 150 chars)
            preview = chunk["content"][:150]
            if len(chunk["content"]) > 150:
                preview += "..."

            sources.append(
                {
                    "file": chunk["source_file"],
                    "heading": chunk.get("heading_path"),
                    "relevance_score": round(chunk["similarity_score"], 3),
                    "content_preview": preview,
                }
            )
            seen_sources.add(source_key)

    return sources
