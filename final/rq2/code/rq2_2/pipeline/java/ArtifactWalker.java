import org.eclipse.jdt.core.dom.*;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.function.Function;

/**
 * 源码侧（无 binding，语法 + 文件索引）的 provider 分析，2026-09-16 定稿口径：
 *
 * Dependency：从 provider 出发，沿着"参数构造相关的 test-code 依赖"一直追——方法调用、字段引用（含字段初始化器）、
 *   构造、方法引用（仅 provider 流水线里调用的）、Type.class——直到 production / JDK 边界为止；在走过的全部 test-code
 *   artifact 里取离测试类最远的等级（同最外层类 L1 → 祖先 L2 → 同包 L3 → 跨包 L4）。production 类型的引用只标
 *   hitsProduction，不进等级。
 *
 * Construction：最终参数值是否"静态可确定、不需要执行生成/变换/运行时逻辑就能得到"。literal / 枚举 / class token /
 *   static final 常量 / 显式数组 / List.of / Arrays.asList / Arguments.of / new ValueObject(literal…) / 简单拼接算术 /
 *   由上述值构成的字段 / 多条显式 add(...) → Literal。if/for/switch、map/filter/flatMap/generate、helper 生成
 *   （helper 体按同样规则递归评估）、builder/配置突变（对象上的链式调用）、IO、环境依赖、random、反射、块体 lambda /
 *   方法引用（可执行行为）、从 production/test API 动态取得对象、字段初始化器本身是动态逻辑 → Dynamic。
 */
public class ArtifactWalker {

    // ---------- 结果 ----------
    public static class Result {
        public boolean isStatic = true;
        public String dynamicReason = "";
        public int level = 0;                 // 0..4 —— 只由 test-code artifact 决定
        public String levelReason = "";
        public boolean hitsProduction = false;
        public int visited = 0;
        public int unresolved = 0;
        public Set<String> artifacts = new LinkedHashSet<>();
    }

    // ---------- 上下文 ----------
    private final Map<String, List<Path>> fileIndex;
    private final Map<String, CompilationUnit> cuCache;
    private final Function<String, CompilationUnit> parser;
    private final String testFile;
    private final String testOutermost;       // 测试类最外层类简单名
    private final String testPackage;
    private final Set<String> testAncestors;  // 测试类祖先（父类链 + 接口）的简单名
    private final String testDeclaringType;   // 测试方法所在的（可能是嵌套的）类型简单名

    private static final int MAX_VISITS = 400;
    private boolean inAncestorLookup = false;
    private static final Set<String> BOXING_STATIC_FACTORIES = Set.of(
            "of", "asList", "singletonList", "singleton", "emptyList", "emptySet", "emptyMap", "unmodifiableList",
            "copyOf", "arguments", "argumentSet", "named", "entry", "listOf", "setOf", "mapOf", "tuple", "pair");
    private static final Set<String> CONTAINER_MUTATORS = Set.of("add", "addAll", "put", "putAll", "set", "offer", "push", "append");
    private static final Set<String> LOCAL_TERMINALS = Set.of("stream", "toArray", "build", "boxed", "toList");
    private static final Set<String> DATA_CTX_CALLS = Set.of(
            "of", "arguments", "argumentSet", "asList", "add", "addAll", "put", "putAll", "set", "singletonList",
            "singleton", "listOf", "setOf", "mapOf", "build", "named", "withArgs", "with", "append", "offer", "push");

    public ArtifactWalker(Map<String, List<Path>> fileIndex, Map<String, CompilationUnit> cuCache,
                          Function<String, CompilationUnit> parser, String testFile, CompilationUnit testCu,
                          MethodDeclaration testMd) {
        this.fileIndex = fileIndex;
        this.cuCache = cuCache;
        this.parser = parser;
        this.testFile = testFile;
        this.testPackage = testCu.getPackage() != null ? testCu.getPackage().getName().getFullyQualifiedName() : "";
        AbstractTypeDeclaration outer = null;
        for (ASTNode p = testMd; p != null; p = p.getParent()) if (p instanceof AbstractTypeDeclaration) outer = (AbstractTypeDeclaration) p;
        this.testOutermost = outer != null ? outer.getName().getIdentifier() : "";
        AbstractTypeDeclaration td = enclosingType(testMd);
        this.testDeclaringType = td != null ? td.getName().getIdentifier() : "";
        this.testAncestors = collectAncestors(td, testCu, testFile);
    }

    // =====================================================================================
    // Dependency：传递式 artifact 遍历
    // =====================================================================================
    private static final class Task {
        final ASTNode node; final CompilationUnit cu; final String file; final AbstractTypeDeclaration type; final String label;
        Task(ASTNode node, CompilationUnit cu, String file, AbstractTypeDeclaration type, String label) {
            this.node = node; this.cu = cu; this.file = file; this.type = type; this.label = label;
        }
    }

    public Result analyze(MethodDeclaration providerMd, String providerFile, boolean providerViaInheritance) {
        Result r = new Result();
        CompilationUnit providerCu = cuCache.computeIfAbsent(providerFile, parser);
        AbstractTypeDeclaration providerType = enclosingType(providerMd);
        // provider 自己的位置：裸名靠继承（向上父类/接口、向下子类 #8）解析到的 → L2；否则按位置
        if (providerViaInheritance) {
            r.level = 2; r.levelReason = "provider_via_inheritance(L2)";
            r.artifacts.add("provider:" + providerType.getName().getIdentifier() + "." + providerMd.getName().getIdentifier() + "(L2)");
        } else {
            noteArtifact(r, providerFile, providerType, "provider:" + providerType.getName().getIdentifier() + "." + providerMd.getName().getIdentifier());
        }

        Deque<Task> work = new ArrayDeque<>();
        Set<String> seen = new HashSet<>();
        work.add(new Task(providerMd, providerCu, providerFile, providerType, "provider"));
        while (!work.isEmpty() && r.visited < MAX_VISITS) {
            Task t = work.poll();
            String key = t.file + "#" + t.node.getStartPosition();
            if (!seen.add(key)) continue;
            r.visited++;
            walkNode(t, r, work);
        }

        // Construction
        r.isStatic = isStaticMethodBody(providerMd, providerFile, providerType, Collections.emptySet(), new HashSet<>(), r);
        return r;
    }

    /**
     * @ValueSource 用：对注解里的每个元素表达式做同一套 artifact 遍历（常量引用 → 所在类 → 等级；Foo.class 同上），
     * 返回 dependency 等级 / hitsProduction / 走过的 artifact。元素是纯字面量时什么都不记（L0）。
     */
    public Result analyzeExpressions(List<Expression> elements, String testFile, CompilationUnit testCu, AbstractTypeDeclaration testType) {
        Result r = new Result();
        Deque<Task> work = new ArrayDeque<>();
        Set<String> seen = new HashSet<>();
        for (Expression e : elements) work.add(new Task(e, testCu, testFile, testType, "value"));
        while (!work.isEmpty() && r.visited < MAX_VISITS) {
            Task t = work.poll();
            String key = t.file + "#" + t.node.getStartPosition();
            if (!seen.add(key)) continue;
            r.visited++;
            walkNode(t, r, work);
        }
        return r;
    }

    /** EnumSource 用：一个类型相对测试类的位置。level: 0..4 / -1 = production / -2 = JDK/第三方或找不到。 */
    public static class TypeInfo { public String file; public AbstractTypeDeclaration type; public int level; public String why; public boolean isTest, isProduction; }

    public TypeInfo lookupType(String simpleName, CompilationUnit ctxCu, String ctxFile, AbstractTypeDeclaration ctxType) {
        TypeInfo ti = new TypeInfo();
        Owner o = resolveOwner(simpleName, ctxCu, ctxFile, ctxType);
        if (o == null) { ti.level = -2; ti.why = "external"; return ti; }
        ti.file = o.file; ti.type = o.type; ti.isTest = o.isTest; ti.isProduction = o.isProduction;
        if (o.isProduction) { ti.level = -1; ti.why = "production"; return ti; }
        Result r = new Result();
        noteArtifact(r, o.file, o.type, "type:" + simpleName);
        ti.level = r.level; ti.why = r.levelReason.isEmpty() ? "same_class" : r.levelReason.substring(r.levelReason.indexOf("->") + 2);
        return ti;
    }

    // ---------- @FieldSource / @ArgumentsSource 用的公开入口 ----------
    public static class FieldLookup { public VariableDeclarationFragment fragment; public CompilationUnit cu; public String file; public AbstractTypeDeclaration type; public boolean inherited; }

    /** 按名字找字段：本类 → 外层类 → 祖先链；`inherited` = 不在测试类自己的封闭类型链里。 */
    public FieldLookup lookupField(String name, CompilationUnit ctxCu, String ctxFile, AbstractTypeDeclaration ctxType) {
        FieldHit fh = findFieldInChain(ctxType, ctxCu, ctxFile, name);
        if (fh == null) return null;
        FieldLookup fl = new FieldLookup(); fl.fragment = fh.fragment; fl.cu = fh.cu; fl.file = fh.file; fl.type = fh.type;
        boolean enclosing = false;
        for (ASTNode p = ctxType; p != null; p = p.getParent()) if (p == fh.type) enclosing = true;
        fl.inherited = !enclosing;
        return fl;
    }

    /** 外部类里的字段：Class#FIELD。 */
    public FieldLookup lookupField(String className, String fieldName, CompilationUnit ctxCu, String ctxFile, AbstractTypeDeclaration ctxType) {
        Owner o = resolveOwner(className.substring(className.lastIndexOf('.') + 1), ctxCu, ctxFile, ctxType);
        if (o == null) return null;
        FieldLookup fl = lookupField(fieldName, o.cu, o.file, o.type);
        if (fl != null) fl.inherited = false;
        return fl;
    }

    /** 类型里名为 name 的方法（@ArgumentsSource 的 provideArguments）。 */
    public MethodDeclaration lookupMethod(String typeSimple, String name, CompilationUnit ctxCu, String ctxFile, AbstractTypeDeclaration ctxType, String[] fileOut, AbstractTypeDeclaration[] typeOut) {
        Owner o = resolveOwner(typeSimple, ctxCu, ctxFile, ctxType);
        if (o == null) return null;
        Target t = findMethodInChain(o.type, o.cu, o.file, name);
        if (t == null) return null;
        fileOut[0] = t.file; typeOut[0] = t.type; return t.md;
    }

    /** @FieldSource：字段初始化器当 provider 体。dependency 从初始化器出发遍历；construction = 字段静态可确定性。 */
    public Result analyzeField(FieldLookup fl, boolean viaInheritance) {
        Result r = new Result();
        if (viaInheritance) { r.level = 2; r.levelReason = "provider_via_inheritance(L2)"; r.artifacts.add("field-provider:" + fl.fragment.getName() + "(L2)"); }
        else noteArtifact(r, fl.file, fl.type, "field-provider:" + fl.fragment.getName().getIdentifier());
        if (fl.fragment.getInitializer() != null) {
            Deque<Task> work = new ArrayDeque<>(); Set<String> seen = new HashSet<>();
            work.add(new Task(fl.fragment.getInitializer(), fl.cu, fl.file, fl.type, "field-provider"));
            while (!work.isEmpty() && r.visited < MAX_VISITS) {
                Task t = work.poll(); String key = t.file + "#" + t.node.getStartPosition();
                if (!seen.add(key)) continue;
                r.visited++; walkNode(t, r, work);
            }
        }
        FieldHit fh = new FieldHit(); fh.fragment = fl.fragment; fh.cu = fl.cu; fh.file = fl.file; fh.type = fl.type;
        r.isStatic = isStaticField(fh, r);
        return r;
    }

