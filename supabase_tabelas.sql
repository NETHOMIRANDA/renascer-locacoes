-- =========================================================
-- TABELAS SUPABASE PARA RENASCER LOCAÇÕES
-- Copie e cole no **SQL Editor** do Supabase (Dashboard → SQL Editor → New query)
-- =========================================================

-- Habilita UUID (opcional, mas recomendado)
create extension if not exists "uuid-ossp";

-- ---------------------------------------------------------
-- CATÁLOGO DE PRODUTOS
-- ---------------------------------------------------------
create table if not exists catalogo (
  id bigint generated always as identity primary key,
  categoria text not null default 'Geral',
  nome text not null,
  unidade text not null default 'Unidade',
  preco numeric(10,2) not null default 0,
  estoque integer not null default 0,
  ativo boolean not null default true,
  atualizado_em timestamptz not null default now()
);

-- ---------------------------------------------------------
-- CLIENTES
-- ---------------------------------------------------------
create table if not exists clientes (
  id bigint generated always as identity primary key,
  nome text not null,
  telefone text,
  endereco text,
  criado_em timestamptz not null default now()
);

-- ---------------------------------------------------------
-- PEDIDOS / ORÇAMENTOS
-- ---------------------------------------------------------
create table if not exists orcamentos (
  id bigint generated always as identity primary key,
  cliente text not null,
  telefone text,
  endereco text,
  data_evento text,
  orcamento text not null,  -- texto/JSON dos itens
  tipo text not null check (tipo in (
    'Orcamento', 'Pedido', 'Cancelado', 
    'Ja Entregue', 'Ja Recolhido', 'Arquivado'
  )),
  distancia_km numeric(8,2) default 0,
  desconto numeric(10,2) default 0,
  observacoes text,
  criado_em timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);

-- ---------------------------------------------------------
-- ÍNDICES PARA PERFORMANCE
-- ---------------------------------------------------------
create index if not exists idx_catalogo_categoria on catalogo(categoria);
create index if not exists idx_catalogo_nome on catalogo(nome);
create index if not exists idx_clientes_nome on clientes(nome);
create index if not exists idx_clientes_telefone on clientes(telefone);
create index if not exists idx_orcamentos_cliente on orcamentos(cliente);
create index if not exists idx_orcamentos_tipo on orcamentos(tipo);
create index if not exists idx_orcamentos_data on orcamentos(data_evento);
create index if not exists idx_orcamentos_criado on orcamentos(criado_em desc);

-- ---------------------------------------------------------
-- ROW LEVEL SECURITY (RLS)
-- Leitura pública, escrita só via service_role (Python backend)
-- ---------------------------------------------------------
alter table catalogo enable row level security;
alter table clientes enable row level security;
alter table orcamentos enable row level security;

-- Políticas de leitura (qualquer um pode ler)
create policy "leitura_publica_catalogo" on catalogo
  for select using (true);

create policy "leitura_publica_clientes" on clientes
  for select using (true);

create policy "leitura_publica_orcamentos" on orcamentos
  for select using (true);

-- Políticas de escrita (apenas service_role - será bypassado pelo Python)
-- O Python usa a service_role key que ignora RLS automaticamente

-- ---------------------------------------------------------
-- TRIGGER PARA ATUALIZAR 'atualizado_em' AUTOMATICAMENTE
-- ---------------------------------------------------------
create or replace function trigger_atualizado_em()
returns trigger language plpgsql as $$
begin
  new.atualizado_em = now();
  return new;
end $$;

drop trigger if exists trg_catalogo_atualizado on catalogo;
create trigger trg_catalogo_atualizado
  before update on catalogo
  for each row execute function trigger_atualizado_em();

drop trigger if not exists trg_orcamentos_atualizado on orcamentos;
create trigger trg_orcamentos_atualizado
  before update on orcamentos
  for each row execute function trigger_atualizado_em();

-- ---------------------------------------------------------
-- POPULAR CATÁLOGO INICIAL (opcional - roda se vazio)
-- ---------------------------------------------------------
insert into catalogo (categoria, nome, unidade, preco, estoque)
select * from (values
  ('MOBILIÁRIO & MESAS', 'Jogo de Mesa com Cadeiras de Plástico (Branca)', 'Jogo', 14.00, 50),
  ('MOBILIÁRIO & MESAS', 'Mesa Redonda de 6 Lugares (com tampão de madeira)', 'Unidade', 18.00, 20),
  ('MOBILIÁRIO & MESAS', 'Mesa Redonda de 7 Lugares (com tampão de madeira)', 'Unidade', 20.00, 20),
  ('MOBILIÁRIO & MESAS', 'Aparador de Madeira (2,50m x 0,80m)', 'Unidade', 25.00, 5),
  ('TOALHAS & ENXOVAL', 'Toalha Quadrada para 4 Lugares (1,50m x 1,50m)', 'Unidade', 6.00, 100),
  ('TOALHAS & ENXOVAL', 'Toalha Redonda para 6 e 7 Lugares (Cor Lisa)', 'Unidade', 12.00, 80),
  ('TOALHAS & ENXOVAL', 'Toalha para Aparador', 'Unidade', 25.00, 10),
  ('LOUÇAS, TALHERES & COPOS', 'Prataria (Prato, Garfo e Faca de Jantar/Sobremesa)', 'Unidade', 0.80, 300),
  ('LOUÇAS, TALHERES & COPOS', 'Copo Tradicional', 'Unidade', 0.80, 300),
  ('LOUÇAS, TALHERES & COPOS', 'Taça para Água / Flauta', 'Unidade', 1.00, 200),
  ('LOUÇAS, TALHERES & COPOS', 'Taça Colorida', 'Unidade', 1.50, 150),
  ('SERVIÇO & RECHAUDS', 'Rechaud Redondo', 'Unidade', 25.00, 10),
  ('SERVIÇO & RECHAUDS', 'Rechaud Quadrado 9 Litros', 'Unidade', 40.00, 10),
  ('SERVIÇO & RECHAUDS', 'Bandeja Oval Média', 'Unidade', 10.00, 15),
  ('SERVIÇO & RECHAUDS', 'Bandeja Oval Grande', 'Unidade', 15.00, 15),
  ('SERVIÇO & RECHAUDS', 'Bandeja para Garçom', 'Unidade', 10.00, 10),
  ('SERVIÇO & RECHAUDS', 'Pegador / Colher para Arroz ou Feijão Tropeiro', 'Unidade', 7.00, 20),
  ('SERVIÇO & RECHAUDS', 'Jarra em Inox', 'Unidade', 10.00, 15),
  ('SERVIÇO & RECHAUDS', 'Lixeira Redonda 7 Litros', 'Unidade', 25.00, 10),
  ('EQUIPAMENTOS', 'Freezer Horizontal Branca 2 Tampas (400 Litros)', 'Diária', 200.00, 3),
  ('EQUIPAMENTOS', 'Freezer Horizontal Branca 2 Tampas (500 Litros)', 'Diária', 250.00, 2)
) as v(categoria, nome, unidade, preco, estoque)
where not exists (select 1 from catalogo limit 1);

-- ---------------------------------------------------------
-- VERIFICAÇÃO
-- ---------------------------------------------------------
select 'catalogo' as tabela, count(*) as registros from catalogo
union all
select 'clientes', count(*) from clientes
union all
select 'orcamentos', count(*) from orcamentos;