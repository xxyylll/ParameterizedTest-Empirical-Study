#!/usr/bin/env python3
"""为每个抽样条目抽出评分者需要看的代码。

评分者只判 usage intent，不判 dependency，所以**不给**分析器算出的调用链和等级 ——
那会把答案透露出去。只给：

  1. 测试方法本身（含其上的注解块）
  2. MethodSource：provider 方法的源码（同文件，或注解里 `#` 指定的类）
  3. EnumSource：枚举类型的声明（含常量与构造参数 —— 判 label / data-carrying 必须看到）
  4. ValueSource / CsvSource：注解里的字面量已在测试方法里，无需额外抽取

纯文本花括号配对，不依赖 JDT：只需要切出人读的片段，不需要语义正确。
"""
import os
import re

MAX_LINES = 160          # 单个片段上限，防止把几百行的类整个倒给评分者


def _read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def _code_mask(src):
    """标出哪些字符是真代码（不在字符串/字符常量/注释里）。

    反向扫描注解时必须有这个 —— `@ValueSource(strings = {"a)b"})` 里的 `)` 在字符串里，
    不排除掉的话括号配对会错位，整块注解就被吃掉。
    """
    m = bytearray(b'\x01') * len(src)
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''
        if c == '/' and nxt == '/':
            while i < n and src[i] != '\n':
                m[i] = 0; i += 1
        elif c == '/' and nxt == '*':
            m[i] = m[i + 1] = 0; i += 2
            while i < n and not (src[i] == '*' and i + 1 < n and src[i + 1] == '/'):
                m[i] = 0; i += 1
            if i < n:
                m[i] = 0
                if i + 1 < n:
                    m[i + 1] = 0
                i += 2
        elif c in '"\'':
            q = c
            triple = src[i:i + 3] == '"""'
            m[i] = 0; i += 1
            if triple:
                m[i] = m[i + 1] = 0; i += 2
                while i < n and src[i:i + 3] != '"""':
                    m[i] = 0; i += 1
                for _ in range(min(3, n - i)):
                    m[i] = 0; i += 1
            else:
                while i < n and src[i] != q:
                    if src[i] == '\\':
                        m[i] = 0; i += 1
                    if i < n:
                        m[i] = 0; i += 1
                if i < n:
                    m[i] = 0; i += 1
        else:
            i += 1
    return m


def _block(src, start):
    """从 start（方法签名处）起按花括号配对截到方法结束。"""
    mask = _code_mask(src)
    i = start
    while i < len(src) and not (src[i] == '{' and mask[i]):
        if src[i] == ';' and mask[i]:
            return src[start:i + 1]                     # 抽象方法
        i += 1
    if i >= len(src):
        return None
    depth = 0
    for k in range(i, len(src)):
        if not mask[k]:
            continue
        if src[k] == '{':
            depth += 1
        elif src[k] == '}':
            depth -= 1
            if depth == 0:
                return src[start:k + 1]
    return None


def _with_annotations(src, sig_start, mask=None):
    """把签名上方连续的注解（含多行、含数组字面量的）整块带上。"""
    if mask is None:
        mask = _code_mask(src)
    i = sig_start
    while True:
        j = i - 1
        while j >= 0 and (src[j] in ' \t\n\r' or not mask[j]):
            j -= 1                                       # 跳过空白与注释
        if j < 0:
            break
        if src[j] == ')' and mask[j]:                    # @Foo(...) 形式
            depth, k = 0, j
            while k >= 0:
                if mask[k]:
                    if src[k] == ')':
                        depth += 1
                    elif src[k] == '(':
                        depth -= 1
                        if depth == 0:
                            break
                k -= 1
            if k < 0:
                break
            m = k - 1
            while m >= 0 and (src[m].isalnum() or src[m] in '_.$'):
                m -= 1
            if m >= 0 and src[m] == '@':
                i = m
                continue
            break
        if src[j].isalnum() or src[j] in '_$':           # @Test 这类无参注解
            m = j
            while m >= 0 and (src[m].isalnum() or src[m] in '_.$'):
                m -= 1
            if m >= 0 and src[m] == '@':
                i = m
                continue
            break
        break
    out = src[i:sig_start].rstrip()
    # 去掉行首多余缩进之外的空行
    return '\n'.join(ln for ln in out.split('\n') if ln.strip())


def _is_declaration(src, mask, paren_open):
    """参数表之后跟 `{` 或 `throws` 才是方法声明。

    光靠正则分不开声明和调用：一行裸调用 `foo(a, b);` 的缩进会被当成返回类型，
    `obj.foo(a);` 的接收者会被当成修饰符。调用语句后面必然是 `;` 或 `.`，
    而声明后面必然是方法体或 throws 子句 —— 用这个判据一刀切开。
    """
    depth, k = 0, paren_open
    while k < len(src):
        if mask[k]:
            if src[k] == '(':
                depth += 1
            elif src[k] == ')':
                depth -= 1
                if depth == 0:
                    break
        k += 1
    else:
        return False
    k += 1
    while k < len(src) and (src[k] in ' \t\r\n' or not mask[k]):
        k += 1
    if k >= len(src):
        return False
    return src[k] == '{' or src[k:k + 6] == 'throws'


