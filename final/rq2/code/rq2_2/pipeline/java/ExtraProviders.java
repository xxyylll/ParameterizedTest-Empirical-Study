import org.eclipse.jdt.core.dom.*;
import java.util.*;

/** @ArgumentsSource(Provider.class) / @FieldSource("NAME") 的 provider 单元，供 CC 与 construction/dependency 两个分类器复用。 */
public class ExtraProviders {
    public static class Unit {
        public MethodDeclaration method;              // ArgumentsSource: provideArguments
        public ArtifactWalker.FieldLookup field;      // FieldSource
        public String file; public boolean viaInheritance; public String label; public String note;
    }

    /** 测试方法上有没有 @MethodSource / @ArgumentsSource / @FieldSource 之一（决定"无 provider 注解"要不要报）。 */
    public static boolean hasAnyProviderAnnotation(MethodDeclaration md) {
        for (Object m : md.modifiers()) if (m instanceof Annotation) {
            String n = ((Annotation) m).getTypeName().getFullyQualifiedName(); n = n.substring(n.lastIndexOf('.') + 1);
            if (n.equals("MethodSource") || n.equals("ArgumentsSource") || n.equals("ArgumentsSources") || n.equals("FieldSource")) return true;
        }
        return false;
    }

    public static List<Unit> collect(MethodDeclaration testMd, CompilationUnit testCu, String testFile, ArtifactWalker walker) {
        List<Unit> out = new ArrayList<>();
        AbstractTypeDeclaration type = null;
        for (ASTNode p = testMd.getParent(); p != null; p = p.getParent()) if (p instanceof AbstractTypeDeclaration) { type = (AbstractTypeDeclaration) p; break; }
        for (Object m : testMd.modifiers()) {
            if (!(m instanceof Annotation)) continue;
            Annotation ann = (Annotation) m;
            String n = ann.getTypeName().getFullyQualifiedName(); n = n.substring(n.lastIndexOf('.') + 1);
            if (n.equals("ArgumentsSource") || n.equals("ArgumentsSources")) collectArgumentsSource(ann, testCu, testFile, type, walker, out);
            else if (n.equals("FieldSource")) collectFieldSource(ann, testMd, testCu, testFile, type, walker, out);
        }
        return out;
    }

    private static void collectArgumentsSource(Annotation ann, CompilationUnit testCu, String testFile, AbstractTypeDeclaration type, ArtifactWalker walker, List<Unit> out) {
        for (Expression v : values(ann)) {
            if (v instanceof Annotation) { collectArgumentsSource((Annotation) v, testCu, testFile, type, walker, out); continue; }
            if (!(v instanceof TypeLiteral)) continue;
            String t = ((TypeLiteral) v).getType().toString(); t = t.replaceAll("<.*>", ""); String simple = t.substring(t.lastIndexOf('.') + 1);
            String[] fileOut = new String[1]; AbstractTypeDeclaration[] typeOut = new AbstractTypeDeclaration[1];
            MethodDeclaration md = walker.lookupMethod(simple, "provideArguments", testCu, testFile, type, fileOut, typeOut);
            Unit u = new Unit(); u.label = "ArgumentsSource:" + simple;
            if (md == null) { u.note = "PROVIDER_NOT_FOUND:ArgumentsSource:" + simple; out.add(u); continue; }
            u.method = md; u.file = fileOut[0]; u.viaInheritance = false; out.add(u);
        }
    }

    private static void collectFieldSource(Annotation ann, MethodDeclaration testMd, CompilationUnit testCu, String testFile, AbstractTypeDeclaration type, ArtifactWalker walker, List<Unit> out) {
        List<String> names = new ArrayList<>();
        for (Expression v : values(ann)) if (v instanceof StringLiteral) names.add(((StringLiteral) v).getLiteralValue());
        if (names.isEmpty()) names.add(testMd.getName().getIdentifier());
        for (String ref : names) {
            Unit u = new Unit(); u.label = "FieldSource:" + ref;
            ArtifactWalker.FieldLookup fl;
            if (ref.contains("#")) fl = walker.lookupField(ref.substring(0, ref.indexOf('#')), ref.substring(ref.indexOf('#') + 1), testCu, testFile, type);
            else fl = walker.lookupField(ref, testCu, testFile, type);
            if (fl == null) { u.note = "PROVIDER_NOT_FOUND:FieldSource:" + ref; out.add(u); continue; }
            u.field = fl; u.file = fl.file; u.viaInheritance = !ref.contains("#") && fl.inherited; out.add(u);
        }
    }

    private static List<Expression> values(Annotation ann) {
        List<Expression> out = new ArrayList<>(); Expression v = null;
        if (ann instanceof SingleMemberAnnotation) v = ((SingleMemberAnnotation) ann).getValue();
        else if (ann instanceof NormalAnnotation) for (Object o : ((NormalAnnotation) ann).values()) { MemberValuePair mvp = (MemberValuePair) o; if (mvp.getName().getIdentifier().equals("value")) v = mvp.getValue(); }
        if (v == null) return out;
        if (v instanceof ArrayInitializer) for (Object e : ((ArrayInitializer) v).expressions()) out.add((Expression) e); else out.add(v);
        return out;
    }
}
