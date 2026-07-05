# -*- coding: utf-8 -*-
"""
- MAE 0.995 gol por time
- 70.7% de acerto de resultado
- 19.5% de placar exato

Hiperparametros do grid search:
  SUAVIZACAO = 0.5   (meio jogo ficticio "na media" por time)
  DECAIMENTO = 0.92  (jogo de k dias atras pesa 0.92^k)

M = soma de gols da amostra / jogos / 2
ataque(T) = gols feitos por jogo (ponderado) / M
defesa(T) = gols sofridos por jogo (ponderado) / M
gols esperados de A = M * ataque(A) * defesa(B)   [cruzado!]
sorte (opcional) = multiplicador aleatorio em [0.525, 1.475]
"""

import csv
import random
from datetime import date

# hiperparametros validados: se mudar, rode o backtest de novo antes
SUAVIZACAO = 0.5
DECAIMENTO = 0.92

# limites do multiplicador de sorte (1 mais ou menos 0.475)
SORTE_MINIMA = 0.525
SORTE_MAXIMA = 1.475

# Camada de dados: leitura e escrita do CSV
def carregar_jogos(caminho_do_csv):
    """Le o CSV e devolve lista de tuplas (data, time_a, gols_a, gols_b, time_b)."""
    jogos = []
    with open(caminho_do_csv, "r", encoding="utf-8") as arquivo:
        leitor = csv.DictReader(arquivo)
        for linha in leitor:
            data_do_jogo = linha["data"]
            time_a = linha["time_a"].strip()
            gols_a = int(linha["gols_a"])
            gols_b = int(linha["gols_b"])
            time_b = linha["time_b"].strip()
            jogos.append((data_do_jogo, time_a, gols_a, gols_b, time_b))
    # ordena por data: o modelo assume passado -> presente
    jogos.sort(key=lambda jogo: jogo[0])
    return jogos


