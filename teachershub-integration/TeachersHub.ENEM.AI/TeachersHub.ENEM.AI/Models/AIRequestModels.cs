namespace TeachersHub.ENEM.AI.Models;

/// <summary>
/// Request model for AI content generation
/// </summary>
public record GenerateContentRequest(
    string Prompt,
    int? MaxTokens = null,
    double? Temperature = null,
    string? SystemMessage = null
);

/// <summary>
/// Response model for AI content generation
/// </summary>
public record GenerateContentResponse(
    string Content,
    int TokensUsed,
    TimeSpan ProcessingTime,
    bool Success,
    string? ErrorMessage = null
);

/// <summary>
/// Request model for vector similarity search
/// </summary>
public record SimilaritySearchRequest(
    string QueryText,
    int Limit = 10,
    double Threshold = 0.7,
    string? Subject = null
);

/// <summary>
/// Response model for vector similarity search
/// </summary>
public record SimilaritySearchResponse(
    IEnumerable<SimilarQuestion> SimilarQuestions,
    int TotalFound,
    TimeSpan ProcessingTime,
    bool Success,
    string? ErrorMessage = null
);

/// <summary>
/// Model representing a similar question result
/// </summary>
public record SimilarQuestion(
    Guid QuestionId,
    double SimilarityScore,
    string QuestionText,
    string Subject,
    int? Year = null,
    int? Day = null
);

/// <summary>
/// Health check response model
/// </summary>
public record HealthCheckResponse(
    bool IsHealthy,
    string ServiceName,
    TimeSpan ResponseTime,
    string? ErrorMessage = null,
    Dictionary<string, object>? AdditionalInfo = null
);

/// <summary>
/// Configuration model for AI services
/// </summary>
public record AIServiceConfiguration
{
    public required string LLama3Host { get; init; }
    public required string DatabaseConnectionString { get; init; }
    public int RequestTimeoutSeconds { get; init; } = 30;
    public int MaxRequestsPerMinute { get; init; } = 10;
    public int VectorDimension { get; init; } = 384;
    public string DefaultEmbeddingModel { get; init; } = "sentence-transformers";
    public double DefaultSimilarityThreshold { get; init; } = 0.7;
}
