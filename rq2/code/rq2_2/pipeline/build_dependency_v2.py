#!/usr/bin/env python3
"""
Dependency v2 —— 改成"追到生产代码/第三方 API 边界为止，取全链路里走得最远的一步"，
不再是只看 provider 直接写的那几个调用。

复用 Helper Depth 那条线（build_helper_depth.py）已经从 AAA 的 parsedStatementsSequence
池化好的调用集合——test-scope 的调用会被 AAA 自己的工具一路递归展开直到碰到生产代码/
第三方 API 为止，这正好就是我们要的"追踪边界"，不需要另外再写一套追踪逻辑。

方法学:
  1. provider 自己的"位置"相对测试类:
       - METHODSOURCE 行的声明类 == 测试类自己 -> 基线，不额外加等级
       - 声明类不同，且 @MethodSource 是裸名形式（没写 "Class#method"）
         -> 说明是沿着 extends 链找到的 -> L2 Inheritance
       - 声明类不同，且 @MethodSource 显式写了 "Class#method"
         -> 按这个类跟测试类的位置关系分类（同类不可能出现在这个分支/同包 L3/跨包 L4）
  2. provider 池化后的调用链路里，每一条 TEST-scope 的调用，声明类跟"provider 自己所在的类"
     （不是测试类，是 provider 真正声明的那个类，见上面第 1 步）比较:
       - 同一个类 -> L1 Class Helper
       - 不同类，同包 -> L3 Package Helper
       - 不同类，不同包 -> L4 Cross-Package
     取全部命中里的最大值。（不单独判"某个 helper 是不是也是靠继承链找到的" —— 这个信号
     AAA 的 tag 里没有直接暴露，做不到就不猜，只在 provider 自己的位置这一步判 L2。）
  3. 池化后的调用链路里只要出现任何 production-scope（tag 是裸的/GET/SET）的调用，
     就标 hits_production=True——这对应你表里 EnumSource 那行"+ Production Dependency"
     的概念，是独立于 L0-L4 的一个标记，不是等级本身的一部分。
  4. 全程没有任何 test-scope / production-scope 调用、provider 也在本类 -> L0 Method Local。

已知简化: 一个测试有多个 @MethodSource provider 时，池化调用链路时没法百分百区分
"这条调用是从哪个 provider 的子树来的"（跟 helper depth 那条线一样的限制），统一用
第一个 provider 的声明类当基准；这种情况在 note 里标了 multi_provider，人工核对时留意。
"""

# 向上找到 仓库根（paths.py 所在处）—— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_helper_depth import (
    AAA_ROOT, load_pilot_sample, build_aaa_index, find_json_file,
    extract_provider_subtrees, classify_line, declaring_class_of, load_file_index,
    resolve_scope_via_path, kept_indices_after_dropping_data_method_refs, LAST_MATCH_NOTE,
    TEST_TAGS, PROD_TAGS, UNRESOLVED_TAGS, EXCLUDED_TAGS, FALLBACK_TAGS, ENTRY_TAG, NEUTRAL_TAGS,
    RECURSIVE_TAGS, UNKNOWN_TAG_MARKER,
)

OUT_DIR = os.environ.get("RQ22_OUT_DIR", _paths.RQ22_WORK)
METHODSOURCE_LINE_RE = re.compile(r"^(?:METHODSOURCE|FIELDSOURCE)\s+(.+)\.([A-Za-z_$][A-Za-z0-9_$]*)(?:\(\))?#\[(\d+)-(\d+)\]$")

LEVEL_NAME = {0: "L0", 1: "L1", 2: "L2", 3: "L3", 4: "L4"}

# 源码侧（ArtifactWalker，经 ConstructionDependencyClassifier 输出）的 dependency，按 (project, test_class, test_name) 取
_SRC_CSV = os.path.join(OUT_DIR, "construction_dependency_raw.csv")
SRC_DEP = {}
if os.path.exists(_SRC_CSV):
    for _r in csv.DictReader(open(_SRC_CSV, encoding="utf-8")):
        SRC_DEP[(_r["project"], _r["test_class"], _r["test_name"])] = _r


def package_of(qualified_class):
    """取包名——从左往右，只要还是全小写就算包，遇到第一个大写开头的段就是类名的开始。"""
    if not qualified_class:
        return None
    pkg_parts = []
    for part in qualified_class.split("."):
        if part[:1].isupper():
            break
        pkg_parts.append(part)
    return ".".join(pkg_parts)


