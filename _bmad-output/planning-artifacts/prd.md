# TeachersHub-ENEM Integration Product Requirements Document (PRD)

## Goals and Background Context

### Goals
• Integrar funcionalidades do banco de dados de questões ENEM à plataforma educacional TeachersHub existente
• Habilitar ferramentas educacionais baseadas em IA através da integração Semantic Kernel para criação de atividades e avaliações
• Manter a experiência do usuário TeachersHub existente enquanto adiciona capacidades poderosas de recuperação e análise de questões
• Estabelecer padrão de arquitetura híbrida permitindo que componentes ML Python aprimorem plataforma educacional baseada em .NET
• Fornecer aos professores ferramentas inteligentes para criar avaliações, atividades e correção automatizada usando corpus de questões ENEM

### Background Context

TeachersHub é uma plataforma educacional estabelecida construída com backend .NET 8, frontend React/TypeScript e banco de dados PostgreSQL, servindo professores com ferramentas de planejamento de aulas e gerenciamento de recursos. Através do trabalho de desenvolvimento anterior, criamos com sucesso um sistema RAG de Questões ENEM abrangente com 2.452 questões do exame nacional brasileiro, completo com endpoints FastAPI, capacidades de busca semântica e navegação HATEOAS.

A oportunidade de integração surgiu do reconhecimento de que o fluxo de trabalho educacional do TeachersHub poderia ser significativamente aprimorado incorporando análise de questões baseada em IA e capacidades de geração de atividades. Em vez de manter sistemas separados, esta integração posicionará o TeachersHub como uma plataforma educacional abrangente aprimorada por IA, aproveitando tanto a arquitetura .NET comprovada quanto as sofisticadas capacidades ML baseadas em Python para criação inteligente de conteúdo educacional.

### Change Log
| Data | Versão | Descrição | Autor |
|------|---------|-------------|---------|
| 2025-10-11 | v1.0 | PRD inicial para integração TeachersHub-ENEM | PM |

## Requisitos

### Funcionais

**FR1:** O sistema deve integrar o banco de dados ENEM com 2.452 questões ao TeachersHub mantendo a estrutura existente de dados PostgreSQL

**FR2:** Professores devem poder buscar questões ENEM por disciplina, ano, dificuldade e tópicos através da interface TeachersHub

**FR3:** O sistema deve fornecer análise semântica de questões usando capacidades RAG para sugerir questões relacionadas

**FR4:** Professores devem poder gerar atividades personalizadas automaticamente baseadas em critérios selecionados (disciplina, nível, quantidade)

**FR5:** O sistema deve integrar Semantic Kernel .NET para processar prompts de IA e gerar conteúdo educacional

**FR6:** Professores devem poder criar avaliações customizadas selecionando questões ENEM com preview e edição

**FR7:** O sistema deve manter componentes Python ML como microsserviços para processamento RAG e análise semântica

**FR8:** A autenticação TeachersHub existente (JWT) deve ser estendida para autenticar acesso aos recursos ENEM

**FR9:** O sistema deve fornecer correção automatizada de questões objetivas ENEM com feedback detalhado

**FR10:** Professores devem poder exportar atividades geradas em formatos PDF e Word mantendo formatação ENEM oficial

### Não-Funcionais

**NFR1:** A integração não deve impactar negativamente o tempo de resposta das funcionalidades TeachersHub existentes

**NFR2:** O sistema deve suportar até 100 professores simultâneos realizando buscas de questões sem degradação de performance

**NFR3:** Componentes Python ML devem responder em até 3 segundos para consultas RAG simples

**NFR4:** A arquitetura híbrida deve manter separação clara entre serviços .NET e Python com APIs bem definidas

**NFR5:** O sistema deve manter disponibilidade de 99.5% considerando ambos sistemas TeachersHub e ENEM

**NFR6:** Dados sensíveis de questões ENEM devem ser protegidos seguindo LGPD e políticas educacionais brasileiras

**NFR7:** O sistema deve suportar crescimento para até 10.000 questões ENEM futuras sem reestruturação arquitetural

**NFR8:** Logs detalhados devem ser mantidos para auditoria de uso de questões e geração de conteúdo IA

