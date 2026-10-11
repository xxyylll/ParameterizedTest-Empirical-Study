import org.eclipse.jdt.core.dom.*;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/**
 * @ValueSource 的 construction / dependency / arity。
 *   construction：按属性名——strings/booleans/ints/longs/doubles/shorts/bytes/floats/chars → Literal-Primitive；classes → Literal-Metadata。
 *   dependency：注解元素里的常量引用（CONST、Type.CONST、静态导入）和 Foo.class 按 MethodSource 同一套 artifact 规则定级
 *               （同类 L0 / 同最外层类 L1 / 祖先 L2 / 同包 L3 / 跨包 L4；production 类型 → hits_production）。纯字面量 → L0。
 *   arity：n_params（去掉 TestInfo/TestReporter/RepetitionInfo）× n_sets（元素个数）。
 * 输入 CSV 同 cognitive_targets_v2.csv（project, project_root, test_class, test_name, test_source_file）。
 */
public class ValueSourceAnalyzer {
    private static final Set<String> PRIMITIVE = Set.of("strings", "booleans", "ints", "longs", "doubles", "shorts", "bytes", "floats", "chars");

    public static void main(String[] args) throws Exception {
        List<String[]> rows = readCsv(args[0]);
        String[] header = rows.get(0);
        int iProj = idx(header, "project"), iRoot = idx(header, "project_root"), iName = idx(header, "test_name"), iFile = idx(header, "test_source_file");
        List<String[]> out = new ArrayList<>();
        out.add(append(header, "attribute", "construction", "n_params", "n_sets", "dependency", "hits_production", "dependency_reason", "n_constant_refs", "artifacts", "note"));
        Map<String, CompilationUnit> cuCache = new HashMap<>();
        Map<String, Map<String, List<Path>>> idxCache = new HashMap<>();
        for (int i = 1; i < rows.size(); i++) {
            String[] row = rows.get(i);
            String testFile = row[iFile], testName = row[iName];
            if (testFile == null || testFile.isBlank()) { out.add(append(row, "", "", "", "", "", "", "", "", "", "TEST_FILE_UNKNOWN")); continue; }
            try {
                Map<String, List<Path>> fileIndex = idxCache.computeIfAbsent(row[iRoot], r -> ConstructionDependencyClassifier.fileIndexFor(Paths.get(r)));
                CompilationUnit cu = cuCache.computeIfAbsent(testFile, ConstructionDependencyClassifier::parseQuiet);
                if (cu == null) { out.add(append(row, "", "", "", "", "", "", "", "", "", "TEST_FILE_PARSE_ERROR")); continue; }
                MethodDeclaration md = findValueSourceMethod(cu, testName);
                if (md == null) { out.add(append(row, "", "", "", "", "", "", "", "", "", "TEST_METHOD_NOT_FOUND")); continue; }
                Annotation ann = valueSourceAnnotation(md);
                String attr = null; List<Expression> elements = new ArrayList<>();
                if (ann instanceof NormalAnnotation) {
                    for (Object o : ((NormalAnnotation) ann).values()) {
                        MemberValuePair mvp = (MemberValuePair) o;
                        attr = mvp.getName().getIdentifier();
                        Expression v = mvp.getValue();
                        if (v instanceof ArrayInitializer) for (Object e : ((ArrayInitializer) v).expressions()) elements.add((Expression) e);
                        else elements.add(v);
                    }
                } else if (ann instanceof SingleMemberAnnotation) {
                    attr = "value";
                    Expression v = ((SingleMemberAnnotation) ann).getValue();
                    if (v instanceof ArrayInitializer) for (Object e : ((ArrayInitializer) v).expressions()) elements.add((Expression) e);
                    else elements.add(v);
                }
                String construction = attr == null ? "" : PRIMITIVE.contains(attr) ? "Literal-Primitive" : attr.equals("classes") ? "Literal-Metadata" : "Literal-Other";
                int nParams = 0;
                for (Object p : md.parameters()) {
                    String t = ((SingleVariableDeclaration) p).getType().toString();
                    if (!(t.endsWith("TestInfo") || t.endsWith("TestReporter") || t.endsWith("RepetitionInfo"))) nParams++;
                }
                int constRefs = 0;
                for (Expression e : elements) if (!isPlainLiteral(e)) constRefs++;
                AbstractTypeDeclaration type = null;
                for (ASTNode p = md.getParent(); p != null; p = p.getParent()) if (p instanceof AbstractTypeDeclaration) { type = (AbstractTypeDeclaration) p; break; }
                ArtifactWalker walker = new ArtifactWalker(fileIndex, cuCache, ConstructionDependencyClassifier::parseQuiet, testFile, cu, md);
                ArtifactWalker.Result r = walker.analyzeExpressions(elements, testFile, cu, type);
                out.add(append(row, attr == null ? "" : attr, construction, String.valueOf(nParams), String.valueOf(elements.size()),
                        "L" + r.level, String.valueOf(r.hitsProduction), r.levelReason, String.valueOf(constRefs),
                        String.join(" | ", r.artifacts), ann == null ? "NO_VALUESOURCE_ANNOTATION" : ""));
            } catch (Exception e) {
                out.add(append(row, "", "", "", "", "", "", "", "", "", "ERROR:" + e.getClass().getSimpleName() + ":" + String.valueOf(e.getMessage()).replace(",", ";")));
            }
        }
        writeCsv(args[1], out);
        System.err.println("Done. " + (out.size() - 1) + " rows -> " + args[1]);
    }

