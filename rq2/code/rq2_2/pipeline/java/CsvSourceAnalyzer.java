import org.eclipse.jdt.core.dom.*;
import java.nio.file.*;
import java.util.*;

/**
 * @CsvSource：construction 固定 Literal-Primitive（CSV 文本）；dependency 与 ValueSource 同（元素里的常量拼接、静态导入）；
 * arity：n_params × n_sets（value 数组元素数，或 textBlock 的非空、非 # 注释行数；useHeadersInDisplayName=true 时减 1）；
 * 另给 n_columns（第一行按 delimiter 切出的列数）。
 */
public class CsvSourceAnalyzer {
    public static void main(String[] args) throws Exception {
        List<String[]> rows = ValueSourceAnalyzer.readCsvPublic(args[0]);
        String[] header = rows.get(0);
        int iRoot = ValueSourceAnalyzer.idxPublic(header, "project_root"), iName = ValueSourceAnalyzer.idxPublic(header, "test_name"), iFile = ValueSourceAnalyzer.idxPublic(header, "test_source_file");
        List<String[]> out = new ArrayList<>();
        out.add(ValueSourceAnalyzer.appendPublic(header, "form", "construction", "param_kinds", "n_params", "n_sets", "n_columns", "dependency", "hits_production", "dependency_reason", "n_constant_refs", "artifacts", "note"));
        Map<String, CompilationUnit> cuCache = new HashMap<>();
        Map<String, Map<String, List<Path>>> idxCache = new HashMap<>();
        for (int i = 1; i < rows.size(); i++) {
            String[] row = rows.get(i);
            String testFile = row[iFile], testName = row[iName];
            if (testFile == null || testFile.isBlank()) { out.add(ValueSourceAnalyzer.appendPublic(row, "", "", "", "", "", "", "", "", "", "", "", "TEST_FILE_UNKNOWN")); continue; }
            try {
                Map<String, List<Path>> fileIndex = idxCache.computeIfAbsent(row[iRoot], r -> ConstructionDependencyClassifier.fileIndexFor(Paths.get(r)));
                CompilationUnit cu = cuCache.computeIfAbsent(testFile, ConstructionDependencyClassifier::parseQuiet);
                if (cu == null) { out.add(ValueSourceAnalyzer.appendPublic(row, "", "", "", "", "", "", "", "", "", "", "", "TEST_FILE_PARSE_ERROR")); continue; }
                MethodDeclaration md = findMethodWith(cu, testName, "CsvSource");
                if (md == null) { out.add(ValueSourceAnalyzer.appendPublic(row, "", "", "", "", "", "", "", "", "", "", "", "TEST_METHOD_NOT_FOUND")); continue; }
                Annotation ann = annotationNamed(md, "CsvSource");
                if (ann == null) { out.add(ValueSourceAnalyzer.appendPublic(row, "", "", "", "", "", "", "", "", "", "", "", "NO_CSVSOURCE_ANNOTATION")); continue; }
                List<Expression> elements = new ArrayList<>();
                String form = "array"; String delimiter = ","; boolean headers = false; String textBlock = null;
                if (ann instanceof SingleMemberAnnotation) {
                    Expression v = ((SingleMemberAnnotation) ann).getValue();
                    if (v instanceof ArrayInitializer) for (Object e : ((ArrayInitializer) v).expressions()) elements.add((Expression) e); else elements.add(v);
                } else if (ann instanceof NormalAnnotation) {
                    for (Object o : ((NormalAnnotation) ann).values()) {
                        MemberValuePair mvp = (MemberValuePair) o; String n = mvp.getName().getIdentifier(); Expression v = mvp.getValue();
                        if (n.equals("value")) { if (v instanceof ArrayInitializer) for (Object e : ((ArrayInitializer) v).expressions()) elements.add((Expression) e); else elements.add(v); }
                        else if (n.equals("textBlock")) { form = "textBlock"; textBlock = v instanceof TextBlock ? ((TextBlock) v).getLiteralValue() : v instanceof StringLiteral ? ((StringLiteral) v).getLiteralValue() : null; elements.add(v); }
                        else if (n.equals("delimiter") && v instanceof CharacterLiteral) delimiter = String.valueOf(((CharacterLiteral) v).charValue());
                        else if (n.equals("delimiterString") && v instanceof StringLiteral) delimiter = ((StringLiteral) v).getLiteralValue();
                        else if (n.equals("useHeadersInDisplayName") && v instanceof BooleanLiteral) headers = ((BooleanLiteral) v).booleanValue();
                    }
                }
                int nSets; String firstLine = null;
                if (form.equals("textBlock")) {
                    List<String> lines = new ArrayList<>();
                    if (textBlock != null) for (String l : textBlock.split("\\r?\\n")) { String t = l.strip(); if (!t.isEmpty() && !t.startsWith("#")) lines.add(t); }
                    nSets = lines.size(); if (!lines.isEmpty()) firstLine = lines.get(0);
                } else {
                    nSets = elements.size();
                    if (!elements.isEmpty() && elements.get(0) instanceof StringLiteral) firstLine = ((StringLiteral) elements.get(0)).getLiteralValue();
                }
                if (headers && nSets > 0) nSets--;
                int nColumns = firstLine == null ? -1 : firstLine.split(java.util.regex.Pattern.quote(delimiter), -1).length;
                int nParams = 0;
                for (Object p : md.parameters()) { String t = ((SingleVariableDeclaration) p).getType().toString(); if (!(t.endsWith("TestInfo") || t.endsWith("TestReporter") || t.endsWith("RepetitionInfo"))) nParams++; }
                int constRefs = 0;
                for (Expression e : elements) if (!ValueSourceAnalyzer.isPlainLiteralPublic(e)) constRefs++;
                AbstractTypeDeclaration type = null;
                for (ASTNode p = md.getParent(); p != null; p = p.getParent()) if (p instanceof AbstractTypeDeclaration) { type = (AbstractTypeDeclaration) p; break; }
                ArtifactWalker walker = new ArtifactWalker(fileIndex, cuCache, ConstructionDependencyClassifier::parseQuiet, testFile, cu, md);
                ArtifactWalker.Result r = walker.analyzeExpressions(elements, testFile, cu, type);
                // construction 按 CSV 字符串要转换成的目标参数类型：
                //   primitive/String → Literal-Primitive；Class<?> → Literal-Metadata；
                //   枚举 / JUnit 隐式转换支持的 JDK 类型（BigDecimal、File、Path、Charset、URI、UUID、java.time.*…）/
                //   带 String 单参构造或 valueOf/of/parse(String) 工厂的项目类型 / @ConvertWith → 也是 Literal-Primitive：
                //   注解里写的仍然是字面量，转换由 JUnit 在注入时完成，不属于「需要执行逻辑才能得到参数值」。
                //   细分信息保留在 param_kinds 列的 converted: 前缀里，没有丢。
                //   其它（SMTPMessageSender、MiniCluster 这类由扩展注入的）→ injected，不参与分类。
                List<String> kinds = new ArrayList<>();
                for (Object p : md.parameters()) {
                    SingleVariableDeclaration sv = (SingleVariableDeclaration) p;
                    String t = sv.getType().toString(); String base = t.replaceAll("<.*>", "").replaceAll("\\[\\]", ""); base = base.substring(base.lastIndexOf('.') + 1);
                    boolean convertWith = false;
                    for (Object m : sv.modifiers()) if (m instanceof Annotation) { String an = ((Annotation) m).getTypeName().getFullyQualifiedName(); if (an.endsWith("ConvertWith") || an.endsWith("JavaTimeConversionPattern") || an.endsWith("AggregateWith")) convertWith = true; }
                    String kind;
                    if (base.endsWith("TestInfo") || base.endsWith("TestReporter") || base.endsWith("RepetitionInfo")) kind = "injected";
                    else if (base.equals("ArgumentsAccessor")) kind = "accessor";
                    else if (PRIMITIVE_TYPES.contains(base)) kind = "primitive";
                    else if (base.equals("Class")) kind = "class";
                    else if (convertWith || JDK_CONVERTIBLE.contains(base)) kind = "converted";
                    else {
                        ArtifactWalker.TypeInfo ti = walker.lookupType(base, cu, testFile, type);
                        if (ti.type instanceof EnumDeclaration) kind = "converted";
                        else if (ti.type != null && hasStringFactory(ti.type)) kind = "converted";
                        else kind = "injected";
                    }
                    kinds.add(kind + ":" + base);
                }
                String construction = kinds.stream().anyMatch(k -> k.startsWith("class:")) ? "Literal-Metadata" : "Literal-Primitive";
                out.add(ValueSourceAnalyzer.appendPublic(row, form, construction, String.join(";", kinds), String.valueOf(nParams), String.valueOf(nSets), nColumns < 0 ? "" : String.valueOf(nColumns),
                        "L" + r.level, String.valueOf(r.hitsProduction), r.levelReason, String.valueOf(constRefs), String.join(" | ", r.artifacts), ""));
            } catch (Exception e) {
                out.add(ValueSourceAnalyzer.appendPublic(row, "", "", "", "", "", "", "", "", "", "", "", "ERROR:" + e.getClass().getSimpleName() + ":" + String.valueOf(e.getMessage()).replace(",", ";")));
            }
        }
        ValueSourceAnalyzer.writeCsvPublic(args[1], out);
        System.err.println("Done. " + (out.size() - 1) + " rows -> " + args[1]);
    }