## Objetivos de Design da Interface do Usuário

### Visão Geral de UX
A experiência do usuário deve integrar perfeitamente as capacidades ENEM ao fluxo de trabalho familiar do TeachersHub. Professores devem poder descobrir e utilizar as novas funcionalidades IA sem curva de aprendizado acentuada, mantendo a consistência visual e de interação com o sistema existente. A interface deve priorizar eficiência na busca e seleção de questões, com visualizações claras dos resultados de análise semântica e sugestões IA.

### Paradigmas de Interação Principais
- **Busca Inteligente**: Interface de busca com filtros avançados e sugestões em tempo real baseadas em RAG
- **Seleção Visual**: Cards de questões com preview, permitindo seleção múltipla para criação de atividades
- **Workflow Guiado**: Assistente passo-a-passo para geração automática de avaliações usando IA
- **Feedback Contextual**: Tooltips e sugestões explicando como funcionalidades IA podem ajudar no contexto atual

### Telas e Visualizações Principais
- **Dashboard ENEM**: Nova seção no dashboard TeachersHub com acesso rápido às funcionalidades ENEM
- **Busca de Questões**: Interface de busca avançada com filtros por disciplina, ano, dificuldade e análise semântica
- **Criador de Atividades**: Wizard para geração automática de atividades com preview em tempo real
- **Biblioteca de Questões**: Visualização organizada das questões salvas e atividades criadas
- **Análise de Resultados**: Dashboard com estatísticas de uso de questões e performance dos estudantes

### Acessibilidade: WCAG AA
Conformidade com diretrizes WCAG AA para garantir acessibilidade a professores com diferentes necessidades, incluindo suporte a leitores de tela e navegação por teclado.

### Branding
Manter consistência completa com o design system TeachersHub existente, adicionando elementos visuais que identifiquem claramente as funcionalidades IA (ícones, cores de destaque) sem conflitar com a identidade visual estabelecida. Utilizar ícones universais para IA e funcionalidades educacionais para facilitar reconhecimento.

### Plataformas e Dispositivos Alvo: Web Responsivo
Compatibilidade total com o design responsivo TeachersHub existente, otimizando especialmente para tablets onde professores frequentemente preparam aulas, mantendo funcionalidade completa em desktops e usabilidade adequada em smartphones.

## Premissas Técnicas

### Estrutura de Repositório: Monorepo
Manter estrutura de repositório única integrando tanto componentes .NET quanto Python, facilitando versionamento coordenado e deployment simplificado da solução híbrida.

### Arquitetura de Serviços
**Arquitetura Híbrida**: Combinação de componentes monolíticos .NET (TeachersHub core) com microsserviços Python especializados (ML/RAG). TeachersHub .NET atua como orchestrador principal, consumindo serviços Python via APIs REST bem definidas.

### Requisitos de Testes
**Pirâmide Completa de Testes**: Testes unitários para lógica de negócio .NET e Python, testes de integração para APIs entre serviços, testes end-to-end para fluxos completos de usuário, e testes de performance para validar requisitos NFR de tempo de resposta.

### Premissas Técnicas Adicionais e Solicitações

• **Stack .NET**: Manter .NET 8, Entity Framework Core, ASP.NET Core Identity conforme arquitetura TeachersHub existente

• **Stack Python**: FastAPI, PostgreSQL, Redis para componentes ML/RAG existentes, com adição de bibliotecas de ML conforme necessário

• **Banco de Dados**: PostgreSQL único compartilhado entre componentes .NET e Python com schemas separados para isolamento de dados

• **Autenticação**: Estender sistema JWT TeachersHub existente para autenticar chamadas aos microsserviços Python

• **Container**: Docker Compose para desenvolvimento local, com containers separados para .NET, Python, PostgreSQL e Redis

• **Semantic Kernel**: Integração Microsoft Semantic Kernel para funcionalidades IA no lado .NET, conectando aos modelos LLM via APIs

• **APIs**: RESTful APIs seguindo padrões OpenAPI/Swagger para documentação e teste automatizado

• **Deployment**: Manter estratégia de deployment TeachersHub existente, estendendo para incluir containers Python

• **Monitoring**: Logs centralizados e métricas de performance para ambos componentes .NET e Python

