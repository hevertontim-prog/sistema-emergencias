# Contexto pro Claude Code

> Este arquivo é carregado automaticamente em toda sessão do Claude Code dentro deste repositório. Serve como ponte de contexto entre máquinas (Windows → Mac) já que a memória local em `~/.claude/projects/` não migra.

---

## Quem é o usuário

**Heverton Amaral** — fundador solo, dev solo. Está construindo o **SalvAI**, um MVP de sistema de emergências para vender pra prefeituras brasileiras. Trabalha sob prazo apertado (timeline de 30 dias). Foco extremo em **MVP funcional** — não em código bonito, não em features extras, não em refatorações premaduras.

### Como ele gosta de colaborar

- **Respostas curtas e diretas.** Sem preâmbulo, sem recap, sem "vou fazer X agora". Só faz.
- **Português.** Mistura inglês/português é ok mas o default é PT-BR.
- **Pragmatismo > perfeição.** Se um hack desbloqueia o MVP, é o caminho certo.
- **Avisar se eu detectar feature creep.** Se ele pedir algo fora do escopo do MVP, eu devo alertar antes de implementar.
- **Validar antes de expandir.** Não construir nada que ainda não foi validado com cliente real.
- Quando ele aprova um plano com "manda bala" / "aplica tudo" / "exato", aplicar sem mais perguntas.

---

## O que é o SalvAI

Sistema de emergências composto por 4 partes:

1. **Backend FastAPI** (`app/`) — recebe emergências, despacha agentes via Haversine, faz triagem IA com Claude Sonnet, envia push notifications
2. **App Cidadão** (`app-cidadao/`) — RN/Expo. Botão de emergência → GPS → cria protocolo → tela de acompanhamento com mapa Leaflet
3. **App Agente** (`app-agente/`) — RN/Expo. Lista de chamados atribuídos → tela de atendimento com workflow (a_caminho → no_local → finalizado)
4. **Dashboard Gestor** (Semana 4, ainda não começado) — React + Leaflet para a prefeitura visualizar a operação

**Modelo de venda:** SaaS para prefeituras pequenas/médias do Brasil. Lead inicial é a prefeitura de [REDACTED] via contato pessoal.

---

## Stack e convenções

| Camada       | Tecnologia                              |
| ------------ | --------------------------------------- |
| Backend      | FastAPI + SQLAlchemy + SQLite           |
| ORM          | SQLAlchemy 2.x style                    |
| Validação    | Pydantic v2 (`model_config = {"from_attributes": True}`) |
| Mobile       | Expo SDK 52 + TypeScript                |
| Navegação    | `@react-navigation/native-stack`        |
| GPS          | `expo-location` (com `Promise.race` timeout 5s) |
| Push         | `expo-notifications` + Expo Push API server-side via `httpx` |
| Mapas        | Leaflet via iframe `srcDoc` (funciona em web e nativo) |
| IA Triagem   | `anthropic` SDK + `claude-sonnet-4-6`   |

### Convenção de portas (importante)

| Serviço             | Porta |
| ------------------- | ----- |
| Backend FastAPI     | 8006  |
| App Cidadão (web)   | 8081  |
| App Agente (web)    | 8082  |

A URL do backend está hardcoded em:
- `app-cidadao/src/services/api.ts:1`
- `app-agente/src/services/api.ts:1`

### Tema visual

Dark theme nos dois apps, definido em `src/theme.ts`:
- Cidadão: primary **vermelho** (`#ef4444` ou similar) — cor de emergência
- Agente: primary **azul** (`#3b82f6`) — diferenciar contexto

### Padrões de código

- **Pydantic schemas:** sempre com `model_config = {"from_attributes": True}` quando saem do ORM
- **Endpoints FastAPI:** seguem ordem `# ─── NOME ───` como divisor visual em `main.py`
- **Helper de despacho:** `_executar_despacho(emergencia, db)` em `app/main.py` é compartilhado entre `POST /emergencia` (auto) e `POST /despacho` (manual). Tem fallback: se nenhum agente tem GPS, pega o primeiro disponível.
- **CORS:** `allow_origins=["*"]` (MVP — depois restringir)
- **API client no front:** função genérica `request<T>()` com tratamento de erro padronizado

---

## Estado atual do projeto (último commit: `2ca3dd2`, 13/07/2026)

