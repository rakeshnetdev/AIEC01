from __future__ import annotations

import os
from functools import lru_cache
from typing import Annotated

import tiktoken
from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader
from langchain_core.tools import tool
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Default OpenAI embedding model to use if no override is provided in environment variables.
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def _tiktoken_len(text: str) -> int:
    """
    Helper function to calculate the token length of a given text chunk.
    Uses tiktoken with the 'gpt-4o' encoding to ensure accurate token counting
    matching the target LLM.
    """
    return len(tiktoken.encoding_for_model("gpt-4o").encode(text))


# Cache the retriever initialization to avoid loading and embedding documents on every tool call.
# maxsize=1 ensures only one instance of the retriever is cached and reused.
@lru_cache(maxsize=1)
def _get_retriever():
    # Retrieve the directory containing the source documents from the environment variables,
    # defaulting to the "data" directory in the project root.
    data_dir = os.environ.get("RAG_DATA_DIR", "data")

    # Load all PDF files recursively from the data directory.
    # PyMuPDFLoader is used for fast and accurate PDF parsing.
    try:
        documents = DirectoryLoader(
            data_dir, glob="**/*.pdf", loader_cls=PyMuPDFLoader
        ).load()
    except Exception:
        # Handle cases where the directory does not exist or loader fails, returning an empty document list.
        documents = []

    # If no documents are found, return None so the tool knows the knowledge base is empty.
    if not documents:
        return None

    # Split the loaded documents into smaller, semantic text chunks.
    # Chunk size is limited to 750 tokens, using the _tiktoken_len helper for counting.
    # overlap is set to 0 to minimize duplication across chunks in this simple agent implementation.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=750, chunk_overlap=0, length_function=_tiktoken_len
    )
    chunks = splitter.split_documents(documents)

    # Initialize OpenAI Embeddings with the configured model and API key.
    embeddings = OpenAIEmbeddings(
        model=os.environ.get("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        openai_api_key=os.environ["OPENAI_API_KEY"],
    )
    
    # Create an in-memory vector database using Qdrant.
    # The documents (chunks) and their generated embeddings are indexed here.
    # ':memory:' specifies that the vector store exists purely in RAM and is not persisted to disk.
    vectorstore = QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        location=":memory:",
        collection_name="rag_collection",
    )
    # Return the vector database configured as a retriever for search queries.
    return vectorstore.as_retriever()


@tool
def retrieve_information(
    query: Annotated[str, "query to ask the retrieve information tool"],
) -> str:
    """Retrieve information about feline health, including life stage care, nutrition, vaccinations, parasite control, behavior, diagnostics, and veterinary guidelines for cats."""
    # Fetch the cached vector database retriever.
    retriever = _get_retriever()
    
    # Query the retriever if it exists, otherwise fall back to an empty list of documents.
    docs = retriever.invoke(query) if retriever else []
    
    # If no documents match or retriever is uninitialized, return a default informative message.
    if not docs:
        return "No relevant information found in the knowledge base."
        
    # Join and return the contents of the retrieved document chunks, separated by double newlines.
    return "\n\n".join(doc.page_content for doc in docs)
