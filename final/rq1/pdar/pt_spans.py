#!/usr/bin/env python3
"""一个 Java 文件快照里「属于参数化测试」的行区间（方法级 PDAR 的判定核心）。

### 定义

给定一个 `.java` 文件的完整内容，返回两组闭区间（1-based 行号）：

  - `pt`   —— 每个带 `@ParameterizedTest` 的方法：从它的第一个注解/修饰符到方法体
              右花括号。注解写成全限定名 `@org.junit.jupiter.params.ParameterizedTest`
              也认。方法前的 Javadoc / 注释**不算**（它们不是方法声明的一部分）。
  - `prov` —— `pt` 再加上 PT 的 source 注解**显式引用、且定义在同一文件里**的东西：

      | 注解                         | 引用的东西                              | 缺省时                    |
      |------------------------------|-----------------------------------------|---------------------------|
      | `@MethodSource("m")`         | 同文件里名为 m 的方法（含重载）           | 与测试方法同名的方法        |
      | `@FieldSource("f")`          | 同文件里名为 f 的字段                     | 与测试方法同名的字段        |
      | `@EnumSource(E.class)`       | 同文件里的 enum E                         | 第一个形参的类型            |
      | `@ArgumentsSource(X.class)`  | 同文件里的类 X                            | —                         |

    `"Cls#m"` / `"pkg.Cls#m"` 只有当 Cls 的简单名在本文件里声明过才解析，否则记为
    **跨文件引用**（`xref`），不纳入 —— production 里的 enum、外部 provider 类
    因此被自然排除，不需要单独写例外。只解析一层：provider 自己再调用的方法不追。

### 为什么是「同文件」

它是不需要跨文件符号解析就能**确定性**判定的最大范围，而且恰好与 JUnit 4 的
文件级判定（Layer 2）对齐：JUnit 4 里同一个类中的 `@Parameters` 方法本来就算在内。

### 解析

tree-sitter 是容错解析器，遇到不认识的语法也会给出一棵树（带 ERROR 节点）。
`has_error` 如实返回，由调用方决定如何处理（方法级 PDAR 的做法见
`pdar_v4_method_level.py`：该提交回退到第一阶段的 Layer 1 判定，并计数报告）。
"""

import re
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

import tree_sitter as _ts
import tree_sitter_java as _tsj

_LANG = _ts.Language(_tsj.language())
_PARSER = _ts.Parser(_LANG)

Span = Tuple[int, int]

PT_ANNOTATION = 'ParameterizedTest'
PT_FQN = 'org.junit.jupiter.params.ParameterizedTest'

_TYPE_DECLS = ('class_declaration', 'interface_declaration', 'enum_declaration',
               'record_declaration', 'annotation_type_declaration')


# JUnit 4 参数化类的标注。覆盖 `@RunWith(value = Parameterized.class)` 与全限定名写法；前缀匹配
# （`ParameterizedRobolectricTestRunner` 之类也算，与 v3 一致）。
J4_RE = re.compile(rb'@RunWith\s*\(\s*(?:value\s*=\s*)?(?:[\w$]+\.)*Parameterized')
WHOLE_FILE: Span = (1, 10 ** 9)


class FileSpans(NamedTuple):
    pt: List[Span]
    prov: List[Span]
    has_error: bool
    n_pt_methods: int
    xrefs: int          # 未能在本文件内解析的 source 引用数
    j4: List[Span] = []           # JUnit 4 参数化类的区间（已扣除其中嵌套的独立测试类）
    j4_fallback: bool = False     # 解析出错且文件含 J4 标注 → j4 退回整个文件


EMPTY = FileSpans([], [], False, 0, 0)


def _text(node) -> str:
    return node.text.decode('utf-8', errors='replace')


def _span(node) -> Span:
    return (node.start_point[0] + 1, node.end_point[0] + 1)


def _ann_name(ann) -> str:
    """注解名，原样（可能是全限定名）。"""
    n = ann.child_by_field_name('name')
    return _text(n) if n is not None else ''


def _simple(name: str) -> str:
    return name.rsplit('.', 1)[-1]


def _is_pt_annotation(ann) -> bool:
    name = _ann_name(ann)
    return name == PT_ANNOTATION or name == PT_FQN


