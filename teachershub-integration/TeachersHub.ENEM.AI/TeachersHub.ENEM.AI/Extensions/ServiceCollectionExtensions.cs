using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.SemanticKernel;
using TeachersHub.ENEM.AI.Interfaces;
using TeachersHub.ENEM.AI.Models;
using TeachersHub.ENEM.AI.Services;

namespace TeachersHub.ENEM.AI.Extensions;

public static class ServiceCollectionExtensions
{
    /// <summary>
    /// Adds ENEM AI services to the dependency injection container
    /// </summary>
    /// <param name="services">The service collection</param>
    /// <param name="configuration">AI service configuration</param>
    /// <returns>The service collection for chaining</returns>
    public static IServiceCollection AddEnemAIServices(
        this IServiceCollection services, 
        AIServiceConfiguration configuration)
    {
        // Register configuration
        services.AddSingleton(configuration);

        // Register Semantic Kernel
        var kernelBuilder = Kernel.CreateBuilder();
        // Note: In a full implementation, you would configure the kernel with appropriate connectors
        var kernel = kernelBuilder.Build();
        services.AddSingleton(kernel);

        // Register HTTP client for LLama3
        services.AddHttpClient<LLama3ChatCompletion>(client =>
        {
            client.BaseAddress = new Uri(configuration.LLama3Host);
            client.Timeout = TimeSpan.FromSeconds(configuration.RequestTimeoutSeconds);
        });

        // Register services
        services.AddScoped<IVectorStore, PostgreSQLVectorStore>();
        services.AddScoped<LLama3ChatCompletion>();
        services.AddScoped<IEnemAIService, EnemAIService>();

        return services;
    }

    /// <summary>
    /// Adds ENEM AI services with configuration from appsettings
    /// </summary>
    /// <param name="services">The service collection</param>
    /// <param name="llama3Host">LLama3 service host URL</param>
    /// <param name="connectionString">Database connection string</param>
    /// <returns>The service collection for chaining</returns>
    public static IServiceCollection AddEnemAIServices(
        this IServiceCollection services,
        string llama3Host,
        string connectionString)
    {
        var configuration = new AIServiceConfiguration
        {
            LLama3Host = llama3Host,
            DatabaseConnectionString = connectionString
        };

        return services.AddEnemAIServices(configuration);
    }

    /// <summary>
    /// Adds health checks for AI services
    /// </summary>
    /// <param name="services">The service collection</param>
    /// <returns>The service collection for chaining</returns>
    public static IServiceCollection AddEnemAIHealthChecks(this IServiceCollection services)
    {
        services.AddHealthChecks()
            .AddCheck<EnemAIHealthCheck>("enem-ai-services");

        return services;
    }
}

/// <summary>
/// Health check implementation for ENEM AI services
/// </summary>
public class EnemAIHealthCheck : Microsoft.Extensions.Diagnostics.HealthChecks.IHealthCheck
{
    private readonly IEnemAIService _aiService;
    private readonly ILogger<EnemAIHealthCheck> _logger;

    public EnemAIHealthCheck(IEnemAIService aiService, ILogger<EnemAIHealthCheck> logger)
    {
        _aiService = aiService;
        _logger = logger;
    }

    public async Task<Microsoft.Extensions.Diagnostics.HealthChecks.HealthCheckResult> CheckHealthAsync(
        Microsoft.Extensions.Diagnostics.HealthChecks.HealthCheckContext context,
        CancellationToken cancellationToken = default)
    {
        try
        {
            var isHealthy = await _aiService.IsHealthyAsync(cancellationToken);
            
            if (isHealthy)
            {
                return Microsoft.Extensions.Diagnostics.HealthChecks.HealthCheckResult.Healthy("All AI services are operational");
            }
            else
            {
                return Microsoft.Extensions.Diagnostics.HealthChecks.HealthCheckResult.Unhealthy("One or more AI services are not responding");
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Health check failed with exception");
            return Microsoft.Extensions.Diagnostics.HealthChecks.HealthCheckResult.Unhealthy("Health check failed with exception", ex);
        }
    }
}
