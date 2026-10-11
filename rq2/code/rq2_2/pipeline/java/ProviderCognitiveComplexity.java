import org.eclipse.jdt.core.dom.*;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Cognitive Complexity 目标定位 v2：全程纯语法 AST（setResolveBindings(false)），不依赖
 * AAA 的 declaring-class 解析结果（那一步需要 binding，是"UnknownClass"46 条丢失的根源）。
 *
 * 输入清单每行: project,project_root,test_class,test_name,test_source_file
 * 流程（每一步都不需要类型绑定）:
 *   1. 解析 test_source_file，按名字找到 test_name 对应的 MethodDeclaration。
 *   2. 从它的注解节点里直接读 @MethodSource 的字符串值（SingleMemberAnnotation /
 *      NormalAnnotation 的 StringLiteral，不处理常量拼接等需要绑定才能算的写法——遇到就跳过
 *      并在 note 里标出来，不静默当作找到了）。
 *   3. 对每个 provider 引用：
 *        - "Class#method" 形式：按 Class 的简单名在项目源码树里搜文件。
 *        - 裸名形式：先在测试类自己的文件里按名字找；找不到就读 AST 里 `extends XXX`
 *          写的字面类名（不是绑定后的完全限定名），按简单名搜文件，逐级往上找，
 *          最多 5 层，防止继承环。
 *   4. 找到 provider 的 MethodDeclaration 后用 CognitiveComplexityCalculator 算分，
 *      多个 provider 的话把分数加起来。
 */
public class ProviderCognitiveComplexity {

