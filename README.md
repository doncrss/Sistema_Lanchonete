# Lanchotech

Sistema de pedidos para lanchonete com API FastAPI, banco SQLAlchemy e frontend estático responsivo. O cliente consulta o cardápio e faz pedidos; a equipe acompanha pedidos e gerencia produtos em uma área protegida por chave administrativa.

## Rodar localmente

Requer Python 3.10+ e Node.js apenas para gerar a configuração do frontend.

1. Na pasta `Sistema_Lanchonete`, crie e ative um ambiente virtual e instale as dependências:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Configure as variáveis locais copiando `.env.example` para `.env`. Defina uma chave própria em `ADMIN_TOKEN`. O SQLite local é criado automaticamente em `banco.db`.
3. Inicie a API em um terminal:

   ```powershell
   uvicorn app.main:app --reload
   ```

4. Em outro terminal, dentro de `frontend`, gere a configuração (o padrão local aponta para `http://localhost:8000`) e sirva os arquivos:

   ```powershell
   node build-config.js
   py -m http.server 5500
   ```

5. Acesse `http://localhost:5500`. A documentação interativa da API fica em `http://localhost:8000/docs`.

O primeiro início cadastra um cardápio de demonstração somente quando a tabela de produtos está vazia. Depois, use **Área da equipe** para entrar com `ADMIN_TOKEN`.

## Publicar os dois serviços no Render

O `render.yaml` configura a API (`lanchotech-api`) e o frontend estático (`lanchotech-frontend`). Para dados persistentes em produção, use PostgreSQL gerenciado:

1. Crie um banco PostgreSQL no Render e copie a **Internal Database URL**.
2. Crie os serviços a partir do Blueprint deste repositório. Quando solicitado, informe essa URL em `DATABASE_URL` e gere um valor longo e aleatório para `ADMIN_TOKEN`. Não use a chave local de exemplo em produção.
3. O frontend usa `https://lanchotech-api.onrender.com` por padrão. Se o Render atribuir outra URL à API, atualize `API_BASE_URL` nas variáveis do serviço estático e faça um novo deploy.
4. Se quiser restringir chamadas do navegador, defina `CORS_ORIGINS` no serviço da API para a origem exata do frontend, por exemplo `https://lanchotech-frontend.onrender.com`.

O Render injeta `PORT` na API. O esquema inicial do banco é criado automaticamente; o campo de preço unitário dos itens de pedido também é adicionado a bancos existentes sem apagar os dados.

## O que está incluído

- Cardápio por categoria, busca, sacola e checkout responsivo.
- Pedidos de entrega, retirada ou consumo no local. O total e os preços são calculados pela API a partir do cardápio; não são aceitos valores enviados pelo navegador.
- Painel administrativo com chave via `X-Admin-Token`, listagem/andamento dos pedidos e cadastro/exclusão de produtos.
- Persistência de clientes, itens, pedidos e histórico de status nas tabelas SQLAlchemy existentes.
- Health check em `/api/health`; endpoints documentados automaticamente em `/docs`.

O sistema registra pedidos, mas não processa pagamentos online. O pagamento é combinado no recebimento/retirada.
