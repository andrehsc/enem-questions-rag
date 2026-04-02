using System.Data;
using Npgsql;
using TeachersHub.ENEM.AI.Interfaces;
using TeachersHub.ENEM.AI.Models;
using Microsoft.Extensions.Logging;

namespace TeachersHub.ENEM.AI.Services;

public class PostgreSQLVectorStore : IVectorStore
{
    private readonly string _connectionString;
    private readonly ILogger<PostgreSQLVectorStore> _logger;
    private readonly AIServiceConfiguration _config;

    public PostgreSQLVectorStore(
        AIServiceConfiguration config,
        ILogger<PostgreSQLVectorStore> logger)
    {
        _connectionString = config.DatabaseConnectionString;
        _logger = logger;
        _config = config;
    }

    public async Task StoreEmbeddingAsync(
        Guid questionId, 
        float[] embedding, 
        string model = "sentence-transformers",
        CancellationToken cancellationToken = default)
    {
        if (embedding.Length != _config.VectorDimension)
        {
            throw new ArgumentException($"Embedding must have {_config.VectorDimension} dimensions", nameof(embedding));
        }

        const string sql = @"
            INSERT INTO enem_questions.question_embeddings 
            (question_id, embedding_vector, embedding_model, created_at, updated_at)
            VALUES (@questionId, @embedding, @model, @now, @now)
            ON CONFLICT (question_id, embedding_model) 
            DO UPDATE SET 
                embedding_vector = EXCLUDED.embedding_vector,
                updated_at = EXCLUDED.updated_at";

        try
        {
            using var connection = new NpgsqlConnection(_connectionString);
            await connection.OpenAsync(cancellationToken);

            using var command = new NpgsqlCommand(sql, connection);
            command.Parameters.AddWithValue("questionId", questionId);
            command.Parameters.Add(new NpgsqlParameter("embedding", NpgsqlTypes.NpgsqlDbType.Array | NpgsqlTypes.NpgsqlDbType.Real) { Value = embedding });
            command.Parameters.AddWithValue("model", model);
            command.Parameters.AddWithValue("now", DateTime.UtcNow);

            await command.ExecuteNonQueryAsync(cancellationToken);
            
            _logger.LogDebug("Stored embedding for question {QuestionId} with model {Model}", questionId, model);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to store embedding for question {QuestionId}", questionId);
            throw;
        }
    }

    public async Task<IEnumerable<(Guid QuestionId, double Similarity)>> SearchSimilarAsync(
        float[] queryEmbedding, 
        int limit = 10, 
        double threshold = 0.7,
        CancellationToken cancellationToken = default)
    {
        if (queryEmbedding.Length != _config.VectorDimension)
        {
            throw new ArgumentException($"Query embedding must have {_config.VectorDimension} dimensions", nameof(queryEmbedding));
        }

        const string sql = @"
            SELECT 
                qe.question_id,
                1 - (qe.embedding_vector <=> @queryVector::vector) as similarity
            FROM enem_questions.question_embeddings qe
            WHERE (1 - (qe.embedding_vector <=> @queryVector::vector)) >= @threshold
            ORDER BY similarity DESC
            LIMIT @limit";

        try
        {
            using var connection = new NpgsqlConnection(_connectionString);
            await connection.OpenAsync(cancellationToken);

            using var command = new NpgsqlCommand(sql, connection);
            command.Parameters.Add(new NpgsqlParameter("queryVector", NpgsqlTypes.NpgsqlDbType.Array | NpgsqlTypes.NpgsqlDbType.Real) { Value = queryEmbedding });
            command.Parameters.AddWithValue("threshold", threshold);
            command.Parameters.AddWithValue("limit", limit);

            var results = new List<(Guid QuestionId, double Similarity)>();

            using var reader = await command.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                var questionId = reader.GetGuid("question_id");
                var similarity = reader.GetDouble("similarity");
                results.Add((questionId, similarity));
            }

            _logger.LogDebug("Found {Count} similar questions with threshold {Threshold}", results.Count, threshold);
            return results;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to search similar embeddings");
            throw;
        }
    }

    public async Task<float[]?> GetEmbeddingAsync(
        Guid questionId, 
        string model = "sentence-transformers",
        CancellationToken cancellationToken = default)
    {
        const string sql = @"
            SELECT embedding_vector 
            FROM enem_questions.question_embeddings 
            WHERE question_id = @questionId AND embedding_model = @model";

        try
        {
            using var connection = new NpgsqlConnection(_connectionString);
            await connection.OpenAsync(cancellationToken);

            using var command = new NpgsqlCommand(sql, connection);
            command.Parameters.AddWithValue("questionId", questionId);
            command.Parameters.AddWithValue("model", model);

            var result = await command.ExecuteScalarAsync(cancellationToken);
            
            return result as float[];
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get embedding for question {QuestionId}", questionId);
            throw;
        }
    }

    public async Task<bool> IsHealthyAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            using var connection = new NpgsqlConnection(_connectionString);
            await connection.OpenAsync(cancellationToken);
            
            const string sql = "SELECT 1";
            using var command = new NpgsqlCommand(sql, connection);
            await command.ExecuteScalarAsync(cancellationToken);
            
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Vector store health check failed");
            return false;
        }
    }
}
