# Epic: Melhoria da Qualidade de Extração ENEM

## 🎯 Visão Geral

**Epic ID**: EQ-001  
**Prioridade**: Alta  
**Estimativa**: 2-3 sprints  
**Squad**: Backend/Data Engineering  

## 📋 Contexto

O sistema ENEM RAG possui uma base sólida com 2532 questões extraídas e API GraphQL funcional. No entanto, análises de qualidade identificaram problemas críticos que impactam a experiência do usuário:

- **Problemas de encoding**: Textos com mojibake (Ã¡ → á, â€™ → ')
- **Parsing incompleto**: Alternativas não capturadas corretamente (3/5 em algumas questões)
- **Imagens desconectadas**: 138+ imagens extraídas sem associação contextual
- **Busca limitada**: Texto em imagens não indexável

## 🔍 Evidências dos Problemas

### Análise Atual (10/2025):
- ✅ **Sistema estável**: GraphQL API (11/11 testes passando)
- ✅ **Volume adequado**: 2532 questões de 2020-2024
- ❌ **Qualidade de texto**: Caracteres especiais corrompidos
- ❌ **Completude**: ~15% questões com alternativas incompletas
- ❌ **Renderização**: Imagens sem contexto visual

### Impacto no Negócio:
- **UX degradada**: Questões ilegíveis para usuários finais
- **SEO limitado**: Conteúdo com encoding ruim não indexa bem
- **Escalabilidade**: Processo manual para correção de dados
- **Competitividade**: Concorrentes com melhor qualidade visual

## 🎯 Objetivos do Epic

### Objetivos Primários:
1. **Eliminar problemas de encoding** em 100% das questões
2. **Garantir parsing completo** de alternativas (5/5)
3. **Associar imagens ao contexto** das questões
4. **Implementar validação** de qualidade automática

### Objetivos Secundários:
1. **Pipeline de OCR** para texto em imagens
2. **Renderização híbrida** texto + imagens
3. **Busca full-text** incluindo conteúdo de imagens

## 📊 Métricas de Sucesso

### KPIs Quantitativos:
- **Encoding**: 0% de questões com problemas de mojibake
- **Parsing**: 95%+ questões com 5 alternativas completas
- **Performance**: Tempo de processamento < 2x atual
- **Cobertura**: 100% questões com validação de qualidade

### KPIs Qualitativos:
- **Developer Experience**: Processo automatizado de validação
- **User Experience**: Questões completamente renderizáveis
- **Maintainability**: Pipeline robusto e testável

## 🚀 Estratégia de Implementação

### Fase 1 - Fundação (Sprint 1):
**Foco**: Correção de problemas básicos de qualidade

**Stories**:
- EQ-002: Implementar normalizador de texto
- EQ-003: Melhorar parsing de alternativas
- EQ-004: Adicionar validação de qualidade

### Fase 2 - Associação (Sprint 2):
**Foco**: Conectar imagens ao contexto das questões

**Stories**:
- EQ-005: Mapear posições de imagens no texto
- EQ-006: Implementar placeholders de imagem
- EQ-007: Estender GraphQL schema para imagens

### Fase 3 - Renderização (Sprint 3):
**Foco**: Capacidades avançadas de visualização

**Stories**:
- EQ-008: Pipeline básico de OCR
- EQ-009: Componente de renderização híbrida
- EQ-010: Otimização de imagens para frontend

## 🔄 Dependências e Riscos

### Dependências Técnicas:
- ✅ **Sistema base estável** (GraphQL + Docker)
- ✅ **Pipeline de extração funcionando**
- ⚠️ **Bibliotecas OCR** (pytesseract, easyocr)
- ⚠️ **Storage para imagens** otimizadas

### Riscos Identificados:

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Performance degradation | Média | Alto | Implementar em batches, profiling |
| OCR accuracy baixa | Alta | Médio | Múltiplas engines, fallback |
| Complexidade frontend | Baixa | Médio | Começar com MVP simples |

## 📝 Critérios de Aceite do Epic

### Técnicos:
- [ ] 100% questões com texto limpo (sem mojibake)
- [ ] 95%+ questões com 5 alternativas parseadas
- [ ] Imagens associadas a questões específicas
- [ ] Pipeline de validação automática
- [ ] Testes de regressão passando
- [ ] Performance dentro de SLA (2x atual max)

### Funcionais:
- [ ] Questão pode ser renderizada completamente
- [ ] Busca funciona em texto + imagem (OCR)
- [ ] API retorna imagens associadas
- [ ] Dashboard de qualidade para admin

### Não-Funcionais:
- [ ] Processo é idempotente
- [ ] Rollback seguro implementado
- [ ] Documentação atualizada
- [ ] Alertas de qualidade configurados

## 🛣️ Roadmap Futuro

### Melhorias Pós-Epic:
1. **ML Enhancement**: Classificação automática de qualidade
2. **Advanced OCR**: Detecção de fórmulas matemáticas
3. **Interactive Rendering**: Zoom, anotações, highlight
4. **Analytics**: Dashboards de qualidade de dados

## 📚 Recursos e Referências

### Documentação Técnica:
- [Análise de Qualidade Atual](./quality-analysis.md)
- [Arquitetura Proposta](./architecture-proposal.md)
- [Benchmarks de Performance](./performance-benchmarks.md)

### Ferramentas e Bibliotecas:
- **Normalização**: unicodedata, chardet
- **OCR**: pytesseract, easyocr, paddleocr
- **Imagens**: Pillow, OpenCV
- **Testing**: pytest, hypothesis

---

**Última atualização**: 12/10/2025  
**Responsável**: Architect  
**Aprovação**: Pendente SM