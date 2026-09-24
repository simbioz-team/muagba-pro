"""Разбиение команды оболочки на простые команды.

Общий для хуков: раньше одна и та же функция жила в четырёх файлах, и дыра в
ней была дырой четырежды.

Режем не только по `;`, `&&`, `||`, `|`, но и по скобкам группировки и
подстановки, и снимаем ключевые слова в начале. Без этого команда внутри
`if … then cp … fi`, цикла, `{ … }`, `( … )`, `$( … )` или ветки `case`
начиналась словом `then`, `do`, `{` — и разбор не узнавал в ней `cp`.
Защищённый `.env` так и записали: `if [ ! -f .env ]; then cp .env.example
.env; fi` проходил, а та же команда через `||` блокировалась. Нашёл проект
narta на Э5.
"""
from __future__ import annotations

import re
import shlex

# Разделители простых команд. `(`/`)` покрывают подоболочку, `$( … )` и
# шаблон ветки `case`; `;;` закрывает ветку `case`.
SEPARATORS = {";", ";;", "&&", "||", "|", "|&", "&", "(", ")", "{", "}"}
SEP_CHARS = set(";|&()\n")

# Слова, которые стоят перед командой, но командой не являются.
LEADING = {"if", "then", "else", "elif", "do", "while", "until", "!", "time"}

# Слова, которые закрывают конструкцию и сами по себе ничего не делают.
CLOSING = {"fi", "done", "esac"}


HEREDOC = re.compile(r"""<<(?!<)-?[ \t]*(['"]?)([A-Za-z_][\w-]*)\1""")


def _unquoted(line: str, pos: int) -> bool:
    """Стоит ли позиция вне кавычек. Грубо, но без этого `echo "<<X"`
    объявлял бы heredoc и проглатывал следующие строки — вместе с командами."""
    single = double = False
    i = 0
    while i < pos:
        ch = line[i]
        if ch == "\\" and not single:
            i += 2
            continue
        if ch == "'" and not double:
            single = not single
        elif ch == '"' and not single:
            double = not double
        i += 1
    return not single and not double


def _cut_heredocs(command: str) -> tuple[str, dict[str, str]]:
    """Тела heredoc'ов — отдельно от команды.

    Тело — не команды оболочки, а данные: код Python, текст файла. Разобранное
    вместе с командой, оно резалось по скобкам своего же кода, и запись из
    `python3 - <<PY` терялась. Метка заменяется заглушкой, заглушка потом —
    телом целиком, одним токеном той простой команды, которой тело досталось.
    """
    lines = command.split("\n")
    out: list[str] = []
    bodies: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        pending = []
        pieces, last = [], 0
        for m in HEREDOC.finditer(line):
            if not _unquoted(line, m.start()):
                continue
            key = f"__MUAGBA_HEREDOC_{len(bodies) + len(pending)}__"
            pieces.append(line[last:m.start()] + " " + key + " ")
            last = m.end()
            pending.append((key, m.group(2), m.group(0).startswith("<<-")))
        pieces.append(line[last:])
        out.append("".join(pieces))
        i += 1
        for key, delim, strip_tabs in pending:
            body = []
            while i < len(lines):
                cand = lines[i].lstrip("\t") if strip_tabs else lines[i]
                i += 1
                if cand == delim:
                    break
                body.append(lines[i - 1])
            bodies[key] = "\n".join(body)
    return "\n".join(out), bodies


def segments(command: str) -> list[list[str]]:
    """Команда разбивается на простые; каждая — список токенов."""
    text, bodies = _cut_heredocs(command)
    try:
        # Перевод строки — такой же разделитель, как `;`. Без этого вторая
        # строка многострочной команды считалась аргументами первой, и
        # `echo hi` + `rm -rf /` проходили как безобидный echo.
        lexer = shlex.shlex(text, posix=True, punctuation_chars="();<>|&\n")
        lexer.whitespace = " \t\r"
        lexer.whitespace_split = True
        tokens = [bodies.get(t, t) for t in lexer]
    except ValueError:
        return []
    out: list[list[str]] = []
    cur: list[str] = []
    for t in tokens:
        # shlex склеивает соседние знаки: `;` и перевод строки дают токен
        # `;\n`, `)` и `;` — `);`. Разделитель — любой такой токен без `<`/`>`
        # (с ними это перенаправление).
        if t in SEPARATORS or (t and set(t) <= SEP_CHARS):
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        out.append(cur)

    result = []
    for seg in out:
        while seg and seg[0] in LEADING:
            seg = seg[1:]
        if not seg or seg[0] in CLOSING:
            continue
        # `for x in a b` и `case x in` — заголовки, не команды.
        if seg[0] in ("for", "case", "select"):
            continue
        result.append(seg)
    return result
