import org.eclipse.jdt.core.dom.*;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/**
 * MethodSource 的 Construction（Literal / Dynamic）+ Dependency（L0-L4）分类，纯语法 AST，
 * 复用 ProviderCognitiveComplexity.java 里已经验证过的 provider 定位逻辑（测试方法优先挑带
 * Test 系注解的重载、@MethodSource 值提取、裸名先本类后父类链的查找）。
 *
 * Construction 定义（口径 A，2026-09-15）：见 isLiteralMethod() 上方的注释——"参数集在编译期完全确定"
 *   判 Literal；有控制流 / 变换 / helper 委托 / 运行环境依赖判 Dynamic。CC=0 不等于 Literal：
 *   纯委托 `return helper()` 的 CC 也是 0 但这里是 Dynamic。
 *
 * Dependency 定义（L0-L4，取 provider 自身位置 + 它直接调用的 helper 里"最远"的一级）：
 *   L0 Method Local  — provider 在测试类自己文件里能找到，且不调用任何能定位到的项目内方法
 *   L1 Class Helper  — 调用的 helper 跟 provider 声明在同一个类里
 *   L2 Inheritance   — provider 本身是沿着 extends 链找到的（不在测试类自己文件里），
 *                       或者它调用的某个 helper是沿着 provider 所在类的 extends 链找到的
 *   L3 Package Helper— helper 在不同类，但跟 provider 同包
 *   L4 Cross-Package — helper 跟 provider 不同包
 *   只统计"能明确定位到项目源码里的调用"；无法定位声明类的调用（比如静态 import 进来的
 *   方法、或者项目文件索引里找不到的类名）不计入 helper，不会拉高 Dependency 等级——
 *   宁可低估也不瞎猜，这些情况在 note 里能看到 UNRESOLVED_CALLS 计数，人工核对时留意。
 */
public class ConstructionDependencyClassifier {

    private static final Map<String, Map<String, List<Path>>> fileIndexCache = new HashMap<>();
    private static final Map<String, String> packageCache = new HashMap<>(); // file -> package name

    private static final Set<String> LITERAL_WRAPPER_METHODS = Set.of(
            "of", "asList", "singletonList", "singleton", "emptyList", "unmodifiableList", "copyOf");

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("usage: ConstructionDependencyClassifier <input.csv> <output.csv>");
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
        out.add(append(header, "construction", "dependency", "n_providers_resolved", "note",
                "construction_reason", "dependency_reason", "hits_production_src", "artifacts",
                "n_params", "n_params_effective", "n_sets", "n_sets_status", "n_sets_fail_reason"));

        Map<String, CompilationUnit> cuCache = new HashMap<>();

