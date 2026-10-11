import org.eclipse.jdt.core.dom.*;

import java.util.List;

/**
 * SonarSource Cognitive Complexity（Campbell 2018, Appendix B）的一个手写实现，基于 JDT AST
 * （不需要 binding 解析）。规则来源同 SciTools Understand 官方插件
 * (plugins/Metric/cognitive_complexity.upy) 里注释的那张表，只是那个插件只支持 C++、且因为
 * Understand 的 CFG 不建模表达式，得额外用 lexer 扫 &&/||/?:；这里直接用 JDT 的表达式树，
 * 不需要那些 hack。
 *
 * 已知的近似 / 局限（做人工核对时重点看这几处）：
 *   1. 递归检测：没有做 binding 解析，用"方法名 + 参数个数 + 限定符"判定（见 isSelfRecursion）。
 *      限定符只接受 空/this/外层类自己的简单名；`Other.foo()` 这种同名跨类委托不算递归。
 *      残余风险：外层类与另一个类同简单名（不同包）时的 `Self.foo()` 会误判，极罕见。
 *   2. 连续 &&/|| 序列：依赖 JDT 把同一个运算符的连续链自动拉平成一个 InfixExpression +
 *      extendedOperands；如果源码里显式加括号打断了这个拉平（比如 (a && b) && c），
 *      会把它算成两段序列而不是一段——这跟 Understand 官方插件注释里承认的局限是同一个问题，
 *      不是这次实现独有的缺陷。
 *   3. 只展开 lambda 表达式和匿名类里的方法（"nested methods and method-like structures"），
 *      不会展开对其他具名方法的调用——这是 Cognitive Complexity 本身的定义决定的，
 *      helper 委托由 helper depth 那条线单独覆盖，两者不重叠。
 */
public class CognitiveComplexityCalculator {

    private int score = 0;
    private final String enclosingMethodName;
    private int enclosingParamCount = -1;
    private String enclosingTypeSimpleName = null;

    public CognitiveComplexityCalculator(String enclosingMethodName) {
        this.enclosingMethodName = enclosingMethodName;
    }

    public int forMethod(MethodDeclaration md) {
        score = 0;
        enclosingParamCount = md.parameters().size();
        // #3: 自递归判定需要知道"自己"是谁。只记外层类的简单名，用于放行 `Self.foo()` 这种
        // 显式限定的自调用，同时拒绝 `Other.foo()`（同名但不同类的委托，JUnit 里跨测试类
        // 共享 provider 的标准写法，之前被误判为递归 +1）。
        ASTNode parent = md.getParent();
        while (parent != null && !(parent instanceof AbstractTypeDeclaration)) parent = parent.getParent();
        enclosingTypeSimpleName = parent == null ? null : ((AbstractTypeDeclaration) parent).getName().getIdentifier();
        Block body = md.getBody();
        if (body == null) return 0; // 抽象方法/接口方法，没有函数体
        walkStatement(body, 0, false);
        return score;
    }

    /** @FieldSource：对字段初始化器（表达式）算 CC，规则同方法体（lambda / 三目 / 匿名类体照常计）。 */
    public int forExpression(Expression e) {
        score = 0;
        enclosingParamCount = 0;
        ASTNode parent = e.getParent();
        while (parent != null && !(parent instanceof AbstractTypeDeclaration)) parent = parent.getParent();
        enclosingTypeSimpleName = parent == null ? null : ((AbstractTypeDeclaration) parent).getName().getIdentifier();
        walkExpression(e, 0);
        return score;
    }

    // ---------------- 语句 ----------------

