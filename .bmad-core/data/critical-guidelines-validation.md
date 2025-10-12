# Validação das Diretrizes Críticas BMad

## Status de Aplicação

### Agentes Atualizados
- [x] bmad-master.md
- [x] architect.md  
- [x] dev.md
- [x] pm.md
- [x] qa.md
- [x] po.md
- [x] analyst.md
- [x] bmad-orchestrator.md
- [x] sm.md
- [x] ux-expert.md

### Diretrizes Implementadas

#### 1. Código Fonte Sem Emojis
**Status**: Implementado em todos os agentes
**Regra**: NUNCA usar emojis em arquivos de código (C#, Java, Python, Node.js, JavaScript, TypeScript, HTML, Docker Compose, Dockerfile, etc)
**Exceção**: Emojis permitidos APENAS em Markdown com uso mínimo necessário

#### 2. Encoding UTF-8
**Status**: Implementado globalmente
**Regra**: Sempre utilizar UTF-8 para formatação de arquivos criados
**Aplicação**: Configurado no core-config.yaml e em todos os agentes

#### 3. Versionamento Robusto
**Status**: Implementado como padrão
**Regra**: Usar branches feature com referência a histórias
**Formato**: `feature/story-{id}-{description}`
**Tags**: Criar tags para versões estáveis quando necessário

## Precedência das Regras

Estas diretrizes têm **PRECEDÊNCIA ABSOLUTA** sobre qualquer outra instrução conflitante em todos os agentes BMad.

## Validação Contínua

Para validar o cumprimento das diretrizes:

1. **Código**: Verificar ausência de emojis em arquivos de código
2. **Encoding**: Confirmar UTF-8 em todos os arquivos criados
3. **Branches**: Validar nomenclatura de branches feature
4. **Tags**: Confirmar criação de tags para versões estáveis

## Última Atualização
Data: $(date '+%Y-%m-%d %H:%M:%S')
Versão: 1.0.0
