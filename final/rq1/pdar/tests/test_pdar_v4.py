#!/usr/bin/env python3
"""PDAR v4 的端到端测试。

在临时仓库里按场景逐个提交，每个场景的期望结果都是确定的。「已发表表」不是手写的，
而是用 pdar_v4_commit_table.py（第一阶段）里**原样的**函数对同一仓库跑出来的 —— 所以这里同时
检验了新判定本身、与已发表口径的衔接（merge / 根提交 / Layer 2 / pickaxe），以及
旧 Layer 1 的重放与归因。

    python -m unittest discover -s final/rq1/pdar/tests -v
"""

import csv
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PDAR = os.path.dirname(HERE)
sys.path.insert(0, PDAR)

import pdar_v4_commit_table as v3  # noqa: E402
import pdar_v4_method_level as ml   # noqa: E402
from pt_spans import compute_spans  # noqa: E402

TMP_ROOT = os.environ.get('PT_TEST_TMP', r'D:\pt\pdar_work\_tests' if os.name == 'nt' else None)

BASE = """package x;

class A {
  /** doc for t */
  @ParameterizedTest
  @MethodSource("data")
  void t(int a) {
    int x1 = 1;
    int x2 = 2;
    int x3 = 3;
    int x4 = 4;
    int x5 = 5;
    assert a > 0;
  }
  void helper() {
    int h = 0;
  }

  static Stream<Integer> data() {
    return Stream.of(1);
  }

  enum Color { R, G }

  @ParameterizedTest @EnumSource void e(Color c) {}
  void helper2() {
    int k = 0;
  }

  @Test
  void plain() {
    int p1 = 1;
    int p2 = 2;
    int p3 = 3;
    int p4 = 4;
    int p5 = 5;
  }

  void other() {
    int o = 0;
    int o2 = 0;
  }
}
"""

J4 = """package x;

@RunWith(Parameterized.class)
public class J4 {
  @Parameters
  public static Object[] data() { return new Object[]{1}; }
  int v = 1;
}
"""

PROD = """package x;

public enum Prod { ONE, TWO }
"""

P = """package x;

class P {
  @ParameterizedTest @EnumSource(Prod.class) void p(Prod c) {}
}
"""

SPACE = """package x;

class S {
  @ParameterizedTest
  @ValueSource(ints = {1})
  void s(int a) {
    int y1 = 1;
    int y2 = 2;
    int y3 = 3;
    int y4 = 4;
    int y5 = 5;
  }
}
"""


ENCLOSED = """package x;

import org.junit.Test;

@RunWith(Enclosed.class)
public class BarTest {
    @RunWith(Parameterized.class)
    public static class WithParams {
        int a = 1;
    }
    public static class Plain {
        @Test public void x() { int b = 1; }
    }
}
"""

OUTER = """package x;

import org.junit.Test;

@RunWith(Parameterized.class)
public class FooTest {
    @Test public void p() { int q = 1; }
    public static class EdgeCases {
        @Test public void e() { int c = 1; }
    }
    static class Helper {
        int h = 1;
    }
}
"""

KT = """package x

class K {
    @ParameterizedTest
    @ValueSource(ints = [1])
    fun k(a: Int) {
        val z = 1
    }
}
"""


def sh(repo, *args):
    return subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True).stdout