    public Integer countSetsOfField(FieldLookup fl) {
        lastCountFailReason = ""; lastCountFailStatus = "";
        if (fl.fragment.getInitializer() == null) return nf(RUNTIME, "field-no-initializer");
        FieldHit fh = new FieldHit(); fh.fragment = fl.fragment; fh.cu = fl.cu; fh.file = fl.file; fh.type = fl.type;
        if (mutatedInInitializerBlock(fh)) return nf(RUNTIME, "field-static-block");
        return countOf(fl.fragment.getInitializer(), fl.file, fl.type, new HashMap<>(), 0);
    }

    /** 已定位的类型相对测试类的等级（EnumSource 的 Outer.Inner 场景用）。 */
    public TypeInfo levelOf(String file, AbstractTypeDeclaration type) {
        TypeInfo ti = new TypeInfo(); ti.file = file; ti.type = type;
        Result r = new Result(); noteArtifact(r, file, type, "type:" + type.getName().getIdentifier());
        ti.level = r.level; ti.why = r.levelReason.isEmpty() ? "same_class" : r.levelReason.substring(r.levelReason.indexOf("->") + 2);
        return ti;
    }

    private void walkNode(Task t, Result r, Deque<Task> work) {
        Set<String> locals = localNames(t.node);
        t.node.accept(new ASTVisitor() {
            @Override public boolean visit(MethodInvocation mi) {
                Expression recv = mi.getExpression();
                String name = mi.getName().getIdentifier();
                if (recv == null || recv instanceof ThisExpression) {
                    Target tg = findMethodInChain(t.type, t.cu, t.file, name, mi.arguments().size());
                    if (tg != null) enqueueMethod(tg, r, work, "call:" + name);
                    else if (!resolveStaticImportOwner(t.cu, name, r, work, true, name)) { if (!BOXING_STATIC_FACTORIES.contains(name)) r.unresolved++; }
                } else if (isTypeName(recv)) {
                    String simple = typeSimpleName(recv);
                    Owner o = resolveOwner(simple, t.cu, t.file, t.type);
                    if (o != null) {
                        if (o.isTest) {
                            noteArtifact(r, o.file, o.type, "call:" + simple + "." + name);
                            Target tg = findMethodInChain(o.type, o.cu, o.file, name, mi.arguments().size());
                            if (tg != null) enqueueMethod(tg, r, work, "call:" + simple + "." + name);
                        } else if (o.isProduction) r.hitsProduction = true;
                    }
                } else if (recv instanceof SimpleName && !locals.contains(((SimpleName) recv).getIdentifier())) {
                    // 字段变量上的调用：先把字段本身当 artifact（会顺着初始化器追），再按字段声明类型找方法
                    String var = ((SimpleName) recv).getIdentifier();
                    FieldHit fh = findFieldInChain(t.type, t.cu, t.file, var);
                    if (fh != null) {
                        enqueueField(fh, r, work, "field:" + var);
                        String typeSimple = fh.declaredTypeSimple;
                        if (typeSimple != null) {
                            Owner o = resolveOwner(typeSimple, fh.cu, fh.file, fh.type);
                            if (o != null && o.isTest) {
                                Target tg = findMethodInChain(o.type, o.cu, o.file, name);
                                if (tg != null) enqueueMethod(tg, r, work, "call:" + var + "." + name);
                            } else if (o != null && o.isProduction) r.hitsProduction = true;
                        }
                    }
                } else if (recv instanceof SimpleName) {
                    // 局部变量上的调用：按局部变量声明类型
                    String typeSimple = localDeclaredType(t.node, ((SimpleName) recv).getIdentifier());
                    if (typeSimple != null) {
                        Owner o = resolveOwner(typeSimple, t.cu, t.file, t.type);
                        if (o != null && o.isTest) {
                            noteArtifact(r, o.file, o.type, "call:" + typeSimple + "#" + name);
                            Target tg = findMethodInChain(o.type, o.cu, o.file, name);
                            if (tg != null) enqueueMethod(tg, r, work, "call:" + typeSimple + "#" + name);
                        } else if (o != null && o.isProduction) r.hitsProduction = true;
                    }
                }
                return true;
            }
            @Override public boolean visit(ExpressionMethodReference ref) {
                if (isDataContext(ref)) return false;
                Expression q = ref.getExpression();
                String name = ref.getName().getIdentifier();
                if (isTypeName(q)) {
                    Owner o = resolveOwner(typeSimpleName(q), t.cu, t.file, t.type);
                    if (o != null && o.isTest) {
                        noteArtifact(r, o.file, o.type, "ref:" + typeSimpleName(q) + "::" + name);
                        Target tg = findMethodInChain(o.type, o.cu, o.file, name);
                        if (tg != null) enqueueMethod(tg, r, work, "ref:" + name);
                    } else if (o != null && o.isProduction) r.hitsProduction = true;
                } else if (q instanceof ThisExpression) {
                    Target tg = findMethodInChain(t.type, t.cu, t.file, name);
                    if (tg != null) enqueueMethod(tg, r, work, "ref:this::" + name);
                }
                return true;
            }
            @Override public boolean visit(ClassInstanceCreation cic) {
                String simple = simpleTypeNameOf(cic.getType());
                Owner o = resolveOwner(simple, t.cu, t.file, t.type);
                if (o != null) {
                    if (o.isTest) noteArtifact(r, o.file, o.type, "new:" + simple);
                    else if (o.isProduction) r.hitsProduction = true;
                }
                return true; // 匿名体 / 参数继续遍历
            }
            @Override public boolean visit(TypeLiteral tl) {
                // Foo.class：test 类型 → artifact；production 类型 → 参数直接就是 production 代码，标 hitsProduction
                String simple = simpleTypeNameOf(tl.getType());
                Owner o = resolveOwner(simple, t.cu, t.file, t.type);
                if (o != null && o.isTest) noteArtifact(r, o.file, o.type, "class:" + simple);
                else if (o != null && o.isProduction) r.hitsProduction = true;
                return false;
            }
            @Override public boolean visit(QualifiedName qn) {
                // Type.FIELD（或 Outer.Inner.FIELD）：限定符是类型名
                Name q = qn.getQualifier();
                if (isTypeName(q)) {
                    String simple = typeSimpleName(q);
                    Owner o = resolveOwner(simple, t.cu, t.file, t.type);
                    if (o != null) {
                        if (o.isTest) {
                            noteArtifact(r, o.file, o.type, "field:" + simple + "." + qn.getName().getIdentifier());
                            FieldHit fh = findFieldInChain(o.type, o.cu, o.file, qn.getName().getIdentifier());
                            if (fh != null) enqueueField(fh, r, work, "field:" + simple + "." + qn.getName().getIdentifier());
                        } else if (o.isProduction) r.hitsProduction = true;
                    }
                    return false;
                }
                return true;
            }
            @Override public boolean visit(FieldAccess fa) {
                if (fa.getExpression() instanceof ThisExpression) {
                    FieldHit fh = findFieldInChain(t.type, t.cu, t.file, fa.getName().getIdentifier());
                    if (fh != null) enqueueField(fh, r, work, "field:this." + fa.getName().getIdentifier());
                    return false;
                }
                return true;
            }
            @Override public boolean visit(SimpleName sn) {
                if (sn.isDeclaration()) return false;
                ASTNode p = sn.getParent();
                // 排除：方法名、限定名的一部分、类型、注解、字段访问的名字部分
                if (p instanceof MethodInvocation && ((MethodInvocation) p).getName() == sn) return false;
                if (p instanceof QualifiedName) return false;
                if (p instanceof SimpleType || p instanceof Annotation || p instanceof MemberValuePair) return false;
                if (p instanceof FieldAccess && ((FieldAccess) p).getName() == sn) return false;
                if (p instanceof ExpressionMethodReference && ((ExpressionMethodReference) p).getName() == sn) return false;
                if (p instanceof LabeledStatement || p instanceof BreakStatement || p instanceof ContinueStatement) return false;
                String id = sn.getIdentifier();
                if (locals.contains(id)) return false;
                if (Character.isUpperCase(id.charAt(0)) && !isConstantStyle(id)) return false; // 类型名
                FieldHit fh = findFieldInChain(t.type, t.cu, t.file, id);
                if (fh != null) enqueueField(fh, r, work, "field:" + id);
                else resolveStaticImportOwner(t.cu, id, r, work, false, id);
                return false;
            }
        });
    }

    private void enqueueMethod(Target tg, Result r, Deque<Task> work, String label) {
        noteArtifact(r, tg.file, tg.type, label);
        work.add(new Task(tg.md, tg.cu, tg.file, tg.type, label));
    }

    private void enqueueField(FieldHit fh, Result r, Deque<Task> work, String label) {
        noteArtifact(r, fh.file, fh.type, label);
        if (fh.fragment.getInitializer() != null) work.add(new Task(fh.fragment.getInitializer(), fh.cu, fh.file, fh.type, label));
    }

    /** 静态导入的成员：import static a.b.Type.member / Type.* */
    private boolean resolveStaticImportOwner(CompilationUnit cu, String member, Result r, Deque<Task> work, boolean isMethod, String label) {
        for (Object o : cu.imports()) {
            ImportDeclaration id = (ImportDeclaration) o;
            if (!id.isStatic()) continue;
            String fq = id.getName().getFullyQualifiedName();
            String typeFq;
            if (id.isOnDemand()) typeFq = fq;
            else if (fq.endsWith("." + member)) typeFq = fq.substring(0, fq.lastIndexOf('.'));
            else continue;
            String simple = typeFq.substring(typeFq.lastIndexOf('.') + 1);
            Owner own = resolveOwner(simple, cu, testFile, null);
            if (own == null) { if (id.isOnDemand()) continue; return true; } // JDK/第三方 static import
            if (own.isProduction) { r.hitsProduction = true; return true; }
            if (!own.isTest) return true;
            if (isMethod) {
                Target tg = findMethodInChain(own.type, own.cu, own.file, member);
                if (tg != null) { enqueueMethod(tg, r, work, "static-import:" + simple + "." + member); return true; }
            } else {
                FieldHit fh = findFieldInChain(own.type, own.cu, own.file, member);
                if (fh != null) { enqueueField(fh, r, work, "static-import:" + simple + "." + member); return true; }
            }
            if (!id.isOnDemand()) return true;
        }
        return false;
    }

    // ---------- artifact 等级 ----------
    private void noteArtifact(Result r, String file, AbstractTypeDeclaration type, String label) {
        if (file == null || type == null) return;
        String outer = outermostName(type);
        int lvl;
        String why;
        if (file.equals(testFile) && outer.equals(testOutermost)) {
            // 同一最外层类：provider/helper 就在测试类里 → 不加级（L0 基线）；嵌套类/外层类 → L1
            lvl = type.getName().getIdentifier().equals(testDeclaringType) ? 0 : 1;
            why = lvl == 0 ? "same_class" : "enclosing_class";
        } else if (testAncestors.contains(type.getName().getIdentifier()) || testAncestors.contains(outer)) {
            lvl = 2; why = "inherited";
        } else if (Objects.equals(packageOfFile(file), testPackage)) {
            lvl = 3; why = "same_package";
        } else {
            lvl = 4; why = "cross_package";
        }
        r.artifacts.add(label + "@" + outer + (type.getName().getIdentifier().equals(outer) ? "" : "." + type.getName().getIdentifier()) + "(L" + lvl + ")");
        if (lvl > r.level) { r.level = lvl; r.levelReason = label + "->" + why + "(L" + lvl + ")"; }
    }

    // =====================================================================================
    // Construction：静态可确定性（传递到 helper 体与字段初始化器）
    // =====================================================================================
    private final Map<String, Boolean> fieldStaticCache = new HashMap<>();
    private final Set<String> evaluating = new HashSet<>();

