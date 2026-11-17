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

### Relatórios Financeiros (aba "Relatórios Financeiros")
Organizados em 4 sub-abas, tudo dinâmico e com emissão em PDF:
- **Resumo por Período** — orçamentos/pedidos agregados por **semana, mês e ano**
  (filtros Todos / Semanal / Diário / Mensal / Anual), com bruto, descontos,
  líquido e ticket médio, além de relatório PDF dos três agregados.
- **Itens Mais Locados** — ranking com **quantidade e valor** dos materiais mais
  locados, agrupado por **item** ou por **categoria de materiais**, com destaque do
  **carro-chefe** (mais locado) e participação percentual no faturamento.
- **Perdas por Semana** — quantidade e valor dos pedidos de uma semana de referência
  que **não foram efetivados** (orçamentos não convertidos e cancelados), com taxa
  de perda e relatório PDF detalhado.
- **Projeção Futura** — projeção dinâmica de receita e pedidos para **semanas,
  meses e anos futuros**, calculada a partir da média de movimento recente.

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
