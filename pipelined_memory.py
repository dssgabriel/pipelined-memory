import argparse
import re
import sys
from typing import List, Tuple


def uint(val: str) -> int:
    ival = int(val)
    if ival <= 0:
        raise argparse.ArgumentTypeError(f"{val} must be a positive integer")
    return ival


def parse_expressions(expr: str) -> List[Tuple[int, int]]:
    exprs = []
    expr_split = expr.split(",")
    for e in expr_split:
        i_coeff = 0
        p_coeff = 0
        # Regular expression to match coefficients in the expression
        m = re.match(r"(\d*)i(?!\d)(\+(\d*))?", e)
        if m is not None:
            match m.group(1):
                case None:
                    i_coeff = 0
                case "":
                    i_coeff = 1
                case _:
                    i_coeff = int(m.group(1))

            match m.group(2):
                case None | "":
                    p_coeff = 0
                case _:
                    p_coeff = int(m.group(3))
        else:
            m = re.match(r"(\d+)", e)
            if m is not None:
                p_coeff = int(m.group(1))
            else:
                print(f"\x1b[1;31merror:\x1b[0m invalid expression `{e}`")
                exit(1)
        exprs.append((i_coeff, p_coeff))
    return exprs


def parse_base(base: str) -> List[int]:
    return [int(b) for b in base.split(",")]


def main():
    parser = argparse.ArgumentParser(description="Pipelined memory calculator")
    parser.add_argument(
        "-m",
        "--memory-banks",
        dest="nbanks",
        type=uint,
        required=True,
        help="Number of memory banks",
    )
    parser.add_argument(
        "-l",
        "--latency",
        type=uint,
        dest="mem_latency",
        required=True,
        help="Memory access latency",
    )
    parser.add_argument(
        "-i",
        "--iterations",
        type=uint,
        dest="niter",
        required=True,
        help="Number of loop iterations",
    )
    parser.add_argument(
        "-e",
        "--expressions",
        dest="access_expr",
        type=parse_expressions,
        required=True,
        help="Expressions for array accesses (comma separated list of expressions without whitespace)",
    )
    parser.add_argument(
        "-b",
        "--base",
        dest="starting_banks",
        type=parse_base,
        required=True,
        help="Expressions for base memory banks (comma separated list of expressions without whitespace)",
    )

    args = parser.parse_args()
    if len(args.access_expr) != len(args.starting_banks):
        print(
            f"\x1b[1;31merror:\x1b[0m expression and base lists must be the same length"
        )
        exit(1)

    print(f"Number of memory banks:    {args.nbanks}")
    print(f"Memory access latency:     {args.mem_latency}")
    print(f"Number of iterations:      {args.niter}")
    print(f'Memory access expressions: {[f"{e[0]}i+{e[1]}" for e in args.access_expr]}')
    print(f"Starting memory banks:     {args.starting_banks}")

    bank = []
    for i in range(args.nbanks):
        bank.append([])
    patterns = []
    arrays = [chr(ord("A") + i) for i in range(len(args.access_expr))]

    str_i = "    Iter ❯ "
    str_bank = "Bank pos ❯ "

    def aff_bank():
        print("│" + "│".join([f"{i:>5d}" for i in range(len(bank[0]))]) + "│")
        print("┼" + "┼".join([f"─────" for i in range(len(bank[0]))]) + "┼")
        for i in range(len(bank)):
            print("│" + "│".join(bank[i]) + "│")

    it = 0
    for i in range(0, args.niter):
        str_i += (
            "("
            + ",".join(
                [
                    str(args.access_expr[j][0] * i + args.access_expr[j][1])
                    for j in range(3)
                ]
            )
            + ")"
        )
        str_bank += (
            "("
            + ",".join(
                [
                    str(
                        args.access_expr[j][0] * i
                        + args.access_expr[j][1]
                        + args.starting_banks[j]
                    )
                    for j in range(3)
                ]
            )
            + ")"
        )
        str_i += " - "
        str_bank += " - "

        save_it = it
        pattern = []
        for j in range(len(args.access_expr)):
            str_v = f'{arrays[j] + f"[{args.access_expr[j][0] * i + args.access_expr[j][1]:d}]":>5}'
            for k in range(len(bank)):
                while len(bank[k]) <= it + 3:
                    bank[k].append("     ")

            position = (
                args.access_expr[j][0] * i
                + args.access_expr[j][1]
                + args.starting_banks[j]
            ) % len(bank)
            while bank[position][it] != "     ":
                it += 1
                for k in range(len(bank)):
                    bank[k].append("     ")

            for k in range(it, it + 4):
                bank[position][k] = str_v

            it += 1
            pattern.append([position, it - save_it])
        if pattern in patterns:
            str_op = ""
            for k in range(len(args.access_expr)):
                str_op += arrays[k] + "["
                str_op += (
                    str(args.access_expr[k][0]) + "i"
                    if args.access_expr[k][0] != 1
                    else "i"
                )
                str_op += (
                    f"+{args.access_expr[k][1]}]" if args.access_expr[k][1] else "]"
                )

            str_op = "], ".join(str_op.split("]"))
            print(
                "===============",
                str_op[:-2],
                f"== n={args.niter} == init",
                args.starting_banks,
                "===============",
            )

            print(str_i[:-3])
            print(str_bank[:-3])
            print("")
            aff_bank()

            temps_it = save_it - 1
            while (
                bank[patterns[-1][-1][0]][save_it - 1]
                == bank[patterns[-1][-1][0]][temps_it]
            ):
                temps_it += 1

            print(
                f"\nPattern found between iterations {patterns.index(pattern)} and {len(patterns)}"
            )
            print("Startup time:", temps_it)
            rendement_max = save_it - patterns[patterns.index(pattern)][0][1] + 1
            decalage_iterations = patterns.index(pattern)
            nb_iterations = len(patterns) - patterns.index(pattern)
            print("Max efficiency:", rendement_max)
            print("Loop iterations:", nb_iterations)
            latence = (
                f"{int(rendement_max/nb_iterations)}"
                if (rendement_max / nb_iterations) == int(rendement_max / nb_iterations)
                else f"{rendement_max}/{nb_iterations}"
            )
            latence += f"(n-{decalage_iterations})" if decalage_iterations else "n"
            latence += f"+{temps_it-rendement_max}"
            print("Latency:", latence)
            tps_exec = float(rendement_max / nb_iterations) * float(
                args.niter - decalage_iterations
            ) + float(temps_it - rendement_max)
            print(f"Execution time: {tps_exec}T, {tps_exec*args.mem_latency} cycles (w/ T = {args.mem_latency})")
            break
        patterns.append(pattern)


if __name__ == "__main__":
    main()