    private boolean isStaticMethodBody(MethodDeclaration md, String file, AbstractTypeDeclaration type,
                                       Set<String> staticParams, Set<String> dynamicParams, Result r) {
        Block body = md.getBody();
        if (body == null) return fail(r, "abstract/native:" + md.getName());
        String key = file + "#m#" + md.getStartPosition();
        if (!evaluating.add(key)) return fail(r, "recursion:" + md.getName());
        try {
            Set<String> staticLocals = new HashSet<>(staticParams);
            boolean sawReturn = false;
            for (Object o : body.statements()) {
                Statement st = (Statement) o;
                if (st instanceof VariableDeclarationStatement) {
                    for (Object f : ((VariableDeclarationStatement) st).fragments()) {
                        VariableDeclarationFragment frag = (VariableDeclarationFragment) f;
                        Expression init = frag.getInitializer();
                        if (init == null || !isStaticExpr(init, staticLocals, dynamicParams, file, type, r)) return false;
                        staticLocals.add(frag.getName().getIdentifier());
                    }
                } else if (st instanceof ExpressionStatement) {
                    Expression e = ((ExpressionStatement) st).getExpression();
                    if (e instanceof MethodInvocation) {
                        MethodInvocation mi = (MethodInvocation) e;
                        if (!(mi.getExpression() instanceof SimpleName)
                                || !staticLocals.contains(((SimpleName) mi.getExpression()).getIdentifier())
                                || !CONTAINER_MUTATORS.contains(mi.getName().getIdentifier()))
                            return fail(r, "statement:" + abbreviate(e));
                        for (Object a : mi.arguments())
                            if (!isStaticExpr((Expression) a, staticLocals, dynamicParams, file, type, r)) return false;
                    } else if (e instanceof Assignment && ((Assignment) e).getLeftHandSide() instanceof SimpleName) {
                        if (!isStaticExpr(((Assignment) e).getRightHandSide(), staticLocals, dynamicParams, file, type, r)) return false;
                        staticLocals.add(((SimpleName) ((Assignment) e).getLeftHandSide()).getIdentifier());
                    } else return fail(r, "statement:" + abbreviate(e));
                } else if (st instanceof ReturnStatement) {
                    Expression ret = ((ReturnStatement) st).getExpression();
                    if (ret == null || !isStaticExpr(ret, staticLocals, dynamicParams, file, type, r)) return false;
                    sawReturn = true;
                } else {
                    return fail(r, "control-flow:" + st.getClass().getSimpleName());
                }
            }
            return sawReturn || fail(r, "no-return");
        } finally {
            evaluating.remove(key);
        }
    }

    private boolean isStaticExpr(Expression expr, Set<String> staticLocals, Set<String> dynamicParams,
                                 String file, AbstractTypeDeclaration type, Result r) {
        if (expr == null) return false;
        if (expr instanceof NumberLiteral || expr instanceof StringLiteral || expr instanceof BooleanLiteral
                || expr instanceof CharacterLiteral || expr instanceof NullLiteral || expr instanceof TypeLiteral
                || expr instanceof TextBlock) return true;
        if (expr instanceof PrefixExpression)
            return isStaticExpr(((PrefixExpression) expr).getOperand(), staticLocals, dynamicParams, file, type, r);
        if (expr instanceof InfixExpression) {
            InfixExpression ie = (InfixExpression) expr;
            if (!isStaticExpr(ie.getLeftOperand(), staticLocals, dynamicParams, file, type, r)) return false;
            if (!isStaticExpr(ie.getRightOperand(), staticLocals, dynamicParams, file, type, r)) return false;
            for (Object o : ie.extendedOperands()) if (!isStaticExpr((Expression) o, staticLocals, dynamicParams, file, type, r)) return false;
            return true;
        }
        if (expr instanceof CastExpression) return isStaticExpr(((CastExpression) expr).getExpression(), staticLocals, dynamicParams, file, type, r);
        if (expr instanceof ParenthesizedExpression) return isStaticExpr(((ParenthesizedExpression) expr).getExpression(), staticLocals, dynamicParams, file, type, r);
        if (expr instanceof ArrayInitializer) {
            for (Object o : ((ArrayInitializer) expr).expressions()) if (!isStaticExpr((Expression) o, staticLocals, dynamicParams, file, type, r)) return false;
            return true;
        }
        if (expr instanceof ArrayCreation) {
            ArrayCreation ac = (ArrayCreation) expr;
            if (ac.getInitializer() != null) return isStaticExpr(ac.getInitializer(), staticLocals, dynamicParams, file, type, r);
            for (Object d : ac.dimensions()) if (!isStaticExpr((Expression) d, staticLocals, dynamicParams, file, type, r)) return false;
            return true;
        }
        if (expr instanceof SimpleName) {
            String id = ((SimpleName) expr).getIdentifier();
            if (staticLocals.contains(id)) return true;
            if (dynamicParams.contains(id)) return fail(r, "param:" + id);
            CompilationUnit cu = cuCache.get(file);
            FieldHit fh = findFieldInChain(type, cu, file, id);
            if (fh != null) return isStaticField(fh, r);
            // 静态导入的常量 / 找不到的名字：常量命名视为静态，其它视为动态
            return isConstantStyle(id) || fail(r, "unknown-name:" + id);
        }
        if (expr instanceof QualifiedName) {
            QualifiedName qn = (QualifiedName) expr;
            if (!isTypeName(qn.getQualifier())) return fail(r, "field-of-expr:" + qn);
            String simple = typeSimpleName(qn.getQualifier());
            Owner o = resolveOwner(simple, cuCache.get(file), file, type);
            if (o != null && o.isTest) {
                FieldHit fh = findFieldInChain(o.type, o.cu, o.file, qn.getName().getIdentifier());
                return fh != null ? isStaticField(fh, r) : (isConstantStyle(qn.getName().getIdentifier()) || fail(r, "unknown-field:" + qn));
            }
            // production / JDK / 第三方类型上的静态字段访问（枚举常量、常量，含 SnmpConstants.version1 这种小写命名的常量）
            // → 静态给出的值
            return true;
        }
        if (expr instanceof FieldAccess) {
            FieldAccess fa = (FieldAccess) expr;
            if (fa.getExpression() instanceof ThisExpression) {
                FieldHit fh = findFieldInChain(type, cuCache.get(file), file, fa.getName().getIdentifier());
                return fh != null ? isStaticField(fh, r) : fail(r, "unknown-field:this." + fa.getName());
            }
            return isConstantStyle(fa.getName().getIdentifier()) || fail(r, "field-of-expr:" + abbreviate(fa));
        }
        if (expr instanceof ClassInstanceCreation) {
            ClassInstanceCreation cic = (ClassInstanceCreation) expr;
            if (cic.getAnonymousClassDeclaration() != null) return fail(r, "anonymous:" + simpleTypeNameOf(cic.getType()));
            for (Object o : cic.arguments()) if (!isStaticExpr((Expression) o, staticLocals, dynamicParams, file, type, r)) return false;
            return isDataHolderConstruction(cic, staticLocals, dynamicParams, file, type, r);
        }
        if (expr instanceof MethodInvocation) return isStaticCall((MethodInvocation) expr, staticLocals, dynamicParams, file, type, r);
        if (expr instanceof LambdaExpression) {
            LambdaExpression le = (LambdaExpression) expr;
            if (le.getBody() instanceof Expression) {
                Set<String> params = new HashSet<>();
                for (Object p : le.parameters()) params.add(p instanceof VariableDeclaration ? ((VariableDeclaration) p).getName().getIdentifier() : p.toString());
                Set<String> dyn = new HashSet<>(dynamicParams); dyn.addAll(params);
                return isStaticExpr((Expression) le.getBody(), staticLocals, dyn, file, type, r);
            }
            return fail(r, "block-lambda");
        }
        if (expr instanceof MethodReference) return fail(r, "method-ref:" + abbreviate(expr));
        if (expr instanceof ConditionalExpression) return fail(r, "conditional");
        return fail(r, expr.getClass().getSimpleName() + ":" + abbreviate(expr));
    }

    private boolean isStaticCall(MethodInvocation mi, Set<String> staticLocals, Set<String> dynamicParams,
                                 String file, AbstractTypeDeclaration type, Result r) {
        String name = mi.getName().getIdentifier();
        Expression recv = mi.getExpression();
        CompilationUnit cu = cuCache.get(file);
        // 1) 项目内 test helper：本类/祖先（裸名或 this.）、Type.helper()、静态导入 → 递归评估其体
        Target tg = null;
        if (recv == null || recv instanceof ThisExpression) {
            tg = findMethodInChain(type, cu, file, name, mi.arguments().size());
            if (tg == null) tg = staticImportMethod(cu, name);
        } else if (isTypeName(recv)) {
            Owner o = resolveOwner(typeSimpleName(recv), cu, file, type);
            if (o != null && o.isTest) tg = findMethodInChain(o.type, o.cu, o.file, name, mi.arguments().size());
            else if (o != null && o.isProduction) return fail(r, "production-call:" + typeSimpleName(recv) + "." + name);
        }
        if (tg != null) {
            List<String> paramNames = new ArrayList<>();
            for (Object p : tg.md.parameters()) paramNames.add(((SingleVariableDeclaration) p).getName().getIdentifier());
            Set<String> sp = new HashSet<>(), dp = new HashSet<>();
            for (int i = 0; i < paramNames.size(); i++) {
                boolean argStatic = i < mi.arguments().size()
                        && isStaticExprQuiet((Expression) mi.arguments().get(i), staticLocals, dynamicParams, file, type);
                (argStatic ? sp : dp).add(paramNames.get(i));
            }
            Result sub = new Result();
            boolean ok = isStaticMethodBody(tg.md, tg.file, tg.type, sp, dp, sub);
            return ok || fail(r, "helper:" + name + "->" + sub.dynamicReason);
        }
        // 2) 静态工厂装箱：Type.of(...) / 无接收者的 arguments(...)，参数全静态
        boolean staticFactoryForm = (recv == null) || isTypeName(recv);
        if (staticFactoryForm && BOXING_STATIC_FACTORIES.contains(name)) {
            for (Object a : mi.arguments()) if (!isStaticExpr((Expression) a, staticLocals, dynamicParams, file, type, r)) return false;
            return true;
        }
        // 3) 字面量局部容器的单层终结调用 list.stream() / toArray() / build()
        if (recv instanceof SimpleName && staticLocals.contains(((SimpleName) recv).getIdentifier()) && LOCAL_TERMINALS.contains(name)) {
            for (Object a : mi.arguments()) if (!isStaticExpr((Expression) a, staticLocals, dynamicParams, file, type, r)) return false;
            return true;
        }
        return fail(r, "call:" + abbreviate(mi));
    }

    private boolean isStaticExprQuiet(Expression e, Set<String> sl, Set<String> dp, String file, AbstractTypeDeclaration type) {
        return isStaticExpr(e, sl, dp, file, type, new Result());
    }

    private boolean isStaticField(FieldHit fh, Result r) {
        String key = fh.file + "#f#" + fh.fragment.getStartPosition();
        Boolean cached = fieldStaticCache.get(key);
        if (cached != null) return cached || fail(r, "field:" + fh.fragment.getName() + "(dynamic)");
        if (!evaluating.add(key)) return fail(r, "field-cycle:" + fh.fragment.getName());
        try {
            Expression init = fh.fragment.getInitializer();
            boolean ok;
            if (init == null) ok = false;                       // 在静态块 / @BeforeAll 里赋值 → 动态
            else if (mutatedInInitializerBlock(fh)) { ok = false; fail(r, "field:" + fh.fragment.getName() + "(mutated-in-static-block)"); }
            else {
                Result sub = new Result();
                ok = isStaticExpr(init, Collections.emptySet(), Collections.emptySet(), fh.file, fh.type, sub);
                if (!ok) fail(r, "field:" + fh.fragment.getName() + "->" + sub.dynamicReason);
            }
            if (init == null) fail(r, "field:" + fh.fragment.getName() + "(no-initializer)");
            fieldStaticCache.put(key, ok);
            return ok;
        } finally {
            evaluating.remove(key);
        }
    }

    private static final Set<String> MUTATORS = Set.of("add", "addAll", "put", "putAll", "set", "remove", "removeAll", "removeIf", "retainAll",
            "clear", "offer", "push", "pop", "poll", "accept", "merge", "compute", "computeIfAbsent", "computeIfPresent", "putIfAbsent", "replaceAll", "sort");