        for (int i = 1; i < rows.size(); i++) {
            if (i % 25 == 0) System.err.println("progress: " + i + "/" + (rows.size() - 1));
            String[] row = rows.get(i);
            String project = row[idxProject];
            String projectRoot = row[idxProjectRoot];
            String testName = row[idxTestName];
            String testFile = row[idxTestFile];

            if (testFile == null || testFile.isBlank()) {
                out.add(append(row, "", "", "0", "TEST_FILE_UNKNOWN"));
                continue;
            }
            try {
                Map<String, List<Path>> fileIndex = fileIndexCache.computeIfAbsent(projectRoot,
                        r -> buildFileIndex(Paths.get(r)));

                CompilationUnit testCu = cuCache.computeIfAbsent(testFile, ConstructionDependencyClassifier::parseQuiet);
                if (testCu == null) {
                    out.add(append(row, "", "", "0", "TEST_FILE_PARSE_ERROR"));
                    continue;
                }
                MethodDeclaration testMd = findTestMethodByName(testCu, testName);
                if (testMd == null) {
                    out.add(append(row, "", "", "0", "TEST_METHOD_NOT_FOUND"));
                    continue;
                }

                List<String> providerRefs = extractMethodSourceValues(testMd, testName, testCu, fileIndex, cuCache);
                ArtifactWalker walker0 = new ArtifactWalker(fileIndex, cuCache, ConstructionDependencyClassifier::parseQuiet, testFile, testCu, testMd);
                List<ExtraProviders.Unit> extra = ExtraProviders.collect(testMd, testCu, testFile, walker0);
                if (providerRefs.isEmpty() && extra.isEmpty()) {
                    out.add(append(row, "", "", "0", "NO_METHODSOURCE_ANNOTATION_VALUE"));
                    continue;
                }

                String worstConstruction = "Literal"; // Dynamic 一旦出现就整体判 Dynamic
                int worstLevel = 0; // 0..4，取所有 provider 里最大的
                int resolved = 0;
                int unresolvedCallsTotal = 0;
                List<String> notes = new ArrayList<>();
                List<String> cReasons = new ArrayList<>(), dReasons = new ArrayList<>(), artifacts = new ArrayList<>();
                boolean hitsProd = false;
                Integer nSets = 0; boolean setsExact = true; List<String> setsWhy = new ArrayList<>(); List<String> setsStatus = new ArrayList<>();
                ArtifactWalker walker = walker0;
                for (ExtraProviders.Unit u : extra) {
                    if (u.note != null) { notes.add(u.note); continue; }
                    resolved++;
                    ArtifactWalker.Result ar; Integer c;
                    if (u.method != null) { ar = walker.analyze(u.method, u.file, u.viaInheritance); c = walker.countSets(u.method, u.file); }
                    else { ar = walker.analyzeField(u.field, u.viaInheritance); c = walker.countSetsOfField(u.field); }
                    if (!ar.isStatic) { worstConstruction = "Dynamic"; cReasons.add(ar.dynamicReason); }
                    worstLevel = Math.max(worstLevel, ar.level);
                    if (!ar.levelReason.isEmpty()) dReasons.add(ar.levelReason);
                    hitsProd |= ar.hitsProduction; unresolvedCallsTotal += ar.unresolved; artifacts.addAll(ar.artifacts);
                    if (c == null) { setsExact = false; setsWhy.add(walker.lastCountFailReason); setsStatus.add(walker.lastCountFailStatus); } else nSets += c;
                }

                for (String ref : providerRefs) {
                    if (ref.startsWith(UNRESOLVED_VALUE_PREFIX)) {
                        // #7: 注解有值但语法上求不出来（非常量表达式等）。明确报出来，不落到
                        // "同名方法"兜底，避免把测试方法自己当 provider 算出一个错值还标 OK。
                        notes.add("UNRESOLVED_ANNOTATION_VALUE:" + ref.substring(UNRESOLVED_VALUE_PREFIX.length(), ref.length() - 1));
                        continue;
                    }
                    ProviderLoc loc = resolveProvider(ref, testCu, testFile, fileIndex, cuCache, testMd);
                    if (loc == null) {
                        // @MethodSource 指向 JDK/第三方（如 java.util.Locale#getAvailableLocales）：provider 不是项目代码，
                        // 无源码可算——这不是"找不到"，是"在项目之外"，标签要区分开。
                        notes.add((isJdkOrExternalRef(ref) ? "PROVIDER_EXTERNAL:" : "PROVIDER_NOT_FOUND:") + ref);
                        continue;
                    }
                    resolved++;
                    // 2026-09-16 口径：源码侧传递式 artifact 遍历（dependency）+ 静态可确定性（construction），见 ArtifactWalker
                    ArtifactWalker.Result ar = walker.analyze(loc.method, loc.file, loc.viaSuperclass);
                    if (!ar.isStatic) { worstConstruction = "Dynamic"; cReasons.add(ar.dynamicReason); }
                    worstLevel = Math.max(worstLevel, ar.level);
                    if (!ar.levelReason.isEmpty()) dReasons.add(ar.levelReason);
                    hitsProd |= ar.hitsProduction;
                    unresolvedCallsTotal += ar.unresolved;
                    artifacts.addAll(ar.artifacts);
                    Integer c = walker.countSets(loc.method, loc.file);
                    if (c == null) { setsExact = false; setsWhy.add(walker.lastCountFailReason); setsStatus.add(walker.lastCountFailStatus); } else nSets += c;
                }
                // arity：测试方法形参个数（原始 / 去掉 JUnit 注入的 TestInfo、TestReporter、RepetitionInfo）
                int nParams = testMd.parameters().size(), nEff = 0;
                for (Object p : testMd.parameters()) {
                    String t = ((SingleVariableDeclaration) p).getType().toString();
                    if (!(t.endsWith("TestInfo") || t.endsWith("TestReporter") || t.endsWith("RepetitionInfo"))) nEff++;
                }

                if (resolved == 0) {
                    String note = notes.isEmpty() ? "PROVIDER_NOT_FOUND" : String.join(";", notes);
                    out.add(append(row, "", "", "0", note));
                    continue;
                }
                String note = String.join(";", notes);
                if (unresolvedCallsTotal > 0) note = (note.isEmpty() ? "" : note + ";") + "UNRESOLVED_CALLS:" + unresolvedCallsTotal;
                out.add(append(row, worstConstruction, "L" + worstLevel, String.valueOf(resolved), note,
                        String.join(" | ", cReasons), String.join(" | ", dReasons), String.valueOf(hitsProd),
                        String.join(" | ", artifacts),
                        String.valueOf(nParams), String.valueOf(nEff), setsExact ? String.valueOf(nSets) : "", setsExact ? "EXACT" : worstStatus(setsStatus), String.join(" | ", setsWhy)));
            } catch (Exception e) {
                out.add(append(row, "", "", "0", "ERROR:" + e.getClass().getSimpleName() + ":" +
                        String.valueOf(e.getMessage()).replace(",", ";").replace("\n", " ")));
            }
        }

