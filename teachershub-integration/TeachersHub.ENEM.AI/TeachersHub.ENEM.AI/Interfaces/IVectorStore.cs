namespace TeachersHub.ENEM.AI.Interfaces;

public interface IVectorStore
{
    /// <summary>
    /// Stores an embedding vector for a question
    /// </summary>
    /// <param name="questionId">Question ID</param>
    /// <param name="embedding">Embedding vector (384 dimensions)</param>
    /// <param name="model">Model name used for embedding</param>
    /// <param name="cancellationToken">Cancellation token</param>
    Task StoreEmbeddingAsync(
        Guid questionId, 
        float[] embedding, 
        string model = "sentence-transformers",
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Searches for similar embeddings using cosine similarity
    /// </summary>
    /// <param name="queryEmbedding">Query embedding vector</param>
    /// <param name="limit">Maximum number of results</param>
    /// <param name="threshold">Minimum similarity threshold (0.0 to 1.0)</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>List of question IDs with similarity scores</returns>
    Task<IEnumerable<(Guid QuestionId, double Similarity)>> SearchSimilarAsync(
        float[] queryEmbedding, 
        int limit = 10, 
        double threshold = 0.7,
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Gets the embedding vector for a specific question
    /// </summary>
    /// <param name="questionId">Question ID</param>
    /// <param name="model">Model name</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>Embedding vector or null if not found</returns>
    Task<float[]?> GetEmbeddingAsync(
        Guid questionId, 
        string model = "sentence-transformers",
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Checks if the vector store is healthy and accessible
    /// </summary>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>True if healthy, false otherwise</returns>
    Task<bool> IsHealthyAsync(CancellationToken cancellationToken = default);
}