def _decl_pattern(name):
    return re.compile(
        r'(?m)^[ \t]*'
        r'(?:(?:public|private|protected|static|final|abstract|synchronized|default|native|strictfp)[ \t]+)*'
        r'(?:<[^>\n]{0,160}>[ \t]*)?'
        r'[\w.$]+(?:[ \t]*<[^;{}\n]{0,200}>)?(?:[ \t]*\[[ \t]*\])*'   # 返回类型
        r'[ \t]+'                                                        # 类型与名字之间必须有空白
        + re.escape(name) + r'[ \t]*\(')


def method(path, name):
    """抽出名为 name 的方法声明（含注解）。找不到返回 None。"""
    src = _read(path)
    mask = _code_mask(src)
    for m in _decl_pattern(name).finditer(src):
        start = m.start()
        if not mask[start:m.end()].count(1):
            continue
        paren = src.index('(', m.end() - 1)
        if not _is_declaration(src, mask, paren):
            continue                                   # 是调用不是声明
        body = _block(src, start)
        if body is None:
            continue
        ann = _with_annotations(src, start, mask)
        out = (ann + '\n' if ann else '') + body
        lines = out.split('\n')
        if len(lines) > MAX_LINES:
            out = '\n'.join(lines[:MAX_LINES]) + f'\n    // … 省略 {len(lines)-MAX_LINES} 行'
        return out
    return None


def annotation_of(path, test_name):
    """取出测试方法上方的注解块，用来读 @MethodSource / @EnumSource 的参数。"""
    src = _read(path)
    m = re.search(r'(?m)^[ \t]*(?:(?:public|private|protected|static|final)\s+)*'
                  r'(?:<[^>]{0,120}>\s*)?[\w.$<>\[\],?\s]{1,160}?\b' + re.escape(test_name) + r'\s*\(', src)
    return _with_annotations(src, m.start()) if m else ''


def provider_names(ann):
    """从 @MethodSource(...) 里解析 provider 方法名。"""
    out = []
    for m in re.finditer(r'@MethodSource\s*\(([^)]*)\)', ann, re.S):
        for lit in re.findall(r'"([^"]+)"', m.group(1)):
            out.append(lit)
    return out


def enum_types(ann):
    """从 @EnumSource(...) 里解析枚举类型名。"""
    out = []
    for m in re.finditer(r'@EnumSource\s*\(([^)]*)\)', ann, re.S):
        body = m.group(1)
        for t in re.findall(r'(?:value\s*=\s*)?([A-Za-z_$][\w.$]*)\s*\.class', body):
            out.append(t.split('.')[-1])
    return out


def param_types(path, meth):
    """取测试方法签名里的参数类型。

    `@EnumSource` 不写类型时，枚举类型由参数声明推断 —— 而判 label / data-carrying
    必须看到枚举声明，所以这里得把类型名找回来。
    """
    src = _read(path)
    m = re.search(r'(?m)^[ \t]*(?:(?:public|private|protected|static|final)\s+)*'
                  r'(?:<[^>]{0,120}>\s*)?[\w.$<>\[\],?\s]{1,160}?\b' + re.escape(meth) + r'\s*\(', src)
    if not m:
        return []
    i = src.find('(', m.start())
    depth, k = 0, i
    while k < len(src):
        if src[k] == '(':
            depth += 1
        elif src[k] == ')':
            depth -= 1
            if depth == 0:
                break
        k += 1
    out = []
    for part in src[i + 1:k].split(','):
        part = re.sub(r'@\w+(\([^)]*\))?', '', part).strip()
        toks = part.split()
        if len(toks) >= 2:
            t = toks[-2].split('<')[0].replace('[]', '').split('.')[-1]
            if t and t[0].isupper():
                out.append(t)
    return out


_FILE_INDEX = {}


def _file_index(root):
    """项目内 文件名 → 路径列表。只 walk 一次，后续查找免费。"""
    if root not in _FILE_INDEX:
        idx = {}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in ('.git', 'target', 'build', 'node_modules')]
            for fn in filenames:
                if fn.endswith('.java'):
                    idx.setdefault(fn, []).append(os.path.join(dirpath, fn))
        _FILE_INDEX[root] = idx
    return _FILE_INDEX[root]