    /**
     * 字段在声明类的任何地方（static {} / 实例初始化块 / 构造函数 / @BeforeEach / 任意方法）被填充（LIST.add(...)）、重新赋值
     * （data = ...）或整个交给别的方法（Collections.addAll(LIST, ...)、fill(list)）→ 值不是在声明处静态给出的。
     * 只看声明类自己的体；跨类修改（别的类改 public static 字段）不追。
     */
    private static boolean mutatedInInitializerBlock(FieldHit fh) {
        String name = fh.fragment.getName().getIdentifier();
        final boolean[] hit = {false};
        fh.type.accept(new ASTVisitor() {
            @Override public boolean visit(MethodInvocation mi) {
                if (hit[0]) return false;
                Expression r = mi.getExpression();
                boolean onField = (r instanceof SimpleName && ((SimpleName) r).getIdentifier().equals(name))
                        || (r instanceof FieldAccess && ((FieldAccess) r).getExpression() instanceof ThisExpression && ((FieldAccess) r).getName().getIdentifier().equals(name));
                if (onField && MUTATORS.contains(mi.getName().getIdentifier())) { hit[0] = true; return false; }
                for (Object a : mi.arguments()) {
                    if (a instanceof SimpleName && ((SimpleName) a).getIdentifier().equals(name)) {
                        String m = mi.getName().getIdentifier();
                        // 只读用途（unmodifiableList(LIST)、stream(LIST)、copyOf、asList、size 等）不算突变
                        if (!(m.startsWith("unmodifiable") || m.equals("stream") || m.equals("copyOf") || m.equals("asList") || m.equals("of")
                                || m.equals("size") || m.equals("assertEquals") || m.equals("assertThat") || m.startsWith("assert") || m.equals("format")
                                || m.equals("println") || m.equals("contains") || m.equals("indexOf") || m.equals("join") || m.equals("get")
                                || m.equals("synchronizedList") || m.equals("newArrayList") || m.equals("newHashSet") || m.equals("concat") || m.equals("toArray"))) { hit[0] = true; return false; }
                    }
                }
                return true;
            }
            @Override public boolean visit(Assignment a) {
                if (hit[0]) return false;
                Expression l = a.getLeftHandSide();
                if ((l instanceof SimpleName && ((SimpleName) l).getIdentifier().equals(name))
                        || (l instanceof FieldAccess && ((FieldAccess) l).getExpression() instanceof ThisExpression && ((FieldAccess) l).getName().getIdentifier().equals(name))) hit[0] = true;
                return !hit[0];
            }
            @Override public boolean visit(VariableDeclarationFragment f) { return f != fh.fragment; }  // 声明自己的初始化器不算
        });
        return hit[0];
    }

    /**
     * new T(args)：production/JDK 类型按值对象处理（看不到体，`new File("x")`）；test-code 类型要求是"纯数据持有者"——
     * record，或匹配参数个数的构造函数体里只有 this.f = 参数/静态值 的赋值（和 super(...)）；否则视为在执行构造逻辑
     * （MockedSCM(new TestableCluster(4, STORAGE_UNIT)) 这种 mock 装配）→ Dynamic。
     */
    private boolean isDataHolderConstruction(ClassInstanceCreation cic, Set<String> staticLocals, Set<String> dynamicParams,
                                             String file, AbstractTypeDeclaration type, Result r) {
        String simple = simpleTypeNameOf(cic.getType());
        Owner o = resolveOwner(simple, cuCache.get(file), file, type);
        if (o == null || !o.isTest) return true;
        if (o.type instanceof RecordDeclaration) return true;
        int arity = cic.arguments().size();
        MethodDeclaration ctor = null; boolean anyCtor = false;
        for (Object bd : o.type.bodyDeclarations()) {
            if (bd instanceof MethodDeclaration && ((MethodDeclaration) bd).isConstructor()) {
                anyCtor = true;
                if (((MethodDeclaration) bd).parameters().size() == arity) { ctor = (MethodDeclaration) bd; break; }
            }
        }
        // 实例字段初始化器 / 实例初始化块必须是静态的
        for (Object bd : o.type.bodyDeclarations()) {
            if (bd instanceof Initializer && !Modifier.isStatic(((Initializer) bd).getModifiers())) return fail(r, "new:" + simple + "(instance-initializer)");
            if (bd instanceof FieldDeclaration && !Modifier.isStatic(((FieldDeclaration) bd).getModifiers())) {
                for (Object fr : ((FieldDeclaration) bd).fragments()) {
                    Expression init = ((VariableDeclarationFragment) fr).getInitializer();
                    if (init != null && !isStaticExpr(init, Collections.emptySet(), Collections.emptySet(), o.file, o.type, new Result()))
                        return fail(r, "new:" + simple + "(field-init:" + ((VariableDeclarationFragment) fr).getName() + ")");
                }
            }
        }
        if (!anyCtor) return true;                       // 默认构造
        if (ctor == null || ctor.getBody() == null) return fail(r, "new:" + simple + "(no-matching-ctor)");
        Set<String> params = new HashSet<>();
        for (Object p : ctor.parameters()) params.add(((SingleVariableDeclaration) p).getName().getIdentifier());
        for (Object st : ctor.getBody().statements()) {
            if (st instanceof SuperConstructorInvocation || st instanceof ConstructorInvocation) continue;
            if (!(st instanceof ExpressionStatement)) return fail(r, "new:" + simple + "(ctor-logic)");
            Expression e = ((ExpressionStatement) st).getExpression();
            if (!(e instanceof Assignment)) return fail(r, "new:" + simple + "(ctor-logic)");
            Expression rhs = ((Assignment) e).getRightHandSide();
            if (rhs instanceof SimpleName && params.contains(((SimpleName) rhs).getIdentifier())) continue;
            if (!isStaticExpr(rhs, params, Collections.emptySet(), o.file, o.type, new Result())) return fail(r, "new:" + simple + "(ctor-logic)");
        }
        return true;
    }

    private static boolean fail(Result r, String why) {
        if (r.dynamicReason.isEmpty()) r.dynamicReason = why;
        return false;
    }

    // =====================================================================================
    // 解析工具
    // =====================================================================================
    private static final class Owner { CompilationUnit cu; String file; AbstractTypeDeclaration type; boolean isTest; boolean isProduction; }
    private static final class Target { MethodDeclaration md; CompilationUnit cu; String file; AbstractTypeDeclaration type; }
    private static final class FieldHit { VariableDeclarationFragment fragment; CompilationUnit cu; String file; AbstractTypeDeclaration type; String declaredTypeSimple; }

    /** 简单类型名 → 所在文件/类型；先看当前文件里的（嵌套）类型，再 import / 同包 / 唯一候选。 */
    private static final Set<String> JAVA_LANG = Set.of("String", "Object", "Integer", "Long", "Double", "Float", "Short", "Byte",
            "Character", "Boolean", "Math", "System", "Thread", "Class", "Enum", "Number", "StringBuilder", "StringBuffer",
            "Iterable", "Runnable", "Throwable", "Exception", "RuntimeException", "Error", "Void", "Comparable", "CharSequence");

    private Owner resolveOwner(String simple, CompilationUnit ctxCu, String ctxFile, AbstractTypeDeclaration ctxType) {
        if (simple == null || simple.isEmpty()) return null;
        if (ctxCu != null) {
            AbstractTypeDeclaration local = findTypeInCu(ctxCu, simple);
            if (local != null) return owner(ctxCu, ctxFile, local);
            // 显式 import 自 java./javax./jakarta. 的类型 → JDK/平台类，不是项目类（poi 有自己的 Stream.java，
            // 但 java.util.stream.Stream 被 import 时不能误认）
            for (Object o : ctxCu.imports()) {
                ImportDeclaration id = (ImportDeclaration) o;
                if (id.isStatic() || id.isOnDemand()) continue;
                String fq = id.getName().getFullyQualifiedName();
                if (fq.endsWith("." + simple) && (fq.startsWith("java.") || fq.startsWith("javax.") || fq.startsWith("jakarta.") || fq.startsWith("org.junit.")
                        || fq.startsWith("org.mockito.") || fq.startsWith("org.assertj.") || fq.startsWith("com.google.common."))) return null;
            }
            if (JAVA_LANG.contains(simple)) return null;
        }
        List<Path> cands = fileIndex.get(simple);
        if ((cands == null || cands.isEmpty()) && ctxType != null && ctxCu != null && !inAncestorLookup) {
            // 祖先类里声明的嵌套类型（AbstractXxxTestBase.Mode，子类不用 import 就能用）。
            // supertypes() 自己会调 resolveOwner，用标志位防止互相递归。
            inAncestorLookup = true;
            try {
                Deque<Object[]> q = new ArrayDeque<>(); Set<String> seen = new HashSet<>();
                for (Owner sup : supertypes(ctxType, ctxCu, ctxFile)) q.add(new Object[]{sup, 0});
                while (!q.isEmpty()) {
                    Object[] it = q.poll(); Owner sup = (Owner) it[0]; int d = (Integer) it[1];
                    if (!seen.add(sup.file + "#" + sup.type.getStartPosition()) || d > 8) continue;
                    AbstractTypeDeclaration nested = findTypeInCu(sup.cu, simple);
                    if (nested != null) return owner(sup.cu, sup.file, nested);
                    for (Owner s2 : supertypes(sup.type, sup.cu, sup.file)) q.add(new Object[]{s2, d + 1});
                }
            } finally {
                inAncestorLookup = false;
            }
        }
        if (cands == null || cands.isEmpty()) {
            // 嵌套类型：import a.b.Outer.Simple; → 找 Outer 的文件，再在里面找 Simple（HoodieRecord.HoodieRecordType 这类）
            if (ctxCu != null) {
                for (Object o : ctxCu.imports()) {
                    ImportDeclaration id = (ImportDeclaration) o;
                    if (id.isStatic() || id.isOnDemand()) continue;
                    String fq = id.getName().getFullyQualifiedName();
                    if (!fq.endsWith("." + simple)) continue;
                    String[] segs = fq.split("\\.");
                    for (int k = segs.length - 2; k >= 0 && Character.isUpperCase(segs[k].charAt(0)); k--) {
                        Owner outer = resolveOwner(segs[k], null, null, null);
                        if (outer == null) {
                            List<Path> oc = fileIndex.get(segs[k]);
                            if (oc == null) continue;
                            String pkgPath = String.join("/", Arrays.copyOfRange(segs, 0, k)) + "/" + segs[k] + ".java";
                            Path op = null; for (Path pp : oc) if (pp.toString().endsWith("/" + pkgPath)) { op = pp; break; }
                            if (op == null && oc.size() == 1) op = oc.get(0);
                            if (op == null) continue;
                            CompilationUnit ocu = cuCache.computeIfAbsent(op.toString(), parser);
                            AbstractTypeDeclaration nested = ocu == null ? null : findTypeInCu(ocu, simple);
                            if (nested != null) return owner(ocu, op.toString(), nested);
                        } else {
                            AbstractTypeDeclaration nested = findTypeInCu(outer.cu, simple);
                            if (nested != null) return owner(outer.cu, outer.file, nested);
                        }
                    }
                }
            }
            return null;
        }
        Path pick = null;
        if (cands.size() == 1) pick = cands.get(0);
        else if (ctxCu != null) {
            String pkg = ctxCu.getPackage() != null ? ctxCu.getPackage().getName().getFullyQualifiedName() : "";
            for (Object o : ctxCu.imports()) {
                ImportDeclaration id = (ImportDeclaration) o;
                if (id.isStatic() || id.isOnDemand()) continue;
                String fq = id.getName().getFullyQualifiedName();
                if (fq.endsWith("." + simple)) {
                    String pkgPath = fq.substring(0, fq.lastIndexOf('.')).replace('.', '/');
                    for (Path p : cands) if (p.toString().contains("/" + pkgPath + "/")) { pick = p; break; }
                }
            }
            if (pick == null) for (Path p : cands) if (p.toString().contains("/" + pkg.replace('.', '/') + "/" + simple + ".java")) { pick = p; break; }
            if (pick == null) {
                for (Object o : ctxCu.imports()) {
                    ImportDeclaration id = (ImportDeclaration) o;
                    if (id.isStatic() || !id.isOnDemand()) continue;
                    String pkgPath = id.getName().getFullyQualifiedName().replace('.', '/');
                    for (Path p : cands) if (p.toString().contains("/" + pkgPath + "/" + simple + ".java")) { pick = p; break; }
                    if (pick != null) break;
                }
            }
        }
        if (pick == null) return null;
        CompilationUnit cu = cuCache.computeIfAbsent(pick.toString(), parser);
        if (cu == null) return null;
        AbstractTypeDeclaration td = findTypeInCu(cu, simple);
        if (td == null) return null;
        return owner(cu, pick.toString(), td);
    }