def _annotations_of(decl) -> List:
    """一个声明的 modifiers 里的全部注解，含容器注解（如 @ArgumentsSources({...})）内层的。"""
    mods = next((c for c in decl.children if c.type == 'modifiers'), None)
    if mods is None:
        return []
    out = []
    stack = list(mods.children)
    while stack:
        n = stack.pop()
        if n.type in ('annotation', 'marker_annotation'):
            out.append(n)
        stack.extend(n.children)
    return out


def _string_values(node) -> Optional[List[str]]:
    """element value → 字符串列表；不是字符串字面量（或其数组）时返回 None。"""
    if node.type == 'string_literal':
        frag = ''.join(_text(c) for c in node.children if c.type == 'string_fragment')
        return [frag]
    if node.type == 'element_value_array_initializer':
        vals = []
        for c in node.named_children:
            v = _string_values(c)
            if v is None:
                return None
            vals.extend(v)
        return vals
    return None


def _class_values(node) -> Optional[List[str]]:
    """element value → class literal 的简单类名列表。"""
    if node.type == 'class_literal':
        t = node.named_children[0] if node.named_children else None
        return [_simple(_text(t))] if t is not None else []
    if node.type == 'element_value_array_initializer':
        vals = []
        for c in node.named_children:
            v = _class_values(c)
            if v is None:
                return None
            vals.extend(v)
        return vals
    return None


def _ann_args(ann) -> Dict[str, object]:
    """注解参数 → {key: value_node}；位置参数记为 'value'。"""
    args = ann.child_by_field_name('arguments')
    out: Dict[str, object] = {}
    if args is None:
        return out
    for c in args.named_children:
        if c.type == 'element_value_pair':
            k = c.child_by_field_name('key')
            v = c.child_by_field_name('value')
            if k is not None and v is not None:
                out[_text(k)] = v
        elif c.type not in ('comment', 'line_comment', 'block_comment'):
            out['value'] = c
    return out


def _first_param_type(method) -> Optional[str]:
    params = method.child_by_field_name('parameters')
    if params is None:
        return None
    for p in params.named_children:
        if p.type in ('formal_parameter', 'spread_parameter'):
            t = p.child_by_field_name('type')
            if t is None:
                t = next((c for c in p.named_children if 'type' in c.type), None)
            if t is None:
                return None
            if t.type == 'generic_type':
                t = t.named_children[0]
            return _simple(_text(t))
    return None


def _index(root):
    """一次遍历收集：方法（名→节点列表）、字段（名→节点）、类型声明（简单名→节点）、PT 方法。"""
    methods: Dict[str, List] = {}
    fields: Dict[str, List] = {}
    types: Dict[str, List] = {}
    pt_methods = []
    stack = [root]
    while stack:
        n = stack.pop()
        t = n.type
        if t == 'method_declaration':
            name = n.child_by_field_name('name')
            if name is not None:
                methods.setdefault(_text(name), []).append(n)
            if any(_is_pt_annotation(a) for a in _annotations_of(n)):
                pt_methods.append(n)
        elif t == 'field_declaration':
            for d in n.children_by_field_name('declarator'):
                name = d.child_by_field_name('name')
                if name is not None:
                    fields.setdefault(_text(name), []).append(n)
        elif t in _TYPE_DECLS:
            name = n.child_by_field_name('name')
            if name is not None:
                types.setdefault(_text(name), []).append(n)
        stack.extend(n.children)
    return methods, fields, types, pt_methods


def _resolve_member_ref(ref: str, default: str, table: Dict[str, List],
                        types: Dict[str, List]) -> Tuple[List, bool]:
    """MethodSource/FieldSource 的一个引用 → (同文件内的节点, 是否跨文件)。"""
    ref = ref.strip()
    if not ref:
        ref = default
    if '#' in ref:
        cls, member = ref.split('#', 1)
        cls_simple = cls.replace('$', '.').rsplit('.', 1)[-1]
        if cls_simple not in types:
            return [], True
        ref = member
    ref = ref.split('(', 1)[0].strip()      # "m(int, String)" → "m"
    nodes = table.get(ref, [])
    return nodes, not nodes


def _is_separate_test_class(node) -> bool:
    """嵌套类型是否是一个独立的测试类：自己带 @RunWith / @Nested，或直接含 @Test 方法。"""
    for a in _annotations_of(node):
        if _simple(_ann_name(a)) in ('RunWith', 'Nested'):
            return True
    body = node.child_by_field_name('body')
    if body is None:
        return False
    for m in body.named_children:
        if m.type == 'method_declaration' and \
                any(_simple(_ann_name(a)) == 'Test' for a in _annotations_of(m)):
            return True
    return False


