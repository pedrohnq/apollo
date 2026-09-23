# Estrutura do projeto

API Django para uma carteira financeira, com depósito em dólar convertido pela
cotação atual. O projeto serve de exemplo de testes automatizados, mock,
cobertura e CI.

## Árvore

```
apollo/
├── apollo/                  configuração do projeto
│   ├── settings.py          apps, middleware, banco (via DATABASE_URL)
│   ├── urls.py              rotas raiz: /admin/ e /api/
│   ├── wsgi.py              ponto de entrada do gunicorn
│   └── asgi.py
│
├── financeiro/              app de domínio
│   ├── models.py            Carteira: deposito, saque, deposito_em_dolar
│   ├── services.py          integração com a API de cotação
│   ├── serializers.py       validação de entrada e formato de saída
│   ├── views.py             DepositarEmDolarView (APIView do DRF)
│   ├── exceptions.py        APIException de 503
│   ├── urls.py              rotas do app
│   ├── admin.py             registro da Carteira no admin
│   ├── migrations/
│   └── tests/
│       ├── test_services.py testes de função
│       ├── test_models.py   testes de model
│       ├── test_views.py    testes de view
│       └── test_e2e.py      teste de fluxo completo
│
├── .github/workflows/ci.yml pipeline de testes e cobertura
├── Dockerfile               imagem da aplicação
├── docker-compose.yml       web + postgres
├── entrypoint.sh            espera o banco, migra, collectstatic, sobe gunicorn
├── .coveragerc              configuração do coverage
├── requirements.txt         dependências de produção
└── requirements-dev.txt     produção + coverage e model-bakery
```

## Camadas

```mermaid
flowchart TB
    C(["Cliente HTTP"])
    V["<b>views.py</b><br/>autenticação e contrato HTTP"]
    S["<b>serializers.py</b><br/>validação da entrada"]
    M["<b>models.py</b><br/>regra de negócio"]
    SV["<b>services.py</b><br/>chamada à API externa"]
    API(["API de cotação"])
    DB[("PostgreSQL")]

    C --> V --> S --> M --> SV --> API
    M --> DB

    classDef borda fill:#e0e7ff,stroke:#4338ca,color:#1e1b4b
    classDef externo fill:#fee2e2,stroke:#b91c1c,color:#450a0a
    class V,S,M,SV borda
    class API,DB externo
```

Cada camada só conhece a de baixo. A separação existe para que `services.py`
concentre tudo que fala com a rede — o que torna o mock trivial nos testes.

## Fluxo de um depósito

```mermaid
sequenceDiagram
    autonumber
    participant C as Cliente
    participant V as View
    participant S as Serializer
    participant M as Carteira
    participant SV as services
    participant A as API de cotação
    participant DB as PostgreSQL

    C->>V: POST valor_em_dolar = 100.00
    V->>V: IsAuthenticated
    V->>S: valida entrada
    S-->>V: Decimal 100.00
    V->>M: deposito_em_dolar(100)
    M->>SV: buscar_cotacao_dolar()
    SV->>A: GET USD-BRL
    A-->>SV: bid = 5.20
    SV-->>M: Decimal 5.20
    M->>M: 100 x 5.20 = 520.00
    M->>DB: UPDATE saldo
    M-->>V: Decimal 520.00
    V-->>C: 201 valor_creditado = 520.00
```

## Endpoint

```
POST /api/carteira/deposito-dolar/
```

Entrada:

```json
{ "valor_em_dolar": "100.00" }
```

Resposta (201):

```json
{ "valor_creditado": "520.00", "saldo_atual": "520.00" }
```

| Status | Quando |
|---|---|
| 201 | depósito realizado |
| 400 | valor ausente, não numérico ou menor que 0.01 |
| 403 | usuário não autenticado |
| 404 | usuário sem carteira |
| 503 | API de cotação indisponível |

## Testes

```bash
coverage run manage.py test financeiro
coverage report
```

Os quatro arquivos se distinguem pelo ponto onde cortam a cadeia com um mock:

```mermaid
flowchart TB
    V["views.py"]
    S["serializers.py"]
    M["models.py"]
    BC["services.buscar_cotacao_dolar()"]
    RG["requests.get()"]
    API(["rede"])

    V --> S --> M --> BC --> RG --> API

    classDef unit fill:#fde68a,stroke:#b45309,color:#451a03
    classDef e2e fill:#bfdbfe,stroke:#1d4ed8,color:#172554
    class BC unit
    class RG e2e
```

O nó **amarelo** é onde `test_models.py` e `test_views.py` cortam: tudo abaixo
dele é substituído. O **azul** é onde `test_e2e.py` corta — só a chamada de
rede sai, e todas as camadas acima rodam de verdade.

| Arquivo | Alvo do mock | Roda de verdade |
|---|---|---|
| `test_services.py` | `requests.get` | services |
| `test_models.py` | `buscar_cotacao_dolar` | models |
| `test_views.py` | `buscar_cotacao_dolar` | views, serializers, models |
| `test_e2e.py` | `requests.get` | tudo |

## Infraestrutura

```mermaid
flowchart LR
    U(["localhost:8000"])

    subgraph compose["docker compose"]
        W["<b>web</b><br/>gunicorn + Django"]
        D[("<b>db</b><br/>postgres:16")]
        VOL[("volume<br/>pgdata")]
        W -->|"host: db:5432"| D
        D --- VOL
    end

    U --> W

    classDef svc fill:#dcfce7,stroke:#15803d,color:#052e16
    class W,D svc
```

O `web` só inicia depois que o healthcheck do `db` passa. O host do banco é
`db`, não um IP — o Compose resolve pelo DNS interno.

## Execução

```bash
docker compose up --build
```

O `--build` é necessário quando muda `requirements.txt`, `Dockerfile` ou
`entrypoint.sh`. Para mudanças em código Python, `docker compose restart web`
basta — o código é montado por volume.