    private static final Set<String> PRIMITIVE_TYPES = Set.of("int", "long", "double", "float", "short", "byte", "boolean", "char",
            "Integer", "Long", "Double", "Float", "Short", "Byte", "Boolean", "Character", "String", "CharSequence");
    // JUnit 5 隐式转换支持的目标类型（DefaultArgumentConverter）
    private static final Set<String> JDK_CONVERTIBLE = Set.of("BigDecimal", "BigInteger", "File", "Path", "Charset", "URI", "URL", "UUID",
            "Locale", "Currency", "LocalDate", "LocalTime", "LocalDateTime", "ZonedDateTime", "OffsetDateTime", "OffsetTime", "Instant",
            "Duration", "Period", "Year", "YearMonth", "MonthDay", "ZoneId", "ZoneOffset", "Pattern", "Object");

    /** 项目类型能否被 JUnit 的兜底转换：String 单参构造，或静态 valueOf/of/parse/fromString(String) 工厂。 */
    private static boolean hasStringFactory(AbstractTypeDeclaration td) {
        for (Object b : td.bodyDeclarations()) {
            if (!(b instanceof MethodDeclaration)) continue;
            MethodDeclaration m = (MethodDeclaration) b;
            if (m.parameters().size() != 1) continue;
            String pt = ((SingleVariableDeclaration) m.parameters().get(0)).getType().toString();
            if (!pt.equals("String") && !pt.equals("CharSequence")) continue;
            if (m.isConstructor()) return true;
            String n = m.getName().getIdentifier();
            if (Modifier.isStatic(m.getModifiers()) && (n.equals("valueOf") || n.equals("of") || n.equals("parse") || n.equals("fromString") || n.equals("from"))) return true;
        }
        return false;
    }

    static MethodDeclaration findMethodWith(CompilationUnit cu, String name, String annotation) {
        List<MethodDeclaration> cands = new ArrayList<>();
        cu.accept(new ASTVisitor() { @Override public boolean visit(MethodDeclaration n) { if (n.getName().getIdentifier().equals(name)) cands.add(n); return true; } });
        for (MethodDeclaration m : cands) if (annotationNamed(m, annotation) != null) return m;
        return cands.isEmpty() ? null : cands.get(0);
    }

    static Annotation annotationNamed(MethodDeclaration md, String simple) {
        for (Object m : md.modifiers()) if (m instanceof Annotation) {
            String n = ((Annotation) m).getTypeName().getFullyQualifiedName();
            if (n.equals(simple) || n.endsWith("." + simple)) return (Annotation) m;
        }
        return null;
    }
}