def _subtract(span: Span, holes: List[Span]) -> List[Span]:
    out, cur = [], span[0]
    for a, b in sorted(holes):
        if a > cur:
            out.append((cur, a - 1))
        cur = max(cur, b + 1)
    if cur <= span[1]:
        out.append((cur, span[1]))
    return out


def _j4_regions(types: Dict[str, List]) -> List[Span]:
    """被 @RunWith(...Parameterized...) 标注的类，从注解到右花括号；扣除其中嵌套的独立测试类。

    不含 @Test 的嵌套辅助类型（参数 enum、数据持有类等）保留 —— JUnit 4 参数化的单位是整个类，
    类里的一切（除另一个测试类外）都属于它。嵌套在 Enclosed 等外层里的参数化类只算它自己。
    """
    regions: List[Span] = []
    for nodes in types.values():
        for c in nodes:
            if c.type != 'class_declaration':
                continue
            if not any(_simple(_ann_name(a)) == 'RunWith' and J4_RE.search(a.text)
                       for a in _annotations_of(c)):
                continue
            holes: List[Span] = []
            body = c.child_by_field_name('body')
            stack = list(body.named_children) if body is not None else []
            while stack:
                n = stack.pop()
                if n.type in _TYPE_DECLS:
                    if _is_separate_test_class(n):
                        holes.append(_span(n))
                        continue
                    b = n.child_by_field_name('body')
                    if b is not None:
                        stack.extend(b.named_children)
                elif n.type == 'enum_body_declarations':
                    stack.extend(n.named_children)
            regions.extend(_subtract(_span(c), holes))
    return sorted(regions)


def compute_spans(source: bytes) -> FileSpans:
    if b'Parameterized' not in source:          # 同时覆盖 ParameterizedTest 与 JUnit 4 的 Parameterized
        return EMPTY
    tree = _PARSER.parse(source)
    root = tree.root_node
    methods, fields, types, pt_methods = _index(root)

    pt: List[Span] = []
    prov: Set[Span] = set()
    xrefs = 0
    for m in pt_methods:
        s = _span(m)
        pt.append(s)
        prov.add(s)
        name_node = m.child_by_field_name('name')
        mname = _text(name_node) if name_node is not None else ''
        for ann in _annotations_of(m):
            kind = _simple(_ann_name(ann))
            args = _ann_args(ann)
            if kind in ('MethodSource', 'FieldSource'):
                table = methods if kind == 'MethodSource' else fields
                v = args.get('value')
                refs = _string_values(v) if v is not None else []
                if refs is None:            # 非字面量（常量表达式等）—— 解析不了
                    xrefs += 1
                    continue
                if not refs:
                    refs = ['']             # 缺省 = 与测试方法同名
                for r in refs:
                    nodes, ext = _resolve_member_ref(r, mname, table, types)
                    xrefs += ext
                    prov.update(_span(n) for n in nodes)
            elif kind in ('EnumSource', 'ArgumentsSource'):
                v = args.get('value')
                if v is None:
                    if kind == 'ArgumentsSource':
                        continue
                    t = _first_param_type(m)
                    names = [t] if t else []
                else:
                    names = _class_values(v) or []
                for nm in names:
                    nodes = types.get(nm, [])
                    if kind == 'EnumSource':
                        nodes = [n for n in nodes if n.type == 'enum_declaration']
                    if nodes:
                        prov.update(_span(n) for n in nodes)
                    else:
                        xrefs += 1
    j4: List[Span] = []
    j4_fallback = False
    if J4_RE.search(source):
        if root.has_error:
            j4, j4_fallback = [WHOLE_FILE], True
        else:
            j4 = _j4_regions(types)
    return FileSpans(sorted(pt), sorted(prov), root.has_error, len(pt_methods), xrefs, j4, j4_fallback)


def lines_hit(lines, spans: List[Span]) -> bool:
    """任一行号落在任一闭区间内。spans 很少（每文件几十个），线性扫即可。"""
    if not spans or not lines:
        return False
    for ln in lines:
        for a, b in spans:
            if a <= ln <= b:
                return True
    return False