    private Owner owner(CompilationUnit cu, String file, AbstractTypeDeclaration td) {
        Owner o = new Owner(); o.cu = cu; o.file = file; o.type = td;
        String f = file.replace('\\', '/');
        o.isTest = f.contains("/src/test/") || f.contains("/src/it/") || f.contains("/src/integration-test/") || f.contains("/test/java/");
        o.isProduction = !o.isTest;
        return o;
    }

    /** 方法：当前类型 → 外层类型 → 祖先链（父类 + 接口，≤8 层）。 */
    private Target findMethodInChain(AbstractTypeDeclaration type, CompilationUnit cu, String file, String name) {
        return findMethodInChain(type, cu, file, name, -1);
    }

    /** arity >= 0 时优先参数个数相同的重载（否则 getTestImages(filter) → getTestImages(filter, max) 会被认成自递归）。 */
    private Target findMethodInChain(AbstractTypeDeclaration type, CompilationUnit cu, String file, String name, int arity) {
        Target any = null;
        Deque<Object[]> q = new ArrayDeque<>();
        Set<String> seen = new HashSet<>();
        for (ASTNode p = type; p != null; p = p.getParent()) if (p instanceof AbstractTypeDeclaration) q.add(new Object[]{p, cu, file, 0});
        while (!q.isEmpty()) {
            Object[] it = q.poll();
            AbstractTypeDeclaration td = (AbstractTypeDeclaration) it[0]; CompilationUnit c = (CompilationUnit) it[1]; String f = (String) it[2]; int d = (Integer) it[3];
            if (!seen.add(f + "#" + td.getStartPosition())) continue;
            for (Object o : td.bodyDeclarations()) {
                if (o instanceof MethodDeclaration && ((MethodDeclaration) o).getName().getIdentifier().equals(name) && ((MethodDeclaration) o).getBody() != null) {
                    Target t = new Target(); t.md = (MethodDeclaration) o; t.cu = c; t.file = f; t.type = td;
                    if (arity < 0 || t.md.parameters().size() == arity) return t;
                    if (any == null) any = t;
                }
            }
            if (d < 8) for (Owner sup : supertypes(td, c, f)) q.add(new Object[]{sup.type, sup.cu, sup.file, d + 1});
        }
        return any;
    }

    private FieldHit findFieldInChain(AbstractTypeDeclaration type, CompilationUnit cu, String file, String name) {
        Deque<Object[]> q = new ArrayDeque<>();
        Set<String> seen = new HashSet<>();
        for (ASTNode p = type; p != null; p = p.getParent()) if (p instanceof AbstractTypeDeclaration) q.add(new Object[]{p, cu, file, 0});
        while (!q.isEmpty()) {
            Object[] it = q.poll();
            AbstractTypeDeclaration td = (AbstractTypeDeclaration) it[0]; CompilationUnit c = (CompilationUnit) it[1]; String f = (String) it[2]; int d = (Integer) it[3];
            if (!seen.add(f + "#" + td.getStartPosition())) continue;
            for (Object o : td.bodyDeclarations()) {
                if (o instanceof FieldDeclaration) {
                    for (Object fr : ((FieldDeclaration) o).fragments()) {
                        VariableDeclarationFragment frag = (VariableDeclarationFragment) fr;
                        if (frag.getName().getIdentifier().equals(name)) {
                            FieldHit h = new FieldHit(); h.fragment = frag; h.cu = c; h.file = f; h.type = td;
                            h.declaredTypeSimple = simpleTypeNameOf(((FieldDeclaration) o).getType()); return h;
                        }
                    }
                }
            }
            if (td instanceof EnumDeclaration) for (Object ec : ((EnumDeclaration) td).enumConstants()) {
                if (((EnumConstantDeclaration) ec).getName().getIdentifier().equals(name)) return null; // 枚举常量：静态，不当字段追
            }
            if (d < 8) for (Owner sup : supertypes(td, c, f)) q.add(new Object[]{sup.type, sup.cu, sup.file, d + 1});
        }
        return null;
    }

    /** import static a.b.Type.FIELD / Type.* 里的字段。 */
    private FieldHit staticImportField(CompilationUnit cu, String name) {
        if (cu == null) return null;
        for (Object o : cu.imports()) {
            ImportDeclaration id = (ImportDeclaration) o;
            if (!id.isStatic()) continue;
            String fq = id.getName().getFullyQualifiedName();
            String typeFq = id.isOnDemand() ? fq : (fq.endsWith("." + name) ? fq.substring(0, fq.lastIndexOf('.')) : null);
            if (typeFq == null) continue;
            Owner own = resolveOwner(typeFq.substring(typeFq.lastIndexOf('.') + 1), cu, testFile, null);
            if (own != null) {
                FieldHit fh = findFieldInChain(own.type, own.cu, own.file, name);
                if (fh != null) return fh;
            }
        }
        return null;
    }

    private Target staticImportMethod(CompilationUnit cu, String name) {
        for (Object o : cu.imports()) {
            ImportDeclaration id = (ImportDeclaration) o;
            if (!id.isStatic()) continue;
            String fq = id.getName().getFullyQualifiedName();
            String typeFq = id.isOnDemand() ? fq : (fq.endsWith("." + name) ? fq.substring(0, fq.lastIndexOf('.')) : null);
            if (typeFq == null) continue;
            Owner own = resolveOwner(typeFq.substring(typeFq.lastIndexOf('.') + 1), cu, testFile, null);
            if (own != null && own.isTest) {
                Target t = findMethodInChain(own.type, own.cu, own.file, name);
                if (t != null) return t;
            }
        }
        return null;
    }

    private List<Owner> supertypes(AbstractTypeDeclaration td, CompilationUnit cu, String file) {
        List<Owner> out = new ArrayList<>();
        List<Type> ts = new ArrayList<>();
        if (td instanceof TypeDeclaration) {
            if (((TypeDeclaration) td).getSuperclassType() != null) ts.add(((TypeDeclaration) td).getSuperclassType());
            for (Object i : ((TypeDeclaration) td).superInterfaceTypes()) ts.add((Type) i);
        } else if (td instanceof EnumDeclaration) {
            for (Object i : ((EnumDeclaration) td).superInterfaceTypes()) ts.add((Type) i);
        }
        for (Type t : ts) {
            Owner o = resolveOwner(simpleTypeNameOf(t), cu, file, td);
            if (o != null && o.type != td) out.add(o);
        }
        return out;
    }

    private Set<String> collectAncestors(AbstractTypeDeclaration td, CompilationUnit cu, String file) {
        Set<String> out = new HashSet<>();
        Deque<Object[]> q = new ArrayDeque<>();
        q.add(new Object[]{td, cu, file, 0});
        Set<String> seen = new HashSet<>();
        while (!q.isEmpty()) {
            Object[] it = q.poll();
            AbstractTypeDeclaration t = (AbstractTypeDeclaration) it[0]; int d = (Integer) it[3];
            if (t == null || !seen.add(((String) it[2]) + "#" + t.getStartPosition()) || d > 8) continue;
            for (Owner sup : supertypes(t, (CompilationUnit) it[1], (String) it[2])) {
                out.add(sup.type.getName().getIdentifier());
                out.add(outermostName(sup.type));
                q.add(new Object[]{sup.type, sup.cu, sup.file, d + 1});
            }
        }
        return out;
    }

    private static AbstractTypeDeclaration findTypeInCu(CompilationUnit cu, String simple) {
        final AbstractTypeDeclaration[] hit = new AbstractTypeDeclaration[1];
        cu.accept(new ASTVisitor() {
            @Override public boolean visit(TypeDeclaration n) { return check(n); }
            @Override public boolean visit(EnumDeclaration n) { return check(n); }
            @Override public boolean visit(RecordDeclaration n) { return check(n); }
            private boolean check(AbstractTypeDeclaration n) {
                if (hit[0] == null && n.getName().getIdentifier().equals(simple)) hit[0] = n;
                return hit[0] == null;
            }
        });
        return hit[0];
    }

    private static Set<String> localNames(ASTNode scope) {
        Set<String> names = new HashSet<>();
        if (scope instanceof MethodDeclaration) for (Object p : ((MethodDeclaration) scope).parameters()) names.add(((SingleVariableDeclaration) p).getName().getIdentifier());
        scope.accept(new ASTVisitor() {
            @Override public boolean visit(VariableDeclarationFragment n) { names.add(n.getName().getIdentifier()); return true; }
            @Override public boolean visit(SingleVariableDeclaration n) { names.add(n.getName().getIdentifier()); return true; }
            @Override public boolean visit(LambdaExpression n) {
                for (Object p : n.parameters()) names.add(p instanceof VariableDeclaration ? ((VariableDeclaration) p).getName().getIdentifier() : p.toString());
                return true;
            }
        });
        return names;
    }

    private static String localDeclaredType(ASTNode scope, String var) {
        final String[] hit = new String[1];
        scope.accept(new ASTVisitor() {
            @Override public boolean visit(VariableDeclarationStatement n) {
                for (Object f : n.fragments()) if (((VariableDeclarationFragment) f).getName().getIdentifier().equals(var)) hit[0] = simpleTypeNameOf(n.getType());
                return true;
            }
            @Override public boolean visit(SingleVariableDeclaration n) {
                if (n.getName().getIdentifier().equals(var)) hit[0] = simpleTypeNameOf(n.getType());
                return true;
            }
        });
        return hit[0];
    }

    private boolean isDataContext(ExpressionMethodReference ref) {
        ASTNode n = ref, p = ref.getParent();
        while (p instanceof CastExpression || p instanceof ParenthesizedExpression) { n = p; p = p.getParent(); }
        if (p instanceof MethodInvocation) {
            MethodInvocation mi = (MethodInvocation) p;
            if (!mi.arguments().contains(n)) return false;          // target: 引用本身被调用
            return DATA_CTX_CALLS.contains(mi.getName().getIdentifier());
        }
        return true; // new:* / return / assign / array / lambda / conditional / other
    }

    private static AbstractTypeDeclaration enclosingType(ASTNode node) {
        for (ASTNode p = node.getParent(); p != null; p = p.getParent()) if (p instanceof AbstractTypeDeclaration) return (AbstractTypeDeclaration) p;
        return null;
    }

    private static String outermostName(AbstractTypeDeclaration td) {
        AbstractTypeDeclaration cur = td;
        for (ASTNode p = td.getParent(); p != null; p = p.getParent()) if (p instanceof AbstractTypeDeclaration) cur = (AbstractTypeDeclaration) p;
        return cur.getName().getIdentifier();
    }

    private static boolean isTypeName(Expression e) {
        if (e instanceof SimpleName) { String id = ((SimpleName) e).getIdentifier(); return Character.isUpperCase(id.charAt(0)) && !isConstantStyle(id); }
        if (e instanceof QualifiedName) {
            String id = ((QualifiedName) e).getName().getIdentifier();
            return Character.isUpperCase(id.charAt(0)) && !isConstantStyle(id);
        }
        return false;
    }