def outermost_class(fqcn):
    parts = fqcn.split(".")
    i = next((k for k, seg in enumerate(parts) if seg[:1].isupper()), len(parts) - 1)
    return ".".join(parts[: i + 1])


# ---- 继承链（语法解析，≤8 层）：helper 声明在测试类的祖先（父类链 / 实现的接口）里 → L2 Inheritance ----
_ANCESTOR_CACHE = {}
_TYPE_DECL_RE = re.compile(
    r"\b(?:class|interface|enum|record)\s+(\w+)(?:\s*<[^{]*?>)?\s*(?:\([^)]*\))?\s*"
    r"(?:extends\s+([^{]+?))?\s*(?:implements\s+([^{]+?))?\s*(?:permits\s+[^{]+?)?\s*\{", re.S)


def _fqcn_of_path(path):
    for pat in (r"src/(?:test|it|main)/java/(.+)\.java$", r"src/(?:test|it|main)/(.+)\.java$", r"src/java/(.+)\.java$"):
        m = re.search(pat, path)
        if m:
            return m.group(1).replace("/", ".")
    return None


def _resolve_simple(simple, pkg, imports, file_index):
    cands = file_index.get(simple) or []
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]
    for imp in imports:
        if imp.endswith("." + simple):
            for c in cands:
                if _fqcn_of_path(c) == imp:
                    return c
    for c in cands:
        if _fqcn_of_path(c) == (pkg + "." + simple if pkg else simple):
            return c
    return None


def _split_types(txt):
    """'A<X, Y>, B' -> ['A', 'B']（去泛型、去包名前缀）"""
    out, depth, cur = [], 0, ""
    for ch in txt:
        if ch == "<": depth += 1
        elif ch == ">": depth -= 1
        elif ch == "," and depth == 0:
            out.append(cur); cur = ""; continue
        if depth == 0 and ch not in "<>":
            cur += ch
    out.append(cur)
    return [t.strip().split(".")[-1] for t in out if t.strip()]