def find_type(root, simple_name, decl_kw=None):
    """在项目里找类型声明文件。

    先按 `<Name>.java` 找；找不到再按声明关键字（enum/class/interface）grep ——
    嵌套枚举（ScannerBase.ConsistencyLevel 这种）没有同名文件，只能靠后者。
    """
    idx = _file_index(root)
    hits = idx.get(simple_name + '.java', [])[:3]
    if hits or not decl_kw:
        return hits
    pat = re.compile(r'\b(?:' + decl_kw + r')\s+' + re.escape(simple_name) + r'\b')
    fallback = []
    for fn, paths in idx.items():                      # 嵌套类型没有同名文件，只能扫内容
        for fp in paths:
            try:
                if pat.search(_read(fp)):
                    fallback.append(fp)
                    if len(fallback) >= 4:
                        return fallback
            except OSError:
                pass
    return fallback


def find_method_file(root, meth):
    """provider 不在测试文件里时（继承自父类等），在项目内找声明该方法的文件。"""
    pat = re.compile(r'\b' + re.escape(meth) + r'\s*\(')
    out = []
    for fn, paths in _file_index(root).items():
        for fp in paths:
            try:
                if pat.search(_read(fp)):
                    out.append(fp)
                    if len(out) >= 4:
                        return out
            except OSError:
                pass
    return out


def enum_decl(path, name):
    """抽出 enum 声明体。"""
    src = _read(path)
    m = re.search(r'(?m)^[ \t]*(?:(?:public|private|protected|static|final)\s+)*enum\s+'
                  + re.escape(name) + r'\b', src)
    if not m:
        return None
    body = _block(src, m.start())
    if body is None:
        return None
    lines = body.split('\n')
    if len(lines) > MAX_LINES:
        body = '\n'.join(lines[:MAX_LINES]) + f'\n    // … 省略 {len(lines)-MAX_LINES} 行'
    return body


# ---- 测试体调用到的同文件 helper ----------------------------------------
# codebook 更新：semantic-specific / different-equivalence 的判定要看「test 侧是否存在
# 依参数而变的分支」，而这种分支常常不在测试体里而在它调用的 helper 里。
# 所以必须把 helper 一并给评分者，否则他们看不到判定依据。

_KW = {'if', 'for', 'while', 'switch', 'catch', 'return', 'new', 'synchronized',
       'try', 'do', 'else', 'throw', 'super', 'this', 'assert', 'case', 'instanceof'}
MAX_HELPERS = 6
HELPER_MAX_LINES = 70


def _declared_methods(src, mask=None):
    """同文件内声明的方法名 → 签名起始位置。"""
    if mask is None:
        mask = _code_mask(src)
    out = {}
    for m in re.finditer(r'(?m)^[ \t]*'
                         r'(?:(?:public|private|protected|static|final|abstract|synchronized|'
                         r'default|native|strictfp)[ \t]+)*'
                         r'(?:<[^>\n]{0,160}>[ \t]*)?'
                         r'[\w.$]+(?:[ \t]*<[^;{}\n]{0,200}>)?(?:[ \t]*\[[ \t]*\])*'
                         r'[ \t]+(\w+)[ \t]*\(', src):
        if mask[m.start(1)] and _is_declaration(src, mask, src.index('(', m.end() - 1)):
            out.setdefault(m.group(1), m.start())
    return out


def _calls(body, mask_body):
    names = []
    for m in re.finditer(r'\b([a-z_$]\w*)\s*\(', body):
        if mask_body[m.start(1)] and m.group(1) not in _KW:
            names.append(m.group(1))
    return names


def helpers(path, test_name, depth=2):
    """抽出测试方法（递归）调用到的、声明在同一文件里的 helper。

    只取同文件：跨文件的 helper 需要解析导入与继承，成本高且容易给错；
    同文件已经覆盖绝大多数「分支藏在 helper 里」的情况。
    """
    src = _read(path)
    mask = _code_mask(src)
    decl = _declared_methods(src, mask)
    seen, out, frontier = {test_name}, [], [test_name]
    for _ in range(depth):
        nxt = []
        for nm in frontier:
            start = decl.get(nm)
            if start is None:
                continue
            body = _block(src, start)
            if not body:
                continue
            off = src.index(body, start) if body in src else start
            bmask = mask[off:off + len(body)]
            for c in _calls(body, bmask):
                if c in decl and c not in seen:
                    seen.add(c)
                    nxt.append(c)
                    code = method(path, c)
                    if code:
                        lines = code.split('\n')
                        if len(lines) > HELPER_MAX_LINES:
                            code = '\n'.join(lines[:HELPER_MAX_LINES]) + \
                                   f'\n    // … 省略 {len(lines)-HELPER_MAX_LINES} 行'
                        out.append((c, code))
                    if len(out) >= MAX_HELPERS:
                        return out
        frontier = nxt
        if not frontier:
            break
    return out
