import pytest

from retrieval.index import ChromaVectorStore


@pytest.fixture
def vector_store():
    store = ChromaVectorStore(persist_directory="./data/test_chroma_db")
    store.reset_collection("interview_questions")
    return store


def test_upsert_and_query(vector_store):
    collection_name = "interview_questions"

    # Synthetic fixtures
    ids = ["doc1", "doc2"]
    embeddings = [[0.1, 0.2, 0.3], [0.9, 0.8, 0.7]]
    metadatas = [{"difficulty": "easy"}, {"difficulty": "hard"}]
    documents = ["What is a tuple?", "Explain vector databases."]

    vector_store.upsert_documents(
        collection_name=collection_name,
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=documents,
    )

    results = vector_store.query_similar(
        collection_name=collection_name,
        query_vector=[0.15, 0.25, 0.35],
        top_k=1,
        where_filter={"difficulty": "easy"},
    )

    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "doc1"
    assert results["documents"][0][0] == "What is a tuple?"