    @SuppressWarnings("unchecked")
    private void walkStatement(Statement stmt, int nesting, boolean isElseIfContinuation) {
        if (stmt == null) return;

        if (stmt instanceof Block) {
            for (Object o : ((Block) stmt).statements()) {
                walkStatement((Statement) o, nesting, false);
            }
        } else if (stmt instanceof IfStatement) {
            IfStatement ifStmt = (IfStatement) stmt;
            score += 1 + (isElseIfContinuation ? 0 : nesting);
            if (isElseIfContinuation) {
                // else-if 链本身是"+1 flat"，上面已经加过；这里不再重复加 nesting 项。
            }
            walkExpression(ifStmt.getExpression(), nesting);
            walkStatement(ifStmt.getThenStatement(), nesting + 1, false);
            Statement elseStmt = ifStmt.getElseStatement();
            if (elseStmt != null) {
                if (elseStmt instanceof IfStatement) {
                    // else if：只记一次 flat +1（在递归调用里，因为 isElseIfContinuation=true）
                    walkStatement(elseStmt, nesting, true);
                } else {
                    score += 1; // 终止的 else，flat
                    walkStatement(elseStmt, nesting + 1, false);
                }
            }
        } else if (stmt instanceof SwitchStatement) {
            SwitchStatement sw = (SwitchStatement) stmt;
            score += 1 + nesting;
            walkExpression(sw.getExpression(), nesting);
            for (Object o : sw.statements()) {
                if (o instanceof SwitchCase) continue; // case 标签本身不计分
                walkStatement((Statement) o, nesting + 1, false);
            }
        } else if (stmt instanceof ForStatement) {
            ForStatement f = (ForStatement) stmt;
            score += 1 + nesting;
            for (Object o : f.initializers()) walkExpression((Expression) o, nesting);
            walkExpression(f.getExpression(), nesting);
            for (Object o : f.updaters()) walkExpression((Expression) o, nesting);
            walkStatement(f.getBody(), nesting + 1, false);
        } else if (stmt instanceof EnhancedForStatement) {
            EnhancedForStatement f = (EnhancedForStatement) stmt;
            score += 1 + nesting;
            walkExpression(f.getExpression(), nesting);
            walkStatement(f.getBody(), nesting + 1, false);
        } else if (stmt instanceof WhileStatement) {
            WhileStatement w = (WhileStatement) stmt;
            score += 1 + nesting;
            walkExpression(w.getExpression(), nesting);
            walkStatement(w.getBody(), nesting + 1, false);
        } else if (stmt instanceof DoStatement) {
            DoStatement d = (DoStatement) stmt;
            score += 1 + nesting;
            walkStatement(d.getBody(), nesting + 1, false);
            walkExpression(d.getExpression(), nesting);
        } else if (stmt instanceof TryStatement) {
            TryStatement t = (TryStatement) stmt;
            for (Object o : t.resources()) {
                if (o instanceof Expression) walkExpression((Expression) o, nesting);
                else if (o instanceof VariableDeclarationExpression) walkExpression((Expression) o, nesting);
            }
            walkStatement(t.getBody(), nesting, false);
            for (Object o : t.catchClauses()) {
                CatchClause cc = (CatchClause) o;
                score += 1 + nesting;
                walkStatement(cc.getBody(), nesting + 1, false);
            }
            if (t.getFinally() != null) {
                walkStatement(t.getFinally(), nesting, false);
            }
        } else if (stmt instanceof LabeledStatement) {
            walkStatement(((LabeledStatement) stmt).getBody(), nesting, false);
        } else if (stmt instanceof BreakStatement) {
            if (((BreakStatement) stmt).getLabel() != null) score += 1;
        } else if (stmt instanceof ContinueStatement) {
            if (((ContinueStatement) stmt).getLabel() != null) score += 1;
        } else if (stmt instanceof ExpressionStatement) {
            walkExpression(((ExpressionStatement) stmt).getExpression(), nesting);
        } else if (stmt instanceof ReturnStatement) {
            walkExpression(((ReturnStatement) stmt).getExpression(), nesting);
        } else if (stmt instanceof ThrowStatement) {
            walkExpression(((ThrowStatement) stmt).getExpression(), nesting);
        } else if (stmt instanceof AssertStatement) {
            AssertStatement a = (AssertStatement) stmt;
            walkExpression(a.getExpression(), nesting);
            walkExpression(a.getMessage(), nesting);
        } else if (stmt instanceof SynchronizedStatement) {
            SynchronizedStatement s = (SynchronizedStatement) stmt;
            walkExpression(s.getExpression(), nesting);
            walkStatement(s.getBody(), nesting, false);
        } else if (stmt instanceof TypeDeclarationStatement) {
            // #10 的姊妹情况：方法体里声明的局部类，其方法体/初始化块同样是"写在 provider 里的代码"，
            // 按 Sonar 的 nested-method 规则折进来（nesting+1）。
            AbstractTypeDeclaration td = ((TypeDeclarationStatement) stmt).getDeclaration();
            walkBodyDeclarations(td.bodyDeclarations(), nesting + 1);
        } else if (stmt instanceof VariableDeclarationStatement) {
            for (Object o : ((VariableDeclarationStatement) stmt).fragments()) {
                VariableDeclarationFragment vdf = (VariableDeclarationFragment) o;
                walkExpression(vdf.getInitializer(), nesting);
            }
        } else {
            // 兜底：不认识的语句类型（比如 YieldStatement / local class 声明等少见构造），
            // 用一个通用 visitor 扫一遍它内部直接可见的 if/switch/loop/lambda/布尔序列，
            // 保证不会整段被静默漏掉，只是不保证嵌套层数完全精确。
            genericFallback(stmt, nesting);
        }
    }