• **Compliance**: Implementar controles LGPD para dados educacionais, incluindo auditoria de acesso a questões ENEM

## Lista de Épicos

**Épico 1: Fundação e Infraestrutura de Integração**
Estabelecer base técnica para integração TeachersHub-ENEM incluindo configuração de ambiente híbrido, extensão de autenticação JWT, e implementação de comunicação entre serviços .NET/Python com entrega de health checks funcionais.

**Épico 2: Integração de Dados e APIs ENEM**
Integrar banco de dados ENEM ao TeachersHub com migração de schema, exposição de endpoints REST para busca de questões, e implementação de funcionalidades básicas de recuperação com interface de busca simples.

**Épico 3: Capacidades RAG e Análise Semântica**
Implementar microsserviços Python para análise semântica, busca inteligente baseada em RAG, e sugestões de questões relacionadas com integração completa ao frontend TeachersHub.

**Épico 4: Ferramentas IA para Criação de Conteúdo**
Desenvolver funcionalidades de geração automática de atividades usando Semantic Kernel, criador de avaliações assistido por IA, e correção automatizada com interface de wizard completa.

**Épico 5: Exportação e Compliance**
Implementar exportação de atividades em formatos PDF/Word mantendo formatação oficial ENEM, controles LGPD, auditoria de uso, e monitoramento completo do sistema integrado.

## Épico 1: Fundação e Infraestrutura de Integração

**Objetivo Expandido:** 
Estabelece a infraestrutura técnica fundamental para permitir comunicação segura e eficiente entre TeachersHub (.NET) e componentes ENEM (Python). Inclui configuração de ambiente de desenvolvimento híbrido, extensão do sistema de autenticação JWT existente, implementação de APIs de comunicação inter-serviços, e validação através de health checks que demonstram conectividade end-to-end funcional.

### Story 1.1: Configuração de Ambiente Híbrido
Como um desenvolvedor,
Eu quero configurar ambiente de desenvolvimento que suporte tanto .NET quanto Python,
Para que eu possa trabalhar com ambos os componentes de forma integrada.

#### Critérios de Aceitação
1. Docker Compose configurado com containers para TeachersHub (.NET), ENEM-API (Python), PostgreSQL e Redis
2. Variáveis de ambiente configuradas para desenvolvimento local
3. Rede Docker personalizada permitindo comunicação entre containers
4. Scripts de inicialização automatizada do ambiente completo
5. Documentação de setup atualizada com instruções passo-a-passo

### Story 1.2: Extensão de Autenticação JWT
Como um professor TeachersHub,
Eu quero que minha sessão autentique automaticamente acesso às funcionalidades ENEM,
Para que eu não precise fazer login adicional.

#### Critérios de Aceitação
1. TeachersHub JWT tokens incluem claims necessários para autorização ENEM
2. Microsserviço Python valida tokens JWT TeachersHub
3. Middleware de autenticação implementado no FastAPI
4. Tokens expirados são tratados graciosamente com redirecionamento
5. Logs de autenticação registram tentativas de acesso para auditoria

### Story 1.3: APIs de Comunicação Inter-Serviços
Como um componente TeachersHub .NET,
Eu quero comunicar com serviços Python através de APIs REST bem definidas,
Para que a integração seja robusta e maintível.

#### Critérios de Aceitação
1. Cliente HTTP configurado no .NET para chamadas aos serviços Python
2. Especificações OpenAPI/Swagger documentam todas as interfaces
3. Tratamento de erros padronizado entre serviços
4. Timeout e retry policies implementados
5. Métricas de performance de comunicação inter-serviços coletadas

### Story 1.4: Health Checks e Monitoramento
Como um administrador do sistema,
Eu quero monitorar a saúde de todos os componentes da integração,
Para que eu possa identificar e resolver problemas rapidamente.

#### Critérios de Aceitação
1. Health check endpoints implementados em ambos serviços .NET e Python
2. Dashboard de status mostra conectividade entre todos os componentes
3. Alertas automáticos para falhas de comunicação inter-serviços
4. Logs centralizados agregam informações de ambos os sistemas
5. Métricas de uptime e latência são coletadas e visualizadas