    static boolean isPlainLiteralPublic(Expression e) { return isPlainLiteral(e); }
    static List<String[]> readCsvPublic(String p) throws IOException { return readCsv(p); }
    static void writeCsvPublic(String p, List<String[]> rows) throws IOException { writeCsv(p, rows); }
    static int idxPublic(String[] h, String n) { return idx(h, n); }
    static String[] appendPublic(String[] row, String... extra) { return append(row, extra); }

    private static boolean isPlainLiteral(Expression e) {
        if (e instanceof ParenthesizedExpression) return isPlainLiteral(((ParenthesizedExpression) e).getExpression());
        if (e instanceof PrefixExpression) return isPlainLiteral(((PrefixExpression) e).getOperand());
        if (e instanceof CastExpression) return isPlainLiteral(((CastExpression) e).getExpression());
        if (e instanceof InfixExpression) {
            InfixExpression ie = (InfixExpression) e;
            if (!isPlainLiteral(ie.getLeftOperand()) || !isPlainLiteral(ie.getRightOperand())) return false;
            for (Object o : ie.extendedOperands()) if (!isPlainLiteral((Expression) o)) return false;
            return true;
        }
        return e instanceof NumberLiteral || e instanceof StringLiteral || e instanceof BooleanLiteral || e instanceof CharacterLiteral
                || e instanceof TextBlock || e instanceof NullLiteral;
    }

    /** 同名重载：优先带 @ValueSource 的那个。 */
    private static MethodDeclaration findValueSourceMethod(CompilationUnit cu, String name) {
        List<MethodDeclaration> cands = new ArrayList<>();
        cu.accept(new ASTVisitor() { @Override public boolean visit(MethodDeclaration n) { if (n.getName().getIdentifier().equals(name)) cands.add(n); return true; } });
        for (MethodDeclaration m : cands) if (valueSourceAnnotation(m) != null) return m;
        return cands.isEmpty() ? null : cands.get(0);
    }

    private static Annotation valueSourceAnnotation(MethodDeclaration md) {
        for (Object m : md.modifiers()) {
            if (m instanceof Annotation) {
                String n = ((Annotation) m).getTypeName().getFullyQualifiedName();
                if (n.equals("ValueSource") || n.endsWith(".ValueSource")) return (Annotation) m;
            }
        }
        return null;
    }

    // ---- CSV ----
    private static int idx(String[] h, String n) { for (int i = 0; i < h.length; i++) if (h[i].equals(n)) return i; throw new IllegalArgumentException("no column " + n); }
    private static String[] append(String[] row, String... extra) { String[] o = Arrays.copyOf(row, row.length + extra.length); System.arraycopy(extra, 0, o, row.length, extra.length); return o; }
    private static List<String[]> readCsv(String path) throws IOException {
        List<String[]> rows = new ArrayList<>();
        try (BufferedReader br = Files.newBufferedReader(Paths.get(path), StandardCharsets.UTF_8)) {
            String line; StringBuilder rec = new StringBuilder(); boolean inQ = false;
            while ((line = br.readLine()) != null) {
                rec.append(line);
                for (char c : line.toCharArray()) if (c == '"') inQ = !inQ;
                if (inQ) { rec.append("\n"); continue; }
                rows.add(parseCsvLine(rec.toString())); rec.setLength(0);
            }
        }
        return rows;
    }
    private static String[] parseCsvLine(String line) {
        List<String> out = new ArrayList<>(); StringBuilder cur = new StringBuilder(); boolean q = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (q) { if (c == '"') { if (i + 1 < line.length() && line.charAt(i + 1) == '"') { cur.append('"'); i++; } else q = false; } else cur.append(c); }
            else if (c == '"') q = true; else if (c == ',') { out.add(cur.toString()); cur.setLength(0); } else cur.append(c);
        }
        out.add(cur.toString()); return out.toArray(new String[0]);
    }
    private static void writeCsv(String path, List<String[]> rows) throws IOException {
        try (BufferedWriter bw = Files.newBufferedWriter(Paths.get(path), StandardCharsets.UTF_8)) {
            for (String[] r : rows) {
                StringBuilder sb = new StringBuilder();
                for (int i = 0; i < r.length; i++) {
                    if (i > 0) sb.append(',');
                    String v = r[i] == null ? "" : r[i];
                    if (v.contains(",") || v.contains("\"") || v.contains("\n")) sb.append('"').append(v.replace("\"", "\"\"")).append('"'); else sb.append(v);
                }
                bw.write(sb.toString()); bw.newLine();
            }
        }
    }
}
