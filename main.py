import sys
import os
import tkinter as tk
from tkinter import messagebox

if sys.platform.startswith('win'):
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception:
        pass

import database
import pdf_generator
from interface import FormularioOrcamento

try:
    import ia_service
except ImportError:
    ia_service = None

database.criar_tabelas()

def carregar_tudo():
    orcamentos = database.buscar_por_status('Orcamento')
    entregas = database.buscar_por_status('Pedido')
    cancelados = database.buscar_por_status('Cancelado')
    catalogo = database.buscar_catalogo()

    app.atualizar_listas(orcamentos, entregas, cancelados)
    app.atualizar_tabela_catalogo(catalogo)
    app.atualizar_tabela_clientes(database.listar_clientes())

def salvar_cliente(id_cliente, nome, telefone, endereco):
    ok, msg = database.salvar_cliente(id_cliente, nome, telefone, endereco)
    if not ok:
        messagebox.showwarning("Cliente", msg)
        return False
    app.limpar_campos_clientes()
    carregar_tudo()
    messagebox.showinfo("Sucesso", msg)
    return True

def excluir_cliente(id_cliente):
    if messagebox.askyesno("Confirmar Exclusão", "Remover este cliente do cadastro?\n(Os pedidos já feitos não são apagados.)"):
        database.excluir_cliente(id_cliente)
        app.limpar_campos_clientes()
        carregar_tudo()

def conferir_cliente_duplicado(dados):
    """Evita cadastrar o mesmo cliente de formas diferentes.
    Retorna False se o usuário cancelar o salvamento."""
    similar = database.encontrar_cliente_similar(dados['cliente'], dados['telefone'])
    if not similar:
        return True

    _, nome_cad, tel_cad, end_cad = similar
    if nome_cad.strip() == dados['cliente'].strip() and (tel_cad or '').strip() == dados['telefone'].strip():
        return True

    resp = messagebox.askyesnocancel(
        "Cliente já cadastrado?",
        "Já existe um cliente parecido no cadastro:\n\n"
        f"Nome: {nome_cad}\nTelefone: {tel_cad or '-'}\n\n"
        "Deseja usar o cadastro existente?\n\n"
        "Sim = usar nome/telefone já cadastrados\n"
        "Não = manter como digitado\n"
        "Cancelar = voltar e revisar"
    )
    if resp is None:
        return False
    if resp:
        dados['cliente'] = nome_cad
        dados['telefone'] = tel_cad or dados['telefone']
        if not dados['endereco'] and end_cad:
            dados['endereco'] = end_cad
    return True

def salvar_orcamento():
    dados = app.obter_dados()
    if not dados['cliente']:
        messagebox.showwarning("Campo Obrigatório", "O campo Cliente deve ser preenchido.")
        return
    if not conferir_cliente_duplicado(dados):
        return
    
    id_novo = database.inserir_pedido(dados, tipo='Orcamento')
    app.limpar_campos()
    carregar_tudo()
    
    dados_completos = database.buscar_por_id(id_novo)
    if dados_completos:
        app.exibir_preview(dados_completos)
    
    messagebox.showinfo("Sucesso", f"Orçamento #{id_novo} salvo com sucesso!")

def enviar_entrega():
    dados = app.obter_dados()
    if not dados['cliente']:
        messagebox.showwarning("Campo Obrigatório", "O campo Cliente deve ser preenchido.")
        return
    if not conferir_cliente_duplicado(dados):
        return

    id_novo = database.inserir_pedido(dados, tipo='Pedido')
    app.limpar_campos()
    carregar_tudo()

    dados_completos = database.buscar_por_id(id_novo)
    if dados_completos:
        app.exibir_preview(dados_completos)

    messagebox.showinfo("Sucesso", f"Pedido #{id_novo} salvo para Entrega!")

