# TROC.AI — Tinder do Conhecimento

Plataforma para buscar perfis, identificar compatibilidade de habilidades e permitir que usuários demonstrem interesse mútuo para viabilizar uma permuta.

## Componentes

- `frontend/`: interface React + Vite.
- `backend/`: API REST em Python + Flask.
- `Bd - Troc.AI/`: banco SQLite, modelo relacional, regras de matching e testes.
- `docs/API.md`: contrato da API para integração do front-end.
- `backend/README.md`: instruções de preparação e execução do back-end.

## Início rápido

Na raiz do repositório, crie e ative um ambiente virtual Python, instale as dependências de `backend/requirements.txt` e inicie a API:

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m backend.app
```

Em outro terminal, inicie o front-end:

```bash
cd frontend
npm install
npm run dev
```

A API fica em `http://127.0.0.1:3001`; o front-end Vite fica em `http://localhost:5173`. Consulte `docs/API.md` antes de integrar componentes React aos endpoints.

## 🎬 Demonstração do Sistema (Prova de Conceito)
👉 [Assistir ao Vídeo de Demonstração](https://youtu.be/AQviN4rIISk).

## 📋 Qualidade e Testes (QA)
👉 [Acessar Relatório de QA Completo](Relatorio_QA_Trocai.pdf).
