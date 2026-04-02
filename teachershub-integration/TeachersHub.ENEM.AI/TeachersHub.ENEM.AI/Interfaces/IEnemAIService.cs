using Microsoft.SemanticKernel;

namespace TeachersHub.ENEM.AI.Interfaces;

public interface IEnemAIService
{
    /// <summary>
    /// Gets the Semantic Kernel instance for AI operations
    /// </summary>
    Kernel Kernel { get; }

    /// <summary>
    /// Generates educational content using LLama3
    /// </summary>
    /// <param name="prompt">The input prompt</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>Generated AI response</returns>
    Task<string> GenerateContentAsync(string prompt, CancellationToken cancellationToken = default);

    /// <summary>
    /// Finds similar questions using vector search
    /// </summary>
    /// <param name="queryText">Query text to search for</param>
    /// <param name="limit">Maximum number of results</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>List of similar question IDs with similarity scores</returns>
    Task<IEnumerable<(Guid QuestionId, double Similarity)>> FindSimilarQuestionsAsync(
        string queryText, 
        int limit = 10, 
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Checks if the AI service is healthy and responding
    /// </summary>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>True if healthy, false otherwise</returns>
    Task<bool> IsHealthyAsync(CancellationToken cancellationToken = default);
}
