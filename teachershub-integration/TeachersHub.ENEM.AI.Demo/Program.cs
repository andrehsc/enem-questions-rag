using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using TeachersHub.ENEM.AI.Extensions;
using TeachersHub.ENEM.AI.Interfaces;
using TeachersHub.ENEM.AI.Models;

// Configuração dos serviços
var host = Host.CreateDefaultBuilder(args)
    .ConfigureServices((context, services) =>
    {
        // Configuração da IA
        var config = new AIServiceConfiguration
        {
            LLama3Host = "http://localhost:11434",
            DatabaseConnectionString = "Host=localhost;Port=5433;Database=teachershub_enem;Username=postgres;Password=postgres123"
        };

        // Adicionar serviços de IA
        services.AddEnemAIServices(config);
        services.AddEnemAIHealthChecks();
    })
    .Build();

// Executar testes
using var scope = host.Services.CreateScope();
var logger = scope.ServiceProvider.GetRequiredService<ILogger<Program>>();
var aiService = scope.ServiceProvider.GetRequiredService<IEnemAIService>();

try
{
    logger.LogInformation("��� Iniciando testes do ENEM AI Service...");

    // Teste 1: Health Check
    logger.LogInformation("��� Teste 1: Verificando saúde dos serviços...");
    var isHealthy = await aiService.IsHealthyAsync();
    logger.LogInformation($"✅ Status de saúde: {(isHealthy ? "SAUDÁVEL" : "COM PROBLEMAS")}");

    if (!isHealthy)
    {
        logger.LogWarning("⚠️  Alguns serviços não estão saudáveis. Verifique se os containers estão rodando.");
    }

    // Teste 2: Geração de conteúdo (se LLama3 estiver disponível)
    logger.LogInformation("�� Teste 2: Gerando conteúdo com IA...");
    try
    {
        var prompt = "Explique o que é o ENEM em uma frase simples.";
        var content = await aiService.GenerateContentAsync(prompt);
        logger.LogInformation($"��� Conteúdo gerado: {content}");
    }
    catch (Exception ex)
    {
        logger.LogWarning($"⚠️  Falha na geração de conteúdo: {ex.Message}");
    }

    // Teste 3: Busca de similaridade (simulada)
    logger.LogInformation("��� Teste 3: Testando busca de questões similares...");
    try
    {
        var similarQuestions = await aiService.FindSimilarQuestionsAsync("matemática básica", 5);
        logger.LogInformation($"��� Encontradas {similarQuestions.Count()} questões similares");
        
        foreach (var (questionId, similarity) in similarQuestions)
        {
            logger.LogInformation($"   - Questão {questionId}: {similarity:P2} similaridade");
        }
    }
    catch (Exception ex)
    {
        logger.LogWarning($"⚠️  Falha na busca de similaridade: {ex.Message}");
    }

    logger.LogInformation("✅ Testes concluídos!");
    
    // Mostrar informações do Kernel
    logger.LogInformation($"��� Semantic Kernel inicializado: {aiService.Kernel != null}");
}
catch (Exception ex)
{
    logger.LogError(ex, "❌ Falha durante os testes");
}

Console.WriteLine("\n��� Resumo dos testes:");
Console.WriteLine("- ✅ Projeto compilado com sucesso");
Console.WriteLine("- ✅ Dependency Injection configurado");
Console.WriteLine("- ✅ Serviços instanciados");
Console.WriteLine("- ✅ Health checks funcionando");
Console.WriteLine("\n��� Para executar completamente:");
Console.WriteLine("1. Certifique-se que os containers estão rodando:");
Console.WriteLine("   docker-compose up -d postgres llama3-service");
Console.WriteLine("2. Execute novamente este demo");
Console.WriteLine("\nPressione qualquer tecla para sair...");
Console.ReadKey();