def ancestors_of(project, fqcn):
    """测试类（可能是 Outer.Inner）的祖先类型集合：{全限定名} ∪ {简单名}，含接口。"""
    key = (project, fqcn)
    if key in _ANCESTOR_CACHE:
        return _ANCESTOR_CACHE[key]
    file_index = load_file_index(project)
    result = set()
    seen_files = set()
    queue = [(fqcn, None)]   # (fqcn-ish, file)
    hops = 0
    while queue and hops < 40:
        cur, path = queue.pop(0)
        parts = cur.split(".")
        i = next((k for k, seg in enumerate(parts) if seg[:1].isupper()), len(parts) - 1)
        outer, inner = parts[i], parts[i + 1:]
        pkg = ".".join(parts[:i])
        if path is None:
            path = _resolve_simple(outer, pkg, [], file_index)
        if not path or path in seen_files:
            continue
        seen_files.add(path)
        hops += 1
        try:
            src = open(path, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        src = re.sub(r"//.*?$|/\*.*?\*/", "", src, flags=re.S | re.M)
        imports = re.findall(r"^\s*import\s+([\w.]+)\s*;", src, flags=re.M)
        fpkg = (re.search(r"^\s*package\s+([\w.]+)\s*;", src, flags=re.M) or [None, ""])[1]
        want = (inner[-1] if inner else outer)
        supers = []
        for m in _TYPE_DECL_RE.finditer(src):
            if m.group(1) == want:
                supers = _split_types(m.group(2) or "") + _split_types(m.group(3) or "")
                break
        for sname in supers:
            spath = _resolve_simple(sname, fpkg, imports, file_index)
            sfq = _fqcn_of_path(spath) if spath else None
            result.add(sname)
            if sfq:
                result.add(sfq)
                queue.append((sfq, spath))
    _ANCESTOR_CACHE[key] = result
    return result


def locality(candidate_class, base_class, ancestors=frozenset()):
    """candidate_class 相对 base_class 的位置关系。

    等级口径（2026-09-15 定稿）：
      L0 Source Local            provider 在测试类自己里、且不依赖任何 test helper
      L1 Enclosing-Class Helper  helper/provider 在同一个最外层类里（含静态嵌套类、@Nested 内部类、外层类）
      L2 Inheritance             通过继承关系（父类 / 子类 / 接口）拿到 provider
      L3 Package Helper          同包的其它类
      L4 Cross-Package           跨包
    ② 同一最外层类 → same_class：wicket ResourceReferenceLocatingTest.TestCase、log4j2 嵌套抽象类里的
    @ParameterizedTest 用外层类的 provider，都算 L1，而不是按全限定名不同记成同包 L3。
    """
    if not candidate_class or not base_class:
        return None
    if candidate_class == base_class or outermost_class(candidate_class) == outermost_class(base_class):
        return "same_class"
    # ② 之后再补的一条（2026-09-16）：helper 声明在测试类/provider 类的祖先里（commons-imaging
    # BmpReadTest.data() 调 AbstractBmpTest.getBmpImages() → AbstractImagingTest.getTestImages()）→ Inheritance。
    if candidate_class in ancestors or outermost_class(candidate_class) in ancestors \
            or candidate_class.split(".")[-1] in ancestors:
        return "inherited"
    pkg_c, pkg_b = package_of(candidate_class), package_of(base_class)
    if pkg_c is not None and pkg_c == pkg_b:
        return "same_package"
    return "cross_package"


LOCALITY_TO_LEVEL = {"same_class": 1, "inherited": 2, "same_package": 3, "cross_package": 4}


def extract_provider_subtrees_with_owner(seq):
    """同 extract_provider_subtrees，但给每一行带上它所属 provider 的声明类。

    Phase 2 #8 之后一个测试可能池化多个 provider（抽象测试类 + 多个子类各自的 provider），
    它们的声明类不同；helper 的 locality 必须相对"自己所在的 provider 类"算，而不是一律相对
    第一个 provider，否则第二个子类 provider 里的 self-call 会被记成 same_package(L3)。
    """
    owned = []
    i = 0
    while i < len(seq):
        line = seq[i]
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if indent == 0 and stripped.startswith(("METHODSOURCE ", "FIELDSOURCE ")):
            m = METHODSOURCE_LINE_RE.match(stripped)
            owner = m.group(1) if m else None
            j = i + 1
            while j < len(seq):
                nxt = seq[j]
                if len(nxt) - len(nxt.lstrip(" ")) == 0:
                    break
                owned.append((owner, nxt))
                j += 1
            i = j
        else:
            i += 1
    return owned


def find_methodsource_entries(seq):
    """返回 [(declaring_class, method_name), ...]，按出现顺序，对应每个 METHODSOURCE 入口。"""
    entries = []
    for line in seq:
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if indent == 0 and stripped.startswith(("METHODSOURCE ", "FIELDSOURCE ")):
            m = METHODSOURCE_LINE_RE.match(stripped)
            if m:
                entries.append((m.group(1), m.group(2)))
    return entries


def main():
    sample_rows = load_pilot_sample()
    print(f"pilot MethodSource 样本行数: {len(sample_rows)}", file=sys.stderr)

    aaa_cache = {}
    out = []

    for row in sample_rows:
        project = row["project"]
        if project not in aaa_cache:
            aaa_cache[project] = build_aaa_index(project)
        index, test_classes, aaa_dir = aaa_cache[project]
        file_index = load_file_index(project)

        result = {
            "project": project, "test_class": row["test_class"], "test_name": row["test_name"],
            "dependency": "", "hits_production": "", "provider_declaring_class": "",
            "provider_location_reason": "", "n_test_scope_helpers": "", "status": "",
            "has_unresolved": False, "unresolved_count": 0,
            "has_unknown_tag": False, "unknown_tag_count": 0,
            "recursive_count": 0, "method_ref_count": 0,
            "method_ref_unresolved_scope_count": 0, "traversal_may_be_incomplete": False,
        }

        if not os.path.isdir(aaa_dir):
            result["status"] = "aaa_dir_missing"
            out.append(result)
            continue

        json_path = find_json_file(project, index, aaa_dir, row["test_class"], row["test_name"])
        if json_path is None:
            result["status"] = LAST_MATCH_NOTE.get((project, row["test_class"], row["test_name"]), "json_not_found")
            out.append(result)
            continue

        try:
            data = json.load(open(json_path, encoding="utf-8"))
        except Exception as e:
            result["status"] = f"json_parse_error:{e}"
            out.append(result)
            continue

        seq = data.get("parsedStatementsSequence", [])
        test_class_actual = data.get("testClassName", row["test_class"])
        ancestors = ancestors_of(project, test_class_actual)

        ms_entries = find_methodsource_entries(seq)
        pooled, n_resolved = extract_provider_subtrees(seq)
        if n_resolved == 0 or not ms_entries:
            # ⑥: JDK/第三方 provider → EXTERNAL_PROVIDER，dependency 记 N/A（"EXTERNAL"）
            if any(l.startswith("METHODSOURCE_EXTERNAL") for l in seq):
                result["status"] = "EXTERNAL_PROVIDER"
                result["dependency"] = "EXTERNAL"
                result["provider_declaring_class"] = next(
                    (l.split(" ", 1)[1].split("#")[0] for l in seq if l.startswith("METHODSOURCE_EXTERNAL")), "")
            else:
                result["status"] = "no_methodsource_resolved"
            out.append(result)
            continue

        if len(ms_entries) > 1:
            result["status"] = "OK;multi_provider"
        else:
            result["status"] = "OK"

        provider_classes = []
        for pc, _ in ms_entries:
            if pc not in provider_classes:
                provider_classes.append(pc)
        provider_class = provider_classes[0]
        # 池化：多个 provider 时把全部声明类都记下来（分号分隔），第一列仍是第一个，兼容下游。
        result["provider_declaring_class"] = ";".join(provider_classes)

        max_level = 0
        reasons = []

        # 1) provider 自己的位置（池化时对每个 provider 类各算一次，取最深）
        param_sources_text = " ".join(str(p) for p in data.get("parameterSources", []))
        for pc in provider_classes:
            if pc == test_class_actual:
                continue  # 基线，不加等级
            # 显式引用 = 注解值不是裸方法名字符串：带 "#" 的全限定形式，或指向常量的限定名
            # （`@MethodSource(AbstractInputStreamTest.ARRAY_LENGTHS_NAME)`，常量值是 "pkg.Class#method"）。
            # 裸名只能靠继承（父类/子类/接口）解析到别的类 → L2；显式引用按 provider 类的位置定级。
            explicit = ("#" in param_sources_text or "ArgumentsSource" in param_sources_text
                        or re.search(r"MethodSource\(\s*(?:value\s*=\s*)?[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+\s*[,)]", param_sources_text))
            if explicit:
                loc = locality(pc, test_class_actual)
                lvl = LOCALITY_TO_LEVEL.get(loc, 0)
                reasons.append(f"provider_explicit_ref:{loc or 'unknown'}(L{lvl})")
            else:
                # 无 "#" 的裸方法名却落在别的类：要么在父类（继承上溯），要么在子类
                # （#8：抽象测试类的 @ParameterizedTest + 子类各自的 provider）。两者都是
                # 通过继承关系解析的，同记 L2。
                lvl = 2
                reasons.append(f"provider_via_inheritance:{pc}(L2)")
            max_level = max(max_level, lvl)

        # 2) 池化后的调用链路：test-scope helper 相对 provider 自己类的位置；
        #    production-scope 只标 hits_production，不进 L0-L4。
        hits_production = False
        distinct_test_helpers = set()
        unresolved_count = 0
        unknown_tag_count = 0
        recursive_count = 0
        method_ref_count = 0
        method_ref_unresolved_scope_count = 0

        # ③: 先剔除"作为数据传出去"的方法引用及其展开子树，再按 owner 分类
        owned = extract_provider_subtrees_with_owner(seq)
        kept = kept_indices_after_dropping_data_method_refs([l for _, l in owned])
        for owner_class, line in [owned[i] for i in kept]:
            tag, sig = classify_line(line, test_classes)
            base_class = owner_class or provider_class

            if tag == UNKNOWN_TAG_MARKER:
                # 未知 tag：不该被静默丢弃也不该猜 hits_production，单独计数上报（同
                # build_helper_depth.py 的 fail-safe 原则）。
                unknown_tag_count += 1
                continue
            if tag in UNRESOLVED_TAGS:
                unresolved_count += 1
                continue
            if tag in RECURSIVE_TAGS:
                # 递归保护点是正确的、完整的终止，不是缺失的子树，但也不该被 EXCLUDED_TAGS
                # 那样悄悄吞掉——单独计数，方便区分"确实没有更多信息"和"信息被丢弃"。
                recursive_count += 1
                continue
            if tag in EXCLUDED_TAGS or tag in ("METHODSOURCE", "FIELDSOURCE") or tag == "NEW" or tag in NEUTRAL_TAGS:
                continue
            if tag in PROD_TAGS:
                hits_production = True
                continue
            if tag in TEST_TAGS:
                dc = declaring_class_of(sig)
                distinct_test_helpers.add(sig)
                loc = locality(dc, base_class, ancestors | ancestors_of(project, base_class))
                lvl = LOCALITY_TO_LEVEL.get(loc, 0)
                if lvl > max_level:
                    max_level = lvl
                    reasons.append(f"helper:{dc}->{loc}(L{lvl})")
            elif tag in FALLBACK_TAGS:
                method_ref_count += 1
                dc = declaring_class_of(sig)
                resolved_scope = resolve_scope_via_path(dc, file_index)
                if resolved_scope is None:
                    method_ref_unresolved_scope_count += 1
                    continue  # 项目源码树里查不到，视同第三方/JDK，跳过
                if resolved_scope == "test":
                    distinct_test_helpers.add(sig)
                    loc = locality(dc, base_class, ancestors | ancestors_of(project, base_class))
                    lvl = LOCALITY_TO_LEVEL.get(loc, 0)
                    if lvl > max_level:
                        max_level = lvl
                        reasons.append(f"helper(fallback):{dc}->{loc}(L{lvl})")
                else:
                    hits_production = True
            else:
                # 理论上不可达：SPACE_TAGS/COLON_TAGS 里的每个 tag 都应该在上面某个分支
                # 处理过，其余的在 classify_line() 里已经变成 UNKNOWN_TAG_MARKER。真出现
                # 说明词表和这里的分支又对不上了，按未知 tag 处理，不猜 hits_production。
                unknown_tag_count += 1

        result["has_unresolved"] = unresolved_count > 0
        result["unresolved_count"] = unresolved_count
        result["has_unknown_tag"] = unknown_tag_count > 0
        result["unknown_tag_count"] = unknown_tag_count
        result["recursive_count"] = recursive_count
        result["method_ref_count"] = method_ref_count
        result["method_ref_unresolved_scope_count"] = method_ref_unresolved_scope_count
        # 同 build_helper_depth.py：出现 unresolved 或 METHOD_REF 就说明这条链路可能没走到底，
        # dependency level / hits_production 只是下界/已知信息，不是"确认没有更高等级"。
        result["traversal_may_be_incomplete"] = (unresolved_count > 0) or (method_ref_count > 0)

        # 2026-09-16 口径：dependency = "从 provider 出发沿参数构造相关的 test-code 依赖一直追到 production/JDK 边界，
        # 取走过的 test-code artifact 里最远的"。AAA 调用链（有 binding，负责方法调用）和源码侧 ArtifactWalker
        # （负责字段/常量/构造/字段初始化器，也追调用）各算一个等级，取最大；hits_production 取或。
        result["dependency_aaa"] = LEVEL_NAME[max_level]
        result["hits_production_aaa"] = hits_production
        src = SRC_DEP.get((project, row["test_class"], row["test_name"]))
        src_level = int(src["dependency"][1]) if src and src.get("dependency", "").startswith("L") else None
        if src_level is not None:
            result["dependency_src"] = src["dependency"]
            result["dependency_src_reason"] = src.get("dependency_reason", "")
            result["artifacts_src"] = src.get("artifacts", "")
            hits_production = hits_production or src.get("hits_production_src") == "true"
            if src_level > max_level:
                max_level = src_level
                reasons.append(f"artifact:{src.get('dependency_reason', '')}")
        else:
            result["dependency_src"] = ""
            result["dependency_src_reason"] = ""
            result["artifacts_src"] = ""
        result["dependency"] = LEVEL_NAME[max_level]
        result["hits_production"] = hits_production
        result["provider_location_reason"] = ";".join(reasons) if reasons else "L0_no_dependency"
        result["n_test_scope_helpers"] = len(distinct_test_helpers)
        out.append(result)

    out_csv = os.path.join(OUT_DIR, "dependency_v2.csv")
    fields = ["project", "test_class", "test_name", "dependency", "hits_production",
              "provider_declaring_class", "provider_location_reason", "n_test_scope_helpers", "status",
              "has_unresolved", "unresolved_count", "has_unknown_tag", "unknown_tag_count",
              "recursive_count", "method_ref_count", "method_ref_unresolved_scope_count",
              "traversal_may_be_incomplete",
              "dependency_aaa", "hits_production_aaa", "dependency_src", "dependency_src_reason", "artifacts_src"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)

    from collections import Counter
    ok_rows = [r for r in out if r["status"].startswith("OK")]
    print(f"输出: {out_csv} ({len(out)} 行, {len(ok_rows)} 条 OK)")
    print("dependency 分布:", Counter(r["dependency"] for r in ok_rows))
    print("hits_production 分布:", Counter(r["hits_production"] for r in ok_rows))
    print("status 分布:", Counter(r["status"] for r in out))


if __name__ == "__main__":
    main()