## Épico 2: Integração de Dados e APIs ENEM

**Objetivo Expandido:** 
Integra o banco de dados existente de questões ENEM ao ecossistema TeachersHub, incluindo migração de schema para PostgreSQL compartilhado, criação de endpoints REST .NET para busca básica de questões, e implementação de interface de usuário inicial que permite professores descobrirem e utilizarem o banco de questões através do TeachersHub.

### Story 2.1: Migração de Schema ENEM
Como um administrador de dados,
Eu quero migrar as questões ENEM para o banco TeachersHub,
Para que os dados estejam integrados e acessíveis via .NET.

#### Critérios de Aceitação
1. Schema ENEM criado no PostgreSQL TeachersHub com isolamento adequado
2. Migration scripts Entity Framework Core para estrutura de dados questões
3. Dados das 2.452 questões ENEM migrados com integridade mantida
4. Índices otimizados para busca por disciplina, ano, dificuldade e tópicos
5. Testes de validação confirmam integridade e performance dos dados migrados

### Story 2.2: Endpoints REST Básicos
Como um desenvolvedor frontend,
Eu quero APIs .NET para acessar questões ENEM,
Para que eu possa construir interfaces de busca no TeachersHub.

#### Critérios de Aceitação
1. Controller .NET implementado com endpoints de busca de questões
2. Filtros por disciplina, ano, dificuldade implementados
3. Paginação e ordenação configuradas
4. Documentação Swagger gerada automaticamente
5. Testes unitários cobrem todos os endpoints criados

### Story 2.3: Interface de Busca Básica
Como um professor,
Eu quero buscar questões ENEM através do TeachersHub,
Para que eu possa encontrar conteúdo relevante para minhas aulas.

#### Critérios de Aceitação
1. Página de busca ENEM integrada ao dashboard TeachersHub
2. Filtros visuais por disciplina, ano e dificuldade
3. Resultados exibidos em cards com preview da questão
4. Paginação e ordenação funcionais
5. Loading states e tratamento de erros implementados

## Épico 3: Capacidades RAG e Análise Semântica

**Objetivo Expandido:** 
Implementa funcionalidades avançadas de inteligência artificial aproveitando os microsserviços Python existentes para análise semântica, busca inteligente baseada em RAG, e sistema de recomendações de questões relacionadas, tudo integrado perfeitamente ao frontend TeachersHub para uma experiência de usuário enriquecida.

### Story 3.1: Microsserviço RAG
Como um sistema TeachersHub,
Eu quero acessar capacidades de análise semântica via microsserviços Python,
Para que professores recebam sugestões inteligentes de questões.

#### Critérios de Aceitação
1. Microsserviço Python FastAPI operacional com endpoints RAG
2. Integração com modelos de embedding para análise semântica
3. Cache Redis implementado para consultas frequentes
4. APIs documentadas e testadas via Swagger
5. Performance atende NFR3 (resposta < 3 segundos)

### Story 3.2: Busca Semântica Integrada
Como um professor,
Eu quero buscar questões por conceitos e não apenas palavras-chave,
Para que eu encontre conteúdo mais relevante pedagogicamente.

#### Critérios de Aceitação
1. Campo de busca semântica integrado à interface existente
2. Resultados mostram questões semanticamente relacionadas
3. Explicação visual de por que questões foram sugeridas
4. Combinação de filtros tradicionais com busca semântica
5. Feedback do usuário coletado para melhoria contínua

### Story 3.3: Sistema de Recomendações
Como um professor,
Eu quero receber sugestões de questões relacionadas ao que estou visualizando,
Para que eu possa descobrir conteúdo adicional relevante.

#### Critérios de Aceitação
1. Seção "Questões Relacionadas" em cada visualização de questão
2. Algoritmo considera contexto pedagógico e dificuldade
3. Recomendações atualizadas dinamicamente
4. Professores podem marcar recomendações como úteis/não úteis
5. Métricas de engajamento com recomendações coletadas

## Épico 4: Ferramentas IA para Criação de Conteúdo

**Objetivo Expandido:** 
Desenvolve funcionalidades avançadas de inteligência artificial usando Microsoft Semantic Kernel para automatizar criação de atividades educacionais, incluindo gerador de avaliações personalizadas, correção automatizada com feedback inteligente, e interface wizard que guia professores através de processos de criação assistidos por IA.