    /**
     * 是否为对外层方法自身的递归调用（#3）。没有 binding，规则是：名字相同、参数个数相同、且
     * 限定符只能是 (a) 空——裸调用 foo(...)；(b) this；(c) 外层类自己的简单名——Self.foo(...)。
     * 任何其它限定符（Other.foo()、obj.foo()、this.field.foo()）都不算递归：那是调用别处的
     * 同名方法，不是调用自己。JUnit 里 `testX() { return OtherTest.testX(); }` 跨类共享 provider
     * 是标准写法，之前被误判为递归 +1。
     */
    private boolean isSelfRecursion(MethodInvocation mi) {
        if (!mi.getName().getIdentifier().equals(enclosingMethodName)) return false;
        if (enclosingParamCount >= 0 && mi.arguments().size() != enclosingParamCount) return false;
        Expression q = mi.getExpression();
        if (q == null || q instanceof ThisExpression) return true;
        if (q instanceof SimpleName && enclosingTypeSimpleName != null) {
            return ((SimpleName) q).getIdentifier().equals(enclosingTypeSimpleName);
        }
        return false;
    }

    /**
     * 走一个类体（匿名类 / 局部类）里所有"可执行的"成员：方法体 + 初始化块。
     * #10：之前只走 MethodDeclaration，实例/静态初始化块 `{ ... }`（JDT 的 Initializer）被跳过，
     * 里面的 for/if 全部漏算——mina-sshd 的 CliSupportSplitCommandLineArgumentsTest.parameters()
     * 就是把整个 for 循环写在匿名 ArrayList 的初始化块里，之前算成 0，应为 2。
     * 字段声明的初始化表达式也一并走（可能含三元/lambda）。
     */
    @SuppressWarnings("unchecked")
    private void walkBodyDeclarations(java.util.List<?> bodyDeclarations, int nesting) {
        for (Object o : bodyDeclarations) {
            if (o instanceof MethodDeclaration) {
                MethodDeclaration m = (MethodDeclaration) o;
                if (m.getBody() != null) walkStatement(m.getBody(), nesting, false);
            } else if (o instanceof Initializer) {
                walkStatement(((Initializer) o).getBody(), nesting, false);
            } else if (o instanceof FieldDeclaration) {
                for (Object f : ((FieldDeclaration) o).fragments()) {
                    walkExpression(((VariableDeclarationFragment) f).getInitializer(), nesting);
                }
            }
        }
    }

    private void genericFallback(ASTNode node, final int nesting) {
        node.accept(new ASTVisitor() {
            @Override
            public boolean visit(IfStatement n) { walkStatement(n, nesting, false); return false; }
            @Override
            public boolean visit(SwitchStatement n) { walkStatement(n, nesting, false); return false; }
            @Override
            public boolean visit(ForStatement n) { walkStatement(n, nesting, false); return false; }
            @Override
            public boolean visit(EnhancedForStatement n) { walkStatement(n, nesting, false); return false; }
            @Override
            public boolean visit(WhileStatement n) { walkStatement(n, nesting, false); return false; }
            @Override
            public boolean visit(DoStatement n) { walkStatement(n, nesting, false); return false; }
            @Override
            public boolean visit(TryStatement n) { walkStatement(n, nesting, false); return false; }
            @Override
            public boolean visit(LambdaExpression n) { walkExpression(n, nesting); return false; }
            @Override
            public boolean visit(ConditionalExpression n) { walkExpression(n, nesting); return false; }
            @Override
            public boolean visit(InfixExpression n) { walkExpression(n, nesting); return false; }
        });
    }

    // ---------------- 表达式 ----------------

