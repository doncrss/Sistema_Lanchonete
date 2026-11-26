# Lanchotech

Sistema de pedidos para lanchonete com API FastAPI, banco SQLAlchemy e frontend responsivo. O mesmo serviço serve o site e a API; não é necessário contratar um serviço separado para o frontend.

## Rodar localmente

Requer Python 3.10+.

1. Na pasta `Sistema_Lanchonete`, crie e ative um ambiente virtual e instale as dependências:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Copie `.env.example` para `.env` e escolha uma chave local em `ADMIN_TOKEN`. O SQLite é criado automaticamente em `banco.db`.
3. Inicie o site e a API juntos:

   ```powershell
   uvicorn app.main:app --reload
   ```

4. Abra `http://localhost:8000`. A documentação da API está em `http://localhost:8000/docs`.

O primeiro início cadastra produtos de demonstração somente se o cardápio estiver vazio. A área administrativa usa a chave definida em `ADMIN_TOKEN`.

## Publicar no Render Free

O `render.yaml` cria **um único Web Service Python no plano Free**. Esse serviço entrega o site e a API pelo mesmo domínio, sem serviço Static separado e sem configuração de CORS ou de URL do frontend.

1. Envie o projeto atualizado ao GitHub.
2. No Render, crie um Blueprint para o repositório e confira que ele encontrou o `render.yaml` da raiz.
3. Informe um valor longo e aleatório para `ADMIN_TOKEN`. Não use nem publique a chave de exemplo.
4. Faça o deploy e abra a URL do Web Service. A API fica no mesmo domínio, em `/api`, e sua documentação em `/docs`.

### Persistência no plano gratuito

Por padrão, o serviço usa SQLite (`banco.db`) dentro do Web Service. No plano Free, o disco do serviço é efêmero: pedidos e alterações do cardápio **podem ser perdidos** após um novo deploy, reinício ou outra substituição da instância. O serviço gratuito também pode adormecer quando não recebe tráfego, deixando o primeiro acesso mais lento.

Para guardar dados de forma persistente, conecte um PostgreSQL externo e configure `DATABASE_URL` nas variáveis do Web Service com a URL de conexão desse banco. Confira os limites, a política de expiração e as condições atuais do plano gratuito do provedor de banco escolhido. O SQLite local continua sendo usado se `DATABASE_URL` não estiver definida.

## Funcionalidades

- Cardápio por categoria, busca, sacola e checkout.
- Pedidos para entrega, retirada ou consumo no local. O total e os preços são calculados pela API.
- Área administrativa protegida por `ADMIN_TOKEN`, com consulta/status de pedidos e gerenciamento de produtos.
- Health check em `/api/health`.

O sistema registra pedidos, mas não processa pagamentos online.
