import org.eclipse.jdt.core.dom.*;
import java.nio.file.*;
import java.util.*;

/**
 * @EnumSource：
 *   dependency：枚举类型在 test-code 里 → L0–L4（同 MethodSource 口径）；在 production 里 → "Production"（L0–L4 之外单列）；
 *               JDK/第三方 → "External"。
 *   enum_structure：Label-based（枚举常量都是裸标签：没有构造参数、字段、方法、常量体）/ Data-carrying（常量带参数、或枚举声明了
 *                   字段 / 构造函数 / 方法 / 常量特有类体）。production/test 枚举都能看源码；External 为 n/a。
 *   arity：n_params × n_sets（枚举常量个数；names+INCLUDE → names 数；EXCLUDE → 总数−names 数；MATCH_* → 不可数）。
 */
public class EnumSourceAnalyzer {
    public static void main(String[] args) throws Exception {
        List<String[]> rows = ValueSourceAnalyzer.readCsvPublic(args[0]);
        String[] header = rows.get(0);
        int iRoot = ValueSourceAnalyzer.idxPublic(header, "project_root"), iName = ValueSourceAnalyzer.idxPublic(header, "test_name"), iFile = ValueSourceAnalyzer.idxPublic(header, "test_source_file");
        List<String[]> out = new ArrayList<>();
        out.add(ValueSourceAnalyzer.appendPublic(header, "enum_type", "enum_location", "dependency", "dependency_reason", "enum_structure", "enum_structure_reason",
                "n_params", "n_sets", "n_sets_status", "n_enum_constants", "names_mode", "note"));
        Map<String, CompilationUnit> cuCache = new HashMap<>();
        Map<String, Map<String, List<Path>>> idxCache = new HashMap<>();
        for (int i = 1; i < rows.size(); i++) {
            String[] row = rows.get(i);
            String testFile = row[iFile], testName = row[iName];
            if (testFile == null || testFile.isBlank()) { out.add(pad(row, "TEST_FILE_UNKNOWN")); continue; }
            try {
                Map<String, List<Path>> fileIndex = idxCache.computeIfAbsent(row[iRoot], r -> ConstructionDependencyClassifier.fileIndexFor(Paths.get(r)));
                CompilationUnit cu = cuCache.computeIfAbsent(testFile, ConstructionDependencyClassifier::parseQuiet);
                if (cu == null) { out.add(pad(row, "TEST_FILE_PARSE_ERROR")); continue; }
                MethodDeclaration md = CsvSourceAnalyzer.findMethodWith(cu, testName, "EnumSource");
                if (md == null) { out.add(pad(row, "TEST_METHOD_NOT_FOUND")); continue; }
                Annotation ann = CsvSourceAnalyzer.annotationNamed(md, "EnumSource");
                if (ann == null) { out.add(pad(row, "NO_ENUMSOURCE_ANNOTATION")); continue; }
                // 枚举类型：value / 单成员 / 缺省 = 第一个参数的类型
                String enumSimple = null; List<String> names = new ArrayList<>(); String mode = "INCLUDE";
                Expression valueExpr = null;
                if (ann instanceof SingleMemberAnnotation) valueExpr = ((SingleMemberAnnotation) ann).getValue();
                else if (ann instanceof NormalAnnotation) for (Object o : ((NormalAnnotation) ann).values()) {
                    MemberValuePair mvp = (MemberValuePair) o; String n = mvp.getName().getIdentifier(); Expression v = mvp.getValue();
                    if (n.equals("value")) valueExpr = v;
                    else if (n.equals("names")) { if (v instanceof ArrayInitializer) for (Object e : ((ArrayInitializer) v).expressions()) names.add(e.toString()); else names.add(v.toString()); }
                    else if (n.equals("mode")) { String m = v.toString(); mode = m.substring(m.lastIndexOf('.') + 1); }
                }
                String enumQualifier = null;
                if (valueExpr instanceof TypeLiteral) { enumSimple = simpleName(((TypeLiteral) valueExpr).getType()); enumQualifier = qualifierName(((TypeLiteral) valueExpr).getType()); }
                else if (valueExpr instanceof ArrayInitializer && !((ArrayInitializer) valueExpr).expressions().isEmpty() && ((ArrayInitializer) valueExpr).expressions().get(0) instanceof TypeLiteral)
                    enumSimple = simpleName(((TypeLiteral) ((ArrayInitializer) valueExpr).expressions().get(0)).getType());
                if (enumSimple == null && !md.parameters().isEmpty()) { Type pt = ((SingleVariableDeclaration) md.parameters().get(0)).getType(); enumSimple = simpleName(pt); enumQualifier = qualifierName(pt); }
                int nParams = 0;
                for (Object p : md.parameters()) { String t = ((SingleVariableDeclaration) p).getType().toString(); if (!(t.endsWith("TestInfo") || t.endsWith("TestReporter") || t.endsWith("RepetitionInfo"))) nParams++; }
                AbstractTypeDeclaration type = null;
                for (ASTNode p = md.getParent(); p != null; p = p.getParent()) if (p instanceof AbstractTypeDeclaration) { type = (AbstractTypeDeclaration) p; break; }
                ArtifactWalker walker = new ArtifactWalker(fileIndex, cuCache, ConstructionDependencyClassifier::parseQuiet, testFile, cu, md);
                ArtifactWalker.TypeInfo ti = walker.lookupType(enumSimple, cu, testFile, type);
                if (ti.level == -2 && enumQualifier != null) {
                    // Outer.Inner.class：先定位 Outer，再在其文件里找 Inner
                    ArtifactWalker.TypeInfo outer = walker.lookupType(enumQualifier, cu, testFile, type);
                    if (outer.type != null) {
                        CompilationUnit ocu = cuCache.get(outer.file);
                        ArtifactWalker.TypeInfo inner = walker.lookupType(enumSimple, ocu, outer.file, outer.type);
                        if (inner.type != null) {
                            // 等级仍要相对测试类算：用测试类上下文再查一次（此时 Inner 已能通过 Outer 文件命中）
                            ti = inner; ti.level = outer.level == -1 ? -1 : (outer.level == -2 ? -2 : walker.lookupType(enumSimple, ocu, outer.file, outer.type).level);
                            if (outer.level >= 0) { ArtifactWalker.TypeInfo lv = walker.levelOf(inner.file, inner.type); ti.level = lv.level; ti.why = lv.why; }
                            ti.isProduction = outer.isProduction; ti.isTest = outer.isTest;
                            if (outer.isProduction) { ti.level = -1; ti.why = "production"; }
                        }
                    }
                }
                // 找不到源码但 import 的包前缀与测试类同属本项目（org.apache.hadoop.hdds.protocol.proto.HddsProtos.LifeCycleState 这类
                // protobuf 生成的枚举）→ 视为 production（generated），不算 External
                boolean generatedProd = false;
                if (ti.level == -2 && enumSimple != null && cu.getPackage() != null) {
                    String testPkg = cu.getPackage().getName().getFullyQualifiedName();
                    String[] tp = testPkg.split("\\.");
                    String prefix = tp.length >= 3 ? tp[0] + "." + tp[1] + "." + tp[2] : testPkg;
                    for (Object o : cu.imports()) {
                        String fq = ((ImportDeclaration) o).getName().getFullyQualifiedName();
                        if ((fq.endsWith("." + enumSimple) || (enumQualifier != null && fq.endsWith("." + enumQualifier))) && fq.startsWith(prefix + ".")) { generatedProd = true; break; }
                    }
                    if (!generatedProd && enumQualifier != null) {
                        // 通过同包类的嵌套访问（HddsProtos.X 且 HddsProtos 是同项目生成类）：限定符本身能在本项目包前缀下 import 到
                        for (Object o : cu.imports()) { String fq = ((ImportDeclaration) o).getName().getFullyQualifiedName(); if (fq.endsWith("." + enumQualifier) && fq.startsWith(prefix + ".")) { generatedProd = true; break; } }
                    }
                }
                if (generatedProd) { ti.level = -1; ti.why = "production(generated)"; }
                String location = ti.level == -1 ? (generatedProd ? "production(generated)" : "production") : ti.level == -2 ? "external" : "test";
                String dependency = ti.level == -1 ? "Production" : ti.level == -2 ? "External" : "L" + ti.level;
                // 结构 + 常量数
                String structure = "", structureReason = ""; Integer total = null;
                if (ti.type instanceof EnumDeclaration) {
                    EnumDeclaration ed = (EnumDeclaration) ti.type;
                    total = ed.enumConstants().size();
                    List<String> reasons = new ArrayList<>();
                    for (Object c : ed.enumConstants()) {
                        EnumConstantDeclaration ecd = (EnumConstantDeclaration) c;
                        if (!ecd.arguments().isEmpty()) { reasons.add("constant-args"); break; }
                    }
                    for (Object c : ed.enumConstants()) if (((EnumConstantDeclaration) c).getAnonymousClassDeclaration() != null) { reasons.add("constant-body"); break; }
                    for (Object b : ed.bodyDeclarations()) {
                        if (b instanceof FieldDeclaration) { reasons.add("fields"); break; }
                    }
                    for (Object b : ed.bodyDeclarations()) {
                        if (b instanceof MethodDeclaration) { reasons.add(((MethodDeclaration) b).isConstructor() ? "constructor" : "methods"); }
                    }
                    Set<String> rs = new LinkedHashSet<>(reasons);
                    structure = rs.isEmpty() ? "Label-based" : "Data-carrying"; structureReason = String.join("+", rs);
                } else if (ti.type != null) { structure = "n/a"; structureReason = "not-an-enum:" + ti.type.getClass().getSimpleName(); }
                else {
                    // 看不到源码的枚举：按来源判断结构（JDK/第三方；protobuf 生成的枚举都带 int value + getNumber() → Data-carrying）
                    String fq = null;
                    for (Object o : cu.imports()) { String f = ((ImportDeclaration) o).getName().getFullyQualifiedName(); if (enumSimple != null && (f.endsWith("." + enumSimple) || (enumQualifier != null && f.endsWith("." + enumQualifier)))) { fq = f; break; } }
                    if (fq == null && enumQualifier != null) fq = enumQualifier + "." + enumSimple;
                    if (fq == null) fq = enumSimple == null ? "" : enumSimple;
                    if (fq.contains("Protos.") || fq.endsWith("Protos") || generatedProd) { structure = "Data-carrying"; structureReason = "protobuf-generated(value+getNumber)"; }
                    else if (fq.startsWith("software.amazon.awssdk.")) { structure = "Data-carrying"; structureReason = "aws-sdk(value+fromValue)"; }
                    else if (fq.equals("java.nio.file.LinkOption") || fq.equals("Thread.State") || fq.equals("java.lang.Thread.State")
                            || fq.equals("org.apache.hadoop.hive.metastore.TableType")) { structure = "Label-based"; structureReason = "known-external"; }
                    else { structure = "n/a"; structureReason = "external:" + fq; }
                }
                Integer nSets = null; String setsStatus;
                List<String> constNames = new ArrayList<>();
                if (ti.type instanceof EnumDeclaration) for (Object c : ((EnumDeclaration) ti.type).enumConstants()) constNames.add(((EnumConstantDeclaration) c).getName().getIdentifier());
                List<String> patterns = new ArrayList<>();
                for (String n : names) patterns.add(n.startsWith("\"") && n.endsWith("\"") ? n.substring(1, n.length() - 1) : n);
                if (names.isEmpty()) { nSets = total; }
                else if (mode.equals("INCLUDE")) nSets = names.size();
                else if (mode.equals("EXCLUDE") && total != null) nSets = total - names.size();
                else if ((mode.equals("MATCH_ANY") || mode.equals("MATCH_ALL") || mode.equals("MATCH_NONE")) && total != null) {
                    // 正则模式：把 names 里的正则套在枚举常量名上数——枚举声明在手，静态可数
                    int cnt = 0;
                    for (String cn : constNames) {
                        int hits = 0;
                        for (String pat : patterns) { try { if (java.util.regex.Pattern.matches(pat, cn)) hits++; } catch (Exception ex) { hits = -1; break; } }
                        if (hits < 0) { cnt = -1; break; }
                        boolean sel = mode.equals("MATCH_ANY") ? hits > 0 : mode.equals("MATCH_ALL") ? hits == patterns.size() : hits == 0;
                        if (sel) cnt++;
                    }
                    if (cnt >= 0) nSets = cnt;
                }
                setsStatus = nSets != null ? "EXACT" : (total == null ? "UNRESOLVED_SOURCE" : "STATIC_UNSUPPORTED");
                out.add(ValueSourceAnalyzer.appendPublic(row, enumSimple == null ? "" : enumSimple, location, dependency, ti.why == null ? "" : ti.why, structure, structureReason,
                        String.valueOf(nParams), nSets == null ? "" : String.valueOf(nSets), setsStatus, total == null ? "" : String.valueOf(total),
                        names.isEmpty() ? "" : mode + ":" + names.size(), ""));
            } catch (Exception e) {
                out.add(pad(row, "ERROR:" + e.getClass().getSimpleName() + ":" + String.valueOf(e.getMessage()).replace(",", ";")));
            }
        }
        ValueSourceAnalyzer.writeCsvPublic(args[1], out);
        System.err.println("Done. " + (out.size() - 1) + " rows -> " + args[1]);
    }

    private static String[] pad(String[] row, String note) { return ValueSourceAnalyzer.appendPublic(row, "", "", "", "", "", "", "", "", "", "", "", note); }

    /** Outer.Inner → Outer（取最后一个限定段）；无限定返回 null。 */
    private static String qualifierName(Type t) {
        String n = t.toString(); int lt = n.indexOf('<'); if (lt >= 0) n = n.substring(0, lt);
        int d = n.lastIndexOf('.'); if (d < 0) return null;
        String q = n.substring(0, d); int d2 = q.lastIndexOf('.'); return d2 >= 0 ? q.substring(d2 + 1) : q;
    }

    private static String simpleName(Type t) {
        String n = t.toString(); int lt = n.indexOf('<'); if (lt >= 0) n = n.substring(0, lt);
        int br = n.indexOf('['); if (br >= 0) n = n.substring(0, br);
        int d = n.lastIndexOf('.'); return d >= 0 ? n.substring(d + 1) : n;
    }
}
