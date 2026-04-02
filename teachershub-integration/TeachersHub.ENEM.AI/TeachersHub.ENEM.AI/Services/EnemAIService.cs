using Microsoft.Extensions.Logging;
using Microsoft.SemanticKernel;
using TeachersHub.ENEM.AI.Interfaces;
using TeachersHub.ENEM.AI.Models;

namespace TeachersHub.ENEM.AI.Services;

public class EnemAIService : IEnemAIService
{
    private readonly Kernel _kernel;
    private readonly LLama3ChatCompletion _llama3Service;
    private readonly IVectorStore _vectorStore;
    private readonly ILogger<EnemAIService> _logger;
    private readonly AIServiceConfiguration _config;

    public EnemAIService(
        Kernel kernel,
        LLama3ChatCompletion llama3Service,
        IVectorStore vectorStore,
        AIServiceConfiguration config,
        ILogger<EnemAIService> logger)
    {
        _kernel = kernel;
        _llama3Service = llama3Service;
        _vectorStore = vectorStore;
        _config = config;
        _logger = logger;
    }

    public Kernel Kernel => _kernel;

    public async Task<string> GenerateContentAsync(
        string prompt, 
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(prompt))
        {
            throw new ArgumentException("Prompt cannot be null or empty", nameof(prompt));
        }

        var startTime = DateTime.UtcNow;

        try
        {
            _logger.LogInformation("Generating content for prompt length: {PromptLength}", prompt.Length);

            // Use LLama3 service for generation
            var result = await _llama3Service.GenerateAsync(prompt, cancellationToken);

            var processingTime = DateTime.UtcNow - startTime;
            _logger.LogInformation("Content generated successfully in {ProcessingTime}ms", processingTime.TotalMilliseconds);

            return result;
        }
        catch (Exception ex)
        {
            var processingTime = DateTime.UtcNow - startTime;
            _logger.LogError(ex, "Failed to generate content after {ProcessingTime}ms", processingTime.TotalMilliseconds);
            throw;
        }
    }

    public async Task<IEnumerable<(Guid QuestionId, double Similarity)>> FindSimilarQuestionsAsync(
        string queryText, 
        int limit = 10, 
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(queryText))
        {
            throw new ArgumentException("Query text cannot be null or empty", nameof(queryText));
        }

        if (limit <= 0 || limit > 100)
        {
            throw new ArgumentException("Limit must be between 1 and 100", nameof(limit));
        }

        var startTime = DateTime.UtcNow;

        try
        {
            _logger.LogInformation("Finding similar questions for query length: {QueryLength}, limit: {Limit}", 
                queryText.Length, limit);

            // For now, we'll use a simple text-based approach
            // In a full implementation, we would:
            // 1. Generate embeddings for the query text using a sentence transformer
            // 2. Use vector search to find similar questions
            
            // Placeholder implementation - generate random embedding for demonstration
            var queryEmbedding = GeneratePlaceholderEmbedding();
            
            var results = await _vectorStore.SearchSimilarAsync(
                queryEmbedding, 
                limit, 
                _config.DefaultSimilarityThreshold, 
                cancellationToken);

            var processingTime = DateTime.UtcNow - startTime;
            _logger.LogInformation("Found {ResultCount} similar questions in {ProcessingTime}ms", 
                results.Count(), processingTime.TotalMilliseconds);

            return results;
        }
        catch (Exception ex)
        {
            var processingTime = DateTime.UtcNow - startTime;
            _logger.LogError(ex, "Failed to find similar questions after {ProcessingTime}ms", processingTime.TotalMilliseconds);
            throw;
        }
    }

    public async Task<bool> IsHealthyAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            _logger.LogDebug("Performing health check for AI services");

            // Check LLama3 service
            var llama3Healthy = await _llama3Service.IsHealthyAsync(cancellationToken);
            
            // Check Vector Store
            var vectorStoreHealthy = await _vectorStore.IsHealthyAsync(cancellationToken);

            var isHealthy = llama3Healthy && vectorStoreHealthy;

            _logger.LogInformation("Health check completed - LLama3: {LLama3Health}, VectorStore: {VectorStoreHealth}, Overall: {OverallHealth}",
                llama3Healthy, vectorStoreHealthy, isHealthy);

            return isHealthy;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Health check failed with exception");
            return false;
        }
    }

    private float[] GeneratePlaceholderEmbedding()
    {
        // Placeholder implementation - in production, this would use a proper sentence transformer
        var random = new Random();
        var embedding = new float[_config.VectorDimension];
        
        for (int i = 0; i < _config.VectorDimension; i++)
        {
            embedding[i] = (float)(random.NextDouble() * 2.0 - 1.0); // Random values between -1 and 1
        }
        
        // Normalize the vector
        var magnitude = Math.Sqrt(embedding.Sum(x => x * x));
        for (int i = 0; i < embedding.Length; i++)
        {
            embedding[i] = (float)(embedding[i] / magnitude);
        }
        
        return embedding;
    }
}