### Story 4.1: Integração Semantic Kernel
Como um sistema TeachersHub,
Eu quero processar prompts educacionais usando IA,
Para que professores recebam conteúdo gerado automaticamente.

#### Critérios de Aceitação
1. Microsoft Semantic Kernel integrado ao backend .NET
2. Conexão configurada com modelos LLM (OpenAI/Azure)
3. Prompts educacionais especializados desenvolvidos e testados
4. Rate limiting e controle de custos implementados
5. Logs detalhados para auditoria de uso de IA

### Story 4.2: Gerador de Atividades
Como um professor,
Eu quero gerar atividades automaticamente baseadas em critérios,
Para que eu economize tempo na preparação de aulas.

#### Critérios de Aceitação
1. Wizard de criação de atividades com interface passo-a-passo
2. Seleção de critérios: disciplina, nível, quantidade, tópicos
3. Preview em tempo real da atividade sendo gerada
4. Opções de personalização e edição pós-geração
5. Salvamento e reutilização de templates de atividades

### Story 4.3: Correção Automatizada
Como um professor,
Eu quero correção automática de questões objetivas com feedback,
Para que eu possa focar em aspectos pedagógicos mais complexos.

#### Critérios de Aceitação
1. Sistema reconhece respostas de questões objetivas ENEM
2. Feedback detalhado explicando respostas corretas/incorretas
3. Estatísticas de performance por tópico/disciplina
4. Relatórios de progresso individual e da turma
5. Integração com sistema de notas TeachersHub existente

## Épico 5: Exportação e Compliance

**Objetivo Expandido:** 
Completa o sistema com funcionalidades de produção incluindo exportação profissional de atividades em formatos PDF e Word mantendo formatação oficial ENEM, implementação completa de controles LGPD para dados educacionais, sistema de auditoria robusto, e monitoramento abrangente para operação estável em ambiente de produção.

### Story 5.1: Exportação PDF/Word
Como um professor,
Eu quero exportar atividades em formatos profissionais,
Para que eu possa usar o material em diversos contextos educacionais.

#### Critérios de Aceitação
1. Exportação PDF mantém formatação oficial ENEM
2. Exportação Word permite edição posterior
3. Templates customizáveis para diferentes tipos de atividade
4. Cabeçalhos e rodapés personalizáveis por escola/professor
5. Batch export para múltiplas atividades simultaneamente

### Story 5.2: Controles LGPD
Como um administrador escolar,
Eu quero garantir conformidade LGPD no uso de dados educacionais,
Para que a escola opere dentro da legislação brasileira.

#### Critérios de Aceitação
1. Consentimento explícito para uso de dados implementado
2. Logs de auditoria para todos os acessos a dados pessoais
3. Funcionalidade de exclusão de dados (direito ao esquecimento)
4. Relatórios de conformidade LGPD gerados automaticamente
5. Políticas de retenção de dados configuráveis e automáticas

### Story 5.3: Monitoramento de Produção
Como um administrador de sistema,
Eu quero visibilidade completa do sistema em produção,
Para que eu possa garantir operação estável e confiável.

#### Critérios de Aceitação
1. Dashboard executivo com métricas de uso e performance
2. Alertas proativos para problemas de sistema
3. Métricas de negócio: atividades criadas, questões utilizadas, engagement
4. Relatórios de capacity planning e crescimento
5. Integração com ferramentas de monitoramento TeachersHub existentes

## Próximos Passos

### Prompt para Especialista UX
"Com base neste PRD de integração TeachersHub-ENEM, desenvolva especificações detalhadas de UX/UI focando na integração perfeita das funcionalidades IA ao workflow existente de professores, priorizando discovery intuitiva das novas capacidades e workflows guiados para adoção gradual das ferramentas avançadas."

### Prompt para Arquiteto
"Utilizando este PRD como base, crie arquitetura técnica detalhada para integração híbrida .NET/Python, especificando padrões de comunicação inter-serviços, estratégias de deployment, monitoramento de performance, e planos de migração de dados que mantenham estabilidade do TeachersHub durante toda a integração."