### O que já funciona end-to-end

1. Cidadão faz login com CPF + nome → backend cria/recupera usuário
2. Cidadão descreve o que está acontecendo (opcional, até 300 chars) e escolhe o tipo → GPS (fallback Brasília) → `POST /emergencia`. Se descreveu e não informou gravidade, a IA tria (corrige até o tipo se necessário); sem descrição, gravidade default 3.
3. Backend auto-despacha o agente disponível mais próximo (Haversine)
4. Cidadão vai pra tela Acompanhamento → mapa Leaflet, polling 3s, prioridade/tipo/descrição refletidos
5. Push notification dispara pro celular do cidadão (só dispositivo físico) e, se o agente tiver `push_token`, pra ele também com o briefing da IA
6. Agente loga com **ID numérico** do agente (não a matrícula tipo `PM001`) → tela Chamados mostra o despacho ativo
7. Agente abre o chamado e vê um card com tipo/gravidade (selo G1–G5 colorido)/descrição completa, antes dos botões de status
8. Agente avança status: a_caminho → no_local → finalizado
9. Cidadão vê o status mudando em tempo real
10. Painel do gestor (`dashboard/index.html`, estático, mount `/dashboard`): entrada manual de ocorrência com CEP/endereço/pino arrastável, trilha de auditoria, cadastro de agente/viatura/operador, botão Finalizar em qualquer chamado ativo

### Endpoints implementados

```
POST   /usuario                            — cria ou retorna por CPF
PUT    /usuario/{id}/push-token            — salva Expo push token
PUT    /agente/{id}/push-token             — idem, pro agente
POST   /emergencia                         — cria (cidadão) + triagem IA opcional + auto-despacha
GET    /emergencia/{id}
GET    /emergencia/{id}/acompanhamento     — status, tipo, gravidade, descricao, ETA, posição do agente
PATCH  /emergencia/{id}/finalizar          — finaliza c/ ou sem despacho ativo, libera agente
GET    /frota                              — agentes + despacho_id/emergencia_id ativos
GET    /emergencias                        — lista pro dashboard
POST   /despacho                           — manual (mesmo helper que o automático)
PATCH  /despacho/{id}/status
POST   /posicao                            — GPS update do agente
POST   /triagem                            — chamada direta à IA (usada pelo app-agente)
POST   /ocorrencias/manual                 — modo operador (central), triagem IA automática
GET    /auditoria                          — trilha de eventos
POST   /agentes · GET /agentes             — cadastro
POST   /viaturas
POST   /operadores · GET /operadores
```

### Modelos do banco

- `Usuario` — id, cpf, nome, push_token
- `Agente` — id, nome, matricula, tipo_recurso (`policia`/`ambulancia`/`bombeiro`), status, push_token
- `Viatura` — id, placa, tipo, id_agente
- `Emergencia` — id, lat, lon, tipo, gravidade, status, descricao, id_usuario, created_at
- `Despacho` — id, id_emergencia, id_agente, status, created_at
- `PosicaoGPS` — id, id_agente, lat, lon, timestamp
- `AuditLog` — id, ator, acao, entidade, entidade_id, detalhe, created_at
- `Operador` — id, nome, matricula, ativo, created_at

### O que **não** está no git (recriar manualmente no Mac)

- `.env` (raiz) — contém `ANTHROPIC_API_KEY`
- `app-cidadao/.env` e `app-agente/.env` — `EXPO_PUBLIC_API_KEY` (mesma key do `SALVAI_API_KEY` do Railway). **Sem isso o app builda normal mas todo POST/PUT/PATCH falha com 401 silencioso** (login e criação de emergência incluídos).
- `emergencias.db` — rodar `python -m app.seed`
- `node_modules/` — `npm install` em cada app
- `.venv/` — recriar venv Python

---

## Lições aprendidas (gotchas que já me custaram tempo)