def adicionar_jogo(caminho_do_csv, data_do_jogo, time_a, gols_a, gols_b, time_b):
    """Anexa um jogo novo ao fim do CSV (cria o arquivo se nao existir)."""
    import os
    arquivo_existe = os.path.exists(caminho_do_csv)
    with open(caminho_do_csv, "a", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        if not arquivo_existe:
            escritor.writerow(["data", "time_a", "gols_a", "gols_b", "time_b"])
        escritor.writerow([data_do_jogo, time_a, gols_a, gols_b, time_b])

# Media da amostra (a regua M)
def calcular_media_amostra(jogos):
    total_de_gols = 0
    for jogo in jogos:
        gols_a = jogo[2]
        gols_b = jogo[3]
        total_de_gols = total_de_gols + gols_a + gols_b
    numero_de_jogos = len(jogos)
    media_por_jogo = total_de_gols / numero_de_jogos
    media_por_time_por_jogo = media_por_jogo / 2
    return media_por_time_por_jogo

# Peso temporal: decaimento exponencial
def calcular_peso_temporal(data_do_jogo, data_de_referencia):
    dia_do_jogo = date.fromisoformat(data_do_jogo)
    dia_de_referencia = date.fromisoformat(data_de_referencia)
    idade_em_dias = (dia_de_referencia - dia_do_jogo).days
    if idade_em_dias < 0:
        # jogo "do futuro" em relacao a referencia: peso zero, por seguranca
        return 0.0
    peso = DECAIMENTO ** idade_em_dias
    return peso

# Ataque e Fraqueza defensiva de um time
def calcular_forcas_do_time(nome_do_time, jogos, media_M, data_de_referencia):
    """
    Devolve (ataque, fraqueza_defensiva, jogos_encontrados) do time.
    ataque > 1  -> ataca acima da media da amostra
    defesa > 1  -> defende PIOR que a media (fraqueza)
    """
    soma_gols_feitos = 0.0
    soma_gols_sofridos = 0.0
    soma_dos_pesos = 0.0
    jogos_encontrados = 0

    for jogo in jogos:
        data_do_jogo, time_a, gols_a, gols_b, time_b = jogo
        if nome_do_time != time_a and nome_do_time != time_b:
            continue
        peso = calcular_peso_temporal(data_do_jogo, data_de_referencia)
        if nome_do_time == time_a:
            gols_feitos_neste_jogo = gols_a
            gols_sofridos_neste_jogo = gols_b
        else:
            gols_feitos_neste_jogo = gols_b
            gols_sofridos_neste_jogo = gols_a
        soma_gols_feitos = soma_gols_feitos + gols_feitos_neste_jogo * peso
        soma_gols_sofridos = soma_gols_sofridos + gols_sofridos_neste_jogo * peso
        soma_dos_pesos = soma_dos_pesos + peso
        jogos_encontrados = jogos_encontrados + 1

    if jogos_encontrados == 0:
        return None

    # Suavizacao: meio jogo ficticio com "media_M" gols feitos e sofridos.
    # Segura extremos de amostra pequena (tipo: seleção que não tomou nenhum gol).
    gols_feitos_ajustado = soma_gols_feitos + SUAVIZACAO * media_M
    gols_sofridos_ajustado = soma_gols_sofridos + SUAVIZACAO * media_M
    jogos_ajustado = soma_dos_pesos + SUAVIZACAO

    gols_feitos_por_jogo = gols_feitos_ajustado / jogos_ajustado
    gols_sofridos_por_jogo = gols_sofridos_ajustado / jogos_ajustado

    ataque = gols_feitos_por_jogo / media_M
    fraqueza_defensiva = gols_sofridos_por_jogo / media_M
    return ataque, fraqueza_defensiva, jogos_encontrados

# Gols esperados (ataque de um bate na defesa do OUTRO)
def prever_placar(time_a, time_b, jogos, data_de_referencia):
    """
    Devolve um dicionario com os gols esperados crus e os coeficientes,
    ou None se algum time nao tem historico.
    """
    media_M = calcular_media_amostra(jogos)

    forcas_a = calcular_forcas_do_time(time_a, jogos, media_M, data_de_referencia)
    forcas_b = calcular_forcas_do_time(time_b, jogos, media_M, data_de_referencia)
    if forcas_a is None or forcas_b is None:
        return None

    ataque_a, defesa_a, jogos_a = forcas_a
    ataque_b, defesa_b, jogos_b = forcas_b

    gols_esperados_a = media_M * ataque_a * defesa_b
    gols_esperados_b = media_M * ataque_b * defesa_a

    return {
        "media_M": media_M,
        "ataque_a": ataque_a, "defesa_a": defesa_a, "jogos_a": jogos_a,
        "ataque_b": ataque_b, "defesa_b": defesa_b, "jogos_b": jogos_b,
        "gols_esperados_a": gols_esperados_a,
        "gols_esperados_b": gols_esperados_b,
    }

# Fator sorte (só pra simulacao, nunca pra palpite seco)
def aplicar_sorte(gols_esperados):
    multiplicador = random.uniform(SORTE_MINIMA, SORTE_MAXIMA)
    return gols_esperados * multiplicador, multiplicador


def simular_placar(gols_esperados_a, gols_esperados_b, numero_de_simulacoes=10000):
    """
    Monte Carlo: roda o jogo N vezes com sorte e conta os placares.
    Devolve (placar_mais_comum, probabilidade_vitoria_a, empate, vitoria_b).
    """
    contagem_de_placares = {}
    vitorias_a = 0
    empates = 0
    vitorias_b = 0

    for _rodada in range(numero_de_simulacoes):
        gols_a_com_sorte, _s1 = aplicar_sorte(gols_esperados_a)
        gols_b_com_sorte, _s2 = aplicar_sorte(gols_esperados_b)
        placar_a = round(gols_a_com_sorte)
        placar_b = round(gols_b_com_sorte)
        chave = (placar_a, placar_b)
        contagem_de_placares[chave] = contagem_de_placares.get(chave, 0) + 1
        if placar_a > placar_b:
            vitorias_a = vitorias_a + 1
        elif placar_a < placar_b:
            vitorias_b = vitorias_b + 1
        else:
            empates = empates + 1

    placares_ordenados = sorted(contagem_de_placares.items(),
                                key=lambda item: -item[1])
    return {
        "placares_mais_comuns": placares_ordenados[:5],
        "probabilidade_vitoria_a": vitorias_a / numero_de_simulacoes,
        "probabilidade_empate": empates / numero_de_simulacoes,
        "probabilidade_vitoria_b": vitorias_b / numero_de_simulacoes,
    }