        writeCsv(args[1], out);
        System.err.println("Done. " + (out.size() - 1) + " rows -> " + args[1]);
    }

    // ================= Construction =================

    @SuppressWarnings("unchecked")
    // ================= Construction（口径 A，2026-09-15 定稿）=================
    // Literal = provider 产出的参数集在编译期就完全确定：没有控制流，除"装箱/装配/值对象构造"以外没有
    // 任何调用，每个值都不依赖变量或运行环境。允许：
    //   - 字面量、-1、Foo.class、字面量数组、括号、类型转换、字面量之间的 + / 算术
    //   - 常量引用：全大写静态字段（Integer.MAX_VALUE）、Type.MEMBER 形式的静态成员（枚举 Color.RED、
    //     Locale.ENGLISH、StandardCharsets.UTF_8）、本类 static final 且初始化为字面量的字段、
    //     本方法里初始化为字面量的局部变量
    //   - new ValueObject(字面量…)（无匿名体）、new ArrayList<>() 之类的空容器
    //   - 装箱/装配白名单调用（Stream.of / List.of / Arrays.asList / Arguments.of / arguments / named /
    //     Map.entry / Pair.of / builder().add(..).build() / list.add(..) / stream()），参数全部字面量
    //   - 多条语句：局部变量声明、对本地容器的 add/put/addAll、最后 return 本地容器或装箱表达式
    //   - lambda 值：表达式体且为字面量（() -> null）；方法引用一律 Dynamic（指向别处的代码）
    // 其余（if/for/switch/try、map/filter 等变换、helper 委托、IO、字段/参数/外部变量引用、三目）→ Dynamic。
    private static final Set<String> BOXING_METHODS = Set.of(
            "of", "asList", "singletonList", "singleton", "emptyList", "emptySet", "emptyMap", "unmodifiableList",
            "copyOf", "arguments", "argumentSet", "named", "entry", "stream", "builder", "build", "add", "addAll",
            "put", "putAll", "set", "toArray", "toList", "boxed", "tuple", "pair", "listOf", "setOf", "mapOf");
    private static final Set<String> CONTAINER_MUTATORS = Set.of("add", "addAll", "put", "putAll", "set", "offer", "push", "append");
    private static final Set<String> LOCAL_TERMINALS = Set.of("stream", "toArray", "build", "boxed", "toList");
    private static final Set<String> DATA_CONTAINER_TYPES = Set.of(
            "ArrayList", "LinkedList", "HashMap", "LinkedHashMap", "TreeMap", "HashSet", "LinkedHashSet", "TreeSet",
            "ArrayDeque", "Vector", "Stack");

    private static boolean isLiteralMethod(MethodDeclaration md) {
        Block body = md.getBody();
        if (body == null) return false;
        Set<String> literalLocals = new HashSet<>();
        Set<String> constFields = literalStaticFinalFields(md);
        boolean sawReturn = false;
        for (Object o : body.statements()) {
            Statement st = (Statement) o;
            if (st instanceof VariableDeclarationStatement) {
                for (Object f : ((VariableDeclarationStatement) st).fragments()) {
                    VariableDeclarationFragment frag = (VariableDeclarationFragment) f;
                    Expression init = frag.getInitializer();
                    if (init == null || !isLiteralExpression(init, literalLocals, constFields)) return false;
                    literalLocals.add(frag.getName().getIdentifier());
                }
            } else if (st instanceof ExpressionStatement) {
                Expression e = ((ExpressionStatement) st).getExpression();
                if (e instanceof MethodInvocation) {
                    // A2: only a *single* `local.add/put/addAll(...)` statement on a local data holder;
                    // chained calls (builder.add(..).add(..)) are handled by the general rule → Dynamic.
                    MethodInvocation mi = (MethodInvocation) e;
                    if (!(mi.getExpression() instanceof SimpleName)
                            || !literalLocals.contains(((SimpleName) mi.getExpression()).getIdentifier())
                            || !CONTAINER_MUTATORS.contains(mi.getName().getIdentifier())) return false;
                    for (Object a : mi.arguments()) {
                        if (!isLiteralExpression((Expression) a, literalLocals, constFields)) return false;
                    }
                } else if (e instanceof Assignment) {
                    Assignment a = (Assignment) e;
                    if (!(a.getLeftHandSide() instanceof SimpleName)) return false;
                    if (!isLiteralExpression(a.getRightHandSide(), literalLocals, constFields)) return false;
                    literalLocals.add(((SimpleName) a.getLeftHandSide()).getIdentifier());
                } else {
                    return false;
                }
            } else if (st instanceof ReturnStatement) {
                Expression r = ((ReturnStatement) st).getExpression();
                if (r == null || !isLiteralExpression(r, literalLocals, constFields)) return false;
                sawReturn = true;
            } else {
                return false; // if / for / while / switch / try / throw / enhanced-for / do / labeled ...
            }
        }
        return sawReturn;
    }

    /** Names of `static final` fields of the enclosing type whose initializer is itself literal-ish. */
    private static Set<String> literalStaticFinalFields(MethodDeclaration md) {
        Set<String> out = new HashSet<>();
        ASTNode p = md.getParent();
        if (!(p instanceof AbstractTypeDeclaration)) return out;
        for (Object o : ((AbstractTypeDeclaration) p).bodyDeclarations()) {
            if (!(o instanceof FieldDeclaration)) continue;
            FieldDeclaration fd = (FieldDeclaration) o;
            if (!Modifier.isStatic(fd.getModifiers()) || !Modifier.isFinal(fd.getModifiers())) continue;
            for (Object f : fd.fragments()) {
                VariableDeclarationFragment frag = (VariableDeclarationFragment) f;
                Expression init = frag.getInitializer();
                if (init != null && isLiteralExpression(init, Set.of(), Set.of())) out.add(frag.getName().getIdentifier());
            }
        }
        return out;
    }

    @SuppressWarnings("unchecked")
    private static boolean isLiteralExpression(Expression expr, Set<String> literalLocals, Set<String> constFields) {
        if (expr == null) return false;
        if (expr instanceof NumberLiteral || expr instanceof StringLiteral || expr instanceof BooleanLiteral
                || expr instanceof CharacterLiteral || expr instanceof NullLiteral || expr instanceof TypeLiteral
                || expr instanceof TextBlock) {
            return true;
        }
        if (expr instanceof PrefixExpression) {
            PrefixExpression pe = (PrefixExpression) expr;
            return (pe.getOperator() == PrefixExpression.Operator.MINUS || pe.getOperator() == PrefixExpression.Operator.PLUS
                    || pe.getOperator() == PrefixExpression.Operator.NOT)
                    && isLiteralExpression(pe.getOperand(), literalLocals, constFields);
        }
        if (expr instanceof InfixExpression) {
            InfixExpression ie = (InfixExpression) expr;
            if (!isLiteralExpression(ie.getLeftOperand(), literalLocals, constFields)
                    || !isLiteralExpression(ie.getRightOperand(), literalLocals, constFields)) return false;
            for (Object o : ie.extendedOperands()) {
                if (!isLiteralExpression((Expression) o, literalLocals, constFields)) return false;
            }
            return true;
        }
        if (expr instanceof CastExpression) {
            return isLiteralExpression(((CastExpression) expr).getExpression(), literalLocals, constFields);
        }
        if (expr instanceof ParenthesizedExpression) {
            return isLiteralExpression(((ParenthesizedExpression) expr).getExpression(), literalLocals, constFields);
        }
        if (expr instanceof SimpleName) {
            String id = ((SimpleName) expr).getIdentifier();
            return literalLocals.contains(id) || constFields.contains(id) || isConstantStyleName(id);
        }
        if (expr instanceof QualifiedName) {
            QualifiedName qn = (QualifiedName) expr;
            String name = qn.getName().getIdentifier();
            String qualifierLast = qn.getQualifier() instanceof QualifiedName
                    ? ((QualifiedName) qn.getQualifier()).getName().getIdentifier() : qn.getQualifier().toString();
            // Type.MEMBER（枚举常量 / 静态常量）：限定符以大写开头视为类型名；变量.字段 → Dynamic
            return isConstantStyleName(name) || Character.isUpperCase(qualifierLast.charAt(0));
        }
        if (expr instanceof FieldAccess) {
            FieldAccess fa = (FieldAccess) expr;
            if (fa.getExpression() instanceof ThisExpression) return constFields.contains(fa.getName().getIdentifier());
            return isConstantStyleName(fa.getName().getIdentifier());
        }
        if (expr instanceof ArrayInitializer) {
            for (Object o : ((ArrayInitializer) expr).expressions()) {
                if (!isLiteralExpression((Expression) o, literalLocals, constFields)) return false;
            }
            return true;
        }
        if (expr instanceof ArrayCreation) {
            ArrayCreation ac = (ArrayCreation) expr;
            if (ac.getInitializer() != null) return isLiteralExpression(ac.getInitializer(), literalLocals, constFields);
            for (Object d : ac.dimensions()) {
                if (!isLiteralExpression((Expression) d, literalLocals, constFields)) return false;
            }
            return true;
        }
        if (expr instanceof ClassInstanceCreation) {
            ClassInstanceCreation cic = (ClassInstanceCreation) expr;
            if (cic.getAnonymousClassDeclaration() != null) return false;
            for (Object o : cic.arguments()) {
                if (!isLiteralExpression((Expression) o, literalLocals, constFields)) return false;
            }
            return true; // 值对象 / 空容器：由字面量构造
        }
        if (expr instanceof MethodInvocation) {
            MethodInvocation mi = (MethodInvocation) expr;
            String name = mi.getName().getIdentifier();
            if (!BOXING_METHODS.contains(name)) return false;
            Expression recv = mi.getExpression();
            // A2（2026-09-16）：装箱白名单只对"静态工厂"形式生效——接收者是类型名（Stream.of / Arrays.asList /
            // Arguments.of / Named.of / Map.entry）或没有接收者（静态导入的 arguments(...)）；另外允许对字面量
            // 局部容器的单层终结调用 list.stream() / list.toArray() / builder.build()。接收者是对象的链式调用
            // （new ImmutableMap.Builder<>().putAll(..).put(..).build()、x.stream().map(..)）→ Dynamic：
            // 那是在"装配"复合对象，不是现成的数据。
            if (recv != null) {
                boolean recvOk;
                if (recv instanceof SimpleName) {
                    String id = ((SimpleName) recv).getIdentifier();
                    recvOk = Character.isUpperCase(id.charAt(0))
                            || (literalLocals.contains(id) && LOCAL_TERMINALS.contains(name));
                } else if (recv instanceof QualifiedName) {
                    recvOk = Character.isUpperCase(((QualifiedName) recv).getName().getIdentifier().charAt(0)); // java.util.List.of
                } else {
                    recvOk = false; // 链式 / 表达式接收者
                }
                if (!recvOk) return false;
            }
            for (Object o : mi.arguments()) {
                if (!isLiteralExpression((Expression) o, literalLocals, constFields)) return false;
            }
            return true;
        }
        if (expr instanceof LambdaExpression) {
            LambdaExpression le = (LambdaExpression) expr;
            return le.getBody() instanceof Expression && isLiteralExpression((Expression) le.getBody(), literalLocals, constFields);
        }
        // MethodReference / ConditionalExpression / SuperMethodInvocation / ThisExpression / ... → Dynamic
        return false;
    }

    // JDK 里少数几个不遵守 ALL_CAPS 命名习惯、但本质就是字面常量的字段，特判掉。
    private static final Set<String> CONSTANT_NAME_EXCEPTIONS = Set.of("NaN");

    private static boolean isConstantStyleName(String identifier) {
        if (CONSTANT_NAME_EXCEPTIONS.contains(identifier)) return true;
        if (identifier.isEmpty() || !Character.isUpperCase(identifier.charAt(0))) return false;
        for (int i = 0; i < identifier.length(); i++) {
            char c = identifier.charAt(i);
            if (Character.isLetter(c) && Character.isLowerCase(c)) return false;
        }
        return true;
    }

    // ================= Dependency =================

    private static final class DependencyResult {
        int level;
        int unresolvedCalls;
    }

    @SuppressWarnings("unchecked")
    private static DependencyResult classifyDependency(MethodDeclaration providerMd, String providerFile,
                                                         Map<String, List<Path>> fileIndex,
                                                         Map<String, CompilationUnit> cuCache) throws IOException {
        DependencyResult result = new DependencyResult();
        String providerPackage = packageOf(providerFile, cuCache);
        CompilationUnit providerCu = cuCache.get(providerFile);
        String providerClassSimple = enclosingTypeSimpleName(providerMd);

        List<MethodInvocation> calls = new ArrayList<>();
        providerMd.accept(new ASTVisitor() {
            @Override
            public boolean visit(MethodInvocation node) { calls.add(node); return true; }
        });

        for (MethodInvocation mi : calls) {
            String methodName = mi.getName().getIdentifier();
            Expression qualifier = mi.getExpression();

            if (qualifier instanceof SimpleName && Character.isUpperCase(((SimpleName) qualifier).getIdentifier().charAt(0))) {
                // 形如 Type.method(...) 的静态调用
                String typeSimple = ((SimpleName) qualifier).getIdentifier();
                Path file = pickFile(fileIndex, typeSimple, null);
                if (file == null) { result.unresolvedCalls++; continue; } // 大概率是 JDK/第三方类，跳过
                if (file.toString().equals(providerFile)) {
                    result.level = Math.max(result.level, 1); // 同文件里另一个顶层/嵌套类，按 L1 处理
                    continue;
                }
                String calleePackage = packageOf(file.toString(), cuCache);
                result.level = Math.max(result.level, Objects.equals(calleePackage, providerPackage) ? 3 : 4);
            } else if (qualifier == null) {
                // 裸调用：本类 -> 父类链 -> 放弃（可能是静态 import，不计入 helper）
                if (findMethodByNameInType(providerCu, providerClassSimple, methodName) != null) {
                    result.level = Math.max(result.level, 1);
                    continue;
                }
                String superSimple = getSuperclassSimpleNameFor(providerCu, providerClassSimple);
                boolean foundInSuper = false;
                Set<String> visited = new HashSet<>();
                CompilationUnit cur = providerCu;
                String curType = providerClassSimple;
                for (int depth = 0; depth < 5 && superSimple != null && visited.add(superSimple); depth++) {
                    Path superFile = pickFile(fileIndex, superSimple, null);
                    if (superFile == null) break;
                    CompilationUnit superCu = cuCache.computeIfAbsent(superFile.toString(), ConstructionDependencyClassifier::parseQuiet);
                    if (superCu == null) break;
                    if (findMethodByNameInType(superCu, superSimple, methodName) != null) {
                        result.level = Math.max(result.level, 2);
                        foundInSuper = true;
                        break;
                    }
                    cur = superCu; curType = superSimple;
                    superSimple = getSuperclassSimpleNameFor(cur, curType);
                }
                if (!foundInSuper) result.unresolvedCalls++; // 静态 import 或者本来就没找到，不计
            }
            // qualifier 是 this/字段/表达式链（比如 stream 方法调用本身）不算跨类依赖，跳过
        }
        return result;
    }

    @SuppressWarnings("unchecked")
    private static MethodDeclaration findMethodByNameInType(CompilationUnit cu, String typeSimpleName, String methodName) {
        if (cu == null) return null;
        final MethodDeclaration[] found = new MethodDeclaration[1];
        cu.accept(new ASTVisitor() {
            @Override
            public boolean visit(MethodDeclaration node) {
                if (found[0] != null) return false;
                if (node.getName().getIdentifier().equals(methodName)) found[0] = node;
                return true;
            }
        });
        return found[0];
    }

    @SuppressWarnings("unchecked")
    private static String getSuperclassSimpleNameFor(CompilationUnit cu, String typeSimpleName) {
        for (Object o : cu.types()) {
            if (o instanceof TypeDeclaration && ((TypeDeclaration) o).getName().getIdentifier().equals(typeSimpleName)) {
                Type sup = ((TypeDeclaration) o).getSuperclassType();
                if (sup == null) return null;
                String name = sup.toString();
                int lt = name.indexOf('<');
                if (lt >= 0) name = name.substring(0, lt);
                int dot = name.lastIndexOf('.');
                return dot >= 0 ? name.substring(dot + 1) : name;
            }
        }
        return null;
    }

    private static String enclosingTypeSimpleName(MethodDeclaration md) {
        ASTNode parent = md.getParent();
        while (parent != null && !(parent instanceof TypeDeclaration)) parent = parent.getParent();
        return parent == null ? "" : ((TypeDeclaration) parent).getName().getIdentifier();
    }

    private static String packageOf(String filePath, Map<String, CompilationUnit> cuCache) {
        return packageCache.computeIfAbsent(filePath, fp -> {
            CompilationUnit cu = cuCache.computeIfAbsent(fp, ConstructionDependencyClassifier::parseQuiet);
            if (cu == null || cu.getPackage() == null) return "";
            return cu.getPackage().getName().getFullyQualifiedName();
        });
    }

    // ================= Provider 定位（跟 ProviderCognitiveComplexity 一致） =================

    private static final class ProviderLoc {
        final MethodDeclaration method;
        final String file;
        final boolean viaSuperclass;
        ProviderLoc(MethodDeclaration m, String f, boolean viaSuperclass) { this.method = m; this.file = f; this.viaSuperclass = viaSuperclass; }
    }

    private static ProviderLoc resolveProvider(String ref, CompilationUnit testCu, String testFile,
                                                Map<String, List<Path>> fileIndex,
                                                Map<String, CompilationUnit> cuCache, MethodDeclaration testMd) throws IOException {
        String className = null;
        String methodName = ref;
        if (ref.contains("#")) {
            String[] parts = ref.split("#", 2);
            className = parts[0];
            methodName = parts[1];
        }
        if (methodName.indexOf('(') >= 0) methodName = methodName.substring(0, methodName.indexOf('('));

        if (className != null) {
            String simple = className.contains(".") ? className.substring(className.lastIndexOf('.') + 1) : className;
            Path file = pickFile(fileIndex, simple, className);
            if (file == null) return null;
            CompilationUnit cu = cuCache.computeIfAbsent(file.toString(), ConstructionDependencyClassifier::parseQuiet);
            if (cu == null) return null;
            MethodDeclaration md = findMethodByName(cu, methodName, null);
            return md == null ? null : new ProviderLoc(md, file.toString(), false);
        }

        MethodDeclaration local = findMethodByName(testCu, methodName, testMd);
        if (local != null) return new ProviderLoc(local, testFile, false);

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
                CompilationUnit superCu = cuCache.computeIfAbsent(superFile.toString(), ConstructionDependencyClassifier::parseQuiet);
                if (superCu == null) continue;
                expanded++;
                MethodDeclaration md = findMethodByName(superCu, methodName, null);
                if (md != null) return new ProviderLoc(md, superFile.toString(), true);
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
                CompilationUnit cu = cuCache.computeIfAbsent(f.toString(), ConstructionDependencyClassifier::parseQuiet);
                if (cu == null) continue;
                MethodDeclaration md = findMethodByName(cu, methodName, null);
                if (md != null) return new ProviderLoc(md, f.toString(), true);
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
                int lt = name.indexOf('<');
                if (lt >= 0) name = name.substring(0, lt);
                int dot = name.lastIndexOf('.');
                return dot >= 0 ? name.substring(dot + 1) : name;
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
        for (MethodDeclaration c : candidates) if (c != exclude && c.parameters().isEmpty()) return c;
        for (MethodDeclaration c : candidates) if (c != exclude) return c;
        return null;
    }

    static CompilationUnit parseQuiet(String filePath) {
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

    private static final Path CACHE_DIR = Paths.get(System.getProperty("cognitive.cache.dir",
            "file_index_cache"   /* run_rq22.sh 用 -Dcognitive.cache.dir 指到中间产物目录 */));

    /** 给 ValueSourceAnalyzer 复用的文件索引入口（带磁盘缓存）。 */
    static Map<String, List<Path>> fileIndexFor(Path root) { return buildFileIndex(root); }

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
                index.computeIfAbsent(line.substring(0, tab), k -> new ArrayList<>()).add(Paths.get(line.substring(tab + 1)));
            }
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
                    for (Path p : e.getValue()) { bw.write(e.getKey() + "\t" + p); bw.newLine(); }
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

    /** 多 provider 时取"最差"的状态：UNRESOLVED_SOURCE > RUNTIME_DEPENDENT > STATIC_UNSUPPORTED。 */
    private static String worstStatus(List<String> st) {
        if (st.contains("UNRESOLVED_SOURCE")) return "UNRESOLVED_SOURCE";
        if (st.contains("RUNTIME_DEPENDENT")) return "RUNTIME_DEPENDENT";
        if (st.contains("STATIC_UNSUPPORTED")) return "STATIC_UNSUPPORTED";
        return st.isEmpty() ? "STATIC_UNSUPPORTED" : st.get(0);
    }

    private static String[] append(String[] row, String... extra) {
        String[] out = Arrays.copyOf(row, row.length + extra.length);
        System.arraycopy(extra, 0, out, row.length, extra.length);
        return out;
    }
}
