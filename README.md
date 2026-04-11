# SalvAI — Sistema de Emergências

MVP de resposta a emergências para prefeituras brasileiras: CAD digital + triagem IA + despacho automático + rastreamento de frota.

**Stack:** FastAPI + SQLAlchemy (SQLite) · React Native / Expo (TypeScript) · Claude Sonnet API · Leaflet.js

---

## Estrutura do repositório

```
sistema-emergencias/
├── app/                    # Backend FastAPI
│   ├── main.py             # Endpoints HTTP
│   ├── models.py           # SQLAlchemy ORM
│   ├── schemas.py          # Pydantic schemas
│   ├── database.py         # Engine + sessão
│   └── seed.py             # Popular DB com dados de teste
├── app-cidadao/            # App do cidadão (Expo / RN)
│   └── src/
│       ├── screens/        # Login, Home, Acompanhamento
│       ├── services/       # api.ts, notifications.ts
│       ├── navigation.ts
│       └── theme.ts
├── app-agente/             # App do agente (Expo / RN)
│   └── src/
│       ├── screens/        # Login, Chamados, Atendimento
│       ├── services/       # api.ts
│       ├── navigation.ts
│       └── theme.ts
└── README.md
```

---

## Setup no Macbook (do zero)

### 1. Clonar

```bash
git clone https://github.com/hevertontim-prog/sistema-emergencias.git
cd sistema-emergencias
```

### 2. Backend FastAPI

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi 'uvicorn[standard]' sqlalchemy pydantic python-dotenv anthropic httpx
```

Criar `.env` na raiz (não vai vir do git — está no `.gitignore`):

```bash
echo 'ANTHROPIC_API_KEY=sk-ant-xxxxx' > .env
```

Popular o banco SQLite com dados de teste (5 agentes, 1 usuário João Silva):

```bash
python -m app.seed
```

Subir servidor:

```bash
uvicorn app.main:app --reload --port 8006
```

Testar:

```bash
curl http://localhost:8006/frota
```

### 3. App Cidadão (Expo Web)

Em outro terminal:

```bash
cd app-cidadao
npm install
npx expo start --web --port 8081
```

Abre em `http://localhost:8081`.

### 4. App Agente (Expo Web)

Em mais um terminal:

```bash
cd app-agente
npm install
npx expo start --web --port 8082
```

Abre em `http://localhost:8082`.

---

## Convenção de portas

| Serviço             | URL                       |
| ------------------- | ------------------------- |
| Backend FastAPI     | `http://localhost:8006`   |
| App Cidadão (web)   | `http://localhost:8081`   |
| App Agente (web)    | `http://localhost:8082`   |

A URL do backend está hardcoded em:

- `app-cidadao/src/services/api.ts` (linha 1)
- `app-agente/src/services/api.ts` (linha 1)

Se precisar mudar de porta, editar nos dois arquivos.

---

## Endpoints da API

| Método | Rota                              | Descrição                                 |
| ------ | --------------------------------- | ----------------------------------------- |
| POST   | `/usuario`                        | Cria usuário (ou retorna existente por CPF) |
| PUT    | `/usuario/{id}/push-token`        | Salva Expo push token                     |
| POST   | `/emergencia`                     | Cria emergência **e auto-despacha**       |
| GET    | `/emergencia/{id}`                | Busca emergência por ID                   |
| GET    | `/frota`                          | Lista agentes + despacho ativo de cada um |
| POST   | `/despacho`                       | Despacho manual (mesmo helper interno)    |
| PATCH  | `/despacho/{id}/status`           | Atualiza status (`a_caminho`/`no_local`/`finalizado`) |
| POST   | `/posicao`                        | Atualiza GPS de um agente                 |
| POST   | `/triagem`                        | Triagem IA via Claude Sonnet              |

### Auto-despacho

`POST /emergencia` chama internamente `_executar_despacho()` que:

1. Busca agentes com `status == "disponivel"`
2. Para cada um, pega a última `PosicaoGPS` registrada
3. Calcula distância com Haversine até a emergência
4. Atribui o mais próximo, marca como `em_atendimento`
5. **Fallback:** se ninguém tem GPS, pega o primeiro disponível mesmo assim
6. Dispara push notification pro cidadão via Expo Push API

---

## Fluxo end-to-end de teste

1. **App Cidadão** (8081) → Login com CPF qualquer + nome → Home
2. Botão **EMERGÊNCIA** → permite GPS (ou usa fallback Brasília)
3. Backend cria emergência, auto-despacha pro agente mais próximo, retorna protocolo
4. Tela **Acompanhamento** abre com mapa Leaflet + status badge atualizando a cada 5s
5. **App Agente** (8082) → Login com matrícula = ID do agente despachado → tela Chamados mostra o card
6. Toca no card → tela **Atendimento** → botões avançam: 🚑 a caminho → 📍 no local → ✅ finalizado
7. Cidadão vê o status mudando em tempo real

---

## Modelos do banco

- **Usuario** — id, cpf, nome, push_token
- **Agente** — id, nome, matricula, tipo_recurso (`policia`/`ambulancia`/`bombeiro`), status (`disponivel`/`em_atendimento`)
- **Viatura** — id, placa, tipo, id_agente
- **Emergencia** — id, lat, lon, tipo, gravidade, status, id_usuario, created_at
- **Despacho** — id, id_emergencia, id_agente, status, created_at
- **PosicaoGPS** — id, id_agente, lat, lon, timestamp

---

## O que **não** está no repositório

| Item                  | Por quê                       | Como recriar                   |
| --------------------- | ----------------------------- | ------------------------------ |
| `.env`                | Contém `ANTHROPIC_API_KEY`    | Criar manualmente              |
| `emergencias.db`      | Banco local SQLite            | `python -m app.seed`           |
| `node_modules/`       | Dependências npm              | `npm install` em cada app      |
| `.expo/`              | Cache do Expo                 | Gerado automaticamente         |
| `.venv/`              | Virtualenv Python             | Recriar conforme passo 2       |

---

## Troubleshooting

**Porta ocupada:** Mac não tem `taskkill` — use `lsof -ti:8006 | xargs kill -9`.

**CORS:** Backend já tem `CORSMiddleware` com `allow_origins=["*"]`. Se navegador reclamar, conferir que está hitando a porta certa.

**Push notifications:** Só funcionam em dispositivo físico via Expo Go. No Web são silenciosamente puladas (`Device.isDevice === false`).

**Triagem IA falhando:** Verificar `.env` com `ANTHROPIC_API_KEY` válida e modelo `claude-sonnet-4-6` disponível na conta.

**`module 'app' not found`:** Rodar `uvicorn` da raiz do repositório, não de dentro de `app/`.

---

## Próximos passos (roadmap)

- [ ] Build TestFlight do app-cidadão (iOS nativo)
- [ ] Dashboard web do gestor (React + Leaflet) — Semana 4
- [ ] Integração com sistemas existentes da prefeitura (CAD/AVL legados)
- [ ] Relatórios e métricas de tempo de resposta
