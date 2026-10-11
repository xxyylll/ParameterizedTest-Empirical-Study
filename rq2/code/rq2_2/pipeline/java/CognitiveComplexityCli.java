import org.eclipse.jdt.core.dom.*;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;

/**
 * 独立小工具：给定一份 CSV 清单（project,test_class,test_name,provider_seq,declaring_class,
 * method_name,start_line,end_line,source_file），对每一行定位到源文件里的那个方法声明，
 * 按 SonarSource Cognitive Complexity 规范（Campbell 2018, Appendix B）算一个分数，
 * 输出同样的列 + cognitive_complexity + note。
 *
 * 只做语法分析（setResolveBindings(false)），不需要项目 classpath，所以不依赖
 * Javalang-analyzing-cli 那套 Maven/Gradle 依赖解析——每个文件独立解析，足够算这个指标。
 * 唯一的代价：递归检测退化成"调用名字和参数个数都跟外层方法一样"的启发式，而不是靠
 * 类型绑定精确判断——provider 方法几乎不会自递归，这个近似影响可以忽略，但报告里要注明。
 *
 * 用法: java -cp <jdt jar>:. CognitiveComplexityCli input.csv output.csv
 */
public class CognitiveComplexityCli {

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("usage: CognitiveComplexityCli <input.csv> <output.csv>");
            System.exit(1);
        }
        List<String[]> rows = readCsv(args[0]);
        String[] header = rows.get(0);
        int idxSourceFile = indexOf(header, "source_file");
        int idxMethodName = indexOf(header, "method_name");
        int idxStartLine = indexOf(header, "start_line");
        int idxEndLine = indexOf(header, "end_line");

        List<String[]> outRows = new ArrayList<>();
        String[] outHeader = append(header, "cognitive_complexity", "note");
        outRows.add(outHeader);

        // 缓存同一个文件的 CompilationUnit，避免同一个 provider 文件被解析多次
        Map<String, CompilationUnit> cuCache = new HashMap<>();

        for (int i = 1; i < rows.size(); i++) {
            String[] row = rows.get(i);
            String sourceFile = row[idxSourceFile];
            String methodName = row[idxMethodName];
            int startLine = Integer.parseInt(row[idxStartLine]);
            int endLine = Integer.parseInt(row[idxEndLine]);

            if (sourceFile == null || sourceFile.isBlank()) {
                outRows.add(append(row, "", "SOURCE_FILE_UNKNOWN"));
                continue;
            }

            try {
                CompilationUnit cu = cuCache.get(sourceFile);
                if (cu == null) {
                    cu = parse(sourceFile);
                    cuCache.put(sourceFile, cu);
                }
                MethodDeclaration md = findMethod(cu, methodName, startLine, endLine);
                if (md == null) {
                    outRows.add(append(row, "", "METHOD_NOT_FOUND_IN_AST"));
                    continue;
                }
                CognitiveComplexityCalculator calc = new CognitiveComplexityCalculator(md.getName().getIdentifier());
                int score = calc.forMethod(md);
                outRows.add(append(row, String.valueOf(score), ""));
            } catch (Exception e) {
                outRows.add(append(row, "", "ERROR:" + e.getClass().getSimpleName() + ":" + String.valueOf(e.getMessage()).replace(",", ";")));
            }
        }

        writeCsv(args[1], outRows);
        System.err.println("Done. " + (outRows.size() - 1) + " rows -> " + args[1]);
    }

    private static CompilationUnit parse(String filePath) throws IOException {
        String source = new String(Files.readAllBytes(new File(filePath).toPath()), StandardCharsets.UTF_8);
        ASTParser parser = ASTParser.newParser(AST.getJLSLatest());
        parser.setKind(ASTParser.K_COMPILATION_UNIT);
        parser.setResolveBindings(false);
        parser.setStatementsRecovery(true);
        parser.setBindingsRecovery(false);
        Map<String, String> options = JavaCore_getDefaultOptions();
        parser.setCompilerOptions(options);
        parser.setUnitName(filePath);
        parser.setSource(source.toCharArray());
        return (CompilationUnit) parser.createAST(null);
    }

    private static Map<String, String> JavaCore_getDefaultOptions() {
        Map<String, String> options = new HashMap<>();
        options.put(org.eclipse.jdt.core.JavaCore.COMPILER_SOURCE, "17");
        options.put(org.eclipse.jdt.core.JavaCore.COMPILER_COMPLIANCE, "17");
        options.put(org.eclipse.jdt.core.JavaCore.COMPILER_CODEGEN_TARGET_PLATFORM, "17");
        return options;
    }

    /** 按方法名 + 起止行号找方法声明（覆盖重载的情况：取行号范围重叠度最高的一个）。 */
    private static MethodDeclaration findMethod(CompilationUnit cu, String methodName, int startLine, int endLine) {
        List<MethodDeclaration> candidates = new ArrayList<>();
        cu.accept(new ASTVisitor() {
            @Override
            public boolean visit(MethodDeclaration node) {
                if (node.getName().getIdentifier().equals(methodName)) {
                    candidates.add(node);
                }
                return true;
            }
        });
        if (candidates.isEmpty()) return null;
        if (candidates.size() == 1) return candidates.get(0);
        MethodDeclaration best = null;
        int bestOverlap = -1;
        for (MethodDeclaration md : candidates) {
            int mdStart = cu.getLineNumber(md.getStartPosition());
            int mdEnd = cu.getLineNumber(md.getStartPosition() + md.getLength() - 1);
            int overlap = Math.min(mdEnd, endLine) - Math.max(mdStart, startLine);
            if (overlap > bestOverlap) {
                bestOverlap = overlap;
                best = md;
            }
        }
        return best;
    }

    // ---------- 极简 CSV 读写：字段里不含逗号/引号（我们自己生成的 manifest 满足这一点）----------

    private static List<String[]> readCsv(String path) throws IOException {
        List<String[]> rows = new ArrayList<>();
        try (BufferedReader br = new BufferedReader(new InputStreamReader(new FileInputStream(path), StandardCharsets.UTF_8))) {
            String line;
            while ((line = br.readLine()) != null) {
                rows.add(splitCsvLine(line));
            }
        }
        return rows;
    }

    private static String[] splitCsvLine(String line) {
        // manifest 里的字段（类名/方法名/路径/数字）都不含逗号，简单 split 即可
        return line.split(",", -1);
    }

    private static void writeCsv(String path, List<String[]> rows) throws IOException {
        try (BufferedWriter bw = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(path), StandardCharsets.UTF_8))) {
            for (String[] row : rows) {
                StringBuilder sb = new StringBuilder();
                for (int i = 0; i < row.length; i++) {
                    if (i > 0) sb.append(',');
                    String v = row[i] == null ? "" : row[i];
                    if (v.contains(",") || v.contains("\"") || v.contains("\n")) {
                        v = "\"" + v.replace("\"", "\"\"") + "\"";
                    }
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
