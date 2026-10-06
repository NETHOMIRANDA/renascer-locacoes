import tkinter as tk
from tkinter import ttk, messagebox
import re
import difflib
from datetime import datetime
import tkinter.font as tkfont


class ZebraTreeview(ttk.Treeview):
    """Treeview com linhas alternadas (zebradas) para facilitar a leitura."""

    def insert(self, parent, index, iid=None, **kw):
        tags = tuple(kw.pop("tags", ()) or ())
        paridade = "par" if len(self.get_children(parent)) % 2 == 0 else "impar"
        kw["tags"] = tags + (paridade,)
        if iid is not None:
            kw["iid"] = iid
        return super().insert(parent, index, **kw)


def parse_data_br_ou_iso(data_str):
    if not data_str:
        return datetime.min
    data_str = data_str.strip()
    match_br = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', data_str)
    if match_br:
        d, m, y = int(match_br.group(1)), int(match_br.group(2)), int(match_br.group(3))
        if y < 100:
            y += 2000
        try:
            return datetime(y, m, d)
        except ValueError:
            pass
    match_iso = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', data_str)
    if match_iso:
        y, m, d = int(match_iso.group(1)), int(match_iso.group(2)), int(match_iso.group(3))
        try:
            return datetime(y, m, d)
        except ValueError:
            pass
    return datetime.min

def buscar_preco_catalogo(texto_item, catalogo):
    if not catalogo:
        return None, None

    itens_cat = []
    for c in catalogo:
        nome_orig = c[2]
        nome_norm = re.sub(r'[^\w\s]', ' ', nome_orig.lower())
        itens_cat.append({'orig': nome_orig, 'norm': nome_norm, 'preco': float(c[4])})

    texto_limpo = re.sub(r'R\$\s*\d+([.,]\d+)?', '', texto_item, flags=re.IGNORECASE)
    texto_norm = re.sub(r'[^\w\s]', ' ', texto_limpo.lower()).strip()

    for item in itens_cat:
        if item['norm'] in texto_norm or texto_norm in item['norm']:
            return item['preco'], item['orig']

    sub_itens = re.split(r'[,/]|(?:\s+e\s+)|\s+ou\s+', texto_norm)
    sub_itens = [s.strip() for s in sub_itens if s.strip()]

    if len(sub_itens) > 1:
        preco_acumulado = 0.0
        encontrou_algum = False
        nomes_encontrados = []

        for sub in sub_itens:
            melhor_match = None
            maior_ratio = 0.0
            for item in itens_cat:
                ratio = difflib.SequenceMatcher(None, sub, item['norm']).ratio()
                if sub in item['norm'] or item['norm'] in sub:
                    ratio = max(ratio, 0.8)
                if ratio > maior_ratio and ratio >= 0.5:
                    maior_ratio = ratio
                    melhor_match = item
            if melhor_match:
                preco_acumulado += melhor_match['preco']
                encontrou_algum = True
                nomes_encontrados.append(melhor_match['orig'])

        if encontrou_algum:
            nome_sugerido = " + ".join(nomes_encontrados)
            return preco_acumulado, nome_sugerido

    nomes_norm = [i['norm'] for i in itens_cat]
    matches = difflib.get_close_matches(texto_norm, nomes_norm, n=1, cutoff=0.4)
    if matches:
        for item in itens_cat:
            if item['norm'] == matches[0]:
                return item['preco'], item['orig']

    return None, None


