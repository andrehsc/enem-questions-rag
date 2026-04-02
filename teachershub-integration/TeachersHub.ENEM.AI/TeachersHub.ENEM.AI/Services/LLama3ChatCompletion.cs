using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using TeachersHub.ENEM.AI.Models;

namespace TeachersHub.ENEM.AI.Services;

public class LLama3ChatCompletion
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<LLama3ChatCompletion> _logger;
    private readonly AIServiceConfiguration _config;

    public LLama3ChatCompletion(
        HttpClient httpClient,
        AIServiceConfiguration config,
        ILogger<LLama3ChatCompletion> logger)
    {
        _httpClient = httpClient;
        _config = config;
        _logger = logger;
        
        _httpClient.BaseAddress = new Uri(_config.LLama3Host);
        _httpClient.Timeout = TimeSpan.FromSeconds(_config.RequestTimeoutSeconds);
    }

    public async Task<string> GenerateAsync(
        string prompt, 
        CancellationToken cancellationToken = default)
    {
        var startTime = DateTime.UtcNow;
        
        try
        {
            var request = new
            {
                model = "llama3",
                prompt = prompt,
                stream = false,
                options = new
                {
                    temperature = 0.7,
                    max_tokens = 2000
                }
            };

            var json = JsonSerializer.Serialize(request);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            _logger.LogDebug("Sending request to LLama3: {Prompt}", prompt.Substring(0, Math.Min(100, prompt.Length)));

            var response = await _httpClient.PostAsync("/api/generate", content, cancellationToken);
            response.EnsureSuccessStatusCode();

            var responseJson = await response.Content.ReadAsStringAsync(cancellationToken);
            var responseObj = JsonSerializer.Deserialize<JsonElement>(responseJson);

            var generatedText = responseObj.GetProperty("response").GetString() ?? string.Empty;
            var processingTime = DateTime.UtcNow - startTime;

            _logger.LogDebug("LLama3 response received in {ProcessingTime}ms", processingTime.TotalMilliseconds);

            return generatedText;
        }
        catch (Exception ex)
        {
            var processingTime = DateTime.UtcNow - startTime;
            _logger.LogError(ex, "Failed to generate content with LLama3 after {ProcessingTime}ms", processingTime.TotalMilliseconds);
            throw;
        }
    }

    public async Task<bool> IsHealthyAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            var response = await _httpClient.GetAsync("/api/version", cancellationToken);
            return response.IsSuccessStatusCode;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "LLama3 health check failed");
            return false;
        }
    }
}