    @SuppressWarnings("unchecked")
    private void walkExpression(Expression expr, int nesting) {
        if (expr == null) return;

        if (expr instanceof ConditionalExpression) {
            ConditionalExpression c = (ConditionalExpression) expr;
            score += 1 + nesting;
            walkExpression(c.getExpression(), nesting);
            walkExpression(c.getThenExpression(), nesting + 1);
            walkExpression(c.getElseExpression(), nesting + 1);
        } else if (expr instanceof InfixExpression) {
            InfixExpression inf = (InfixExpression) expr;
            InfixExpression.Operator op = inf.getOperator();
            if (op == InfixExpression.Operator.CONDITIONAL_AND || op == InfixExpression.Operator.CONDITIONAL_OR) {
                score += 1; // 一整串同类型的序列只记一次（JDT 会把同运算符的链拉平进 extendedOperands）
            }
            walkExpression(inf.getLeftOperand(), nesting);
            walkExpression(inf.getRightOperand(), nesting);
            for (Object o : inf.extendedOperands()) {
                walkExpression((Expression) o, nesting);
            }
        } else if (expr instanceof LambdaExpression) {
            LambdaExpression lambda = (LambdaExpression) expr;
            ASTNode body = lambda.getBody();
            if (body instanceof Block) {
                walkStatement((Block) body, nesting + 1, false);
            } else if (body instanceof Expression) {
                walkExpression((Expression) body, nesting + 1);
            }
        } else if (expr instanceof ClassInstanceCreation) {
            ClassInstanceCreation cic = (ClassInstanceCreation) expr;
            for (Object o : cic.arguments()) walkExpression((Expression) o, nesting);
            AnonymousClassDeclaration acd = cic.getAnonymousClassDeclaration();
            if (acd != null) {
                walkBodyDeclarations(acd.bodyDeclarations(), nesting + 1);
            }
        } else if (expr instanceof MethodInvocation) {
            MethodInvocation mi = (MethodInvocation) expr;
            if (isSelfRecursion(mi)) {
                score += 1; // 自递归，见 isSelfRecursion 的判定规则
            }
            walkExpression(mi.getExpression(), nesting);
            for (Object o : mi.arguments()) walkExpression((Expression) o, nesting);
        } else if (expr instanceof SuperMethodInvocation) {
            for (Object o : ((SuperMethodInvocation) expr).arguments()) walkExpression((Expression) o, nesting);
        } else if (expr instanceof ParenthesizedExpression) {
            walkExpression(((ParenthesizedExpression) expr).getExpression(), nesting);
        } else if (expr instanceof Assignment) {
            Assignment a = (Assignment) expr;
            walkExpression(a.getLeftHandSide(), nesting);
            walkExpression(a.getRightHandSide(), nesting);
        } else if (expr instanceof CastExpression) {
            walkExpression(((CastExpression) expr).getExpression(), nesting);
        } else if (expr instanceof PrefixExpression) {
            walkExpression(((PrefixExpression) expr).getOperand(), nesting);
        } else if (expr instanceof PostfixExpression) {
            walkExpression(((PostfixExpression) expr).getOperand(), nesting);
        } else if (expr instanceof FieldAccess) {
            walkExpression(((FieldAccess) expr).getExpression(), nesting);
        } else if (expr instanceof ArrayAccess) {
            ArrayAccess aa = (ArrayAccess) expr;
            walkExpression(aa.getArray(), nesting);
            walkExpression(aa.getIndex(), nesting);
        } else if (expr instanceof ArrayInitializer) {
            for (Object o : ((ArrayInitializer) expr).expressions()) walkExpression((Expression) o, nesting);
        } else if (expr instanceof ArrayCreation) {
            ArrayCreation ac = (ArrayCreation) expr;
            for (Object o : ac.dimensions()) walkExpression((Expression) o, nesting);
            walkExpression(ac.getInitializer(), nesting);
        } else if (expr instanceof VariableDeclarationExpression) {
            for (Object o : ((VariableDeclarationExpression) expr).fragments()) {
                walkExpression(((VariableDeclarationFragment) o).getInitializer(), nesting);
            }
        } else {
            // 兜底：方法引用(::)、SwitchExpression(Java14+)、TextBlock 等不常见构造。
            // 只扫它内部可能出现的 if/switch/loop/lambda/布尔序列，不做嵌套精修。
            genericFallback(expr, nesting);
        }
    }
}
