# Credentials Consistency Checklist

## Purpose
Verificação sistemática da consistência de credenciais em todos os arquivos do projeto

## Checklist Items

### ��� Database Credentials
- [ ] **Database Name**: `teachershub_enem` usado consistentemente em todos os arquivos
- [ ] **PostgreSQL Admin**: `postgres` / `postgres123` em docker-compose.yml e scripts
- [ ] **TeachersHub App User**: `teachershub_app` / `teachershub123` em todos os connection strings
- [ ] **ENEM RAG Service User**: `enem_rag_service` / `enem123` em todos os connection strings
- [ ] **Schema Names**: `teachers_hub`, `enem_questions`, `shared_resources` consistentes

### ��� JWT Configuration
- [ ] **JWT Secret Key**: `TeachersHub-ENEM-Integration-Secret-Key-2024` idêntico em todos os serviços
- [ ] **JWT Issuer**: `TeachersHub.ENEM.Api` consistente
- [ ] **JWT Audience**: `TeachersHub.ENEM.Client` consistente

### ��� Service Ports
- [ ] **TeachersHub API**: Porta `5000` em docker-compose.yml e documentação
- [ ] **ENEM RAG Service**: Porta `8000` em docker-compose.yml e documentação  
- [ ] **PostgreSQL**: Porta `5432` consistente
- [ ] **Redis**: Porta `6379` consistente

### ��� Network Configuration
- [ ] **Network Name**: `teachershub-network` em todos os serviços
- [ ] **Subnet**: `172.20.0.0/16` consistente
- [ ] **Container Names**: Seguem padrão definido (teachershub-*, enem-*)

### ��� File Validation
- [ ] **docker-compose.yml**: Todas as environment variables coincidem com referência
- [ ] **.env files**: Valores consistentes com credenciais de referência
- [ ] **Application configs**: Connection strings usam credenciais corretas
- [ ] **SQL Scripts**: Usuários e senhas coincidem com referência
- [ ] **Dockerfiles**: Variáveis de ambiente consistentes
- [ ] **Test configs**: Credenciais de teste coincidem (quando aplicável)

### ��� Integration Testing
- [ ] **Health Checks**: URLs e portas corretas em docker-compose.yml
- [ ] **Service Discovery**: Nomes de serviço consistentes entre containers
- [ ] **Volume Mounts**: Paths corretos para arquivos de credenciais
- [ ] **Dependency Order**: Containers dependem dos serviços corretos

### ��� Documentation Consistency  
- [ ] **README.md**: Credenciais documentadas coincidem com implementação
- [ ] **Architecture docs**: Portas e configurações consistentes
- [ ] **Setup Instructions**: Comandos usam credenciais corretas
- [ ] **Troubleshooting**: Referências a credenciais são corretas

### ��� Security Considerations
- [ ] **Development Only**: Credenciais marcadas claramente como development-only
- [ ] **No Hardcoding**: Credenciais vêm de variáveis de ambiente quando possível
- [ ] **Reference File**: Arquivo de referência atualizado e completo
- [ ] **Team Communication**: Mudanças de credenciais comunicadas à equipe

## Critical Failures
❌ **FAIL CONDITIONS** (Bloqueiam deploy/release):
- Credenciais inconsistentes entre serviços críticos
- JWT secrets diferentes entre componentes
- Connection strings com usuários/senhas incorretas
- Portas conflitantes ou inconsistentes

⚠️ **CONCERN CONDITIONS** (Requerem atenção):
- Documentação desatualizada
- Comentários com credenciais antigas
- Arquivos de exemplo inconsistentes
- Logs com referências a credenciais antigas

## Validation Commands
```bash
# Validação completa
*validate-credentials

# Validação específica
*validate-credentials docker-compose.yml

# Relatório detalhado
*validate-credentials --detailed

# Check específico de conexões de banco
docker-compose exec postgres psql -U postgres -c "\du"
```

## Remediation Actions
1. **Inconsistency Found**: Update file to match reference credentials
2. **Reference Update**: Update `shared/database/init/00-dev-credentials.md` first
3. **Team Communication**: Notify team of credential changes via commit message
4. **Environment Rebuild**: Recreate containers after credential changes
5. **Integration Testing**: Run full test suite after credential updates

## Success Criteria
✅ All credentials match reference file exactly  
✅ All services can connect with specified credentials  
✅ Documentation reflects actual implementation  
✅ Integration tests pass with current credentials  
✅ No security vulnerabilities in credential handling  

## Notes
- Este checklist deve ser executado antes de qualquer commit que altere configurações
- Mudanças de credenciais requerem aprovação da equipe
- Sempre atualizar arquivo de referência primeiro, depois implementação
- Documentar rationale para qualquer desvio das credenciais padrão