1. **CORS:** sem `CORSMiddleware`, Expo Web não fala com FastAPI. Adicionar antes de qualquer endpoint novo.
2. **GPS no Expo Web:** `Location.getCurrentPositionAsync` pode travar indefinidamente. SEMPRE envolver em `Promise.race` com timeout 5s.
3. **Leaflet em RN:** usar iframe com `srcDoc` é mais confiável que pacotes nativos. Funciona em web e mobile.
4. **Layout de mapa:** NUNCA dar `flex: 1` ao container do mapa numa tela com mais conteúdo — ele come tudo. Usar `height: 300` fixo + `ScrollView` no pai.
5. **`Alert.alert` no web:** `onPress` callback do botão não dispara confiavelmente. Para fluxos críticos, navegar direto sem Alert.
6. **Auto-despacho duplicado:** o front NÃO deve mais chamar `/despacho` — backend faz dentro do `POST /emergencia`. Se for adicionar feature de despacho manual, cuidado pra não duplicar.
7. **Filtro de chamados do agente:** em `ChamadosScreen.tsx`, filtrar por `f.id === agenteId && f.despacho_id` — NÃO `f.id_agente` (esse campo não existe na resposta de `/frota`).
8. **`uvicorn` deve rodar da raiz:** `uvicorn app.main:app`, não de dentro de `app/`.
9. **Hot reload Python:** às vezes precisa limpar `__pycache__` manualmente quando o reload não pega.
10. **Portas zumbis:** se uvicorn não morrer, no Mac usar `lsof -ti:8006 | xargs kill -9`.
11. **Push notifications no Web:** sempre falham silenciosamente (não é dispositivo). Não logar como erro — só pular.
12. **Schemas Pydantic v2:** `model_config = {"from_attributes": True}` é obrigatório quando o response model vem de objeto SQLAlchemy (substituiu o `Config: orm_mode = True`).
13. **Tela branca no app-cidadao (web):** extensões de navegador (tradutores, bloqueadores de ads, Grammarly etc.) podem mexer no DOM por fora do React e causar `Uncaught NotFoundError: removeChild` — sem Error Boundary isso desmonta a árvore inteira. Sintoma: título da aba muda (React navegou) mas a tela fica branca. Diagnóstico: testar em aba anônima (extensões desligadas por padrão) — se sumir o problema, é isso. Mitigado com `app-cidadao/src/ErrorBoundary.tsx` envolvendo o `App.tsx`, mas o ideal é sempre testar em aba anônima antes de assumir bug no código.
14. **`Base.metadata.create_all` só cria tabelas novas, não adiciona colunas a tabelas existentes.** Se adicionar uma coluna a um modelo que já tem tabela em produção (Postgres), o boot quebra com "coluna não existe" (502 em tudo, `db.query(Model).count()` já falha no startup). Sem Alembic, use um patch aditivo idempotente logo após o `create_all` (ver `_garantir_colunas_novas` em `app/main.py` — `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` no Postgres, checagem via `PRAGMA table_info` no SQLite). Sempre testar localmente simulando o schema antigo (criar a tabela manualmente sem a coluna nova) antes de fazer deploy.

---

## O que NÃO fazer

- ❌ Não adicionar features fora do escopo do MVP de 30 dias sem alertar
- ❌ Não refatorar código que já funciona "porque tá feio"
- ❌ Não adicionar testes/CI/Docker antes de a primeira venda acontecer
- ❌ Não trocar SQLite por Postgres antes de validar com cliente
- ❌ Não introduzir TypeScript strict mode em código que já compila
- ❌ Não criar abstrações genéricas para um único caso de uso
- ❌ Não commitar `.env`, `*.db`, `node_modules/`
- ❌ Não rodar `expo prebuild` ou `eject` — quebra o fluxo Expo Web

---

## Próximos passos planejados

- [ ] Build TestFlight do app-cidadão (iOS) — Semana 3 final
- [ ] Dashboard web do gestor (React + Leaflet) — Semana 4
- [ ] Demo gravada para enviar ao lead da prefeitura
- [ ] Material de venda (deck + um-pager)

---

## Como me brifar quando começar uma sessão nova no Mac

Ao iniciar a primeira sessão no Mac, você (Claude) vai ler este arquivo automaticamente. Não precisa de instrução adicional do Heverton — só continuar de onde parou. Se ele mandar algo ambíguo, assumir que é continuação do SalvAI e referenciar este arquivo.

A memória local antiga (`~/.claude/projects/.../memory/`) **não migra entre máquinas**. Conforme aprender coisas novas no Mac, salvar de novo na memória local de lá. Os pontos críticos já estão registrados aqui neste CLAUDE.md.