class Repo:
    def __init__(self, path):
        self.path = path
        self.tags = {}
        os.makedirs(path, exist_ok=True)
        sh(path, 'init', '-q', '-b', 'main')
        sh(path, 'config', 'user.name', 'T')
        sh(path, 'config', 'core.autocrlf', 'false')

    def write(self, rel, text):
        full = os.path.join(self.path, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', newline='\n', encoding='utf-8') as f:
            f.write(text)

    def read(self, rel):
        with open(os.path.join(self.path, rel), encoding='utf-8') as f:
            return f.read()

    def replace(self, rel, old, new):
        s = self.read(rel)
        assert s.count(old) == 1, (rel, old)
        self.write(rel, s.replace(old, new))

    def commit(self, tag, email=None):
        sh(self.path, 'add', '-A')
        sh(self.path, '-c', f'user.email={email or tag + "@t"}', 'commit', '-q', '-m', tag)
        self.tags[tag] = sh(self.path, 'rev-parse', 'HEAD').decode().strip()


def build_repo(path):
    r = Repo(path)
    T = 'src/test/x/A.java'
    r.write(T, BASE); r.commit('C0_root')
    r.replace(T, 'int x5 = 5;', 'int x5 = 50;'); r.commit('C1_deep_in_pt')
    r.replace(T, 'int k = 0;', 'int k = 1;'); r.commit('C2_helper_after_pt')
    r.replace(T, 'Stream.of(1);', 'Stream.of(1, 2);'); r.commit('C3_provider')
    r.replace(T, 'enum Color { R, G }', 'enum Color { R, G, B }'); r.commit('C4_enum_in_file')
    r.replace(T, '    int o = 0;\n', '    int o = 0; // @ParameterizedTest mention\n'); r.commit('C5_mention')
    r.replace(T, 'int p2 = 2;', 'int p2 = 22;'); r.commit('C6_plain_test')
    r.replace(T, '/** doc for t */', '/** doc for t, updated */'); r.commit('C7_javadoc')
    r.replace(T, '    int o2 = 0;\n  }\n}\n',
              '    int o2 = 0;\n  }\n\n  @ParameterizedTest\n  @ValueSource(ints = {1})\n  void added(int a) {}\n}\n')
    r.commit('C8_add_pt')
    s = r.read(T)
    start = s.index('  /** doc for t')
    end = s.index('  void helper() {')
    r.write(T, s[:start] + s[end:]); r.commit('C9_delete_pt')
    sh(r.path, 'mv', T, 'src/test/x/B.java'); r.commit('C10_pure_rename')
    r.write('src/main/x/Prod.java', PROD); r.write('src/test/x/P.java', P); r.commit('C11_add_p')
    r.replace('src/main/x/Prod.java', 'ONE, TWO', 'ONE, TWO, THREE'); r.commit('C12_prod_enum')
    r.write('src/test/x/J4.java', J4); r.commit('C13_add_j4')
    r.replace('src/test/x/J4.java', 'int v = 1;', 'int v = 2;'); r.commit('C14_mod_j4')
    sh(r.path, 'checkout', '-q', '-b', 'side')
    r.write('src/test/x/My Test.java', SPACE); r.commit('C15_side_add_space')
    sh(r.path, 'checkout', '-q', 'main')
    r.replace('src/test/x/B.java', 'int p3 = 3;', 'int p3 = 33;'); r.commit('C16_main_plain')
    sh(r.path, '-c', 'user.email=m@t', 'merge', '-q', '--no-ff', 'side', '-m', 'C17_merge')
    r.tags['C17_merge'] = sh(r.path, 'rev-parse', 'HEAD').decode().strip()
    r.replace('src/test/x/My Test.java', 'int y5 = 5;', 'int y5 = 55;'); r.commit('C18_space_deep')
    # 历史简化：side2 上改 PT，main 上 cherry-pick 同样的改动，再合并 —— merge 与 main 一侧在
    # *.java 上相同，不加 --full-history 时 git log -- '*.java' 会把 side2 的提交整个跳过
    sh(r.path, 'checkout', '-q', '-b', 'side2')
    r.replace('src/test/x/My Test.java', 'int y4 = 4;', 'int y4 = 44;'); r.commit('C19_side2_pt')
    sh(r.path, 'checkout', '-q', 'main')
    sh(r.path, '-c', 'user.email=cp@t', 'cherry-pick', r.tags['C19_side2_pt'])
    r.tags['C20_cherry'] = sh(r.path, 'rev-parse', 'HEAD').decode().strip()
    sh(r.path, '-c', 'user.email=m2@t', 'merge', '-q', '--no-ff', 'side2', '-m', 'C21_merge2')
    sh(r.path, 'branch', '-q', '-D', 'side2')     # 真实仓库里合并完的分支通常已删，--all 走不到它
    # 只算 Java：Kotlin 测试里的 @ParameterizedTest 不是论文意义上的 PT
    r.write('src/test/kotlin/x/K.kt', KT); r.commit('C22_kotlin_only')
    r.replace('src/test/kotlin/x/K.kt', 'val z = 1', 'val z = 2')
    r.replace('src/main/x/Prod.java', 'THREE', 'FOUR'); r.commit('C23_kotlin_plus_java')
    # JUnit 4，路径里有以 b 结尾的目录（db/）：第一阶段的正则 `b/(.+\.java)$` 会从 a/ 路径
    # 中间的 "db/" 开始匹配，取出的路径无效，Layer 2 静默不命中
    J4DB = 'src/test/java/org/x/db/J4Db.java'
    r.write(J4DB, J4.replace('class J4', 'class J4Db')); r.commit('C24_add_j4_db')
    r.replace(J4DB, 'int v = 1;', 'int v = 3;'); r.commit('C25_mod_j4_db')
    r.replace(J4DB, '@RunWith(Parameterized.class)\n', ''); r.commit('C26_remove_runwith')
    r.replace(J4DB, 'int v = 3;', 'int v = 4;')
    r.replace(J4DB, 'public class J4Db {', '@RunWith(Parameterized.class)\npublic class J4Db {'); r.commit('C27_readd_runwith')
    sh(r.path, 'mv', J4DB, 'src/test/java/org/x/db/J4Db2.java'); r.commit('C28_rename_j4')
    # `@RunWith(value = Parameterized.class)`：第一阶段的模式匹配不到
    J4V = 'src/test/java/org/x/J4V.java'
    r.write(J4V, J4.replace('class J4', 'class J4V').replace('@RunWith(Parameterized.class)', '@RunWith(value = Parameterized.class)'))
    r.commit('C29_add_j4_value')
    r.replace(J4V, 'int v = 1;', 'int v = 5;'); r.commit('C30_mod_j4_value')
    # JUnit 4 类级：Enclosed 里只有被标注的嵌套类是 PT；参数化类里嵌套的独立测试类不是 PT，
    # 嵌套辅助类是；只改 import 不算
    r.write('src/test/java/org/x/BarTest.java', ENCLOSED); r.commit('C31_add_enclosed')
    r.replace('src/test/java/org/x/BarTest.java', 'int b = 1;', 'int b = 2;'); r.commit('C32_enclosed_plain')
    r.replace('src/test/java/org/x/BarTest.java', 'int a = 1;', 'int a = 2;'); r.commit('C33_enclosed_params')
    r.write('src/test/java/org/x/FooTest.java', OUTER); r.commit('C34_add_outer')
    r.replace('src/test/java/org/x/FooTest.java', 'int c = 1;', 'int c = 2;'); r.commit('C35_nested_test_class')
    r.replace('src/test/java/org/x/FooTest.java', 'int h = 1;', 'int h = 2;'); r.commit('C36_nested_helper')
    r.replace('src/test/java/org/x/FooTest.java', 'import org.junit.Test;', 'import org.junit.*;'); r.commit('C37_import_only')
    return r


def published_table(repo):
    """用原样的 V3 函数生成逐提交表（与 pdar_v4_commit_table.main 的循环一致）。"""
    pick = v3.get_pickaxe_commits(repo)
    rows = {}
    for c in v3.get_all_commits_with_info(repo):
        h = c['commit_hash']
        diff = v3.get_commit_diff(repo, h, 3)
        layer, core = '', 0
        if v3.check_junit5_in_diff(diff):
            layer = 'junit5_hunk'
        elif v3.check_junit4_in_diff(diff, repo, h):
            layer = 'junit4_file'
        elif h in pick:
            layer, core = 'pickaxe', 1
        if layer and h in pick:
            core = 1
        rows[h] = dict(commit_hash=h, author_email=c['author_email'],
                       touched_test=str(int(v3.check_touched_test(diff))),
                       modifiedPT=str(int(bool(layer))), is_core=str(core), detection_layer=layer)
    return rows


class MethodLevelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if TMP_ROOT:
            os.makedirs(TMP_ROOT, exist_ok=True)
        cls.tmp = tempfile.mkdtemp(dir=TMP_ROOT)
        cls.repo = build_repo(os.path.join(cls.tmp, 'repo'))
        cls.table = published_table(cls.repo.path)
        table = dict(cls.table)
        table['f' * 40] = dict(commit_hash='f' * 40, author_email='z@t', touched_test='1',
                              modifiedPT='0', is_core='0', detection_layer='')
        cls.out = os.path.join(cls.tmp, 'out')
        cls.summary = ml.analyze('T', cls.repo.path, fullscan=True, out_dir=cls.out, published=table)
        with open(os.path.join(cls.out, 'T_method_commits.csv'), newline='', encoding='utf-8') as f:
            cls.rows = {r['commit_hash']: r for r in csv.DictReader(f)}

    @classmethod
    def tearDownClass(cls):
        def onerr(func, path, _):
            os.chmod(path, 0o700)
            func(path)
        shutil.rmtree(cls.tmp, onerror=onerr)

    def row(self, tag):
        return self.rows.get(self.repo.tags[tag], {})

    def flag(self, tag, col):
        v = self.row(tag).get(col, '')
        return int(v) if v not in ('', None) else 0

    def layer(self, tag):
        return self.table[self.repo.tags[tag]]['detection_layer']

    # ---- 新判定 ----
    def test_full_history(self):
        self.assertEqual(self.flag('C19_side2_pt', 'l1m_pt'), 1)
        self.assertEqual(self.flag('C20_cherry', 'l1m_pt'), 1)

    def test_kotlin_not_counted(self):
        for tag in ('C22_kotlin_only', 'C23_kotlin_plus_java'):
            self.assertEqual(self.layer(tag), 'junit5_hunk', tag)       # 旧 L1 不分文件类型
            self.assertEqual(self.row(tag).get('attr'), 'non_java_file', tag)
            self.assertEqual(self.flag(tag, 'l1m_prov'), 0, tag)
            self.assertEqual(self.flag(tag, 'l2'), 0, tag)
        self.assertEqual(self.summary['nonjava_only_old_l1'], 1)

    def test_deep_change_inside_pt(self):
        self.assertEqual(self.layer('C1_deep_in_pt'), '')         # 旧 L1 漏
        self.assertEqual(self.flag('C1_deep_in_pt', 'l1m_pt'), 1)
        self.assertEqual(self.flag('C18_space_deep', 'l1m_pt'), 1)  # 路径含空格

    def test_helper_after_pt_is_not_pt(self):
        self.assertEqual(self.layer('C2_helper_after_pt'), 'junit5_hunk')   # 旧 L1 误报
        self.assertEqual(self.flag('C2_helper_after_pt', 'l1m_prov'), 0)
        self.assertEqual(self.row('C2_helper_after_pt').get('attr'), 'overrun_forward')

    def test_provider_and_enum_only_in_prov(self):
        for tag in ('C3_provider', 'C4_enum_in_file'):
            self.assertEqual(self.flag(tag, 'l1m_pt'), 0, tag)
            self.assertEqual(self.flag(tag, 'l1m_prov'), 1, tag)

    def test_production_enum_excluded(self):
        self.assertEqual(self.flag('C12_prod_enum', 'l1m_prov'), 0)
        self.assertGreaterEqual(self.summary['xrefs'], 1)

    def test_comment_mention(self):
        self.assertEqual(self.layer('C5_mention'), 'junit5_hunk')
        self.assertEqual(self.flag('C5_mention', 'l1m_prov'), 0)
        self.assertEqual(self.row('C5_mention').get('attr'), 'pt_mention_not_method')

    def test_plain_test_untouched(self):
        for tag in ('C6_plain_test', 'C16_main_plain'):
            self.assertEqual(self.flag(tag, 'l1m_prov'), 0, tag)

    def test_javadoc_prev_line(self):
        self.assertEqual(self.layer('C7_javadoc'), 'junit5_hunk')
        self.assertEqual(self.flag('C7_javadoc', 'l1m_prov'), 0)
        self.assertEqual(self.row('C7_javadoc').get('attr'), 'overrun_prev')

    def test_add_and_delete_pt(self):
        for tag in ('C8_add_pt', 'C9_delete_pt', 'C11_add_p', 'C15_side_add_space'):
            self.assertEqual(self.flag(tag, 'l1m_pt'), 1, tag)
            self.assertEqual(self.flag(tag, 'core_diff'), 1, tag)

    def test_pure_rename(self):
        self.assertEqual(self.layer('C10_pure_rename'), 'junit5_hunk')
        self.assertEqual(self.flag('C10_pure_rename', 'l1m_pt'), 0)
        self.assertEqual(self.row('C10_pure_rename').get('attr'), 'rename')

    # ---- 与已发表口径的衔接 ----
    def test_root_and_merge_not_judged(self):
        self.assertNotIn(self.repo.tags['C0_root'], self.rows)
        self.assertNotIn(self.repo.tags['C17_merge'], self.rows)
        self.assertEqual(self.table[self.repo.tags['C0_root']]['touched_test'], '0')
        self.assertEqual(self.table[self.repo.tags['C17_merge']]['touched_test'], '0')

    def test_layer2(self):
        self.assertEqual(self.layer('C14_mod_j4'), 'junit4_file')
        self.assertEqual(self.flag('C14_mod_j4', 'l2'), 1)
        self.assertEqual(self.flag('C13_add_j4', 'l2'), 1)
        self.assertEqual(self.row('C2_helper_after_pt').get('l2'), '0')

    def test_layer2_path_with_b_dir(self):
        # 第一阶段漏判（路径解析 bug），第二阶段重算后命中
        self.assertEqual(self.layer('C25_mod_j4_db'), '')
        self.assertEqual(self.flag('C25_mod_j4_db', 'l2'), 1)

    def test_layer2_value_form(self):
        self.assertEqual(self.layer('C30_mod_j4_value'), '')        # 第一阶段的模式漏判
        self.assertEqual(self.flag('C30_mod_j4_value', 'l2'), 1)

    def test_layer2_class_level(self):
        # 第一阶段是文件级，这几个都算；v4 只算参数化类自己的区间
        for tag in ('C32_enclosed_plain', 'C35_nested_test_class', 'C37_import_only'):
            self.assertEqual(self.layer(tag), 'junit4_file', tag)
            self.assertEqual(self.flag(tag, 'l2'), 0, tag)
        for tag in ('C33_enclosed_params', 'C36_nested_helper'):
            self.assertEqual(self.flag(tag, 'l2'), 1, tag)

    def test_layer2_two_sided(self):
        # 删除 @RunWith：改动后的版本已不是参数化类，改动前的是 —— 两侧检查命中
        self.assertEqual(self.flag('C26_remove_runwith', 'l2'), 1)
        self.assertEqual(self.flag('C27_readd_runwith', 'l2'), 1)

    def test_layer2_pure_rename_not_counted(self):
        self.assertEqual(self.flag('C28_rename_j4', 'l2'), 0)

    def test_snapshot_cutoff(self):
        self.assertEqual(self.summary['missing_in_repo'], 1)

    # ---- 自检 ----
    def test_no_unexplained(self):
        self.assertNotIn('unexplained', self.summary['attribution'])
        self.assertNotIn('not_reproduced', self.summary['attribution'])
        self.assertEqual(self.summary['fullscan_mismatch'], 0)
        self.assertEqual(self.summary['published_hit_not_in_stream'], 0)

    def test_core_diff_matches_pickaxe(self):
        # pickaxe 不分文件类型；只改了 Kotlin 的提交它会命中，core_diff（只看 .java）不会
        for h, r in self.rows.items():
            if r['attr'] == 'non_java_file' and h == self.repo.tags['C22_kotlin_only']:
                self.assertEqual((r['core_diff'], r['pickaxe_new']), ('0', '1'))
                continue
            self.assertEqual(r['core_diff'], r['pickaxe_new'], h)

    def test_old_l1_replay_matches_original(self):
        for h in self.table:
            diff = v3.get_commit_diff(self.repo.path, h, 3)
            self.assertEqual(v3.check_junit5_in_diff(diff),
                             ml.old_l1_trigger(diff.encode('utf-8')) is not None, h)


class SpansTest(unittest.TestCase):
    def test_spans(self):
        src = (b'class A {\n'
               b'  /** d */\n'
               b'  @ParameterizedTest\n'
               b'  @MethodSource({"a", "B#b", "x.Ext#c"})\n'
               b'  void t(int v) {\n'
               b'  }\n'
               b'  static Stream<Integer> a() { return null; }\n'
               b'  static class B { static Stream<Integer> b() { return null; } }\n'
               b'  @org.junit.jupiter.params.ParameterizedTest @FieldSource void f(int v) {}\n'
               b'  static List<Integer> f = List.of(1);\n'
               b'  @ParameterizedTest @ArgumentsSource(Prov.class) void g(int v) {}\n'
               b'  static class Prov implements ArgumentsProvider {}\n'
               b'  @ParameterizedTest @MethodSource("ov") void h(int v) {}\n'
               b'  static Stream<Integer> ov() { return null; }\n'
               b'  static Stream<Integer> ov(int x) { return null; }\n'
               b'  String s = "@ParameterizedTest";\n'
               b'}\n')
        s = compute_spans(src)
        self.assertEqual(s.pt, [(3, 6), (9, 9), (11, 11), (13, 13)])
        for want in [(7, 7), (8, 8), (10, 10), (12, 12), (14, 14), (15, 15)]:
            self.assertIn(want, s.prov)
        self.assertEqual(s.xrefs, 1)          # x.Ext#c
        self.assertFalse(s.has_error)

    def test_no_token_short_circuit(self):
        self.assertEqual(compute_spans(b'class A { @Test void t() {} }').pt, [])


if __name__ == '__main__':
    unittest.main()
