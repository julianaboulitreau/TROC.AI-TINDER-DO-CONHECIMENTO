# TROC.AI - Tinder do Conhecimento

Aplicação web para buscar perfis, compartilhar habilidades e criar conexões com
interesse mútuo. O front-end React/Vite se comunica com uma API HTTP em Python,
que utiliza o repositório SQLite em `Bd - Troc.AI`.

## Executar localmente

Requisitos: Python 3.8+ e Node.js.

1. Em um terminal, inicie o backend:

   ```powershell
   cd "Bd - Troc.AI"
   python api.py
   ```

   Na primeira execução, o banco `trocai.db` e os perfis de demonstração são
   criados automaticamente. O servidor fica em `http://127.0.0.1:3001`.

2. Em outro terminal, inicie o front-end:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

   Abra o endereço exibido pelo Vite (por padrão
   `http://localhost:5173`). O Vite encaminha as chamadas `/api` ao backend.

3. Para testar, entre com um perfil de demonstração:

   - E-mail: `lucas.andrade@troc.ai`
   - Senha: `senha123`

   Os demais perfis de demonstração também usam a senha `senha123`. Para testar
   um match, entre em duas sessões/perfis distintos e ambos devem se conectar.

## Testes do backend

```powershell
cd "Bd - Troc.AI"
python -m unittest -v
```

O front-end pode ser validado com `npm run build` dentro da pasta `frontend`.
