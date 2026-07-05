"""
Comandos:
  adicionar  registra o placar de um jogo novo (alimenta o modelo)
  prever     preve o placar de um confronto usando o historico
  listar     mostra os jogos registrados (todos ou de um time)

Exemplos:
  python3 cli.py adicionar --data 2026-07-05 --time-a "Espanha" --gols-a 2 --gols-b 1 --time-b "Portugal"
  python3 cli.py prever --time-a "Argentina" --time-b "Mexico"
  python3 cli.py prever --time-a "Argentina" --time-b "Mexico" --simular
  python3 cli.py listar --time "Austria"
"""

import argparse
import os
import sys
from datetime import date

import formula

CAMINHO_PADRAO_DO_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "dados", "jogos.csv")


def comando_adicionar(argumentos):
    formula.adicionar_jogo(
        caminho_do_csv=argumentos.arquivo,
        data_do_jogo=argumentos.data,
        time_a=argumentos.time_a,
        gols_a=argumentos.gols_a,
        gols_b=argumentos.gols_b,
        time_b=argumentos.time_b,
    )
    print(f"Registrado: {argumentos.data}  "
          f"{argumentos.time_a} {argumentos.gols_a} x "
          f"{argumentos.gols_b} {argumentos.time_b}")


def comando_prever(argumentos):
    if not os.path.exists(argumentos.arquivo):
        print(f"Arquivo de dados nao encontrado: {argumentos.arquivo}")
        print("Adicione jogos primeiro com o comando 'adicionar'.")
        sys.exit(1)

    jogos = formula.carregar_jogos(argumentos.arquivo)
    data_de_referencia = argumentos.data

    resultado = formula.prever_placar(argumentos.time_a, argumentos.time_b,
                                      jogos, data_de_referencia)
    if resultado is None:
        print("Um dos times nao tem nenhum jogo no historico. "
              "Sem dados, sem previsao (cold start).")
        sys.exit(1)

    # aviso de amostra pequena: estatistica no stdout
    if resultado["jogos_a"] < 2 or resultado["jogos_b"] < 2:
        print("AVISO: amostra menor que 2 jogos para um dos times. "
              "Previsao de baixa confianca.\n")

    print(f"Media da amostra (M): {resultado['media_M']:.3f} gols/time/jogo")
    print(f"{argumentos.time_a}: ataque {resultado['ataque_a']:.2f} | "
          f"fraqueza defensiva {resultado['defesa_a']:.2f} | "
          f"{resultado['jogos_a']} jogos")
    print(f"{argumentos.time_b}: ataque {resultado['ataque_b']:.2f} | "
          f"fraqueza defensiva {resultado['defesa_b']:.2f} | "
          f"{resultado['jogos_b']} jogos")
    print()

    gols_a = resultado["gols_esperados_a"]
    gols_b = resultado["gols_esperados_b"]
    print(f"Gols esperados (cru): {argumentos.time_a} {gols_a:.2f} x "
          f"{gols_b:.2f} {argumentos.time_b}")
    print(f"Palpite seco (arredondado): {argumentos.time_a} {round(gols_a)} x "
          f"{round(gols_b)} {argumentos.time_b}")

    if argumentos.simular:
        print()
        print(f"Simulacao Monte Carlo com sorte "
              f"({argumentos.simulacoes} rodadas):")
        simulacao = formula.simular_placar(gols_a, gols_b,
                                           argumentos.simulacoes)
        print(f"  Vitoria {argumentos.time_a}: "
              f"{simulacao['probabilidade_vitoria_a']*100:.1f}%")
        print(f"  Empate: {simulacao['probabilidade_empate']*100:.1f}%")
        print(f"  Vitoria {argumentos.time_b}: "
              f"{simulacao['probabilidade_vitoria_b']*100:.1f}%")
        print("  Placares mais provaveis:")
        for placar, contagem in simulacao["placares_mais_comuns"]:
            frequencia = contagem / argumentos.simulacoes * 100
            print(f"    {placar[0]} x {placar[1]}  ({frequencia:.1f}%)")


def comando_listar(argumentos):
    if not os.path.exists(argumentos.arquivo):
        print(f"Arquivo de dados nao encontrado: {argumentos.arquivo}")
        sys.exit(1)
    jogos = formula.carregar_jogos(argumentos.arquivo)
    contador = 0
    for jogo in jogos:
        data_do_jogo, time_a, gols_a, gols_b, time_b = jogo
        if argumentos.time is not None:
            if argumentos.time != time_a and argumentos.time != time_b:
                continue
        print(f"{data_do_jogo}  {time_a} {gols_a} x {gols_b} {time_b}")
        contador = contador + 1
    print(f"\nTotal: {contador} jogo(s)")


def montar_parser():
    parser = argparse.ArgumentParser(
        prog="placar",
        description="Previsor de placares baseado em ataque/defesa "
                    "normalizados (validado por backtest).")
    parser.add_argument("--arquivo", default=CAMINHO_PADRAO_DO_CSV,
                        help="caminho do CSV de jogos "
                             "(padrao: dados/jogos.csv)")

    subcomandos = parser.add_subparsers(dest="comando", required=True)

    # adicionar
    p_adicionar = subcomandos.add_parser(
        "adicionar", help="registra o placar de um jogo")
    p_adicionar.add_argument("--data", default=str(date.today()),
                             help="data do jogo AAAA-MM-DD (padrao: hoje)")
    p_adicionar.add_argument("--time-a", required=True)
    p_adicionar.add_argument("--gols-a", required=True, type=int)
    p_adicionar.add_argument("--gols-b", required=True, type=int)
    p_adicionar.add_argument("--time-b", required=True)
    p_adicionar.set_defaults(funcao=comando_adicionar)

    # prever
    p_prever = subcomandos.add_parser(
        "prever", help="preve o placar de um confronto")
    p_prever.add_argument("--time-a", required=True)
    p_prever.add_argument("--time-b", required=True)
    p_prever.add_argument("--data", default=str(date.today()),
                          help="data de referencia AAAA-MM-DD (padrao: hoje)")
    p_prever.add_argument("--simular", action="store_true",
                          help="roda Monte Carlo com a variavel sorte")
    p_prever.add_argument("--simulacoes", type=int, default=10000,
                          help="numero de rodadas do Monte Carlo")
    p_prever.set_defaults(funcao=comando_prever)

    # listar
    p_listar = subcomandos.add_parser(
        "listar", help="lista os jogos registrados")
    p_listar.add_argument("--time", default=None,
                          help="filtra por um time especifico")
    p_listar.set_defaults(funcao=comando_listar)

    return parser


def main():
    parser = montar_parser()
    argumentos = parser.parse_args()
    argumentos.funcao(argumentos)


if __name__ == "__main__":
    main()