    private static String typeSimpleName(Expression e) {
        if (e instanceof SimpleName) return ((SimpleName) e).getIdentifier();
        if (e instanceof QualifiedName) return ((QualifiedName) e).getName().getIdentifier();
        return null;
    }

    private static boolean isConstantStyle(String id) {
        if (id.equals("NaN")) return true;
        if (id.isEmpty() || !Character.isUpperCase(id.charAt(0))) return false;
        boolean hasLetter = false;
        for (char c : id.toCharArray()) {
            if (Character.isLetter(c)) { hasLetter = true; if (Character.isLowerCase(c)) return false; }
        }
        return hasLetter;
    }

    private static String simpleTypeNameOf(Type t) {
        if (t == null) return null;
        String name = t.toString();
        int lt = name.indexOf('<'); if (lt >= 0) name = name.substring(0, lt);
        int br = name.indexOf('['); if (br >= 0) name = name.substring(0, br);
        int dot = name.lastIndexOf('.'); return dot >= 0 ? name.substring(dot + 1) : name;
    }

    private String packageOfFile(String file) {
        CompilationUnit cu = cuCache.computeIfAbsent(file, parser);
        return cu != null && cu.getPackage() != null ? cu.getPackage().getName().getFullyQualifiedName() : "";
    }

    private static String abbreviate(ASTNode n) {
        String s = n.toString().replace("\n", " ").replace(",", ";");
        return s.length() > 60 ? s.substring(0, 57) + "..." : s;
    }

    // =====================================================================================
    // Arity：参数组数（静态可数时）
    //   状态：EXACT / RUNTIME_DEPENDENT（跑起来才知道：production/JDK API 返回的集合、filter、带条件的循环、随机、环境）/
    //         STATIC_UNSUPPORTED（原则上静态但本计数器不处理的形态）/ UNRESOLVED_SOURCE（看不到源码：抽象 provider、外部字段、找不到的枚举/名字）
    //   规则（2026-09-19 定稿）：Stream.of/List.of/Arrays.asList/数组/多条 add；Type.builder().add(..).add(..).build()；保基数包装
    //   （map/sorted/collect/unmodifiableList/EnumSet.copyOf/StreamSupport.stream…）；Stream.concat 求和；固定循环与嵌套循环的乘积；
    //   lambda 体可数的 flatMap 取乘积；range/rangeClosed 与 for 边界支持 static final 常量与常量算术；limit/skip 在上游可数时精确；
    //   Enum.values()/EnumSet.allOf 取常量数；helper 递归；字段初始化器。不做更复杂的符号执行。
    // =====================================================================================
    public String lastCountFailReason = "";
    public String lastCountFailStatus = "";
    private boolean quietCount = false;
    private final Map<String, String[]> uncountableLocals = new HashMap<>();   // 局部变量名 → {status, reason}（初始化器不可数时）
    private final Set<String> arrayLocals = new HashSet<>();                  // 声明类型是数组的局部变量名（varargs 摊开判定用）
    private Integer nf(String status, String why) {
        if (!quietCount && lastCountFailReason.isEmpty()) { lastCountFailReason = why; lastCountFailStatus = status; }
        return null;
    }
    private static final String RUNTIME = "RUNTIME_DEPENDENT", UNSUPPORTED = "STATIC_UNSUPPORTED", UNRESOLVED = "UNRESOLVED_SOURCE";

    /** 探测局部变量初始化器是否可数时不记录失败原因（标量声明失败很正常）。 */
    private Integer countQuiet(Expression e, String file, AbstractTypeDeclaration type, Map<String, Integer> locals, int depth) {
        boolean prev = quietCount; quietCount = true;
        try { return countOf(e, file, type, locals, depth); } finally { quietCount = prev; }
    }

    /** 唯一实参是否是数组（数组会被 varargs 摊开）。纯语法判定：局部变量声明、字段声明类型、test-scope 方法的返回类型。 */
    private boolean spreadsAsVarargs(Expression a, String file, AbstractTypeDeclaration type) {
        if (a instanceof SimpleName) {
            String id = ((SimpleName) a).getIdentifier();
            if (arrayLocals.contains(id)) return true;
            FieldHit fh = findFieldInChain(type, cuCache.get(file), file, id);
            if (fh == null) fh = staticImportField(cuCache.get(file), id);
            return fh != null && fh.declaredTypeSimple != null && fh.declaredTypeSimple.endsWith("[]");
        }
        if (a instanceof MethodInvocation) {
            MethodInvocation m = (MethodInvocation) a;
            Expression recv = m.getExpression();
            Target tg = null;
            if (recv == null || recv instanceof ThisExpression) {
                tg = findMethodInChain(type, cuCache.get(file), file, m.getName().getIdentifier(), m.arguments().size());
            } else if (isTypeName(recv)) {
                Owner o = resolveOwner(typeSimpleName(recv), cuCache.get(file), file, type);
                if (o != null && o.isTest) tg = findMethodInChain(o.type, o.cu, o.file, m.getName().getIdentifier(), m.arguments().size());
            }
            return tg != null && tg.md.getReturnType2() instanceof ArrayType;
        }
        return false;
    }

    public Integer countSets(MethodDeclaration providerMd, String file) {
        lastCountFailReason = ""; lastCountFailStatus = ""; uncountableLocals.clear(); arrayLocals.clear();
        AbstractTypeDeclaration type = enclosingType(providerMd);
        return countSetsOfBody(providerMd, file, type, new HashMap<>(), 0);
    }

    private Integer countSetsOfBody(MethodDeclaration md, String file, AbstractTypeDeclaration type, Map<String, Integer> knownParams, int depth) {
        if (md.getBody() == null) return nf(UNRESOLVED, "abstract-provider:" + md.getName());
        if (depth > 6) return nf(UNSUPPORTED, "helper-depth>6");
        Map<String, Integer> localCounts = new HashMap<>(knownParams);   // 局部容器变量 → 当前已知元素数
        Integer ret = countStatements(md.getBody().statements(), file, type, localCounts, depth, 1);
        return ret;
    }

    /**
     * 顺序执行一段语句，维护容器计数；返回 return 语句的计数（没有 return 返回 -1 表示"继续"）。
     * multiplier = 所在循环的迭代次数乘积（循环体内的 add 每次 +multiplier）。
     */
    private Integer countStatements(List<?> statements, String file, AbstractTypeDeclaration type, Map<String, Integer> localCounts, int depth, int multiplier) {
        for (Object o : statements) {
            Statement st = (Statement) o;
            if (st instanceof VariableDeclarationStatement) {
                boolean declIsArray = ((VariableDeclarationStatement) st).getType() instanceof ArrayType;
                for (Object f : ((VariableDeclarationStatement) st).fragments()) {
                    VariableDeclarationFragment frag = (VariableDeclarationFragment) f;
                    if (declIsArray || frag.getExtraDimensions() > 0) arrayLocals.add(frag.getName().getIdentifier());
                    String saveR = lastCountFailReason, saveS = lastCountFailStatus;
                    lastCountFailReason = ""; lastCountFailStatus = "";
                    boolean prevQ = quietCount; quietCount = false;
                    Integer c = frag.getInitializer() == null ? null : countOf(frag.getInitializer(), file, type, localCounts, depth);
                    quietCount = prevQ;
                    if (c != null) { localCounts.put(frag.getName().getIdentifier(), c); uncountableLocals.remove(frag.getName().getIdentifier()); }
                    else uncountableLocals.put(frag.getName().getIdentifier(), new String[]{lastCountFailStatus.isEmpty() ? UNSUPPORTED : lastCountFailStatus, lastCountFailReason});
                    lastCountFailReason = saveR; lastCountFailStatus = saveS;
                }
            } else if (st instanceof ExpressionStatement) {
                Expression e = ((ExpressionStatement) st).getExpression();
                if (e instanceof MethodInvocation) {
                    MethodInvocation mi = (MethodInvocation) e;
                    String name = mi.getName().getIdentifier();
                    Expression recv = mi.getExpression();
                    // 链式：b.add(x).add(y);  —— 找到链根变量
                    Expression root = recv; int chainAdds = 0;
                    while (root instanceof MethodInvocation) {
                        MethodInvocation inner = (MethodInvocation) root;
                        if (inner.getName().getIdentifier().equals("add") || inner.getName().getIdentifier().equals("accept")) chainAdds++;
                        else if (!COUNT_PRESERVING.contains(inner.getName().getIdentifier())) { chainAdds = -1; break; }
                        root = inner.getExpression();
                    }
                    // 实参（通常是 lambda）里碰到了被跟踪的容器：x.forEach(d -> b.accept(..)) 可数时 +count(x)×adds，否则运行时
                    String touchedInArgs = null;
                    for (Object a : mi.arguments()) { touchedInArgs = trackedContainerTouched((ASTNode) a, localCounts.keySet()); if (touchedInArgs != null) break; }
                    if (touchedInArgs != null) {
                        if (name.equals("forEach") && recv != null && mi.arguments().size() == 1 && mi.arguments().get(0) instanceof LambdaExpression) {
                            Integer adds = lambdaAdds((LambdaExpression) mi.arguments().get(0), touchedInArgs);
                            Integer n = adds == null ? null : countOf(recv, file, type, localCounts, depth);
                            if (adds == null) return nf(RUNTIME, "forEach-lambda-logic");
                            if (n == null) return nf(lastCountFailStatus.isEmpty() ? RUNTIME : lastCountFailStatus, "forEach-over:" + abbreviate(recv));
                            localCounts.merge(touchedInArgs, multiplier * n * adds, Integer::sum);
                        } else return nf(RUNTIME, "container-mutated-in:" + name);
                        continue;
                    }
                    if (root instanceof SimpleName && localCounts.containsKey(((SimpleName) root).getIdentifier()) && chainAdds >= 0) {
                        String var = ((SimpleName) root).getIdentifier();
                        if (name.equals("add") || name.equals("put") || name.equals("offer") || name.equals("push") || name.equals("accept")) localCounts.merge(var, multiplier * (chainAdds + 1), Integer::sum);
                        else if (name.equals("addAll") && mi.arguments().size() == 1) {
                            Integer c = countOf((Expression) mi.arguments().get(0), file, type, localCounts, depth);
                            if (c == null) return nf(lastCountFailStatus.isEmpty() ? RUNTIME : lastCountFailStatus, "addAll:" + abbreviate(mi));
                            localCounts.merge(var, multiplier * (c + chainAdds), Integer::sum);
                        } else if (name.equals("clear")) localCounts.put(var, 0);
                        else if (chainAdds > 0 && (name.equals("build") || COUNT_PRESERVING.contains(name))) localCounts.merge(var, multiplier * chainAdds, Integer::sum);
                        else if (name.equals("remove") || name.equals("removeIf") || name.equals("removeAll") || name.equals("retainAll") || name.equals("set")) return nf(RUNTIME, "container-mutation:" + name);
                        else if (!(name.equals("forEach") || name.equals("sort") || name.equals("trimToSize"))) return nf(UNSUPPORTED, "container-op:" + name);
                    } else {
                        // 把容器交给别的方法去填充 → 运行时
                        for (Object a : mi.arguments()) {
                            if (a instanceof SimpleName && localCounts.containsKey(((SimpleName) a).getIdentifier())) return nf(RUNTIME, "container-passed-to:" + name);
                        }
                    }
                } else if (e instanceof Assignment && ((Assignment) e).getLeftHandSide() instanceof SimpleName) {
                    Integer c = countQuiet(((Assignment) e).getRightHandSide(), file, type, localCounts, depth);
                    String var = ((SimpleName) ((Assignment) e).getLeftHandSide()).getIdentifier();
                    if (c != null) localCounts.put(var, c); else localCounts.remove(var);
                } else if (!(e instanceof Assignment || e instanceof PostfixExpression || e instanceof PrefixExpression)) {
                    return nf(UNSUPPORTED, "statement:" + e.getClass().getSimpleName());
                }
            } else if (st instanceof ReturnStatement) {
                return countOf(((ReturnStatement) st).getExpression(), file, type, localCounts, depth);
            } else if (st instanceof EnhancedForStatement || st instanceof ForStatement) {
                Integer iters = loopIterations(st, file, type, localCounts, depth);
                if (iters == null) return null; // nf 已记录
                Statement body = st instanceof EnhancedForStatement ? ((EnhancedForStatement) st).getBody() : ((ForStatement) st).getBody();
                List<?> inner = body instanceof Block ? ((Block) body).statements() : Collections.singletonList(body);
                // 循环体里不允许 return；其它语句按 multiplier 累加
                Integer r = countStatements(inner, file, type, localCounts, depth, multiplier * iters);
                if (r != null && r >= 0) return nf(UNSUPPORTED, "return-inside-loop");
                if (r == null && !lastCountFailReason.isEmpty() && !quietCount) return null;
            } else if (st instanceof IfStatement) {
                return nf(RUNTIME, "control-flow:if");
            } else if (st instanceof TryStatement) {
                // try 只包着 IO/资源：体里没有容器操作就忽略，否则运行时
                return nf(RUNTIME, "control-flow:try");
            } else if (st instanceof EmptyStatement || st instanceof TypeDeclarationStatement) {
                continue;
            } else {
                return nf(RUNTIME, "control-flow:" + st.getClass().getSimpleName());
            }
        }
        return -1;   // 没遇到 return（循环体 / 落空）
    }

