# Validate Credentials Consistency Task

## Purpose
Valida consistência de credenciais em todos os arquivos de configuração do projeto

## Inputs Required
- project_root: Caminho raiz do projeto
- target_files: Lista de arquivos para validar (opcional - se não especificado, valida todos)

## Process

### Step 1: Load Reference Credentials
```markdown
Carregar arquivo de referência: `shared/database/init/00-dev-credentials.md`
Extrair todas as credenciais padrão:
- Database names, usernames, passwords
- JWT secrets, issuer, audience
- Service ports
- Network configurations
```

### Step 2: Scan Configuration Files
```markdown
Escanear arquivos de configuração:
- docker-compose.yml
- .env files
- application configuration files
- Dockerfiles
- Scripts de inicialização
- Arquivos de teste
```

### Step 3: Validate Consistency
```markdown
Para cada credencial encontrada:
1. Comparar com valores de referência
2. Identificar inconsistências
3. Listar arquivos com problemas
4. Sugerir correções específicas
```

### Step 4: Generate Report
```markdown
Criar relatório de validação:
- ✅ Arquivos consistentes
- ⚠️ Inconsistências menores
- ❌ Inconsistências críticas
- ��� Ações recomendadas
```

## Expected Outputs
- **Validation Report**: Lista detalhada de consistências e inconsistências
- **Action Items**: Lista de correções necessárias
- **Status**: PASS/CONCERNS/FAIL based on criticality

## Success Criteria
- Todas as credenciais críticas consistentes
- Relatório detalhado gerado
- Ações corretivas identificadas (se necessário)

## Failure Conditions
- Arquivo de referência não encontrado
- Inconsistências críticas detectadas
- Falha na leitura de arquivos de configuração

## Usage Examples
```bash
# Validar todo o projeto
*validate-credentials

# Validar arquivos específicos
*validate-credentials docker-compose.yml .env

# Validar com relatório detalhado
*validate-credentials --detailed
```

## Related Tasks
- execute-checklist.md (para usar em checklists de qualidade)
- apply-qa-fixes.md (para correções pós-validação)
