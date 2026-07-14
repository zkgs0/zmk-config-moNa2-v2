#!/usr/bin/env python3
"""secrets.txt からシークレットマクロの devicetree 定義を生成する。

使い方:
    リポジトリ直下に secrets.txt (gitignore対象) を置き、
        sec1=my.address@example.com
        sec2=SomeText-123
    の形式で最大8個 (sec1〜sec8) 定義して、このスクリプトを実行する:
        python3 scripts/gen_secrets.py
    boards/shields/mona2/secrets.dtsi (gitignore対象) が生成され、
    ローカルビルド時に本物のフレーズがファームウェアへ焼き込まれる。
    secrets.dtsi が無いビルド (GitHub CI) はダミー実装 (&none) になる。

制約:
    - フレーズはASCII文字のみ (US配列キーコードへ変換して打鍵するため)
    - 行頭 # はコメント。値に = を含む場合は最初の = だけが区切り
    - 各マクロの先頭で英数キー (LANG2) を1回叩き、日本語IMEによる
      ローマ字化けを防ぐ
"""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
SECRETS_TXT = REPO_ROOT / "secrets.txt"
OUT_DTSI = REPO_ROOT / "boards" / "shields" / "mona2" / "secrets.dtsi"
SLOTS = [f"sec{i}" for i in range(1, 9)]

# ASCII文字 → ZMKキーコードの対応表 (US配列)
SHIFTED = {
    "!": "N1", "@": "N2", "#": "N3", "$": "N4", "%": "N5",
    "^": "N6", "&": "N7", "*": "N8", "(": "N9", ")": "N0",
    "_": "MINUS", "+": "EQUAL", "{": "LBKT", "}": "RBKT",
    "|": "BSLH", ":": "SEMI", '"': "SQT", "~": "GRAVE",
    "<": "COMMA", ">": "DOT", "?": "FSLH",
}
PLAIN = {
    "-": "MINUS", "=": "EQUAL", "[": "LBKT", "]": "RBKT",
    "\\": "BSLH", ";": "SEMI", "'": "SQT", "`": "GRAVE",
    ",": "COMMA", ".": "DOT", "/": "FSLH", " ": "SPACE",
}


def char_to_binding(ch: str) -> str:
    """1文字をZMKの &kp バインディングに変換する。"""
    if ch.isascii() and ch.islower():
        return f"&kp {ch.upper()}"
    if ch.isascii() and ch.isupper():
        return f"&kp LS({ch})"
    if ch.isdigit():
        return f"&kp N{ch}"
    if ch in PLAIN:
        return f"&kp {PLAIN[ch]}"
    if ch in SHIFTED:
        return f"&kp LS({SHIFTED[ch]})"
    raise ValueError(f"非対応文字: {ch!r} (ASCII英数記号のみ対応)")


def macro_node(name: str, phrase: str | None) -> str:
    """スロット1個分のマクロノードを生成する。phraseがNoneならダミー(&none)。"""
    if phrase is None:
        bindings = "<&none>"
    else:
        keys = " ".join(char_to_binding(c) for c in phrase)
        bindings = f"<&kp LANG2 {keys}>"  # 先頭で英数モードへ (IME化け防止)
    return f"""        {name}_impl: {name}_impl {{
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            wait-ms = <10>;
            tap-ms = <10>;
            bindings = {bindings};
        }};"""


def main() -> None:
    if not SECRETS_TXT.exists():
        sys.exit(f"secrets.txt が見つかりません: {SECRETS_TXT}\n"
                 "リポジトリ直下に sec1=... 形式で作成してください。")

    phrases: dict[str, str] = {}
    for line in SECRETS_TXT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key not in SLOTS:
            sys.exit(f"不正なキー名: {key} (sec1〜sec8のみ)")
        phrases[key] = value

    nodes = "\n\n".join(macro_node(s, phrases.get(s)) for s in SLOTS)
    OUT_DTSI.write_text(
        "// このファイルは scripts/gen_secrets.py が生成する。手で編集しない。\n"
        "// gitignore対象: リポジトリへコミットしないこと。\n"
        "#include <dt-bindings/zmk/keys.h>\n"  # LS()/LANG2等のキーコードマクロ用
        "/ {\n    macros {\n" + nodes + "\n    };\n};\n",
        encoding="utf-8",
    )
    filled = sorted(phrases.keys())
    print(f"生成OK: {OUT_DTSI}")
    print(f"実フレーズ入りスロット: {', '.join(filled)} (残りはダミー)")


if __name__ == "__main__":
    main()