    /** 语句子树里被引用的、正在跟踪的容器名（不含作为接收者的顶层调用）；没有返回 null。 */
    private static String trackedContainerTouched(ASTNode node, Set<String> tracked) {
        final String[] hit = {null};
        node.accept(new ASTVisitor() {
            @Override public boolean visit(SimpleName n) { if (hit[0] == null && tracked.contains(n.getIdentifier())) hit[0] = n.getIdentifier(); return false; }
        });
        return hit[0];
    }

    /** lambda 体：只允许 b.add/accept(...) 语句（表达式体或块体），返回每次执行的 add 次数；含其它逻辑返回 null。 */
    private static Integer lambdaAdds(LambdaExpression le, String container) {
        List<Expression> exprs = new ArrayList<>();
        if (le.getBody() instanceof Expression) exprs.add((Expression) le.getBody());
        else for (Object st : ((Block) le.getBody()).statements()) {
            if (!(st instanceof ExpressionStatement)) return null;
            exprs.add(((ExpressionStatement) st).getExpression());
        }
        int adds = 0;
        for (Expression e : exprs) {
            if (!(e instanceof MethodInvocation)) return null;
            MethodInvocation mi = (MethodInvocation) e;
            if (!(mi.getExpression() instanceof SimpleName) || !((SimpleName) mi.getExpression()).getIdentifier().equals(container)) return null;
            String n = mi.getName().getIdentifier();
            if (!(n.equals("add") || n.equals("accept") || n.equals("put") || n.equals("offer"))) return null;
            adds++;
        }
        return adds;
    }

    /** 固定循环的迭代次数：for (X x : 可数表达式) / for (int i = A; i < B; i++)，A/B 为字面量或 static final 常量（含常量算术）。 */
    private Integer loopIterations(Statement st, String file, AbstractTypeDeclaration type, Map<String, Integer> locals, int depth) {
        if (st instanceof EnhancedForStatement) {
            Integer n = countOf(((EnhancedForStatement) st).getExpression(), file, type, locals, depth);
            if (n == null) return nf(lastCountFailStatus.isEmpty() ? RUNTIME : lastCountFailStatus, "loop-over:" + abbreviate(((EnhancedForStatement) st).getExpression()));
            return n;
        }
        ForStatement fs = (ForStatement) st;
        if (fs.initializers().size() != 1 || fs.updaters().size() != 1 || !(fs.getExpression() instanceof InfixExpression)) return nf(UNSUPPORTED, "for-shape");
        Object init = fs.initializers().get(0);
        String var; Long start;
        if (init instanceof VariableDeclarationExpression && ((VariableDeclarationExpression) init).fragments().size() == 1) {
            VariableDeclarationFragment fr = (VariableDeclarationFragment) ((VariableDeclarationExpression) init).fragments().get(0);
            var = fr.getName().getIdentifier(); start = constValue(fr.getInitializer(), file, type);
        } else if (init instanceof Assignment && ((Assignment) init).getLeftHandSide() instanceof SimpleName) {
            var = ((SimpleName) ((Assignment) init).getLeftHandSide()).getIdentifier(); start = constValue(((Assignment) init).getRightHandSide(), file, type);
        } else return nf(UNSUPPORTED, "for-shape");
        if (start == null) return nf(RUNTIME, "for-start-nonconst");
        InfixExpression cond = (InfixExpression) fs.getExpression();
        Object upd = fs.updaters().get(0);
        String updS = upd.toString().replace(" ", "");
        long step;
        if (updS.equals(var + "++") || updS.equals("++" + var) || updS.equals(var + "+=1")) step = 1;
        else if (updS.equals(var + "--") || updS.equals("--" + var) || updS.equals(var + "-=1")) step = -1;
        else if (updS.startsWith(var + "+=")) { Long k = constValue(((Assignment) upd).getRightHandSide(), file, type); if (k == null || k == 0) return nf(RUNTIME, "for-step"); step = k; }
        else return nf(UNSUPPORTED, "for-updater:" + updS);
        if (!(cond.getLeftOperand() instanceof SimpleName) || !((SimpleName) cond.getLeftOperand()).getIdentifier().equals(var)) return nf(UNSUPPORTED, "for-cond-shape");
        Long bound = constValue(cond.getRightOperand(), file, type);
        if (bound == null) return nf(RUNTIME, "for-bound-nonconst:" + abbreviate(cond.getRightOperand()));
        String op = cond.getOperator().toString();
        long n;
        if (step > 0 && op.equals("<")) n = Math.max(0, (bound - start + step - 1) / step);
        else if (step > 0 && op.equals("<=")) n = Math.max(0, (bound - start) / step + 1);
        else if (step < 0 && op.equals(">")) n = Math.max(0, (start - bound - step - 1) / -step);
        else if (step < 0 && op.equals(">=")) n = Math.max(0, (start - bound) / -step + 1);
        else return nf(UNSUPPORTED, "for-cond-op:" + op);
        return (int) n;
    }

    /** 整数常量求值：字面量、static final 常量（本类/祖先/其它测试类 Type.CONST）、常量算术（+ - * / << >>）、括号、一元负。 */
    private Long constValue(Expression e, String file, AbstractTypeDeclaration type) {
        if (e == null) return null;
        if (e instanceof NumberLiteral) {
            String tok = ((NumberLiteral) e).getToken().replace("_", "").replaceAll("[lL]$", "");
            try { return tok.startsWith("0x") || tok.startsWith("0X") ? Long.parseLong(tok.substring(2), 16) : Long.parseLong(tok); } catch (NumberFormatException ex) { return null; }
        }
        if (e instanceof ParenthesizedExpression) return constValue(((ParenthesizedExpression) e).getExpression(), file, type);
        if (e instanceof CastExpression) return constValue(((CastExpression) e).getExpression(), file, type);
        if (e instanceof PrefixExpression && ((PrefixExpression) e).getOperator() == PrefixExpression.Operator.MINUS) { Long v = constValue(((PrefixExpression) e).getOperand(), file, type); return v == null ? null : -v; }
        if (e instanceof InfixExpression) {
            InfixExpression ie = (InfixExpression) e;
            Long a = constValue(ie.getLeftOperand(), file, type), b = constValue(ie.getRightOperand(), file, type);
            if (a == null || b == null) return null;
            String op = ie.getOperator().toString(); Long v;
            switch (op) { case "+": v = a + b; break; case "-": v = a - b; break; case "*": v = a * b; break; case "/": v = b == 0 ? null : a / b; break; case "<<": v = a << b; break; case ">>": v = a >> b; break; default: return null; }
            for (Object o : ie.extendedOperands()) { Long c = constValue((Expression) o, file, type); if (c == null || v == null) return null; switch (op) { case "+": v += c; break; case "-": v -= c; break; case "*": v *= c; break; default: return null; } }
            return v;
        }
        FieldHit fh = null;
        if (e instanceof SimpleName) fh = findFieldInChain(type, cuCache.get(file), file, ((SimpleName) e).getIdentifier());
        else if (e instanceof QualifiedName && isTypeName(((QualifiedName) e).getQualifier())) {
            Owner o = resolveOwner(typeSimpleName(((QualifiedName) e).getQualifier()), cuCache.get(file), file, type);
            if (o != null) fh = findFieldInChain(o.type, o.cu, o.file, ((QualifiedName) e).getName().getIdentifier());
        }
        if (fh != null && fh.fragment.getInitializer() != null && fh.fragment.getParent() instanceof FieldDeclaration
                && Modifier.isFinal(((FieldDeclaration) fh.fragment.getParent()).getModifiers()))
            return constValue(fh.fragment.getInitializer(), fh.file, fh.type);
        return null;
    }

    private static final Set<String> DATA_CONTAINER_TYPES = Set.of("ArrayList", "LinkedList", "HashMap", "LinkedHashMap", "TreeMap", "HashSet",
            "LinkedHashSet", "TreeSet", "ArrayDeque", "Vector", "Stack", "CopyOnWriteArrayList", "ConcurrentHashMap", "EnumMap", "List", "Set", "Map");
    private static final Set<String> KNOWN_BUILDERS = Set.of("Stream", "IntStream", "LongStream", "DoubleStream", "ImmutableList", "ImmutableSet",
            "ImmutableMap", "ImmutableSortedSet", "ImmutableSortedMap", "ImmutableMultimap", "ImmutableCollection");
    private static final Set<String> COUNT_PRESERVING = Set.of("map", "mapToObj", "mapToInt", "mapToLong", "mapToDouble", "boxed",
            "stream", "parallelStream", "sorted", "peek", "collect", "toList", "toArray", "sequential", "parallel", "unordered",
            "asList", "unmodifiableList", "unmodifiableSet", "unmodifiableCollection", "unmodifiableMap", "synchronizedList", "copyOf", "build",
            "values", "keySet", "entrySet", "iterator", "asIterable", "asLongStream", "asDoubleStream", "mapToPair", "onClose");
    private static final Set<String> ELEMENTS_ARE_ARGS = Set.of("of", "asList", "listOf", "setOf", "arguments", "argumentSet", "newArrayList", "newHashSet");
    private static final Set<String> RUNTIME_OPS = Set.of("filter", "takeWhile", "dropWhile", "distinct", "generate", "iterate", "flatMapToInt",
            "flatMapToLong", "flatMapToDouble", "flatMapToObj", "mapMulti", "shuffle");

