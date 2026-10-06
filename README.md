# Renascer Locações – Sistema de Gestão

Sistema desktop (Python + Tkinter) para gerenciar orçamentos, pedidos de entrega,
clientes e catálogo de materiais de uma locadora de itens para festas e eventos.

## Funcionalidades
- Cadastro de **orçamentos** e **pedidos** com itens vinculados ao catálogo
- **Cadastro de clientes** com busca automática por nome ou telefone ao digitar
- Aviso ao salvar quando já existe um cliente parecido (evita cadastro duplicado)
- Catálogo e controle de estoque
- Controle de orçamentos, gestão de entregas e cancelados
- Relatórios financeiros
- PDFs profissionais: **Orçamento** e **Pedido** (o título muda conforme onde o registro está),
  contrato de locação, relatório de entregas e impressão rápida

## Como executar
```
pip install -r requirements.txt
python main.py
```
O banco de dados (`banco_dados.db`) é criado automaticamente na primeira execução.
Os PDFs gerados ficam na pasta `PDF/`.

## Observações
- Os arquivos `*.db` e a pasta `PDF/` não são versionados, pois contêm dados de clientes.
- O recurso opcional de IA (`ia_service.py`) usa a variável de ambiente `GEMINI_API_KEY`.