class FormularioOrcamento:
    def __init__(self, root, callbacks):
        self.root = root
        self.callbacks = callbacks
        self.pedido_selecionado_dados = None
        self.id_em_edicao = None
        self.id_item_cat_em_edicao = None
        self.lista_catalogo_completa = []
        self.lista_entregas_completa = []
        self.checados_entrega = set()

        self.style = ttk.Style()
        self.style.theme_use("clam")

        # PALETA MODERNA E MINIMALISTA
        BG_COLOR = "#EEF2F7"        # Fundo da aplicação
        CARD_BG = "#FFFFFF"         # Cartões
        BORDER_COLOR = "#DCE3EC"    # Bordas suaves
        PRIMARY_COLOR = "#0F172A"   # Azul-marinho escuro
        ACCENT_COLOR = "#2563EB"    # Azul de destaque
        TEXT_MAIN = "#0F172A"
        TEXT_MUTED = "#64748B"
        SECONDARY_BTN = "#475569"

        self.BG_COLOR, self.CARD_BG, self.BORDER_COLOR = BG_COLOR, CARD_BG, BORDER_COLOR
        self.PRIMARY_COLOR, self.ACCENT_COLOR = PRIMARY_COLOR, ACCENT_COLOR
        self.TEXT_MAIN, self.TEXT_MUTED = TEXT_MAIN, TEXT_MUTED

        self.root.configure(bg=BG_COLOR)
        self.root.minsize(1100, 680)
        self.root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT_COLOR)

        # Abas modernas: aba ativa branca com filete azul no topo
        self.style.configure("TNotebook", background=BG_COLOR, borderwidth=0, tabmargins=[0, 0, 0, 0])
        self.style.configure("TNotebook.Tab", background="#E3E9F1", foreground=TEXT_MUTED,
                             font=("Segoe UI", 9, "bold"), padding=[6, 9], borderwidth=0)
        self.style.map("TNotebook.Tab",
                       background=[("selected", CARD_BG), ("active", "#F4F7FB")],
                       foreground=[("selected", ACCENT_COLOR), ("active", PRIMARY_COLOR)],
                       lightcolor=[("selected", ACCENT_COLOR), ("!selected", "#E3E9F1")],
                       bordercolor=[("selected", BORDER_COLOR), ("!selected", "#E3E9F1")])

        # Tabelas: cabeçalho discreto, linhas zebradas e seleção azul clara
        self.style.configure("Treeview", background=CARD_BG, foreground=TEXT_MAIN,
                             rowheight=30, fieldbackground=CARD_BG, font=("Segoe UI", 9), borderwidth=0)
        self.style.configure("Treeview.Heading", background="#F1F5F9", foreground=TEXT_MUTED,
                             font=("Segoe UI", 9, "bold"), relief="flat", padding=[8, 8], borderwidth=0)
        self.style.map("Treeview", background=[("selected", "#DBEAFE")], foreground=[("selected", PRIMARY_COLOR)])
        self.style.map("Treeview.Heading", background=[("active", "#E2E8F0")])

        # Campos de seleção e barras de rolagem
        self.style.configure("TCombobox", padding=5, fieldbackground="#F8FAFC", background="#E2E8F0",
                             bordercolor=BORDER_COLOR, lightcolor=BORDER_COLOR, darkcolor=BORDER_COLOR,
                             arrowcolor=TEXT_MUTED, foreground=TEXT_MAIN)
        self.style.map("TCombobox", bordercolor=[("focus", ACCENT_COLOR)], fieldbackground=[("readonly", "#F8FAFC")])
        self.style.configure("TSeparator", background=BORDER_COLOR)
        self.style.configure("Vertical.TScrollbar", background="#CBD5E1", troughcolor=BG_COLOR,
                             bordercolor=BG_COLOR, arrowcolor=TEXT_MUTED, relief="flat")

        # Cabeçalho da aplicação
        self.header = tk.Frame(root, bg=PRIMARY_COLOR, height=58)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)
        self.faixa_destaque = tk.Frame(root, bg=ACCENT_COLOR, height=3)
        self.faixa_destaque.pack(fill="x")

        tk.Label(self.header, text="R", bg=ACCENT_COLOR, fg="white", font=("Segoe UI", 16, "bold"),
                 width=3).pack(side=tk.LEFT, fill="y", padx=(0, 14))
        bloco_titulo = tk.Frame(self.header, bg=PRIMARY_COLOR)
        bloco_titulo.pack(side=tk.LEFT, fill="y", pady=8)
        tk.Label(bloco_titulo, text="Renascer Locações", bg=PRIMARY_COLOR, fg="white",
                 font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(bloco_titulo, text="Gestão de orçamentos, entregas e clientes", bg=PRIMARY_COLOR, fg="#94A3B8",
                 font=("Segoe UI", 9)).pack(anchor="w")

        dias = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
        meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
                 "setembro", "outubro", "novembro", "dezembro"]
        agora = datetime.now()
        tk.Label(self.header, text=f"{dias[agora.weekday()].capitalize()}, {agora.day} de {meses[agora.month - 1]} de {agora.year}",
                 bg=PRIMARY_COLOR, fg="#CBD5E1", font=("Segoe UI", 10)).pack(side=tk.RIGHT, padx=20)

        self.main_container = tk.Frame(root, bg=BG_COLOR)
        self.main_container.pack(fill="both", expand=True, padx=14, pady=14)

        # O painel de prévia é empacotado primeiro para garantir sua largura fixa
        self.frame_direita = tk.Frame(self.main_container, bg=CARD_BG, width=390, bd=1, relief="solid", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.frame_direita.pack(side=tk.RIGHT, fill="y", padx=(14, 0))
        self.frame_direita.pack_propagate(False)

        self.frame_esquerda = tk.Frame(self.main_container, bg=BG_COLOR)
        self.frame_esquerda.pack(side=tk.LEFT, fill="both", expand=True)

        self.lbl_preview_title = tk.Label(self.frame_direita, text="Prévia do Orçamento — Renascer", font=("Segoe UI", 10, "bold"), bg=PRIMARY_COLOR, fg="white", pady=8)
        self.lbl_preview_title.pack(fill="x")

        self.frame_info_cliente = tk.Frame(self.frame_direita, bg="#F1F5F9", bd=0)
        self.frame_info_cliente.pack(fill="x", padx=10, pady=8)

        self.lbl_cliente_prev = tk.Label(self.frame_info_cliente, text="Cliente: -", font=("Segoe UI", 9, "bold"), bg="#F1F5F9", fg=TEXT_MAIN, anchor="w")
        self.lbl_cliente_prev.pack(fill="x", padx=8, pady=(4, 2))
        
        self.lbl_tel_prev = tk.Label(self.frame_info_cliente, text="Tel: -", font=("Segoe UI", 8), bg="#F1F5F9", fg=TEXT_MUTED, anchor="w")
        self.lbl_tel_prev.pack(fill="x", padx=8, pady=1)

        self.lbl_end_prev = tk.Label(self.frame_info_cliente, text="End: -", font=("Segoe UI", 8), bg="#F1F5F9", fg=TEXT_MUTED, anchor="w")
        self.lbl_end_prev.pack(fill="x", padx=8, pady=1)

        self.lbl_data_prev = tk.Label(self.frame_info_cliente, text="Data Evento: -", font=("Segoe UI", 8, "bold"), bg="#F1F5F9", fg=PRIMARY_COLOR, anchor="w")
        self.lbl_data_prev.pack(fill="x", padx=8, pady=2)

        self.lbl_obs_prev = tk.Label(self.frame_info_cliente, text="Obs: -", font=("Segoe UI", 8, "italic"), bg="#F1F5F9", fg=TEXT_MUTED, anchor="w")
        self.lbl_obs_prev.pack(fill="x", padx=8, pady=(1, 4))

        self.lbl_cor_toalha_prev = tk.Label(self.frame_info_cliente, text="", font=("Segoe UI", 8, "bold"), bg="#F1F5F9", fg=ACCENT_COLOR, anchor="w")

        self.tree_preview = ZebraTreeview(
            self.frame_direita, 
            columns=("QTD", "MATERIAL", "CATALOGO", "V.UNIT", "TOTAL"), 
            show="headings", 
            height=7
        )
        self.tree_preview.heading("QTD", text="QTD")
        self.tree_preview.heading("MATERIAL", text="MATERIAL")
        self.tree_preview.heading("CATALOGO", text="CATÁLOGO")
        self.tree_preview.heading("V.UNIT", text="UNIT")
        self.tree_preview.heading("TOTAL", text="TOTAL")

        self.tree_preview.column("QTD", width=38, anchor="center")
        self.tree_preview.column("MATERIAL", width=100)
        self.tree_preview.column("CATALOGO", width=100)
        self.tree_preview.column("V.UNIT", width=62, anchor="e")
        self.tree_preview.column("TOTAL", width=66, anchor="e")
        self.tree_preview.pack(fill="both", expand=True, padx=10, pady=5)

        self.lbl_subtotal_prev = tk.Label(self.frame_direita, text="Subtotal Itens: R$ 0,00", font=("Segoe UI", 8), bg=CARD_BG, fg=TEXT_MUTED, anchor="e")
        self.lbl_subtotal_prev.pack(fill="x", padx=12)

        self.lbl_frete_prev = tk.Label(self.frame_direita, text="Frete (0 km): R$ 0,00", font=("Segoe UI", 8), bg=CARD_BG, fg=TEXT_MUTED, anchor="e")
        self.lbl_frete_prev.pack(fill="x", padx=12)

        self.lbl_desconto_prev = tk.Label(self.frame_direita, text="Desconto Concedido: - R$ 0,00", font=("Segoe UI", 8), bg=CARD_BG, fg=TEXT_MUTED, anchor="e")
        self.lbl_desconto_prev.pack(fill="x", padx=12)

        self.lbl_total_prev = tk.Label(self.frame_direita, text="TOTAL GERAL: R$ 0,00", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=PRIMARY_COLOR, anchor="e")
        self.lbl_total_prev.pack(fill="x", padx=12, pady=(4, 6))

        frame_btn_prev = tk.Frame(self.frame_direita, bg=CARD_BG)
        frame_btn_prev.pack(fill="x", padx=10, pady=10)

        frame_botoes_pdf_contrato = tk.Frame(frame_btn_prev, bg=CARD_BG)
        frame_botoes_pdf_contrato.pack(fill="x", pady=(0, 6))

        self.btn_gerar_pdf = tk.Button(
            frame_botoes_pdf_contrato, text="Gerar PDF do Pedido", bg=PRIMARY_COLOR, fg="white",
            font=("Segoe UI", 8, "bold"), bd=0, padx=6, pady=8, cursor="hand2", activebackground="#334155", activeforeground="white",
            state="disabled", command=self._ao_clicar_pdf
        )
        self.btn_gerar_pdf.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 3))

        self.btn_gerar_contrato = tk.Button(
            frame_botoes_pdf_contrato, text="Gerar Contrato", bg=SECONDARY_BTN, fg="white",
            font=("Segoe UI", 8, "bold"), bd=0, padx=6, pady=8, cursor="hand2", activebackground="#334155", activeforeground="white",
            state="disabled", command=self._ao_clicar_contrato
        )
        self.btn_gerar_contrato.pack(side=tk.RIGHT, fill="x", expand=True, padx=(3, 0))

        self.btn_editar_pedido = tk.Button(
            frame_btn_prev, text="Editar Este Pedido", bg=ACCENT_COLOR, fg="white",
            font=("Segoe UI", 8, "bold"), bd=0, padx=10, pady=8, cursor="hand2", activebackground="#1D4ED8", activeforeground="white",
            state="disabled", command=self.iniciar_edicao
        )
        self.btn_editar_pedido.pack(fill="x")

        self.notebook = ttk.Notebook(self.frame_esquerda)
        self.notebook.pack(fill="both", expand=True)

        self.aba_cadastro = tk.Frame(self.notebook, bg=BG_COLOR)
        self.notebook.add(self.aba_cadastro, text="Novo / Editar Orçamento")

        self.aba_clientes = tk.Frame(self.notebook, bg=BG_COLOR)
        self.notebook.add(self.aba_clientes, text="Clientes")

        self.aba_catalogo = tk.Frame(self.notebook, bg=BG_COLOR)
        self.notebook.add(self.aba_catalogo, text="Catálogo & Estoque")

        self.aba_orcamento = tk.Frame(self.notebook, bg=BG_COLOR)
        self.notebook.add(self.aba_orcamento, text="Controle de Orçamentos")

        self.aba_entrega = tk.Frame(self.notebook, bg=BG_COLOR)
        self.notebook.add(self.aba_entrega, text="Gestão de Entrega")

        self.aba_relatorios = tk.Frame(self.notebook, bg=BG_COLOR)
        self.notebook.add(self.aba_relatorios, text="Relatórios Financeiros")

        self.aba_cancelados = tk.Frame(self.notebook, bg=BG_COLOR)
        self.notebook.add(self.aba_cancelados, text="Cancelados")

        # FORMULÁRIO DE CADASTRO
        card_form = tk.Frame(self.aba_cadastro, bg=CARD_BG, bd=1, relief="solid", highlightbackground=BORDER_COLOR, highlightthickness=1)
        card_form.pack(fill="both", expand=True, padx=2, pady=5)

        self.lbl_titulo_form = tk.Label(card_form, text="Novo Orçamento", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=PRIMARY_COLOR)
        self.lbl_titulo_form.pack(anchor="w", padx=15, pady=(12, 2))

        ttk.Separator(card_form, orient="horizontal").pack(fill="x", padx=15, pady=8)

        frame_campos = tk.Frame(card_form, bg=CARD_BG)
        frame_campos.pack(fill="both", expand=True, padx=15, pady=5)

        f_left = tk.Frame(frame_campos, bg=CARD_BG)
        f_left.pack(side=tk.LEFT, fill="both", expand=True, padx=(0, 10))

        tk.Label(f_left, text="Cliente (digite para buscar nos cadastrados):", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")
        self.entry_nome = tk.Entry(f_left, font=("Segoe UI", 9), bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_nome.pack(fill="x", pady=(0, 6))

        tk.Label(f_left, text="Telefone (ou parte dele):", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")
        self.entry_telefone = tk.Entry(f_left, font=("Segoe UI", 9), bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_telefone.pack(fill="x", pady=(0, 6))

        # CONTROLE DE CLIENTES: sugestões automáticas ao digitar nome ou telefone
        self.entry_nome.bind("<KeyRelease>", lambda e: self._filtrar_clientes(e, self.entry_nome))
        self.entry_telefone.bind("<KeyRelease>", lambda e: self._filtrar_clientes(e, self.entry_telefone))
        for _entry in (self.entry_nome, self.entry_telefone):
            _entry.bind("<Down>", self._foco_lista_clientes)
            _entry.bind("<Escape>", lambda e: self._esconder_sugestoes_clientes())
            _entry.bind("<FocusOut>", lambda e: self.root.after(200, self._esconder_se_sem_foco))

        self.listbox_clientes = tk.Listbox(
            f_left, height=5, font=("Segoe UI", 9), bd=1, relief="solid",
            highlightbackground=ACCENT_COLOR, highlightthickness=1, activestyle="dotbox",
            selectbackground=ACCENT_COLOR, selectforeground="white"
        )
        self.listbox_clientes.bind("<ButtonRelease-1>", self._ao_selecionar_cliente)
        self.listbox_clientes.bind("<Return>", self._ao_selecionar_cliente)
        self.listbox_clientes.bind("<Escape>", lambda e: self._esconder_sugestoes_clientes())
        self._clientes_sugeridos = []
        self._entry_origem_cliente = None

        tk.Label(f_left, text="Data do Evento (DD/MM/AAAA ou AAAA-MM-DD):", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")
        self.entry_data_evento = tk.Entry(f_left, font=("Segoe UI", 9), bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_data_evento.pack(fill="x", pady=(0, 6))

        tk.Label(f_left, text="Distância / Quilometragem (KM):", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")
        self.entry_distancia_km = tk.Entry(f_left, font=("Segoe UI", 9), bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_distancia_km.pack(fill="x", pady=(0, 6))
        self.entry_distancia_km.bind("<KeyRelease>", lambda e: self.atualizar_preview_ao_vivo())

        tk.Label(f_left, text="Desconto Concedido (R$):", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")
        self.entry_desconto = tk.Entry(f_left, font=("Segoe UI", 9), bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_desconto.pack(fill="x", pady=(0, 6))
        self.entry_desconto.bind("<KeyRelease>", lambda e: self.atualizar_preview_ao_vivo())

        f_right = tk.Frame(frame_campos, bg=CARD_BG)
        f_right.pack(side=tk.RIGHT, fill="both", expand=True)

        tk.Label(f_right, text="Endereço de Entrega:", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")
        self.entry_endereco = tk.Entry(f_right, font=("Segoe UI", 9), bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_endereco.pack(fill="x", pady=(0, 6))

        tk.Label(f_right, text="Observações Gerais:", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")
        self.entry_observacoes = tk.Entry(f_right, font=("Segoe UI", 9), bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_observacoes.pack(fill="x", pady=(0, 6))
        self.entry_observacoes.bind("<KeyRelease>", lambda e: self.atualizar_preview_ao_vivo())

        tk.Label(f_right, text="Buscar / Adicionar do Catálogo:", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=PRIMARY_COLOR).pack(anchor="w")
        
        frame_busca_cat = tk.Frame(f_right, bg=CARD_BG)
        frame_busca_cat.pack(fill="x", pady=(0, 2))

        self.entry_busca_catalogo = tk.Entry(frame_busca_cat, font=("Segoe UI", 9), bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_busca_catalogo.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 5))
        self.entry_busca_catalogo.bind("<KeyRelease>", self._filtrar_catalogo_digitacao)

        tk.Label(frame_busca_cat, text="Qtd:", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(2, 2))
        self.entry_qtd_busca = tk.Entry(frame_busca_cat, font=("Segoe UI", 9), width=5, bd=1, relief="solid", highlightbackground=BORDER_COLOR, justify="center")
        self.entry_qtd_busca.insert(0, "1")
        self.entry_qtd_busca.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_add_item_cat = tk.Button(
            frame_busca_cat, text="+ Adicionar", bg=PRIMARY_COLOR, fg="white",
            font=("Segoe UI", 8, "bold"), bd=0, padx=8, pady=2, cursor="hand2", activebackground="#334155", activeforeground="white",
            command=self._adicionar_item_selecionado_busca
        )
        self.btn_add_item_cat.pack(side=tk.RIGHT)

        self.listbox_sugestoes = tk.Listbox(f_right, height=3, font=("Segoe UI", 8), bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.listbox_sugestoes.bind("<<ListboxSelect>>", self._ao_selecionar_sugestao)

        frame_label_detalhes = tk.Frame(f_right, bg=CARD_BG)
        frame_label_detalhes.pack(fill="x", pady=(4, 2))

        tk.Label(frame_label_detalhes, text="Detalhes dos Itens / Orçamento (1 por linha):", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(side=tk.LEFT)

        self.btn_sugerir_itens = tk.Button(
            frame_label_detalhes, text="Vincular Nomes", bg=SECONDARY_BTN, fg="white",
            font=("Segoe UI", 8, "bold"), bd=0, padx=6, pady=1, cursor="hand2", activebackground="#334155", activeforeground="white",
            command=self.aplicar_sugestoes_catalogo
        )
        self.btn_sugerir_itens.pack(side=tk.RIGHT)

        self.text_orcamento = tk.Text(f_right, height=3, font=("Segoe UI", 9), bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.text_orcamento.pack(fill="both", expand=True, pady=(0, 5))
        self.text_orcamento.bind("<KeyRelease>", self._ao_alterar_texto_orcamento)

        self.frame_cor_toalha = tk.Frame(f_right, bg="#F1F5F9", bd=0)
        tk.Label(self.frame_cor_toalha, text="Cor da(s) Toalha(s):", font=("Segoe UI", 8, "bold"), bg="#F1F5F9", fg=PRIMARY_COLOR).pack(side=tk.LEFT, padx=6, pady=4)
        
        self.combo_cor_toalha = ttk.Combobox(
            self.frame_cor_toalha, 
            values=["Branca", "Preta", "Vermelha", "Azul", "Verde", "Amarela", "Rosa", "Dourada", "Outra"],
            font=("Segoe UI", 9)
        )
        self.combo_cor_toalha.set("Branca")
        self.combo_cor_toalha.pack(side=tk.LEFT, fill="x", expand=True, padx=6, pady=4)
        self.combo_cor_toalha.bind("<<ComboboxSelected>>", lambda e: self.atualizar_preview_ao_vivo())

        self.frame_botoes_novos = tk.Frame(card_form, bg=CARD_BG)
        self.frame_botoes_novos.pack(fill="x", padx=15, pady=10)

        self.btn_salvar_orcamento = tk.Button(
            self.frame_botoes_novos, text="Salvar em Orçamentos", bg=PRIMARY_COLOR, fg="white", 
            font=("Segoe UI", 8, "bold"), bd=0, padx=15, pady=6, cursor="hand2", activebackground="#334155", activeforeground="white",
            command=self._ao_clicar_salvar_orcamento
        )
        self.btn_salvar_orcamento.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_enviar_entrega = tk.Button(
            self.frame_botoes_novos, text="Salvar Direto para Entrega", bg=ACCENT_COLOR, fg="white", 
            font=("Segoe UI", 8, "bold"), bd=0, padx=15, pady=6, cursor="hand2", activebackground="#1D4ED8", activeforeground="white",
            command=self._ao_clicar_salvar_entrega
        )
        self.btn_enviar_entrega.pack(side=tk.LEFT)

        self.frame_botoes_edicao = tk.Frame(card_form, bg=CARD_BG)
        self.btn_salvar_edicao = tk.Button(
            self.frame_botoes_edicao, text="Salvar Alterações do Pedido", bg=ACCENT_COLOR, fg="white",
            font=("Segoe UI", 8, "bold"), bd=0, padx=15, pady=6, cursor="hand2", activebackground="#1D4ED8", activeforeground="white",
            command=self._ao_clicar_salvar_edicao
        )
        self.btn_salvar_edicao.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_cancelar_edicao = tk.Button(
            self.frame_botoes_edicao, text="Cancelar Edição", bg="#94A3B8", fg="white",
            font=("Segoe UI", 8, "bold"), bd=0, padx=15, pady=6, cursor="hand2", activebackground="#64748B", activeforeground="white",
            command=self.cancelar_edicao
        )
        self.btn_cancelar_edicao.pack(side=tk.LEFT)

        # ABA CLIENTES (cadastro de todos os clientes)
        self.id_cliente_em_edicao = None
        self._clientes_por_iid = {}
        card_cli = tk.Frame(self.aba_clientes, bg=CARD_BG, bd=1, relief="solid", highlightbackground=BORDER_COLOR, highlightthickness=1)
        card_cli.pack(fill="both", expand=True, padx=2, pady=5)

        tk.Label(card_cli, text="Cadastro de Clientes", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=PRIMARY_COLOR).pack(anchor="w", padx=15, pady=(12, 5))

        frame_inputs_cli = tk.Frame(card_cli, bg=CARD_BG)
        frame_inputs_cli.pack(fill="x", padx=15, pady=5)

        tk.Label(frame_inputs_cli, text="Nome:", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).grid(row=0, column=0, sticky="w")
        self.entry_cli_nome = tk.Entry(frame_inputs_cli, font=("Segoe UI", 9), width=32, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_cli_nome.grid(row=1, column=0, padx=(0, 8), sticky="w")

        tk.Label(frame_inputs_cli, text="Telefone:", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).grid(row=0, column=1, sticky="w")
        self.entry_cli_telefone = tk.Entry(frame_inputs_cli, font=("Segoe UI", 9), width=18, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_cli_telefone.grid(row=1, column=1, padx=(0, 8), sticky="w")

        tk.Label(frame_inputs_cli, text="Endereço:", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).grid(row=0, column=2, sticky="w")
        self.entry_cli_endereco = tk.Entry(frame_inputs_cli, font=("Segoe UI", 9), width=40, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_cli_endereco.grid(row=1, column=2, sticky="w")

        frame_btns_cli = tk.Frame(card_cli, bg=CARD_BG)
        frame_btns_cli.pack(fill="x", padx=15, pady=8)

        tk.Button(frame_btns_cli, text="Salvar Cliente", bg=PRIMARY_COLOR, fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=12, pady=5, cursor="hand2", activebackground="#334155", activeforeground="white", command=self._ao_salvar_cliente).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(frame_btns_cli, text="Limpar Campos", bg=SECONDARY_BTN, fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=12, pady=5, cursor="hand2", activebackground="#334155", activeforeground="white", command=self.limpar_campos_clientes).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(frame_btns_cli, text="Excluir Selecionado", bg="#94A3B8", fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=12, pady=5, cursor="hand2", activebackground="#64748B", activeforeground="white", command=self._ao_excluir_cliente).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(frame_btns_cli, text="Usar no Orçamento", bg=ACCENT_COLOR, fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=12, pady=5, cursor="hand2", activebackground="#1D4ED8", activeforeground="white", command=self._usar_cliente_no_orcamento).pack(side=tk.RIGHT)

        frame_pesq_cli = tk.Frame(card_cli, bg=CARD_BG)
        frame_pesq_cli.pack(fill="x", padx=15, pady=(5, 2))
        tk.Label(frame_pesq_cli, text="Buscar (nome ou telefone):", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=PRIMARY_COLOR).pack(side=tk.LEFT, padx=(0, 5))
        self.entry_filtro_clientes = tk.Entry(frame_pesq_cli, font=("Segoe UI", 9), bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_filtro_clientes.pack(side=tk.LEFT, fill="x", expand=True)
        self.entry_filtro_clientes.bind("<KeyRelease>", lambda e: self._aplicar_filtro_clientes())

        self.tabela_clientes = ZebraTreeview(card_cli, columns=("ID", "Nome", "Telefone", "Endereço"), show="headings", height=10)
        self.tabela_clientes.heading("ID", text="ID")
        self.tabela_clientes.heading("Nome", text="Cliente")
        self.tabela_clientes.heading("Telefone", text="Telefone")
        self.tabela_clientes.heading("Endereço", text="Endereço")
        self.tabela_clientes.column("ID", width=35, anchor="center")
        self.tabela_clientes.column("Nome", width=200)
        self.tabela_clientes.column("Telefone", width=110)
        self.tabela_clientes.column("Endereço", width=260)
        self.tabela_clientes.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        self.tabela_clientes.bind("<<TreeviewSelect>>", self._ao_selecionar_cliente_tabela)
        self.tabela_clientes.bind("<Double-1>", lambda e: self._usar_cliente_no_orcamento())

        # ABA CATÁLOGO
        card_cat = tk.Frame(self.aba_catalogo, bg=CARD_BG, bd=1, relief="solid", highlightbackground=BORDER_COLOR, highlightthickness=1)
        card_cat.pack(fill="both", expand=True, padx=2, pady=5)

        tk.Label(card_cat, text="Gestão de Catálogo e Estoque Editável", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=PRIMARY_COLOR).pack(anchor="w", padx=15, pady=(12, 5))

        frame_inputs_cat = tk.Frame(card_cat, bg=CARD_BG)
        frame_inputs_cat.pack(fill="x", padx=15, pady=5)

        tk.Label(frame_inputs_cat, text="Categoria:", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).grid(row=0, column=0, sticky="w")
        self.entry_cat_categoria = tk.Entry(frame_inputs_cat, font=("Segoe UI", 9), width=20, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_cat_categoria.grid(row=1, column=0, padx=(0, 8), sticky="w")

        tk.Label(frame_inputs_cat, text="Nome do Item / Descrição:", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).grid(row=0, column=1, sticky="w")
        self.entry_cat_nome = tk.Entry(frame_inputs_cat, font=("Segoe UI", 9), width=35, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_cat_nome.grid(row=1, column=1, padx=(0, 8), sticky="w")

        tk.Label(frame_inputs_cat, text="Unidade:", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).grid(row=0, column=2, sticky="w")
        self.entry_cat_unidade = tk.Entry(frame_inputs_cat, font=("Segoe UI", 9), width=10, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_cat_unidade.insert(0, "Unidade")
        self.entry_cat_unidade.grid(row=1, column=2, padx=(0, 8), sticky="w")

        tk.Label(frame_inputs_cat, text="Preço (R$):", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).grid(row=0, column=3, sticky="w")
        self.entry_cat_preco = tk.Entry(frame_inputs_cat, font=("Segoe UI", 9), width=10, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_cat_preco.grid(row=1, column=3, padx=(0, 8), sticky="w")

        tk.Label(frame_inputs_cat, text="Estoque Total:", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).grid(row=0, column=4, sticky="w")
        self.entry_cat_estoque = tk.Entry(frame_inputs_cat, font=("Segoe UI", 9), width=10, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_cat_estoque.grid(row=1, column=4, sticky="w")

        frame_btns_cat = tk.Frame(card_cat, bg=CARD_BG)
        frame_btns_cat.pack(fill="x", padx=15, pady=8)

        self.btn_salvar_cat = tk.Button(frame_btns_cat, text="Salvar/Adicionar Item", bg=PRIMARY_COLOR, fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=12, pady=5, cursor="hand2", activebackground="#334155", activeforeground="white", command=self._ao_salvar_cat)
        self.btn_salvar_cat.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_limpar_cat = tk.Button(frame_btns_cat, text="Limpar Campos", bg=SECONDARY_BTN, fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=12, pady=5, cursor="hand2", activebackground="#334155", activeforeground="white", command=self.limpar_campos_catalogo)
        self.btn_limpar_cat.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_excluir_cat = tk.Button(frame_btns_cat, text="Excluir Selecionado", bg="#94A3B8", fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=12, pady=5, cursor="hand2", activebackground="#64748B", activeforeground="white", command=self._ao_excluir_cat)
        self.btn_excluir_cat.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_pdf_cat = tk.Button(frame_btns_cat, text="Gerar PDF do Catálogo", bg=ACCENT_COLOR, fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=12, pady=5, cursor="hand2", activebackground="#1D4ED8", activeforeground="white", command=self._ao_gerar_pdf_cat)
        self.btn_pdf_cat.pack(side=tk.RIGHT)

        frame_pesquisa_tabela_cat = tk.Frame(card_cat, bg=CARD_BG)
        frame_pesquisa_tabela_cat.pack(fill="x", padx=15, pady=(5, 2))

        tk.Label(frame_pesquisa_tabela_cat, text="Filtro Rápido:", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=PRIMARY_COLOR).pack(side=tk.LEFT, padx=(0, 5))
        
        self.entry_filtro_tabela_cat = tk.Entry(frame_pesquisa_tabela_cat, font=("Segoe UI", 9), bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_filtro_tabela_cat.pack(side=tk.LEFT, fill="x", expand=True)
        self.entry_filtro_tabela_cat.bind("<KeyRelease>", lambda e: self._aplicar_filtro_tabela_cat())

        self.tabela_catalogo = ZebraTreeview(card_cat, columns=("ID", "Categoria", "Nome", "Unidade", "Preço", "Estoque"), show="headings", height=10)
        self.tabela_catalogo.heading("ID", text="ID")
        self.tabela_catalogo.heading("Categoria", text="Categoria")
        self.tabela_catalogo.heading("Nome", text="Item / Descrição")
        self.tabela_catalogo.heading("Unidade", text="Unidade")
        self.tabela_catalogo.heading("Preço", text="Preço (R$)")
        self.tabela_catalogo.heading("Estoque", text="Estoque")

        self.tabela_catalogo.column("ID", width=35, anchor="center")
        self.tabela_catalogo.column("Categoria", width=140)
        self.tabela_catalogo.column("Nome", width=220)
        self.tabela_catalogo.column("Unidade", width=70, anchor="center")
        self.tabela_catalogo.column("Preço", width=80, anchor="e")
        self.tabela_catalogo.column("Estoque", width=60, anchor="center")
        self.tabela_catalogo.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        self.tabela_catalogo.bind("<<TreeviewSelect>>", self._ao_selecionar_item_catalogo)

        # ABA ORÇAMENTOS
        card_tabela_orcamentos = tk.Frame(self.aba_orcamento, bg=CARD_BG, bd=1, relief="solid", highlightbackground=BORDER_COLOR, highlightthickness=1)
        card_tabela_orcamentos.pack(fill="both", expand=True, padx=2, pady=5)
        tk.Label(card_tabela_orcamentos, text="Orçamentos em Acompanhamento", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=PRIMARY_COLOR).pack(anchor="w", padx=15, pady=10)
        self.tabela_orcamentos = self.criar_tabela(card_tabela_orcamentos)

        frame_acoes_orcamento = tk.Frame(card_tabela_orcamentos, bg=CARD_BG)
        frame_acoes_orcamento.pack(fill="x", padx=15, pady=10)
        tk.Button(frame_acoes_orcamento, text="Enviar p/ Gestão de Entrega", bg=ACCENT_COLOR, fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=12, pady=6, cursor="hand2", activebackground="#1D4ED8", activeforeground="white", command=lambda: self.callbacks.get("mover_status")(self.tabela_orcamentos, 'Pedido')).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(frame_acoes_orcamento, text="Marcar como Cancelado", bg="#94A3B8", fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=12, pady=6, cursor="hand2", activebackground="#64748B", activeforeground="white", command=lambda: self.callbacks.get("mover_status")(self.tabela_orcamentos, 'Cancelado')).pack(side=tk.LEFT)

        # ABA GESTÃO DE ENTREGA REFORMULADA
        card_tabela_entregas = tk.Frame(self.aba_entrega, bg=CARD_BG, bd=1, relief="solid", highlightbackground=BORDER_COLOR, highlightthickness=1)
        card_tabela_entregas.pack(fill="both", expand=True, padx=2, pady=5)
        
        frame_top_entrega = tk.Frame(card_tabela_entregas, bg=CARD_BG)
        frame_top_entrega.pack(fill="x", padx=15, pady=10)
        
        tk.Label(frame_top_entrega, text="Gestão de Entregas & Relatório", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=PRIMARY_COLOR).pack(side=tk.LEFT)
        
        frame_filtro_entrega = tk.Frame(frame_top_entrega, bg=CARD_BG)
        frame_filtro_entrega.pack(side=tk.RIGHT)
        
        tk.Label(frame_filtro_entrega, text="Período:", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 2))
        self.combo_filtro_periodo_entrega = ttk.Combobox(
            frame_filtro_entrega, 
            values=["Todos os Dias", "Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"], 
            state="readonly", width=14, font=("Segoe UI", 8)
        )
        self.combo_filtro_periodo_entrega.set("Todos os Dias")
        self.combo_filtro_periodo_entrega.pack(side=tk.LEFT, padx=(0, 10))
        self.combo_filtro_periodo_entrega.bind("<<ComboboxSelected>>", lambda e: self._aplicar_filtro_entregas())

        tk.Label(frame_filtro_entrega, text="Status:", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 2))
        self.combo_filtro_status_entrega = ttk.Combobox(
            frame_filtro_entrega, 
            values=["Todos", "Pendente (Pedido)", "Já Entregue", "Já Recolhido", "Arquivado"], 
            state="readonly", width=16, font=("Segoe UI", 8)
        )
        self.combo_filtro_status_entrega.set("Todos")
        self.combo_filtro_status_entrega.pack(side=tk.LEFT)
        self.combo_filtro_status_entrega.bind("<<ComboboxSelected>>", lambda e: self._aplicar_filtro_entregas())

        self.tabela_entregas = ZebraTreeview(card_tabela_entregas, columns=("Sel", "ID", "Cliente", "Telefone", "Endereço", "Data", "Status"), show="headings", height=9)
        self.tabela_entregas.heading("Sel", text="[X]")
        self.tabela_entregas.heading("ID", text="ID")
        self.tabela_entregas.heading("Cliente", text="Cliente")
        self.tabela_entregas.heading("Telefone", text="Telefone")
        self.tabela_entregas.heading("Endereço", text="Endereço")
        self.tabela_entregas.heading("Data", text="Data Evento ⬆")
        self.tabela_entregas.heading("Status", text="Status")

        self.tabela_entregas.column("Sel", width=35, anchor="center")
        self.tabela_entregas.column("ID", width=35, anchor="center")
        self.tabela_entregas.column("Cliente", width=120)
        self.tabela_entregas.column("Telefone", width=95)
        self.tabela_entregas.column("Endereço", width=150)
        self.tabela_entregas.column("Data", width=85, anchor="center")
        self.tabela_entregas.column("Status", width=100, anchor="center")
        
        self.tabela_entregas.pack(fill="both", expand=True, padx=15, pady=(0, 5))
        self.tabela_entregas.bind("<Button-1>", self._ao_clicar_tabela_entrega_check)
        self.tabela_entregas.bind("<<TreeviewSelect>>", lambda event: self.ao_selecionar_pedido(event, self.tabela_entregas))

        frame_acoes_entrega = tk.Frame(card_tabela_entregas, bg=CARD_BG)
        frame_acoes_entrega.pack(fill="x", padx=15, pady=8)

        # Linha 1: Ações com Pedidos Marcados / Relatórios
        frame_linha1_acoes = tk.Frame(frame_acoes_entrega, bg=CARD_BG)
        frame_linha1_acoes.pack(fill="x", pady=(0, 6))

        self.btn_direcionar_orcamento = tk.Button(
            frame_linha1_acoes, text="Direcionar Marcados p/ Orçamento", bg="#0284C7", fg="white", 
            font=("Segoe UI", 8, "bold"), bd=0, padx=10, pady=5, cursor="hand2", 
            activebackground="#0369A1", activeforeground="white", 
            command=self._ao_clicar_direcionar_orcamento
        )
        self.btn_direcionar_orcamento.pack(side=tk.LEFT, padx=(0, 6))

        btn_impressao_rapida = tk.Button(
            frame_linha1_acoes, text="Impressão Rápida (Seleção)", bg=SECONDARY_BTN, fg="white", 
            font=("Segoe UI", 8, "bold"), bd=0, padx=10, pady=5, cursor="hand2", 
            activebackground="#334155", activeforeground="white", 
            command=self._ao_clicar_impressao_rapida
        )
        btn_impressao_rapida.pack(side=tk.LEFT, padx=(0, 6))

        btn_relatorio_entrega_pdf = tk.Button(
            frame_linha1_acoes, text="Relatório de Entregas (PDF)", bg=ACCENT_COLOR, fg="white", 
            font=("Segoe UI", 8, "bold"), bd=0, padx=10, pady=5, cursor="hand2", 
            activebackground="#1D4ED8", activeforeground="white", 
            command=self._ao_clicar_gerar_relatorio_entrega
        )
        btn_relatorio_entrega_pdf.pack(side=tk.LEFT, padx=(0, 6))

        btn_desmarcar = tk.Button(
            frame_linha1_acoes, text="Desmarcar Todos", bg="#F1F5F9", fg=TEXT_MUTED, 
            font=("Segoe UI", 8), bd=1, relief="solid", highlightbackground=BORDER_COLOR, 
            padx=8, pady=3, cursor="hand2", command=self._desmarcar_todos_entregas
        )
        btn_desmarcar.pack(side=tk.RIGHT, padx=(4, 0))

        btn_marcar = tk.Button(
            frame_linha1_acoes, text="Marcar Todos", bg="#F1F5F9", fg=PRIMARY_COLOR, 
            font=("Segoe UI", 8), bd=1, relief="solid", highlightbackground=BORDER_COLOR, 
            padx=8, pady=3, cursor="hand2", command=self._marcar_todos_entregas
        )
        btn_marcar.pack(side=tk.RIGHT)

        # Linha 2: Alteração de Status da Entrega
        frame_linha2_acoes = tk.Frame(frame_acoes_entrega, bg=CARD_BG)
        frame_linha2_acoes.pack(fill="x")

        tk.Label(frame_linha2_acoes, text="Mudar Status:", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(frame_linha2_acoes, text="Já Entregue", bg=PRIMARY_COLOR, fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=8, pady=4, cursor="hand2", activebackground="#334155", activeforeground="white", command=lambda: self.callbacks.get("mover_status")(self.tabela_entregas, 'Ja Entregue')).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(frame_linha2_acoes, text="Já Recolhido", bg=PRIMARY_COLOR, fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=8, pady=4, cursor="hand2", activebackground="#334155", activeforeground="white", command=lambda: self.callbacks.get("mover_status")(self.tabela_entregas, 'Ja Recolhido')).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(frame_linha2_acoes, text="Arquivar", bg=SECONDARY_BTN, fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=8, pady=4, cursor="hand2", activebackground="#334155", activeforeground="white", command=lambda: self.callbacks.get("mover_status")(self.tabela_entregas, 'Arquivado')).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(frame_linha2_acoes, text="Cancelar", bg="#94A3B8", fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=8, pady=4, cursor="hand2", activebackground="#64748B", activeforeground="white", command=lambda: self.callbacks.get("mover_status")(self.tabela_entregas, 'Cancelado')).pack(side=tk.LEFT)

        # ABA RELATÓRIOS FINANCEIROS
        card_rel = tk.Frame(self.aba_relatorios, bg=CARD_BG, bd=1, relief="solid", highlightbackground=BORDER_COLOR, highlightthickness=1)
        card_rel.pack(fill="both", expand=True, padx=2, pady=5)

        tk.Label(card_rel, text="Relatórios Financeiros & Métricas de Desempenho", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=PRIMARY_COLOR).pack(anchor="w", padx=15, pady=(12, 5))

        frame_filtros_rel = tk.Frame(card_rel, bg=CARD_BG)
        frame_filtros_rel.pack(fill="x", padx=15, pady=5)

        tk.Label(frame_filtros_rel, text="Filtrar por:", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 5))
        self.combo_tipo_filtro_rel = ttk.Combobox(frame_filtros_rel, values=["Todos", "Diário", "Mensal", "Anual"], state="readonly", width=10, font=("Segoe UI", 9))
        self.combo_tipo_filtro_rel.set("Todos")
        self.combo_tipo_filtro_rel.pack(side=tk.LEFT, padx=(0, 10))
        self.combo_tipo_filtro_rel.bind("<<ComboboxSelected>>", self._atualizar_opcoes_filtro_rel)

        tk.Label(frame_filtros_rel, text="Valor:", font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 5))
        self.entry_valor_filtro_rel = tk.Entry(frame_filtros_rel, font=("Segoe UI", 9), width=15, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        self.entry_valor_filtro_rel.pack(side=tk.LEFT, padx=(0, 10))

        btn_aplicar_rel = tk.Button(frame_filtros_rel, text="Calcular / Filtrar", bg=ACCENT_COLOR, fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=10, pady=3, cursor="hand2", activebackground="#1D4ED8", activeforeground="white", command=self.calcular_relatorios_financeiros)
        btn_aplicar_rel.pack(side=tk.LEFT)

        # CARDS MÉTRICAS
        frame_cards_rel = tk.Frame(card_rel, bg=CARD_BG)
        frame_cards_rel.pack(fill="x", padx=15, pady=10)

        self.card_bruto = self._criar_card_metrica(frame_cards_rel, "Total Bruto (Itens+Frete)", "R$ 0,00", PRIMARY_COLOR)
        self.card_bruto.pack(side=tk.LEFT, fill="both", expand=True, padx=4)

        self.card_desconto = self._criar_card_metrica(frame_cards_rel, "Total Descontos", "R$ 0,00", TEXT_MUTED)
        self.card_desconto.pack(side=tk.LEFT, fill="both", expand=True, padx=4)

        self.card_liquido = self._criar_card_metrica(frame_cards_rel, "Receita Líquida", "R$ 0,00", ACCENT_COLOR)
        self.card_liquido.pack(side=tk.LEFT, fill="both", expand=True, padx=4)

        self.card_ticket = self._criar_card_metrica(frame_cards_rel, "Valor Médio / Pedido", "R$ 0,00", PRIMARY_COLOR)
        self.card_ticket.pack(side=tk.LEFT, fill="both", expand=True, padx=4)

        self.card_qtd_ped = self._criar_card_metrica(frame_cards_rel, "Total de Pedidos", "0", PRIMARY_COLOR)
        self.card_qtd_ped.pack(side=tk.LEFT, fill="both", expand=True, padx=4)

        self.tree_relatorio_financeiro = ZebraTreeview(card_rel, columns=("ID", "Cliente", "Data", "Itens", "Frete", "Desconto", "Líquido", "Status"), show="headings", height=8)
        self.tree_relatorio_financeiro.heading("ID", text="ID")
        self.tree_relatorio_financeiro.heading("Cliente", text="Cliente")
        self.tree_relatorio_financeiro.heading("Data", text="Data Evento")
        self.tree_relatorio_financeiro.heading("Itens", text="Total Itens")
        self.tree_relatorio_financeiro.heading("Frete", text="Frete")
        self.tree_relatorio_financeiro.heading("Desconto", text="Desconto")
        self.tree_relatorio_financeiro.heading("Líquido", text="Total Líquido")
        self.tree_relatorio_financeiro.heading("Status", text="Status")

        self.tree_relatorio_financeiro.column("ID", width=35, anchor="center")
        self.tree_relatorio_financeiro.column("Cliente", width=120)
        self.tree_relatorio_financeiro.column("Data", width=80, anchor="center")
        self.tree_relatorio_financeiro.column("Itens", width=80, anchor="e")
        self.tree_relatorio_financeiro.column("Frete", width=70, anchor="e")
        self.tree_relatorio_financeiro.column("Desconto", width=70, anchor="e")
        self.tree_relatorio_financeiro.column("Líquido", width=85, anchor="e")
        self.tree_relatorio_financeiro.column("Status", width=90, anchor="center")
        self.tree_relatorio_financeiro.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # CANCELADOS
        card_tabela_cancelados = tk.Frame(self.aba_cancelados, bg=CARD_BG, bd=1, relief="solid", highlightbackground=BORDER_COLOR, highlightthickness=1)
        card_tabela_cancelados.pack(fill="both", expand=True, padx=2, pady=5)
        tk.Label(card_tabela_cancelados, text="Histórico de Pedidos Cancelados", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=PRIMARY_COLOR).pack(anchor="w", padx=15, pady=10)
        self.tabela_cancelados = self.criar_tabela(card_tabela_cancelados)

        frame_acoes_cancelados = tk.Frame(card_tabela_cancelados, bg=CARD_BG)
        frame_acoes_cancelados.pack(fill="x", padx=15, pady=10)
        tk.Button(frame_acoes_cancelados, text="Reativar em Orçamentos", bg=PRIMARY_COLOR, fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=12, pady=6, cursor="hand2", activebackground="#334155", activeforeground="white", command=lambda: self.callbacks.get("mover_status")(self.tabela_cancelados, 'Orcamento')).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(frame_acoes_cancelados, text="Reativar em Entregas", bg=ACCENT_COLOR, fg="white", font=("Segoe UI", 8, "bold"), bd=0, padx=12, pady=6, cursor="hand2", activebackground="#1D4ED8", activeforeground="white", command=lambda: self.callbacks.get("mover_status")(self.tabela_cancelados, 'Pedido')).pack(side=tk.LEFT)

        self._aplicar_tema_moderno()

    # ------------------------------------------------------------------
    # TEMA MODERNO (aplicado sobre todos os widgets já criados)
    # ------------------------------------------------------------------
    def _cor_rgb(self, cor):
        r, g, b = self.root.winfo_rgb(cor)
        return r // 256, g // 256, b // 256

    def _luminancia(self, cor):
        r, g, b = self._cor_rgb(cor)
        return (0.299 * r + 0.587 * g + 0.114 * b) / 255

    def _ajustar_cor(self, cor, fator):
        """fator < 1 escurece, fator > 1 clareia."""
        r, g, b = self._cor_rgb(cor)
        if fator < 1:
            r, g, b = int(r * fator), int(g * fator), int(b * fator)
        else:
            f = fator - 1
            r, g, b = int(r + (255 - r) * f), int(g + (255 - g) * f), int(b + (255 - b) * f)
        return f"#{max(0, min(255, r)):02X}{max(0, min(255, g)):02X}{max(0, min(255, b)):02X}"

    def _fonte_maior(self, widget):
        try:
            f = tkfont.Font(root=self.root, font=widget.cget("font")).actual()
        except tk.TclError:
            return None
        novo = {8: 9, 9: 10, 10: 12, 11: 13}.get(abs(int(f["size"])), abs(int(f["size"])))
        estilo = [f["weight"]] if f["weight"] != "normal" else []
        if f["slant"] != "roman":
            estilo.append(f["slant"])
        return (f["family"], novo, *estilo)

    def _aplicar_tema_moderno(self):
        ignorar = {str(self.header)}

        def estilizar_botao(w):
            base = w.cget("bg")
            claro = self._luminancia(base) > 0.85
            if claro:
                base = "#E2E8F0"
                hover = "#CBD5E1"
            else:
                hover = self._ajustar_cor(base, 0.82)
            fonte = self._fonte_maior(w) or ("Segoe UI", 9, "bold")
            pad_x = int(float(w.cget("padx"))) if str(w.cget("padx")).replace(".", "").isdigit() else 8
            pad_y = int(float(w.cget("pady"))) if str(w.cget("pady")).replace(".", "").isdigit() else 4
            w.config(bg=base, relief="flat", bd=0, highlightthickness=0, cursor="hand2",
                     font=fonte, padx=pad_x + 2, pady=pad_y + 2,
                     activebackground=hover, activeforeground=w.cget("fg"),
                     disabledforeground="#94A3B8" if not claro else "#94A3B8")

            def entrar(_e, w=w, h=hover):
                if str(w.cget("state")) != "disabled":
                    w.config(bg=h)

            def sair(_e, w=w, b=base):
                w.config(bg=b)

            w.bind("<Enter>", entrar)
            w.bind("<Leave>", sair)

        def estilizar_campo(w, texto=False):
            fonte = self._fonte_maior(w) or ("Segoe UI", 10)
            w.config(relief="flat", bd=0, highlightthickness=1, highlightbackground=self.BORDER_COLOR,
                     highlightcolor=self.ACCENT_COLOR, bg="#F8FAFC", fg=self.TEXT_MAIN,
                     insertbackground=self.ACCENT_COLOR, font=fonte)
            if texto:
                w.config(padx=8, pady=6)
            else:
                gerente = w.winfo_manager()
                if gerente == "pack":
                    w.pack_configure(ipady=5)
                elif gerente == "grid":
                    w.grid_configure(ipady=5)
            w.bind("<FocusIn>", lambda e, w=w: w.config(bg="#FFFFFF"), add="+")
            w.bind("<FocusOut>", lambda e, w=w: w.config(bg="#F8FAFC"), add="+")

        def percorrer(w):
            if str(w) in ignorar:
                return
            if isinstance(w, ttk.Treeview):
                w.tag_configure("par", background=self.CARD_BG)
                w.tag_configure("impar", background="#F6F8FB")
            elif isinstance(w, ttk.Widget):
                pass  # widgets ttk (Combobox, Notebook...) já são estilizados via ttk.Style
            elif isinstance(w, tk.Button):
                estilizar_botao(w)
            elif isinstance(w, tk.Entry):
                estilizar_campo(w)
            elif isinstance(w, tk.Text):
                estilizar_campo(w, texto=True)
            elif isinstance(w, tk.Listbox):
                w.config(relief="flat", bd=0, highlightthickness=1, highlightbackground=self.ACCENT_COLOR,
                         bg="#FFFFFF", font=self._fonte_maior(w) or ("Segoe UI", 10),
                         selectbackground=self.ACCENT_COLOR, selectforeground="white")
            elif isinstance(w, tk.Label):
                fonte = self._fonte_maior(w)
                if fonte:
                    w.config(font=fonte)
            elif isinstance(w, tk.Frame) and int(float(w.cget("highlightthickness") or 0)) > 0:
                w.config(relief="flat", bd=0, highlightbackground=self.BORDER_COLOR)
            for filho in w.winfo_children():
                percorrer(filho)

        percorrer(self.root)

    def _criar_card_metrica(self, parent, titulo, valor_inicial, cor):
        f = tk.Frame(parent, bg="#F1F5F9", bd=1, relief="solid", highlightbackground="#E2E8F0", highlightthickness=1)
        lbl_t = tk.Label(f, text=titulo, font=("Segoe UI", 8, "bold"), bg="#F1F5F9", fg="#64748B")
        lbl_t.pack(anchor="w", padx=8, pady=(6, 0))
        lbl_v = tk.Label(f, text=valor_inicial, font=("Segoe UI", 11, "bold"), bg="#F1F5F9", fg=cor)
        lbl_v.pack(anchor="w", padx=8, pady=(0, 6))
        f.lbl_valor = lbl_v
        return f

    def _atualizar_opcoes_filtro_rel(self, event=None):
        tipo = self.combo_tipo_filtro_rel.get()
        self.entry_valor_filtro_rel.delete(0, tk.END)
        hoje = datetime.now()
        if tipo == "Diário":
            self.entry_valor_filtro_rel.insert(0, hoje.strftime("%d/%m/%Y"))
        elif tipo == "Mensal":
            self.entry_valor_filtro_rel.insert(0, hoje.strftime("%m/%Y"))
        elif tipo == "Anual":
            self.entry_valor_filtro_rel.insert(0, hoje.strftime("%Y"))

    def calcular_relatorios_financeiros(self):
        cb = self.callbacks.get("buscar_todos_pedidos_relatorio")
        if not cb:
            return
        pedidos = cb()
        catalogo = self.callbacks.get("obter_catalogo", lambda: [])()

        tipo_filtro = self.combo_tipo_filtro_rel.get()
        valor_filtro = self.entry_valor_filtro_rel.get().strip()

        for item in self.tree_relatorio_financeiro.get_children():
            self.tree_relatorio_financeiro.delete(item)

        total_bruto_acum = 0.0
        total_desconto_acum = 0.0
        receita_liquida_acum = 0.0
        qtd_pedidos_validos = 0

        for ped in pedidos:
            dt_obj = parse_data_br_ou_iso(ped.get("data_evento", ""))
            
            # Filtro de data
            if tipo_filtro == "Diário" and valor_filtro:
                dt_str_br = dt_obj.strftime("%d/%m/%Y")
                if dt_str_br != valor_filtro and ped.get("data_evento") != valor_filtro:
                    continue
            elif tipo_filtro == "Mensal" and valor_filtro:
                dt_mes_ano = dt_obj.strftime("%m/%Y")
                if dt_mes_ano != valor_filtro and not valor_filtro in ped.get("data_evento", ""):
                    continue
            elif tipo_filtro == "Anual" and valor_filtro:
                dt_ano = dt_obj.strftime("%Y")
                if dt_ano != valor_filtro and not valor_filtro in ped.get("data_evento", ""):
                    continue

            # Cálculo Financeiro
            subtotal_itens = 0.0
            texto_orc = ped.get("orcamento", "")
            linhas = [l.strip() for l in texto_orc.split('\n') if l.strip()]
            for linha in linhas:
                match_qtd = re.match(r'^(\d+)\s*(?:x|un|jogos|jogo)?\s+(.*)', linha, re.IGNORECASE)
                qtd = int(match_qtd.group(1)) if match_qtd else 1
                mat = match_qtd.group(2) if match_qtd else linha
                v_unit, _ = buscar_preco_catalogo(mat, catalogo)
                if v_unit is not None:
                    subtotal_itens += v_unit * qtd

            dist_km = float(ped.get("distancia_km", 0.0) or 0.0)
            valor_frete = (dist_km * 4.0) * 1.10
            valor_bruto = subtotal_itens + valor_frete
            val_desc = float(ped.get("desconto", 0.0) or 0.0)
            val_liq = max(0.0, valor_bruto - val_desc)

            if ped.get("tipo") != "Cancelado":
                total_bruto_acum += valor_bruto
                total_desconto_acum += val_desc
                receita_liquida_acum += val_liq
                qtd_pedidos_validos += 1

            self.tree_relatorio_financeiro.insert("", tk.END, values=(
                ped.get("id"),
                ped.get("cliente"),
                ped.get("data_evento"),
                f"R$ {subtotal_itens:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                f"R$ {valor_frete:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                f"R$ {val_desc:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                f"R$ {val_liq:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
                ped.get("tipo")
            ))

        ticket_medio = (receita_liquida_acum / qtd_pedidos_validos) if qtd_pedidos_validos > 0 else 0.0

        self.card_bruto.lbl_valor.config(text=f"R$ {total_bruto_acum:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','))
        self.card_desconto.lbl_valor.config(text=f"R$ {total_desconto_acum:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','))
        self.card_liquido.lbl_valor.config(text=f"R$ {receita_liquida_acum:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','))
        self.card_ticket.lbl_valor.config(text=f"R$ {ticket_medio:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','))
        self.card_qtd_ped.lbl_valor.config(text=str(qtd_pedidos_validos))

    # ------------------------------------------------------------------
    # ABA CLIENTES (cadastro)
    # ------------------------------------------------------------------
    def atualizar_tabela_clientes(self, lista):
        self.lista_clientes_completa = lista
        self._aplicar_filtro_clientes()

    def _aplicar_filtro_clientes(self):
        filtro = self.entry_filtro_clientes.get().strip()
        listar = self.callbacks.get("listar_clientes")
        lista = listar(filtro) if listar else []
        for item in self.tabela_clientes.get_children():
            self.tabela_clientes.delete(item)
        self._clientes_por_iid = {}
        for row in lista:
            iid = self.tabela_clientes.insert("", tk.END, values=(row[0], row[1], row[2] or "", row[3] or ""))
            self._clientes_por_iid[iid] = row

    def _ao_selecionar_cliente_tabela(self, event=None):
        sel = self.tabela_clientes.selection()
        if not sel or sel[0] not in self._clientes_por_iid:
            return
        cid, nome, tel, end = self._clientes_por_iid[sel[0]]
        self.id_cliente_em_edicao = cid
        for entry, valor in ((self.entry_cli_nome, nome), (self.entry_cli_telefone, tel), (self.entry_cli_endereco, end)):
            entry.delete(0, tk.END)
            entry.insert(0, valor or "")

    def limpar_campos_clientes(self):
        self.id_cliente_em_edicao = None
        for entry in (self.entry_cli_nome, self.entry_cli_telefone, self.entry_cli_endereco):
            entry.delete(0, tk.END)
        self.tabela_clientes.selection_remove(self.tabela_clientes.selection())

    def _ao_salvar_cliente(self):
        cb = self.callbacks.get("salvar_cliente")
        if cb:
            cb(self.id_cliente_em_edicao, self.entry_cli_nome.get(), self.entry_cli_telefone.get(), self.entry_cli_endereco.get())

    def _ao_excluir_cliente(self):
        cb = self.callbacks.get("excluir_cliente")
        if cb and self.id_cliente_em_edicao:
            cb(self.id_cliente_em_edicao)
        elif not self.id_cliente_em_edicao:
            messagebox.showwarning("Aviso", "Selecione um cliente na tabela para excluir.")

    def _usar_cliente_no_orcamento(self):
        if not self.id_cliente_em_edicao:
            messagebox.showwarning("Aviso", "Selecione um cliente na tabela.")
            return
        self.entry_nome.delete(0, tk.END)
        self.entry_nome.insert(0, self.entry_cli_nome.get())
        self.entry_telefone.delete(0, tk.END)
        self.entry_telefone.insert(0, self.entry_cli_telefone.get())
        if self.entry_cli_endereco.get().strip():
            self.entry_endereco.delete(0, tk.END)
            self.entry_endereco.insert(0, self.entry_cli_endereco.get())
        self.notebook.select(self.aba_cadastro)
        self.atualizar_preview_ao_vivo()

    # ------------------------------------------------------------------
    # CONTROLE DE CLIENTES (autocomplete por nome / telefone)
    # ------------------------------------------------------------------
    def _filtrar_clientes(self, event, entry):
        if event is not None and event.keysym in ("Down", "Up", "Return", "Escape", "Tab", "Left", "Right",
                                                  "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return

        termo = entry.get().strip()
        buscar = self.callbacks.get("buscar_clientes")
        if not termo or not buscar:
            self._esconder_sugestoes_clientes()
            return

        self._clientes_sugeridos = buscar(termo)
        self._entry_origem_cliente = entry
        self.listbox_clientes.delete(0, tk.END)

        if not self._clientes_sugeridos:
            self._esconder_sugestoes_clientes()
            return

        for _id, nome, tel, _end in self._clientes_sugeridos:
            self.listbox_clientes.insert(tk.END, f"{nome}  |  {tel or 'sem telefone'}")

        self.listbox_clientes.config(height=min(5, len(self._clientes_sugeridos)))
        self.listbox_clientes.place(in_=entry, relx=0, rely=1.0, relwidth=1.0)
        self.listbox_clientes.lift()

    def _foco_lista_clientes(self, event=None):
        if self._clientes_sugeridos and self.listbox_clientes.winfo_ismapped():
            self.listbox_clientes.focus_set()
            self.listbox_clientes.selection_clear(0, tk.END)
            self.listbox_clientes.selection_set(0)
            self.listbox_clientes.activate(0)
            return "break"

    def _esconder_se_sem_foco(self):
        if self.root.focus_get() is not self.listbox_clientes:
            self._esconder_sugestoes_clientes()

    def _esconder_sugestoes_clientes(self):
        self.listbox_clientes.place_forget()

    def _ao_selecionar_cliente(self, event=None):
        if event is not None and event.type == tk.EventType.ButtonRelease:
            idx = self.listbox_clientes.nearest(event.y)
        else:
            sel = self.listbox_clientes.curselection()
            idx = sel[0] if sel else None

        if idx is None or idx >= len(self._clientes_sugeridos):
            return

        _id, nome, tel, end = self._clientes_sugeridos[idx]
        self.entry_nome.delete(0, tk.END)
        self.entry_nome.insert(0, nome)
        self.entry_telefone.delete(0, tk.END)
        self.entry_telefone.insert(0, tel or "")
        if end and not self.entry_endereco.get().strip():
            self.entry_endereco.insert(0, end)

        self._esconder_sugestoes_clientes()
        self.entry_nome.focus_set()
        self.atualizar_preview_ao_vivo()

    def _ao_alterar_texto_orcamento(self, event=None):
        self._verificar_presenca_toalha()
        self.atualizar_preview_ao_vivo()

    def _verificar_presenca_toalha(self):
        texto = self.text_orcamento.get("1.0", tk.END).lower()
        if "toalha" in texto:
            self.frame_cor_toalha.pack(fill="x", pady=(2, 5))
        else:
            self.frame_cor_toalha.pack_forget()

    def atualizar_preview_ao_vivo(self):
        dados = self.obter_dados()
        self.exibir_preview(dados)

    def _filtrar_catalogo_digitacao(self, event):
        termo = self.entry_busca_catalogo.get().strip().lower()
        catalogo = self.callbacks.get("obter_catalogo", lambda: [])()

        self.listbox_sugestoes.delete(0, tk.END)

        if not termo:
            self.listbox_sugestoes.pack_forget()
            return

        correspondencias = []
        for c in catalogo:
            nome_item = c[2]
            preco_fmt = f"R$ {float(c[4]):,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
            if termo in nome_item.lower():
                correspondencias.append(f"{nome_item} - {preco_fmt}")

        if correspondencias:
            self.listbox_sugestoes.pack(fill="x", pady=(0, 4), before=self.text_orcamento.master.children.get("!frame2", None) or self.text_orcamento)
            for item in correspondencias:
                self.listbox_sugestoes.insert(tk.END, item)
        else:
            self.listbox_sugestoes.pack_forget()

    def _ao_selecionar_sugestao(self, event):
        selecao = self.listbox_sugestoes.curselection()
        if selecao:
            item_texto = self.listbox_sugestoes.get(selecao[0])
            nome_item = item_texto.split(" - R$")[0]
            self.entry_busca_catalogo.delete(0, tk.END)
            self.entry_busca_catalogo.insert(0, nome_item)
            self.listbox_sugestoes.pack_forget()

    def _adicionar_item_selecionado_busca(self):
        nome_item = self.entry_busca_catalogo.get().strip()
        qtd_texto = self.entry_qtd_busca.get().strip()

        if not nome_item:
            return

        if not qtd_texto.isdigit() or int(qtd_texto) < 1:
            qtd_num = "1"
        else:
            qtd_num = qtd_texto

        texto_atual = self.text_orcamento.get("1.0", tk.END).strip()
        novo_texto = f"{qtd_num} {nome_item}"

        if texto_atual:
            self.text_orcamento.insert(tk.END, f"\n{novo_texto}")
        else:
            self.text_orcamento.insert("1.0", novo_texto)

        self.entry_busca_catalogo.delete(0, tk.END)
        self.entry_qtd_busca.delete(0, tk.END)
        self.entry_qtd_busca.insert(0, "1")
        self.listbox_sugestoes.pack_forget()
        self._ao_alterar_texto_orcamento()

    def aplicar_sugestoes_catalogo(self):
        texto_orc = self.text_orcamento.get("1.0", tk.END).strip()
        if not texto_orc:
            messagebox.showwarning("Aviso", "Não há itens preenchidos para consultar o catálogo.")
            return

        catalogo = self.callbacks.get("obter_catalogo", lambda: [])()
        linhas = [l.strip() for l in texto_orc.split('\n') if l.strip()]
        novas_linhas = []

        for linha in linhas:
            match_qtd = re.match(r'^(\d+)\s*(?:x|un|jogos|jogo)?\s+(.*)', linha, re.IGNORECASE)
            if match_qtd:
                qtd = match_qtd.group(1)
                mat = match_qtd.group(2)
            else:
                qtd = "1"
                mat = linha

            _, nome_cat = buscar_preco_catalogo(mat, catalogo)
            if nome_cat:
                novas_linhas.append(f"{qtd} {nome_cat}")
            else:
                novas_linhas.append(linha)

        self.text_orcamento.delete("1.0", tk.END)
        self.text_orcamento.insert("1.0", "\n".join(novas_linhas))
        self._ao_alterar_texto_orcamento()
        messagebox.showinfo("Sucesso", "Nomes vinculados ao catálogo!")

    def criar_tabela(self, parent, com_status=False):
        cols = ("ID", "Cliente", "Telefone", "Endereço", "Data")
        tabela = ZebraTreeview(parent, columns=cols, show="headings")
        tabela.heading("ID", text="ID")
        tabela.heading("Cliente", text="Cliente")
        tabela.heading("Telefone", text="Telefone")
        tabela.heading("Endereço", text="Endereço")
        tabela.heading("Data", text="Data Evento")
        
        tabela.column("ID", width=35, anchor="center")
        tabela.column("Cliente", width=120)
        tabela.column("Telefone", width=95)
        tabela.column("Endereço", width=150)
        tabela.column("Data", width=80, anchor="center")

        tabela.pack(fill="both", expand=True, padx=15, pady=(0, 5))
        tabela.bind("<<TreeviewSelect>>", lambda event, t=tabela: self.ao_selecionar_pedido(event, t))
        return tabela

    def _ao_selecionar_item_catalogo(self, event):
        selecionado = self.tabela_catalogo.selection()
        if selecionado:
            vals = self.tabela_catalogo.item(selecionado[0])['values']
            if vals:
                self.id_item_cat_em_edicao = vals[0]
                self.entry_cat_categoria.delete(0, tk.END)
                self.entry_cat_categoria.insert(0, vals[1])
                self.entry_cat_nome.delete(0, tk.END)
                self.entry_cat_nome.insert(0, vals[2])
                self.entry_cat_unidade.delete(0, tk.END)
                self.entry_cat_unidade.insert(0, vals[3])
                self.entry_cat_preco.delete(0, tk.END)
                self.entry_cat_preco.insert(0, str(vals[4]).replace('R$', '').strip())
                self.entry_cat_estoque.delete(0, tk.END)
                self.entry_cat_estoque.insert(0, str(vals[5]))

    def limpar_campos_catalogo(self):
        self.id_item_cat_em_edicao = None
        self.entry_cat_categoria.delete(0, tk.END)
        self.entry_cat_nome.delete(0, tk.END)
        self.entry_cat_unidade.delete(0, tk.END)
        self.entry_cat_unidade.insert(0, "Unidade")
        self.entry_cat_preco.delete(0, tk.END)
        self.entry_cat_estoque.delete(0, tk.END)
        self.entry_filtro_tabela_cat.delete(0, tk.END)
        self._aplicar_filtro_tabela_cat()

    def _ao_salvar_cat(self):
        cb = self.callbacks.get("salvar_item_catalogo")
        if cb:
            cb(self.id_item_cat_em_edicao)

    def _ao_excluir_cat(self):
        cb = self.callbacks.get("excluir_item_catalogo")
        if cb and self.id_item_cat_em_edicao:
            cb(self.id_item_cat_em_edicao)

    def _ao_gerar_pdf_cat(self):
        cb = self.callbacks.get("gerar_pdf_catalogo")
        if cb:
            cb()

    def atualizar_tabela_catalogo(self, lista):
        self.lista_catalogo_completa = lista
        self._aplicar_filtro_tabela_cat()

    def _aplicar_filtro_tabela_cat(self):
        termo = self.entry_filtro_tabela_cat.get().strip().lower()

        for item in self.tabela_catalogo.get_children():
            self.tabela_catalogo.delete(item)

        for row in self.lista_catalogo_completa:
            cat = str(row[1]).lower()
            nome = str(row[2]).lower()

            if not termo or termo in cat or termo in nome:
                preco_fmt = f"R$ {row[4]:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
                self.tabela_catalogo.insert("", tk.END, values=(row[0], row[1], row[2], row[3], preco_fmt, row[5]))

    def ao_selecionar_pedido(self, event, tabela):
        self.root.after(30, lambda: self._carregar_preview_tabela(tabela))

    def _carregar_preview_tabela(self, tabela):
        selecionado = tabela.selection()
        if selecionado:
            item = tabela.item(selecionado[0])
            if 'values' in item and item['values']:
                idx_id = 1 if tabela == self.tabela_entregas else 0
                pedido_id = item['values'][idx_id]
                if self.callbacks.get("obter_detalhes_pedido"):
                    dados = self.callbacks["obter_detalhes_pedido"](pedido_id)
                    if dados:
                        self.exibir_preview(dados)

    def exibir_preview(self, dados):
        self.pedido_selecionado_dados = dados
        self.btn_editar_pedido.config(state="normal")
        self.btn_gerar_pdf.config(state="normal")
        self.btn_gerar_contrato.config(state="normal")

        # O documento se chama Orçamento ou Pedido conforme o local onde o registro se encontra
        eh_pedido = (dados.get("tipo") or "Orcamento") in ("Pedido", "Ja Entregue", "Ja Recolhido", "Arquivado")
        nome_doc = "Pedido" if eh_pedido else "Orçamento"
        self.lbl_preview_title.config(text=f"Prévia do {nome_doc} — Renascer")
        self.btn_gerar_pdf.config(text=f"Gerar PDF do {nome_doc}")
        self.btn_editar_pedido.config(text=f"Editar Este {nome_doc}")

        self.lbl_cliente_prev.config(text=f"Cliente: {dados.get('cliente') or '-'}")
        self.lbl_tel_prev.config(text=f"Tel: {dados.get('telefone') or '-'}")
        self.lbl_end_prev.config(text=f"End: {dados.get('endereco') or '-'}")
        self.lbl_data_prev.config(text=f"Data Evento: {dados.get('data_evento') or '-'}")
        self.lbl_obs_prev.config(text=f"Obs: {dados.get('observacoes') or '-'}")

        cor_toalha = dados.get("cor_toalha", "")
        if cor_toalha:
            self.lbl_cor_toalha_prev.config(text=f"Cor Toalha: {cor_toalha}")
            self.lbl_cor_toalha_prev.pack(fill="x", padx=8, pady=2)
        else:
            self.lbl_cor_toalha_prev.pack_forget()

        for item in self.tree_preview.get_children():
            self.tree_preview.delete(item)

        texto_orc = dados.get("orcamento", "")
        linhas = [l.strip() for l in texto_orc.split('\n') if l.strip()]

        catalogo = self.callbacks.get("obter_catalogo", lambda: [])()
        subtotal_itens = 0.0

        for linha in linhas:
            match_qtd = re.match(r'^(\d+)\s*(?:x|un|jogos|jogo)?\s+(.*)', linha, re.IGNORECASE)
            if match_qtd:
                qtd = match_qtd.group(1)
                mat = match_qtd.group(2)
            else:
                qtd = "1"
                mat = linha

            v_unit_num, nome_cat = buscar_preco_catalogo(mat, catalogo)
            item_encontrado_cat = f"✔ {nome_cat}" if nome_cat else "Não vinculado"

            if v_unit_num is not None:
                v_unit_str = f"R$ {v_unit_num:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
                v_tot_num = v_unit_num * int(qtd)
                v_tot_str = f"R$ {v_tot_num:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
                subtotal_itens += v_tot_num
            else:
                v_unit_str = "-"
                v_tot_str = "-"

            self.tree_preview.insert("", tk.END, values=(qtd, mat, item_encontrado_cat, v_unit_str, v_tot_str))

        try:
            dist_km = float(str(dados.get("distancia_km", 0.0)).replace(',', '.'))
        except ValueError:
            dist_km = 0.0

        try:
            desconto = float(str(dados.get("desconto", 0.0)).replace(',', '.'))
        except ValueError:
            desconto = 0.0

        valor_frete = (dist_km * 4.0) * 1.10
        total_geral = max(0.0, (subtotal_itens + valor_frete) - desconto)

        subtotal_str = f"R$ {subtotal_itens:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
        frete_str = f"R$ {valor_frete:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
        desconto_str = f"- R$ {desconto:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
        total_str = f"R$ {total_geral:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')

        self.lbl_subtotal_prev.config(text=f"Subtotal Itens: {subtotal_str}")
        self.lbl_frete_prev.config(text=f"Frete ({dist_km:.1f} km): {frete_str}")
        self.lbl_desconto_prev.config(text=f"Desconto Concedido: {desconto_str}")
        self.lbl_total_prev.config(text=f"TOTAL GERAL: {total_str}")

    def _ao_clicar_pdf(self):
        cb = self.callbacks.get("gerar_pdf")
        if cb and self.pedido_selecionado_dados:
            cb(self.pedido_selecionado_dados)

    def _ao_clicar_contrato(self):
        cb = self.callbacks.get("gerar_contrato")
        if cb and self.pedido_selecionado_dados:
            cb(self.pedido_selecionado_dados)

    def iniciar_edicao(self):
        if not self.pedido_selecionado_dados:
            messagebox.showwarning("Aviso", "Selecione um pedido na tabela para editar.")
            return

        dados = self.pedido_selecionado_dados
        self.id_em_edicao = dados.get("id")
        self.tipo_em_edicao = dados.get("tipo")

        self.preencher_campos(dados)
        self.notebook.select(self.aba_cadastro)

        self.lbl_titulo_form.config(text=f"Editando Pedido #{self.id_em_edicao}")

        self.frame_botoes_novos.pack_forget()
        self.frame_botoes_edicao.pack(fill="x", padx=15, pady=10)

    def cancelar_edicao(self):
        self.id_em_edicao = None
        self.limpar_campos()

        self.lbl_titulo_form.config(text="Novo Orçamento")

        self.frame_botoes_edicao.pack_forget()
        self.frame_botoes_novos.pack(fill="x", padx=15, pady=10)

    def _ao_clicar_salvar_edicao(self):
        cb = self.callbacks.get("salvar_edicao")
        if cb and self.id_em_edicao:
            cb(self.id_em_edicao)
            self.cancelar_edicao()

    def _ao_clicar_salvar_orcamento(self):
        cb = self.callbacks.get("salvar_orcamento")
        if cb:
            cb()

    def _ao_clicar_salvar_entrega(self):
        cb = self.callbacks.get("enviar_entrega")
        if cb:
            cb()

    def preencher_campos(self, dados):
        self.entry_nome.delete(0, tk.END)
        self.entry_nome.insert(0, dados.get("cliente", ""))
        self.entry_telefone.delete(0, tk.END)
        self.entry_telefone.insert(0, dados.get("telefone", ""))
        self.entry_endereco.delete(0, tk.END)
        self.entry_endereco.insert(0, dados.get("endereco", ""))
        self.entry_data_evento.delete(0, tk.END)
        self.entry_data_evento.insert(0, dados.get("data_evento", ""))
        self.entry_distancia_km.delete(0, tk.END)
        self.entry_distancia_km.insert(0, str(dados.get("distancia_km", "0")))
        self.entry_desconto.delete(0, tk.END)
        self.entry_desconto.insert(0, str(dados.get("desconto", "0")))
        self.entry_observacoes.delete(0, tk.END)
        self.entry_observacoes.insert(0, dados.get("observacoes", ""))
        self.text_orcamento.delete("1.0", tk.END)
        self.text_orcamento.insert("1.0", dados.get("orcamento", ""))

        cor = dados.get("cor_toalha", "")
        if cor:
            self.combo_cor_toalha.set(cor)

        self._ao_alterar_texto_orcamento()

    def limpar_campos(self):
        self.entry_nome.delete(0, tk.END)
        self.entry_telefone.delete(0, tk.END)
        self.entry_endereco.delete(0, tk.END)
        self.entry_data_evento.delete(0, tk.END)
        self.entry_distancia_km.delete(0, tk.END)
        self.entry_desconto.delete(0, tk.END)
        self.entry_observacoes.delete(0, tk.END)
        self.text_orcamento.delete("1.0", tk.END)
        self.entry_busca_catalogo.delete(0, tk.END)
        self.entry_qtd_busca.delete(0, tk.END)
        self.entry_qtd_busca.insert(0, "1")
        self.combo_cor_toalha.set("Branca")
        self.frame_cor_toalha.pack_forget()
        self.listbox_sugestoes.pack_forget()
        self._esconder_sugestoes_clientes()
        self.exibir_preview({})

    def obter_dados(self):
        tem_toalha = "toalha" in self.text_orcamento.get("1.0", tk.END).lower()
        cor_selecionada = self.combo_cor_toalha.get() if tem_toalha else ""

        try:
            dist = float(self.entry_distancia_km.get().replace(',', '.'))
        except ValueError:
            dist = 0.0

        try:
            desc = float(self.entry_desconto.get().replace(',', '.'))
        except ValueError:
            desc = 0.0

        dados_edicao = {}
        if self.id_em_edicao:
            dados_edicao = {"id": self.id_em_edicao, "tipo": getattr(self, "tipo_em_edicao", None)}

        return {
            **dados_edicao,
            "cliente": self.entry_nome.get(),
            "telefone": self.entry_telefone.get(),
            "endereco": self.entry_endereco.get(),
            "data_evento": self.entry_data_evento.get(),
            "distancia_km": dist,
            "desconto": desc,
            "observacoes": self.entry_observacoes.get(),
            "orcamento": self.text_orcamento.get("1.0", tk.END).strip(),
            "cor_toalha": cor_selecionada
        }

    def atualizar_listas(self, lista_orcamentos, lista_entregas, lista_cancelados):
        for item in self.tabela_orcamentos.get_children():
            self.tabela_orcamentos.delete(item)
        for row in lista_orcamentos:
            self.tabela_orcamentos.insert("", tk.END, values=(row[0], row[1], row[2], row[3], row[4]))

        self.lista_entregas_completa = lista_entregas
        self._aplicar_filtro_entregas()

        for item in self.tabela_cancelados.get_children():
            self.tabela_cancelados.delete(item)
        for row in lista_cancelados:
            self.tabela_cancelados.insert("", tk.END, values=(row[0], row[1], row[2], row[3], row[4]))

        self.calcular_relatorios_financeiros()

    def _aplicar_filtro_entregas(self):
        filtro_status = self.combo_filtro_status_entrega.get()
        filtro_periodo = self.combo_filtro_periodo_entrega.get()

        for item in self.tabela_entregas.get_children():
            self.tabela_entregas.delete(item)

        mapa_status = {
            "Pendente (Pedido)": "Pedido",
            "Já Entregue": "Ja Entregue",
            "Já Recolhido": "Ja Recolhido",
            "Arquivado": "Arquivado"
        }

        dias_semana_map = {
            "Segunda-feira": 0, "Terça-feira": 1, "Quarta-feira": 2,
            "Quinta-feira": 3, "Sexta-feira": 4, "Sábado": 5, "Domingo": 6
        }

        # Ordenar Cronologicamente por Data do Evento Crescente
        itens_ordenados = sorted(
            self.lista_entregas_completa,
            key=lambda r: parse_data_br_ou_iso(r[4])
        )

        for row in itens_ordenados:
            st = row[5] if len(row) > 5 else "Pedido"
            data_str = row[4]
            dt_obj = parse_data_br_ou_iso(data_str)

            # Filtro por Status
            if filtro_status != "Todos" and mapa_status.get(filtro_status) != st:
                continue

            # Filtro por Dia da Semana / Período
            if filtro_periodo != "Todos os Dias":
                dia_alvo = dias_semana_map.get(filtro_periodo)
                if dt_obj == datetime.min or dt_obj.weekday() != dia_alvo:
                    continue

            status_exibicao = st.replace("Ja", "Já").replace("Pedido", "Pendente")
            pid = row[0]
            check_symbol = "☑" if (pid in self.checados_entrega or str(pid) in self.checados_entrega) else "☐"

            self.tabela_entregas.insert("", tk.END, values=(check_symbol, pid, row[1], row[2], row[3], row[4], status_exibicao))

    def _ao_clicar_tabela_entrega_check(self, event):
        region = self.tabela_entregas.identify("region", event.x, event.y)
        column = self.tabela_entregas.identify_column(event.x)

        if region == "heading" and column == "#1":
            ids_visiveis = []
            for item_id in self.tabela_entregas.get_children():
                vals = self.tabela_entregas.item(item_id, "values")
                if vals and len(vals) > 1:
                    raw_id = vals[1]
                    norm_id = int(raw_id) if str(raw_id).isdigit() else raw_id
                    ids_visiveis.append(norm_id)
            if ids_visiveis:
                if all((pid in self.checados_entrega or str(pid) in self.checados_entrega) for pid in ids_visiveis):
                    for pid in ids_visiveis:
                        self.checados_entrega.discard(pid)
                        self.checados_entrega.discard(str(pid))
                else:
                    for pid in ids_visiveis:
                        self.checados_entrega.add(pid)
                self._aplicar_filtro_entregas()
            return

        if region == "cell" and column == "#1":
            item_id = self.tabela_entregas.identify_row(event.y)
            if item_id:
                vals = self.tabela_entregas.item(item_id, "values")
                if vals and len(vals) > 1:
                    raw_id = vals[1]
                    pid = int(raw_id) if str(raw_id).isdigit() else raw_id
                    if pid in self.checados_entrega or str(pid) in self.checados_entrega:
                        self.checados_entrega.discard(pid)
                        self.checados_entrega.discard(str(pid))
                    else:
                        self.checados_entrega.add(pid)
                    self._aplicar_filtro_entregas()

    def _marcar_todos_entregas(self):
        for item_id in self.tabela_entregas.get_children():
            vals = self.tabela_entregas.item(item_id, "values")
            if vals and len(vals) > 1:
                raw_id = vals[1]
                pid = int(raw_id) if str(raw_id).isdigit() else raw_id
                self.checados_entrega.add(pid)
        self._aplicar_filtro_entregas()

    def _desmarcar_todos_entregas(self):
        self.checados_entrega.clear()
        self._aplicar_filtro_entregas()

    def _ao_clicar_direcionar_orcamento(self):
        ids_para_mover = []
        if self.checados_entrega:
            ids_para_mover = [int(p) if str(p).isdigit() else p for p in self.checados_entrega]
        else:
            selecionado = self.tabela_entregas.selection()
            if selecionado:
                item = self.tabela_entregas.item(selecionado[0])
                vals = item.get('values', [])
                if len(vals) > 1:
                    raw_id = vals[1]
                    pid = int(raw_id) if str(raw_id).isdigit() else raw_id
                    ids_para_mover = [pid]

        if not ids_para_mover:
            messagebox.showwarning("Aviso", "Marque pelo menos um pedido na caixa [X] (ou selecione na tabela) para direcionar ao Controle de Orçamento.")
            return

        cb = self.callbacks.get("direcionar_para_orcamento")
        if cb:
            cb(ids_para_mover)

    def _ao_clicar_impressao_rapida(self):
        ids_para_imprimir = []
        if self.checados_entrega:
            ids_para_imprimir = [int(p) if str(p).isdigit() else p for p in self.checados_entrega]
        else:
            selecionado = self.tabela_entregas.selection()
            if selecionado:
                item = self.tabela_entregas.item(selecionado[0])
                vals = item.get('values', [])
                if len(vals) > 1:
                    raw_id = vals[1]
                    pid = int(raw_id) if str(raw_id).isdigit() else raw_id
                    ids_para_imprimir = [pid]

        if not ids_para_imprimir:
            messagebox.showwarning("Aviso", "Selecione pelo menos um pedido marcando a caixa [X] (ou selecione na tabela) para impressão rápida.")
            return

        cb = self.callbacks.get("gerar_impressao_rapida")
        if cb:
            cb(ids_para_imprimir)

    def _ao_clicar_gerar_relatorio_entrega(self):
        ids_visiveis = []
        for item_id in self.tabela_entregas.get_children():
            vals = self.tabela_entregas.item(item_id, "values")
            if vals:
                ids_visiveis.append(vals[1])

        if not ids_visiveis:
            messagebox.showwarning("Aviso", "Não há entregas visíveis na tabela para gerar o relatório.")
            return

        cb = self.callbacks.get("gerar_relatorio_entrega")
        if cb:
            cb(ids_visiveis)