    private Integer countOf(Expression e, String file, AbstractTypeDeclaration type, Map<String, Integer> locals, int depth) {
        if (e == null) return nf(UNSUPPORTED, "null-expr");
        if (e instanceof ParenthesizedExpression) return countOf(((ParenthesizedExpression) e).getExpression(), file, type, locals, depth);
        if (e instanceof CastExpression) return countOf(((CastExpression) e).getExpression(), file, type, locals, depth);
        if (e instanceof ArrayInitializer) return ((ArrayInitializer) e).expressions().size();
        if (e instanceof ArrayCreation) {
            ArrayCreation ac = (ArrayCreation) e;
            if (ac.getInitializer() != null) return ac.getInitializer().expressions().size();
            if (ac.dimensions().size() >= 1) { Long d = constValue((Expression) ac.dimensions().get(0), file, type); if (d == null) return nf(RUNTIME, "array-dim-nonconst"); return d.intValue(); }
            return nf(UNSUPPORTED, "array-shape");
        }
        if (e instanceof SimpleName) {
            String id = ((SimpleName) e).getIdentifier();
            if (locals.containsKey(id)) return locals.get(id);
            if (uncountableLocals.containsKey(id)) { String[] u = uncountableLocals.get(id); return nf(u[0], "local:" + id + "<-" + u[1]); }
            FieldHit fh = findFieldInChain(type, cuCache.get(file), file, id);
            if (fh == null) fh = staticImportField(cuCache.get(file), id);
            if (fh != null) {
                if (fh.fragment.getInitializer() == null) return nf(RUNTIME, "field-no-initializer:" + id);
                if (mutatedInInitializerBlock(fh)) return nf(RUNTIME, "field-static-block:" + id);
                return countOf(fh.fragment.getInitializer(), fh.file, fh.type, new HashMap<>(), depth + 1);
            }
            return nf(UNRESOLVED, "name:" + id);
        }
        if (e instanceof QualifiedName) {
            QualifiedName qn = (QualifiedName) e;
            if (!isTypeName(qn.getQualifier())) return nf(UNSUPPORTED, "field-of-expr:" + abbreviate(qn));
            Owner o = resolveOwner(typeSimpleName(qn.getQualifier()), cuCache.get(file), file, type);
            if (o == null) return nf(UNRESOLVED, "external-field:" + abbreviate(qn));
            if (!o.isTest) return nf(RUNTIME, "production-field:" + abbreviate(qn));
            FieldHit fh = findFieldInChain(o.type, o.cu, o.file, qn.getName().getIdentifier());
            if (fh == null) return nf(UNRESOLVED, "field-not-found:" + abbreviate(qn));
            if (fh.fragment.getInitializer() == null) return nf(RUNTIME, "field-no-initializer:" + abbreviate(qn));
            if (mutatedInInitializerBlock(fh)) return nf(RUNTIME, "field-static-block:" + abbreviate(qn));
            return countOf(fh.fragment.getInitializer(), fh.file, fh.type, new HashMap<>(), depth + 1);
        }
        if (e instanceof ClassInstanceCreation) {
            ClassInstanceCreation cic = (ClassInstanceCreation) e;
            String ctype = simpleTypeNameOf(cic.getType());
            if (cic.getAnonymousClassDeclaration() != null) return nf(UNSUPPORTED, "anonymous-body:" + ctype);   // 双花括号初始化 / 匿名子类
            if (!DATA_CONTAINER_TYPES.contains(ctype)) {
                Owner o = resolveOwner(ctype, cuCache.get(file), file, type);
                return nf(o != null && o.isTest ? UNSUPPORTED : RUNTIME, "new-object:" + ctype);   // 不是集合：new Suite() / new Builder() 的元素数看不出
            }
            if (cic.arguments().isEmpty()) return 0;                         // new ArrayList<>()
            if (cic.arguments().size() == 1) {
                Expression a = (Expression) cic.arguments().get(0);
                if (a instanceof NumberLiteral) return 0;                    // 容量
                Integer c = countQuiet(a, file, type, locals, depth);       // new ArrayList<>(List.of(a, b))
                return c != null ? c : nf(UNSUPPORTED, "new-with-arg:" + simpleTypeNameOf(cic.getType()));
            }
            return nf(UNSUPPORTED, "new-multi-arg:" + simpleTypeNameOf(cic.getType()));
        }
        if (e instanceof ConditionalExpression) {
            ConditionalExpression ce = (ConditionalExpression) e;
            Integer a = countQuiet(ce.getThenExpression(), file, type, locals, depth), b = countQuiet(ce.getElseExpression(), file, type, locals, depth);
            if (a != null && a.equals(b)) return a;
            return nf(RUNTIME, "conditional");
        }
        if (e instanceof MethodInvocation) {
            MethodInvocation mi = (MethodInvocation) e;
            String name = mi.getName().getIdentifier();
            Expression recv = mi.getExpression();
            boolean typeRecv = recv != null && isTypeName(recv);
            // Stream.of(a, b, c) / List.of / Arrays.asList / Set.of：元素 = 实参个数（单个数组实参则取数组长度）
            if (ELEMENTS_ARE_ARGS.contains(name) && (recv == null || typeRecv)) {
                boolean isArgumentsFactory = (typeRecv && typeSimpleName(recv).equals("Arguments")) || name.equals("arguments") || name.equals("argumentSet");
                if (isArgumentsFactory) return 1;                        // Arguments.of(...) 本身就是一组
                if (mi.arguments().size() == 1) {
                    Expression a = (Expression) mi.arguments().get(0);
                    if (a instanceof ArrayCreation || a instanceof ArrayInitializer) return countOf(a, file, type, locals, depth);
                    if (a instanceof SimpleName || a instanceof QualifiedName || a instanceof MethodInvocation) {
                        // 唯一实参是数组时 varargs 会把它摊开（Stream.of(File[]) / Arrays.asList(byte[][])），
                        // 元素数 = 数组长度而非 1。数不出来就如实失败——绝不能回退到 arguments().size()，
                        // 那会把"未知"变成一个看着合理的 1（pdfbox TestRendering.render 就是这么错的）。
                        if (spreadsAsVarargs(a, file, type)) return countOf(a, file, type, locals, depth);
                        Integer c = countQuiet(a, file, type, locals, depth);
                        if (c != null) return c;
                    }
                }
                return mi.arguments().size();
            }
            if (typeRecv) {
                String t = typeSimpleName(recv);
                if (name.equals("builder") && mi.arguments().isEmpty()) {                                              // Stream.builder() / ImmutableList.builder()
                    if (KNOWN_BUILDERS.contains(t)) return 0;
                    Owner ob = resolveOwner(t, cuCache.get(file), file, type);
                    if (ob == null || !ob.isTest) return nf(RUNTIME, "api-builder:" + t);
                    // 项目内的 builder：走 helper 递归（多半 new Builder() → 判 new-object）
                }
                if (name.equals("concat") && mi.arguments().size() == 2) {
                    Integer a = countOf((Expression) mi.arguments().get(0), file, type, locals, depth); if (a == null) return null;
                    Integer b = countOf((Expression) mi.arguments().get(1), file, type, locals, depth); return b == null ? null : a + b;
                }
                if ((name.equals("range") || name.equals("rangeClosed")) && mi.arguments().size() == 2) {
                    Long lo = constValue((Expression) mi.arguments().get(0), file, type), hi = constValue((Expression) mi.arguments().get(1), file, type);
                    if (lo == null || hi == null) return nf(RUNTIME, "range-bound-nonconst");
                    return (int) Math.max(0, name.equals("range") ? hi - lo : hi - lo + 1);
                }
                if (name.equals("values") && mi.arguments().isEmpty()) {
                    Owner o = resolveOwner(t, cuCache.get(file), file, type);
                    if (o != null && o.type instanceof EnumDeclaration) return ((EnumDeclaration) o.type).enumConstants().size();
                    return o == null ? nf(UNRESOLVED, "values-of-external-enum:" + t) : nf(UNSUPPORTED, "values-of-non-enum:" + t);
                }
                if (t.equals("EnumSet") && (name.equals("allOf") || name.equals("complementOf") || name.equals("noneOf")) && mi.arguments().size() == 1 && mi.arguments().get(0) instanceof TypeLiteral) {
                    String en = simpleTypeNameOf(((TypeLiteral) mi.arguments().get(0)).getType());
                    Owner o = resolveOwner(en, cuCache.get(file), file, type);
                    if (o != null && o.type instanceof EnumDeclaration) return name.equals("noneOf") ? 0 : ((EnumDeclaration) o.type).enumConstants().size();
                    return nf(UNRESOLVED, "enumset-of-external:" + en);
                }
                if ((name.equals("stream") || name.equals("copyOf") || name.equals("unmodifiableList") || name.equals("unmodifiableSet") || name.equals("unmodifiableCollection")
                        || name.equals("synchronizedList") || name.equals("newArrayList") || name.equals("newHashSet") || name.equals("newLinkedList")) && mi.arguments().size() >= 1) {
                    return countOf((Expression) mi.arguments().get(0), file, type, locals, depth);              // Arrays.stream(arr) / StreamSupport.stream(it, false) / Collections.unmodifiableList(x)
                }
                if (name.equals("cartesianProduct")) {
                    long prod = 1;
                    for (Object a : mi.arguments()) { Integer c = countOf((Expression) a, file, type, locals, depth); if (c == null) return null; prod *= c; }
                    return (int) prod;
                }
                // test helper：递归数它的返回
                Owner o = resolveOwner(t, cuCache.get(file), file, type);
                if (o != null && o.isTest) {
                    Target tg = findMethodInChain(o.type, o.cu, o.file, name, mi.arguments().size());
                    if (tg != null && depth < 6) { Integer r = countSetsOfBody(tg.md, tg.file, tg.type, new HashMap<>(), depth + 1); return r == null || r < 0 ? (r == null ? null : nf(UNSUPPORTED, "helper-no-return:" + name)) : r; }
                    return nf(UNRESOLVED, "helper-not-found:" + t + "." + name);
                }
                return nf(RUNTIME, "api-call:" + t + "." + name);                                              // production / JDK API 返回的集合
            }
            if (recv == null || recv instanceof ThisExpression) {
                Target tg = findMethodInChain(type, cuCache.get(file), file, name, mi.arguments().size());
                if (tg == null) tg = staticImportMethod(cuCache.get(file), name);
                if (tg != null && depth < 6) { Integer r = countSetsOfBody(tg.md, tg.file, tg.type, new HashMap<>(), depth + 1); return r == null || r < 0 ? (r == null ? null : nf(UNSUPPORTED, "helper-no-return:" + name)) : r; }
                return nf(tg == null ? RUNTIME : UNSUPPORTED, (tg == null ? "api-call:" : "helper-depth:") + name);
            }
            // 对象上的调用：流水线 / 链式 builder
            if (name.equals("add") || name.equals("accept")) { Integer c = countOf(recv, file, type, locals, depth); return c == null ? null : c + 1; }
            if (name.equals("addAll") && mi.arguments().size() == 1) { Integer c = countOf(recv, file, type, locals, depth); if (c == null) return null; Integer d = countOf((Expression) mi.arguments().get(0), file, type, locals, depth); return d == null ? null : c + d; }
            if (COUNT_PRESERVING.contains(name)) return countOf(recv, file, type, locals, depth);
            if (name.equals("limit") || name.equals("skip")) {
                Integer c = countOf(recv, file, type, locals, depth); if (c == null) return null;
                Long k = mi.arguments().size() == 1 ? constValue((Expression) mi.arguments().get(0), file, type) : null;
                if (k == null) return nf(RUNTIME, name + "-nonconst");
                return name.equals("limit") ? (int) Math.min(c, k) : (int) Math.max(0, c - k);
            }
            if (name.equals("flatMap") && mi.arguments().size() == 1) {
                Integer outer = countOf(recv, file, type, locals, depth); if (outer == null) return null;
                Expression fn = (Expression) mi.arguments().get(0);
                if (fn instanceof LambdaExpression && ((LambdaExpression) fn).getBody() instanceof Expression) {
                    Map<String, Integer> inner = new HashMap<>(locals);
                    for (Object p : ((LambdaExpression) fn).parameters()) inner.remove(p instanceof VariableDeclaration ? ((VariableDeclaration) p).getName().getIdentifier() : p.toString());
                    Integer in = countQuiet((Expression) ((LambdaExpression) fn).getBody(), file, type, inner, depth);
                    if (in != null) return outer * in;
                }
                return nf(RUNTIME, "flatMap-inner-uncountable");
            }
            if (RUNTIME_OPS.contains(name)) return nf(RUNTIME, "stream-op:" + name);
            return nf(RUNTIME, "call-on-object:" + name);
        }
        if (e instanceof LambdaExpression || e instanceof MethodReference) return nf(UNSUPPORTED, "function-value");
        if (e instanceof NumberLiteral || e instanceof StringLiteral || e instanceof BooleanLiteral || e instanceof NullLiteral || e instanceof CharacterLiteral || e instanceof TypeLiteral)
            return nf(UNSUPPORTED, "scalar-return");
        return nf(UNSUPPORTED, "expr:" + e.getClass().getSimpleName());
    }
}
