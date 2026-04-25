# Acordo iPhone 14 Pro Max

Sistema de prestação de contas com backend Python + PostgreSQL.

## Estrutura
```
acordo/
├── main.py              # Backend FastAPI
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── static/
    └── index.html       # Frontend
```

## Deploy no EasyPanel

### 1. Suba o projeto para um repositório Git (GitHub/GitLab)

### 2. No EasyPanel:
- Novo App → **Docker Compose**
- Aponte para o repositório
- O EasyPanel vai usar o `docker-compose.yml` automaticamente

### 3. Variáveis de ambiente (mude os PINs!):
```
PIN_USUARIO=1234    ← PIN do funcionário (acesso completo)
PIN_PATRON=5678     ← PIN do patrão (só visualização)
DATABASE_URL=postgresql://acordo_user:acordo_pass@db:5432/acordo_iphone
```

### 4. Domínio:
- Aponte `acordo.alissonjoias.com.br` para o EasyPanel
- Configure HTTPS (obrigatório para o GPS funcionar)
- Porta: **8000**

## PINs padrão (MUDE antes de subir!)
- Funcionário: `1234`
- Patrão: `5678`