def salvar_edicao(id_pedido):
    dados = app.obter_dados()
    if not dados['cliente']:
        messagebox.showwarning("Campo Obrigatório", "O campo Cliente deve ser preenchido.")
        return
    if not conferir_cliente_duplicado(dados):
        return

    database.atualizar_pedido(id_pedido, dados)
    carregar_tudo()
    
    dados_atualizados = database.buscar_por_id(id_pedido)
    if dados_atualizados:
        app.exibir_preview(dados_atualizados)

    messagebox.showinfo("Sucesso", f"Pedido #{id_pedido} atualizado com sucesso!")

def mover_status(tabela, novo_status):
    ids_pedidos = []
    if tabela == app.tabela_entregas and app.checados_entrega:
        ids_pedidos = list(app.checados_entrega)
    else:
        selecionado = tabela.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione ou marque pelo menos um item na tabela primeiro.")
            return

        item = tabela.item(selecionado[0])
        idx_id = 1 if tabela == app.tabela_entregas else 0
        ids_pedidos = [item['values'][idx_id]]

    database.alterar_status_multiplos(ids_pedidos, novo_status)

    if tabela == app.tabela_entregas:
        for pid in ids_pedidos:
            app.checados_entrega.discard(pid)

    carregar_tudo()

    if ids_pedidos:
        dados_atualizados = database.buscar_por_id(ids_pedidos[-1])
        if dados_atualizados:
            app.exibir_preview(dados_atualizados)

def direcionar_para_orcamento(lista_ids):
    if not lista_ids:
        messagebox.showwarning("Aviso", "Marque pelo menos um pedido na caixa [X] (ou selecione na tabela) para direcionar ao Controle de Orçamento.")
        return

    qtd = len(lista_ids)
    msg_confirmacao = (
        f"Deseja direcionar o pedido #{lista_ids[0]} de volta para o Controle de Orçamento?"
        if qtd == 1
        else f"Deseja direcionar os {qtd} pedidos marcados de volta para o Controle de Orçamento?"
    )

    if not messagebox.askyesno("Confirmar Direcionamento", msg_confirmacao):
        return

    database.alterar_status_multiplos(lista_ids, 'Orcamento')

    for pid in lista_ids:
        app.checados_entrega.discard(pid)

    carregar_tudo()

    dados_atualizados = database.buscar_por_id(lista_ids[-1])
    if dados_atualizados:
        app.exibir_preview(dados_atualizados)

    if qtd == 1:
        messagebox.showinfo("Sucesso", f"Pedido #{lista_ids[0]} direcionado para Controle de Orçamento com sucesso!")
    else:
        messagebox.showinfo("Sucesso", f"{qtd} pedidos direcionados para Controle de Orçamento com sucesso!")

def obter_detalhes_pedido(id_pedido):
    return database.buscar_por_id(id_pedido)

def gerar_pdf(dados_pedido):
    catalogo_atual = database.buscar_catalogo()
    caminho = pdf_generator.gerar_pdf_pedido(dados_pedido, catalogo_atual)
    nome_doc = "Pedido" if (dados_pedido.get("tipo") or "Orcamento") in ("Pedido", "Ja Entregue", "Ja Recolhido", "Arquivado") else "Orçamento"
    messagebox.showinfo("Sucesso", f"PDF do {nome_doc} gerado com sucesso em:\n{os.path.abspath(caminho)}")

def gerar_contrato(dados_pedido):
    catalogo_atual = database.buscar_catalogo()
    caminho = pdf_generator.gerar_contrato_pedido(dados_pedido, catalogo_atual)
    messagebox.showinfo("Sucesso", f"Contrato do Pedido gerado com sucesso em:\n{os.path.abspath(caminho)}")

