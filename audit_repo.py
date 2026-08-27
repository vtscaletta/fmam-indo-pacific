"""
Опись состава хранилища. Что живо, что мертво.

Назначение. Перед вычисткой надлежит установить, какие единицы хранения
участвуют в работе, а какие остались от прежних заходов. Опись строится
разбором связей ввоза между единицами, а не чтением содержимого, вследствие
чего пригодна и для единиц, содержание которых неизвестно.

Что делает. Обходит все единицы с расширением py, разбирает их
синтаксическое дерево, извлекает связи ввоза и строит достижимость от двух
точек входа, а именно от `run_model.py` и от `app.py`. Единица признаётся
живой, если достижима хотя бы от одной точки входа, и мёртвой в противном
случае. Испытания рассматриваются отдельно, поскольку от точек входа
недостижимы по устройству, но живыми являются.

Чего не делает. Ничего не удаляет, не переименовывает и не изменяет.
Печатает опись и завершается.

Запуск из корня хранилища.

    python audit_repo.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ENTRY_POINTS = ("run_model.py", "app.py", "build_coding.py")
TEST_DIRS = ("tests",)
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", ".streamlit", "node_modules"}


def module_name(path: Path, root: Path) -> str:
    """Имя ввоза, отвечающее расположению единицы."""
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def collect_imports(path: Path) -> set[str]:
    """Имена, ввозимые единицей. При неразбираемом содержимом пусто."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return set()
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                out.add(node.module)
    return out


def main() -> None:
    root = Path(".").resolve()
    files = [p for p in root.rglob("*.py")
             if not any(d in SKIP_DIRS for d in p.parts)]

    by_module: dict[str, Path] = {}
    for p in files:
        by_module[module_name(p, root)] = p

    imports: dict[str, set[str]] = {}
    for mod, p in by_module.items():
        raw = collect_imports(p)
        own = set()
        for name in raw:
            if name in by_module:
                own.add(name)
                continue
            for cand in by_module:
                if name.startswith(cand + ".") or cand.startswith(name + "."):
                    own.add(cand)
        imports[mod] = own

    reachable: set[str] = set()
    queue = []
    for e in ENTRY_POINTS:
        m = module_name(root / e, root)
        if m in by_module:
            queue.append(m)
    while queue:
        cur = queue.pop()
        if cur in reachable:
            continue
        reachable.add(cur)
        queue.extend(imports.get(cur, set()))

    tests, live, dead = [], [], []
    for mod, p in sorted(by_module.items()):
        rel = p.relative_to(root)
        if any(str(rel).startswith(d) for d in TEST_DIRS):
            tests.append((mod, rel))
        elif mod in reachable:
            live.append((mod, rel))
        else:
            dead.append((mod, rel))

    print("ОПИСЬ СОСТАВА ХРАНИЛИЩА")
    print()
    print(f"  корень {root}")
    print(f"  точек входа {sum(1 for e in ENTRY_POINTS if (root / e).exists())}"
          f" из {len(ENTRY_POINTS)}, а именно "
          f"{', '.join(e for e in ENTRY_POINTS if (root / e).exists())}")
    print(f"  единиц всего {len(by_module)}")
    print()

    print(f"ЖИВЫЕ, достижимы от точек входа, {len(live)}")
    for mod, rel in live:
        n = len(imports.get(mod, set()))
        print(f"  {str(rel):45} ввозит своих {n}")
    print()

    print(f"ИСПЫТАНИЯ, {len(tests)}")
    for mod, rel in tests:
        targets = sorted(imports.get(mod, set()))
        broken = [t for t in targets if t not in by_module]
        state = "цел" if not broken else f"ссылается на отсутствующее {broken}"
        print(f"  {str(rel):45} {state}")
    print()

    print(f"МЁРТВЫЕ, от точек входа недостижимы, {len(dead)}")
    if not dead:
        print("  нет")
    for mod, rel in dead:
        users = [m for m, deps in imports.items() if mod in deps]
        if users:
            print(f"  {str(rel):45} ввозится из {', '.join(sorted(users))}")
        else:
            print(f"  {str(rel):45} не ввозится ниоткуда")
    print()

    print("ЧТО С ЭТИМ ДЕЛАТЬ")
    print()
    print("  Единица из мёртвых, не ввозимая ниоткуда, к вычистке пригодна.")
    print("  Единица из мёртвых, ввозимая только испытаниями, требует")
    print("  решения, а именно либо ввести её в работу, либо удалить вместе")
    print("  с испытанием.")
    print("  Испытание, ссылающееся на отсутствующее, сломано и подлежит")
    print("  исправлению прежде вычистки.")


if __name__ == "__main__":
    sys.exit(main())