    // 每个项目一份 简单类名 -> 候选文件 索引，跨行复用
    private static final Map<String, Map<String, List<Path>>> fileIndexCache = new HashMap<>();

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("usage: ProviderCognitiveComplexity <input.csv> <output.csv>");
            System.exit(1);
        }
        List<String[]> rows = readCsv(args[0]);
        String[] header = rows.get(0);
        int idxProject = indexOf(header, "project");
        int idxProjectRoot = indexOf(header, "project_root");
        int idxTestClass = indexOf(header, "test_class");
        int idxTestName = indexOf(header, "test_name");
        int idxTestFile = indexOf(header, "test_source_file");

        List<String[]> out = new ArrayList<>();
        out.add(append(header, "transformation_complexity", "n_providers_resolved", "note"));

        Map<String, CompilationUnit> cuCache = new HashMap<>();

        for (int i = 1; i < rows.size(); i++) {
            if (i % 25 == 0) System.err.println("progress: " + i + "/" + (rows.size() - 1));
            String[] row = rows.get(i);
            String project = row[idxProject];
            String projectRoot = row[idxProjectRoot];
            String testName = row[idxTestName];
            String testFile = row[idxTestFile];

            if (testFile == null || testFile.isBlank()) {
                out.add(append(row, "", "0", "TEST_FILE_UNKNOWN"));
                continue;
            }
            try {
                Map<String, List<Path>> fileIndex = fileIndexCache.computeIfAbsent(projectRoot,
                        r -> buildFileIndex(Paths.get(r)));

                CompilationUnit testCu = cuCache.computeIfAbsent(testFile, ProviderCognitiveComplexity::parseQuiet);
                if (testCu == null) {
                    out.add(append(row, "", "0", "TEST_FILE_PARSE_ERROR"));
                    continue;
                }
                MethodDeclaration testMd = findTestMethodByName(testCu, testName);
                if (testMd == null) {
                    out.add(append(row, "", "0", "TEST_METHOD_NOT_FOUND"));
                    continue;
                }

                List<String> providerRefs = extractMethodSourceValues(testMd, testName, testCu, fileIndex, cuCache);
                ArtifactWalker xwalker = new ArtifactWalker(fileIndex, cuCache, ProviderCognitiveComplexity::parseQuiet, testFile, testCu, testMd);
                List<ExtraProviders.Unit> extra = ExtraProviders.collect(testMd, testCu, testFile, xwalker);
                if (providerRefs.isEmpty() && extra.isEmpty()) {
                    out.add(append(row, "", "0", "NO_METHODSOURCE_ANNOTATION_VALUE"));
                    continue;
                }

                int total = 0;
                int resolved = 0;
                List<String> notes = new ArrayList<>();
                // @ArgumentsSource → provideArguments() 的 CC；@FieldSource → 字段初始化器的 CC
                for (ExtraProviders.Unit u : extra) {
                    if (u.note != null) { notes.add(u.note); continue; }
                    if (u.method != null) { total += new CognitiveComplexityCalculator(u.method.getName().getIdentifier()).forMethod(u.method); resolved++; }
                    else if (u.field != null && u.field.fragment.getInitializer() != null) { total += new CognitiveComplexityCalculator(u.field.fragment.getName().getIdentifier()).forExpression(u.field.fragment.getInitializer()); resolved++; }
                    else notes.add("FIELD_NO_INITIALIZER:" + u.label);
                }
                for (String ref : providerRefs) {
                    if (ref.startsWith(UNRESOLVED_VALUE_PREFIX)) {
                        // #7: 注解有值但语法上求不出来（非常量表达式等）。明确报出来，不落到
                        // "同名方法"兜底，避免把测试方法自己当 provider 算出一个错值还标 OK。
                        notes.add("UNRESOLVED_ANNOTATION_VALUE:" + ref.substring(UNRESOLVED_VALUE_PREFIX.length(), ref.length() - 1));
                        continue;
                    }
                    ProviderResult pr = resolveProvider(ref, testCu, testFile, fileIndex, cuCache, testMd);
                    if (pr == null) {
                        // @MethodSource 指向 JDK/第三方（如 java.util.Locale#getAvailableLocales）：provider 不是项目代码，
                        // 无源码可算——这不是"找不到"，是"在项目之外"，标签要区分开。
                        notes.add((isJdkOrExternalRef(ref) ? "PROVIDER_EXTERNAL:" : "PROVIDER_NOT_FOUND:") + ref);
                        continue;
                    }
                    CognitiveComplexityCalculator calc = new CognitiveComplexityCalculator(pr.method.getName().getIdentifier());
                    total += calc.forMethod(pr.method);
                    resolved++;
                }
                String note = notes.isEmpty() ? "" : String.join(";", notes);
                out.add(append(row, resolved > 0 ? String.valueOf(total) : "", String.valueOf(resolved), note));
            } catch (Exception e) {
                out.add(append(row, "", "0", "ERROR:" + e.getClass().getSimpleName() + ":" +
                        String.valueOf(e.getMessage()).replace(",", ";").replace("\n", " ")));
            }
        }

        writeCsv(args[1], out);
        System.err.println("Done. " + (out.size() - 1) + " rows -> " + args[1]);
    }

    private static final class ProviderResult {
        final MethodDeclaration method;
        ProviderResult(MethodDeclaration m) { this.method = m; }
    }

    /** 解析一个 @MethodSource 引用（裸名 或 "Class#method"）到具体的方法声明。 */
    private static ProviderResult resolveProvider(String ref, CompilationUnit testCu, String testFile,
                                                   Map<String, List<Path>> fileIndex,
                                                   Map<String, CompilationUnit> cuCache, MethodDeclaration testMd) throws IOException {
        String className = null;
        String methodName = ref;
        if (ref.contains("#")) {
            String[] parts = ref.split("#", 2);
            className = parts[0];
            methodName = parts[1];
        }
        if (methodName.indexOf('(') >= 0) {
            methodName = methodName.substring(0, methodName.indexOf('('));
        }

        if (className != null) {
            String simple = className.contains(".") ? className.substring(className.lastIndexOf('.') + 1) : className;
            Path file = pickFile(fileIndex, simple, className);
            if (file == null) return null;
            CompilationUnit cu = cuCache.computeIfAbsent(file.toString(), ProviderCognitiveComplexity::parseQuiet);
            if (cu == null) return null;
            MethodDeclaration md = findMethodByName(cu, methodName, null);
            return md == null ? null : new ProviderResult(md);
        }

        // 裸名：先在测试类自己的文件里找
        MethodDeclaration local = findMethodByName(testCu, methodName, testMd);
        if (local != null) return new ProviderResult(local);

        // #9/#17: BFS over the *literal* supertype names (superclass + implemented interfaces —
        // JUnit 5 accepts static factories declared on an interface the test class implements),
        // bounded, dedup'd by simple name.
        java.util.Deque<CompilationUnit> queue = new java.util.ArrayDeque<>();
        Set<String> visited = new HashSet<>();
        queue.add(testCu);
        int expanded = 0;
        while (!queue.isEmpty() && expanded < 40) {
            CompilationUnit cur = queue.poll();
            for (String superName : getSupertypeSimpleNames(cur)) {
                if (!visited.add(superName)) continue;
                Path superFile = pickFile(fileIndex, superName, null);
                if (superFile == null) continue;
                CompilationUnit superCu = cuCache.computeIfAbsent(superFile.toString(), ProviderCognitiveComplexity::parseQuiet);
                if (superCu == null) continue;
                expanded++;
                MethodDeclaration md = findMethodByName(superCu, methodName, null);
                if (md != null) return new ProviderResult(md);
                queue.add(superCu);
            }
        }
        // #8: template-method style — the abstract test class declares the @ParameterizedTest and each
        // concrete subclass supplies the provider. Walk the inheritance tree *downwards* (bounded).
        String ownName = testFile.substring(testFile.lastIndexOf('/') + 1).replace(".java", "");
        java.util.Deque<String> down = new java.util.ArrayDeque<>();
        Set<String> seen = new HashSet<>();
        down.add(ownName);
        int hops = 0;
        while (!down.isEmpty() && hops < 200) {
            String t = down.poll();
            if (!seen.add(t)) continue;
            for (Path f : directSubtypeFiles(fileIndex, t)) {
                hops++;
                CompilationUnit cu = cuCache.computeIfAbsent(f.toString(), ProviderCognitiveComplexity::parseQuiet);
                if (cu == null) continue;
                MethodDeclaration md = findMethodByName(cu, methodName, null);
                if (md != null) return new ProviderResult(md);
                down.add(f.getFileName().toString().replace(".java", ""));
            }
        }
        return null;
    }

    private static boolean isJdkOrExternalRef(String ref) {
        String cls = ref.contains("#") ? ref.substring(0, ref.indexOf('#')) : "";
        return cls.startsWith("java.") || cls.startsWith("javax.") || cls.startsWith("jdk.") || cls.startsWith("sun.");
    }

    private static Path pickFile(Map<String, List<Path>> fileIndex, String simpleName, String fqnHint) {
        List<Path> candidates = fileIndex.get(simpleName);
        if (candidates == null || candidates.isEmpty()) return null;
        if (candidates.size() == 1) return candidates.get(0);
        if (fqnHint != null) {
            String pkgPath = fqnHint.contains(".") ? fqnHint.substring(0, fqnHint.lastIndexOf('.')).replace('.', '/') : "";
            for (Path p : candidates) {
                if (!pkgPath.isEmpty() && p.toString().replace(File.separatorChar, '/').contains(pkgPath)) return p;
            }
        }
        return candidates.get(0);
    }

    @SuppressWarnings("unchecked")

    /** #17: superclass + implemented interfaces, simple names (generics / package prefix stripped). */
    private static List<String> getSupertypeSimpleNames(CompilationUnit cu) {
        List<String> out = new ArrayList<>();
        for (Object o : cu.types()) {
            if (!(o instanceof TypeDeclaration)) continue;
            TypeDeclaration td = (TypeDeclaration) o;
            List<Type> ts = new ArrayList<>();
            if (td.getSuperclassType() != null) ts.add(td.getSuperclassType());
            for (Object i : td.superInterfaceTypes()) ts.add((Type) i);
            for (Type t : ts) {
                String name = t.toString();
                int lt = name.indexOf('<'); if (lt >= 0) name = name.substring(0, lt);
                int dot = name.lastIndexOf('.'); if (dot >= 0) name = name.substring(dot + 1);
                out.add(name);
            }
            break;
        }
        return out;
    }

    /** #8: files whose top-level type `extends`/`implements` the given simple name (regex over the index). */
    private static final Map<Map<String, List<Path>>, Map<String, List<Path>>> SUBTYPE_INDEX = new HashMap<>();
    private static List<Path> directSubtypeFiles(Map<String, List<Path>> fileIndex, String simpleName) {
        Map<String, List<Path>> idx = SUBTYPE_INDEX.get(fileIndex);
        if (idx == null) {
            idx = new HashMap<>();
            java.util.regex.Pattern p = java.util.regex.Pattern.compile("\\b(?:extends|implements)\\s+([^{]+?)\\s*(?:\\{|implements|permits)");
            for (List<Path> paths : fileIndex.values()) for (Path f : paths) {
                try {
                    java.util.regex.Matcher m = p.matcher(new String(Files.readAllBytes(f), java.nio.charset.StandardCharsets.UTF_8));
                    while (m.find()) for (String part : m.group(1).split(",")) {
                        String n = part.trim(); int lt = n.indexOf('<'); if (lt >= 0) n = n.substring(0, lt);
                        int dot = n.lastIndexOf('.'); if (dot >= 0) n = n.substring(dot + 1);
                        if (!n.isEmpty()) idx.computeIfAbsent(n, k -> new ArrayList<>()).add(f);
                    }
                } catch (IOException ignored) { }
            }
            SUBTYPE_INDEX.put(fileIndex, idx);
        }
        return idx.getOrDefault(simpleName, java.util.Collections.emptyList());
    }

    private static String getSuperclassSimpleName(CompilationUnit cu) {
        for (Object o : cu.types()) {
            if (o instanceof TypeDeclaration) {
                Type sup = ((TypeDeclaration) o).getSuperclassType();
                if (sup == null) return null;
                String name = sup.toString();
                // 去掉泛型参数 <...> 和包名前缀，只留最后一段简单名
                int lt = name.indexOf('<');
                if (lt >= 0) name = name.substring(0, lt);
                int dot = name.lastIndexOf('.');
                if (dot >= 0) name = name.substring(dot + 1);
                return name;
            }
        }
        return null;
    }

    @SuppressWarnings("unchecked")
    // #7: 注解值不是字符串字面量时的标记。之前遇到常量引用（@MethodSource(DATE_PARSER_PARAMETERS)、
    // @MethodSource(Other.CONST)）会静默退化成"同名方法"兜底，结果找到的是测试方法自己，
    // 算出一个错误的 CC 却标 OK。现在：能语法解析的常量就解析；解析不了的返回这个前缀，
    // 由调用方标 UNRESOLVED_ANNOTATION_VALUE，绝不再猜。
    static final String UNRESOLVED_VALUE_PREFIX = "<unresolved:";

    @SuppressWarnings("unchecked")
    private static List<String> extractMethodSourceValues(MethodDeclaration md, String defaultName,
                                                          CompilationUnit cu, Map<String, List<Path>> fileIndex,
                                                          Map<String, CompilationUnit> cuCache) {
        List<String> values = new ArrayList<>();
        for (Object o : md.modifiers()) {
            if (!(o instanceof Annotation)) continue;
            Annotation ann = (Annotation) o;
            String simpleName = ann.getTypeName().getFullyQualifiedName();
            if (simpleName.contains(".")) simpleName = simpleName.substring(simpleName.lastIndexOf('.') + 1);
            if (!"MethodSource".equals(simpleName)) continue;

            Expression valueExpr = null;
            if (ann instanceof SingleMemberAnnotation) {
                valueExpr = ((SingleMemberAnnotation) ann).getValue();
            } else if (ann instanceof NormalAnnotation) {
                for (Object mv : ((NormalAnnotation) ann).values()) {
                    MemberValuePair mvp = (MemberValuePair) mv;
                    if ("value".equals(mvp.getName().getIdentifier())) { valueExpr = mvp.getValue(); break; }
                }
            }
            if (valueExpr == null) {
                // 真正的 bare @MethodSource / @MethodSource()：JUnit 默认取与测试方法同名的工厂方法。
                // 只有这一种情况允许用 defaultName 兜底。
                values.add(defaultName);
                continue;
            }
            List<Expression> elems = new ArrayList<>();
            if (valueExpr instanceof ArrayInitializer) {
                for (Object e : ((ArrayInitializer) valueExpr).expressions()) elems.add((Expression) e);
            } else {
                elems.add(valueExpr);
            }
            for (Expression e : elems) {
                String s = resolveStringConstant(e, cu, fileIndex, cuCache, 0);
                values.add(s != null ? s : UNRESOLVED_VALUE_PREFIX + e.toString().replace(",", ";") + ">");
            }
        }
        return values;
    }

    /** 纯语法求一个编译期字符串常量的值；解析不了返回 null（不猜）。 */
    private static String resolveStringConstant(Expression e, CompilationUnit cu, Map<String, List<Path>> fileIndex,
                                                Map<String, CompilationUnit> cuCache, int depth) {
        if (e == null || depth > 8) return null;
        if (e instanceof StringLiteral) return ((StringLiteral) e).getLiteralValue();
        if (e instanceof ParenthesizedExpression) {
            return resolveStringConstant(((ParenthesizedExpression) e).getExpression(), cu, fileIndex, cuCache, depth + 1);
        }
        if (e instanceof InfixExpression && ((InfixExpression) e).getOperator() == InfixExpression.Operator.PLUS) {
            InfixExpression inf = (InfixExpression) e;
            StringBuilder sb = new StringBuilder();
            List<Expression> parts = new ArrayList<>();
            parts.add(inf.getLeftOperand()); parts.add(inf.getRightOperand());
            for (Object x : inf.extendedOperands()) parts.add((Expression) x);
            for (Expression p : parts) {
                String s = resolveStringConstant(p, cu, fileIndex, cuCache, depth + 1);
                if (s == null) return null;
                sb.append(s);
            }
            return sb.toString();
        }
        if (e instanceof SimpleName) {
            // 本类字段 → 沿 extends 链向上
            return findStringFieldInitializer(((SimpleName) e).getIdentifier(), cu, fileIndex, cuCache, depth + 1);
        }
        if (e instanceof QualifiedName) {
            // Other.CONST 或 a.b.Other.CONST：先定位 Other 的源文件，再在那里找字段
            QualifiedName qn = (QualifiedName) e;
            String owner = qn.getQualifier().getFullyQualifiedName();
            String simple = owner.contains(".") ? owner.substring(owner.lastIndexOf('.') + 1) : owner;
            Path f = pickFile(fileIndex, simple, owner);
            if (f == null) return null;
            CompilationUnit ocu = cuCache.computeIfAbsent(f.toString(), k -> parseQuiet(k));
            if (ocu == null) return null;
            return findStringFieldInitializer(qn.getName().getIdentifier(), ocu, fileIndex, cuCache, depth + 1);
        }
        return null;
    }

    /** 在 cu 及其 extends 链（最多 5 层）里找名为 fieldName 的字段，返回其可静态求值的字符串初始值。 */
    @SuppressWarnings("unchecked")
    private static String findStringFieldInitializer(String fieldName, CompilationUnit cu, Map<String, List<Path>> fileIndex,
                                                     Map<String, CompilationUnit> cuCache, int depth) {
        CompilationUnit cur = cu;
        java.util.Set<String> visited = new java.util.HashSet<>();
        for (int level = 0; level < 6 && cur != null; level++) {
            final Expression[] init = new Expression[1];
            final String want = fieldName;
            cur.accept(new ASTVisitor() {
                @Override public boolean visit(FieldDeclaration fd) {
                    if (init[0] != null) return false;
                    for (Object fr : fd.fragments()) {
                        VariableDeclarationFragment v = (VariableDeclarationFragment) fr;
                        if (v.getName().getIdentifier().equals(want) && v.getInitializer() != null) { init[0] = v.getInitializer(); return false; }
                    }
                    return true;
                }
            });
            if (init[0] != null) return resolveStringConstant(init[0], cur, fileIndex, cuCache, depth + 1);
            String sup = getSuperclassSimpleName(cur);
            if (sup == null || !visited.add(sup)) break;
            Path sf = pickFile(fileIndex, sup, null);
            if (sf == null) break;
            cur = cuCache.computeIfAbsent(sf.toString(), k -> parseQuiet(k));
        }
        return null;
    }


    // JUnit 5.11+ 允许测试方法和它的同名 @MethodSource provider 用参数个数区分重载
    // （比如 void testX(Character c) 配 static Stream<Arguments> testX()）。找"测试方法"
    // 本身时不能像找 provider 那样优先挑无参重载——那样会挑到 provider 自己头上，导致读不到
    // @MethodSource 注解。这里改成优先挑带 Test 系注解的那个重载。
    private static final Set<String> TEST_ANNOTATIONS = Set.of(
            "Test", "ParameterizedTest", "RepeatedTest", "TestFactory", "TestTemplate");

    @SuppressWarnings("unchecked")
    private static MethodDeclaration findTestMethodByName(CompilationUnit cu, String methodName) {
        List<MethodDeclaration> candidates = new ArrayList<>();
        cu.accept(new ASTVisitor() {
            @Override
            public boolean visit(MethodDeclaration node) {
                if (node.getName().getIdentifier().equals(methodName)) candidates.add(node);
                return true;
            }
        });
        if (candidates.size() == 1) return candidates.get(0);
        // #14: 同名重载消歧。这批样本的前提就是 MethodSource 参数化测试，所以优先级必须是
        //   @MethodSource > @ParameterizedTest > 其它 Test 系注解 > 第一个。
        // 之前"带任意 Test 注解即可"会在 `@Test void foo()` + `@ParameterizedTest @MethodSource void foo(int)`
        // 并存时挑中前者（commons-lang 里大量这种写法），导致读不到 @MethodSource。
        MethodDeclaration best = null; int bestRank = -1;
        for (MethodDeclaration c : candidates) {
            int rank = 0;
            for (Object o : c.modifiers()) {
                if (!(o instanceof Annotation)) continue;
                String n = ((Annotation) o).getTypeName().getFullyQualifiedName();
                if (n.contains(".")) n = n.substring(n.lastIndexOf('.') + 1);
                if ("MethodSource".equals(n)) rank = Math.max(rank, 3);
                else if ("ParameterizedTest".equals(n)) rank = Math.max(rank, 2);
                else if (TEST_ANNOTATIONS.contains(n)) rank = Math.max(rank, 1);
            }
            if (rank > bestRank) { bestRank = rank; best = c; }
        }
        return best != null ? best : (candidates.isEmpty() ? null : candidates.get(0));
    }

    private static MethodDeclaration findMethodByName(CompilationUnit cu, String methodName, MethodDeclaration exclude) {
        List<MethodDeclaration> candidates = new ArrayList<>();
        cu.accept(new ASTVisitor() {
            @Override
            public boolean visit(MethodDeclaration node) {
                if (node.getName().getIdentifier().equals(methodName)) candidates.add(node);
                return true;
            }
        });
        // ⑦: prefer the candidate declared in the anchor (test) method's own enclosing type, then its
        // enclosing types outward, before falling back to "anywhere in the file" — a file with several
        // nested classes each declaring their own `cases()` otherwise always resolves to the first.
        if (exclude != null) {
            List<ASTNode> scopes = new ArrayList<>();
            for (ASTNode p = exclude.getParent(); p != null; p = p.getParent()) {
                if (p instanceof AbstractTypeDeclaration) scopes.add(p);
            }
            for (ASTNode scope : scopes) {
                for (boolean zeroArg : new boolean[]{true, false}) {
                    for (MethodDeclaration c : candidates) {
                        if (c == exclude || c.getParent() != scope) continue;
                        if (zeroArg && !c.parameters().isEmpty()) continue;
                        return c;
                    }
                }
            }
        }
        for (MethodDeclaration c : candidates) {
            if (c != exclude && c.parameters().isEmpty()) return c;
        }
        for (MethodDeclaration c : candidates) {
            if (c != exclude) return c;
        }
        return null;
    }

    private static CompilationUnit parseQuiet(String filePath) {
        try {
            String source = new String(Files.readAllBytes(Paths.get(filePath)), StandardCharsets.UTF_8);
            ASTParser parser = ASTParser.newParser(AST.getJLSLatest());
            parser.setKind(ASTParser.K_COMPILATION_UNIT);
            parser.setResolveBindings(false);
            parser.setStatementsRecovery(true);
            Map<String, String> options = new HashMap<>();
            options.put(org.eclipse.jdt.core.JavaCore.COMPILER_SOURCE, "17");
            options.put(org.eclipse.jdt.core.JavaCore.COMPILER_COMPLIANCE, "17");
            parser.setCompilerOptions(options);
            parser.setUnitName(filePath);
            parser.setSource(source.toCharArray());
            return (CompilationUnit) parser.createAST(null);
        } catch (Exception e) {
            return null;
        }
    }

    // 磁盘缓存：project_root 目录本身的名字（项目名）作为缓存文件名，避免每次批量跑都要
    // 重新 Files.walk 一遍整个项目源码树。缓存格式是最简单的 "简单类名\t路径" 每行一条，
    // 没有用 JSON 库以保持这个独立小工具零额外依赖。
    private static final Path CACHE_DIR = Paths.get(System.getProperty("cognitive.cache.dir",
            "file_index_cache"   /* run_rq22.sh 用 -Dcognitive.cache.dir 指到中间产物目录 */));

    private static Map<String, List<Path>> buildFileIndex(Path root) {
        Path cacheFile = CACHE_DIR.resolve(root.getFileName().toString() + ".idx");
        Map<String, List<Path>> fromCache = readIndexCache(cacheFile);
        if (fromCache != null) return fromCache;

        Map<String, List<Path>> index = new HashMap<>();
        try {
            Files.walk(root)
                    .filter(p -> p.toString().endsWith(".java"))
                    .filter(p -> {
                        String s = p.toString();
                        return !s.contains("/target/") && !s.contains("/build/") && !s.contains("/AAA/") && !s.contains("/.git/");
                    })
                    .forEach(p -> {
                        String fn = p.getFileName().toString();
                        String simple = fn.substring(0, fn.length() - ".java".length());
                        index.computeIfAbsent(simple, k -> new ArrayList<>()).add(p);
                    });
        } catch (IOException e) {
            System.err.println("WARN: file index build failed for " + root + ": " + e.getMessage());
        }
        writeIndexCache(cacheFile, index);
        return index;
    }

    private static Map<String, List<Path>> readIndexCache(Path cacheFile) {
        if (!Files.isRegularFile(cacheFile)) return null;
        try {
            Map<String, List<Path>> index = new HashMap<>();
            for (String line : Files.readAllLines(cacheFile, StandardCharsets.UTF_8)) {
                int tab = line.indexOf('\t');
                if (tab < 0) continue;
                String simple = line.substring(0, tab);
                Path p = Paths.get(line.substring(tab + 1));
                index.computeIfAbsent(simple, k -> new ArrayList<>()).add(p);
            }
            System.err.println("INFO: loaded file index cache " + cacheFile + " (" + index.size() + " class names)");
            return index;
        } catch (IOException e) {
            return null;
        }
    }

    private static void writeIndexCache(Path cacheFile, Map<String, List<Path>> index) {
        try {
            Files.createDirectories(CACHE_DIR);
            try (BufferedWriter bw = Files.newBufferedWriter(cacheFile, StandardCharsets.UTF_8)) {
                for (Map.Entry<String, List<Path>> e : index.entrySet()) {
                    for (Path p : e.getValue()) {
                        bw.write(e.getKey() + "\t" + p);
                        bw.newLine();
                    }
                }
            }
        } catch (IOException e) {
            System.err.println("WARN: could not write file index cache " + cacheFile + ": " + e.getMessage());
        }
    }

    // ---------------- CSV ----------------

    private static List<String[]> readCsv(String path) throws IOException {
        List<String[]> rows = new ArrayList<>();
        try (BufferedReader br = new BufferedReader(new InputStreamReader(new FileInputStream(path), StandardCharsets.UTF_8))) {
            String line;
            while ((line = br.readLine()) != null) rows.add(line.split(",", -1));
        }
        return rows;
    }

    private static void writeCsv(String path, List<String[]> rows) throws IOException {
        try (BufferedWriter bw = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(path), StandardCharsets.UTF_8))) {
            for (String[] row : rows) {
                StringBuilder sb = new StringBuilder();
                for (int i = 0; i < row.length; i++) {
                    if (i > 0) sb.append(',');
                    String v = row[i] == null ? "" : row[i];
                    if (v.contains(",") || v.contains("\"") || v.contains("\n")) v = "\"" + v.replace("\"", "\"\"") + "\"";
                    sb.append(v);
                }
                bw.write(sb.toString());
                bw.newLine();
            }
        }
    }

    private static int indexOf(String[] header, String name) {
        for (int i = 0; i < header.length; i++) if (header[i].equals(name)) return i;
        throw new IllegalArgumentException("column not found: " + name);
    }

    private static String[] append(String[] row, String... extra) {
        String[] out = Arrays.copyOf(row, row.length + extra.length);
        System.arraycopy(extra, 0, out, row.length, extra.length);
        return out;
    }
}