def salvar_item_catalogo(id_item):
    cat = app.entry_cat_categoria.get().strip()
    nome = app.entry_cat_nome.get().strip()
    unidade = app.entry_cat_unidade.get().strip()
    preco_str = app.entry_cat_preco.get().strip().replace(',', '.')
    estoque_str = app.entry_cat_estoque.get().strip()

    if not nome:
        messagebox.showwarning("Campo Obrigatório", "Informe pelo menos o Nome do Item.")
        return

    try:
        preco = float(preco_str) if preco_str else 0.0
    except ValueError:
        messagebox.showerror("Erro de Valor", "Preço inválido. Use formato numérico ex: 25.00")
        return

    try:
        estoque = int(estoque_str) if estoque_str else 0
    except ValueError:
        messagebox.showerror("Erro de Estoque", "Quantidade em Estoque deve ser número inteiro.")
        return

    database.salvar_item_catalogo(id_item, cat, nome, unidade, preco, estoque)
    app.limpar_campos_catalogo()
    carregar_tudo()
    messagebox.showinfo("Sucesso", "Item salvo no catálogo com sucesso!")

def excluir_item_catalogo(id_item):
    if messagebox.askyesno("Confirmar Exclusão", "Deseja realmente remover este item do catálogo?"):
        database.excluir_item_catalogo(id_item)
        app.limpar_campos_catalogo()
        carregar_tudo()

def gerar_pdf_catalogo():
    lista = database.buscar_catalogo()
    caminho = pdf_generator.gerar_pdf_catalogo(lista)
    messagebox.showinfo("Sucesso", f"PDF do Catálogo gerado em:\n{os.path.abspath(caminho)}")

def gerar_impressao_rapida(lista_ids):
    if not lista_ids:
        messagebox.showwarning("Aviso", "Selecione ou marque pelo menos um pedido para impressão rápida.")
        return
    try:
        pedidos = [database.buscar_por_id(pid) for pid in lista_ids if database.buscar_por_id(pid)]
        if not pedidos:
            messagebox.showwarning("Aviso", "Nenhum dado encontrado para os pedidos selecionados.")
            return
        catalogo_atual = database.buscar_catalogo()
        caminho = pdf_generator.gerar_impressao_rapida_multipla(pedidos, catalogo_atual)
        try:
            os.startfile(caminho)
        except Exception:
            pass
        messagebox.showinfo("Sucesso", f"Impressão Rápida gerada com sucesso em:\n{os.path.abspath(caminho)}")
    except Exception as e:
        messagebox.showerror("Erro na Impressão", f"Ocorreu um erro ao gerar a Impressão Rápida:\n{str(e)}")

def gerar_relatorio_entrega(lista_ids):
    pedidos = [database.buscar_por_id(pid) for pid in lista_ids if database.buscar_por_id(pid)]
    caminho = pdf_generator.gerar_relatorio_entregas(pedidos)
    messagebox.showinfo("Sucesso", f"Relatório de Entregas gerado com sucesso em:\n{os.path.abspath(caminho)}")

root = tk.Tk()
root.title("Sistema de Gestão - Renascer Locações")
root.geometry("1280x750")

callbacks = {
    "salvar_orcamento": salvar_orcamento,
    "enviar_entrega": enviar_entrega,
    "salvar_edicao": salvar_edicao,
    "mover_status": mover_status,
    "direcionar_para_orcamento": direcionar_para_orcamento,
    "obter_detalhes_pedido": obter_detalhes_pedido,
    "gerar_pdf": gerar_pdf,
    "gerar_contrato": gerar_contrato,
    "buscar_clientes": database.buscar_clientes,
    "listar_clientes": database.listar_clientes,
    "salvar_cliente": salvar_cliente,
    "excluir_cliente": excluir_cliente,
    "obter_catalogo": database.buscar_catalogo, 
    "salvar_item_catalogo": salvar_item_catalogo,
    "excluir_item_catalogo": excluir_item_catalogo,
    "gerar_pdf_catalogo": gerar_pdf_catalogo,
    "buscar_todos_pedidos_relatorio": database.buscar_todos_pedidos_relatorio,
    "gerar_impressao_rapida": gerar_impressao_rapida,
    "gerar_relatorio_entrega": gerar_relatorio_entrega
}

app = FormularioOrcamento(root, callbacks)
carregar_tudo()
root.mainloop()
