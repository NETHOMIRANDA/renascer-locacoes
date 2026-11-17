# Renascer Locações — App Mobile (PWA)

Aplicativo mobile (Progressive Web App) com todas as funções do sistema desktop:
orçamentos, pedidos/entregas, clientes, catálogo e relatórios financeiros.

## Como rodar (desenvolvimento)

```bash
npm install
npm run dev
```

Acesse `http://localhost:5173` no navegador ou no celular (mesma rede Wi-Fi).

## Build de produção

```bash
npm run build
```

Os arquivos ficam em `dist/`. Faça deploy dessa pasta em Vercel, Netlify, GitHub Pages ou qualquer host estático.

## Configuração

Na primeira abertura, informe a **SUPABASE_URL** e a **service_role key** do seu projeto Supabase
(mesmas credenciais do sistema desktop). Os dados são lidos/gravados diretamente no Supabase.

## Instalar no celular

Após publicar, abra a URL no navegador do celular e use "Adicionar à tela inicial"
para instalar como aplicativo (PWA).

## Funcionalidades

- Dashboard com contagens
- Orçamentos: criar, editar, enviar para pedido, cancelar, gerar PDF
- Pedidos/Entregas: criar, editar, marcar entregue/recolhido, arquivar, direcionar para orçamento, gerar PDF
- Clientes: cadastro com busca automática e aviso de duplicado
- Catálogo: CRUD de itens e estoque
- Relatórios: resumo por status, itens mais locados, perdas, projeção
- Geração de PDF no próprio aparelho