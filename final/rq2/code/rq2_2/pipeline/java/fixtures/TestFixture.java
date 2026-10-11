import java.util.stream.Stream;
import java.util.function.Function;

public class TestFixture {

    // expect 4: for(+1) + for(+1+1 nesting) + if(+1+2 nesting) = 1+2+3=... 见 sonar 官方例子, 期望 7
    int sumOfPrimesLike(int max) {
        int total = 0;
        for (int i = 1; i <= max; ++i) {          // +1 (nesting 0->1)
            for (int j = 2; j < i; ++j) {          // +1+1=2 (nesting 1->2)
                if (i % j == 0) {                  // +1+2=3 (nesting 2->3)
                    break;
                }
            }
            total += i;
        }
        return total;
        // 期望: 1 + 2 + 3 = 6 (sonar 官方例子里多了个 goto，我们这里用 break 代替，少 1)
    }

    // switch 只应该计 1 次，不管多少个 case
    String getWords(int number) {
        switch (number) {
            case 1: return "one";
            case 2: return "a couple";
            case 3: return "a few";
            default: return "lots";
        }
        // 期望: 1
    }

    // else-if 链：不应该逐级叠加 nesting
    int elseIfChain(int x) {
        if (x == 1) {          // +1+0=1
            return 1;
        } else if (x == 2) {   // +1 flat
            return 2;
        } else if (x == 3) {   // +1 flat
            return 3;
        } else {                // +1 flat
            return 0;
        }
        // 期望: 4
    }

    // 真正嵌套的 if（不是 else-if），应该叠加 nesting
    int nestedIf(int x, int y) {
        if (x > 0) {            // +1+0=1
            if (y > 0) {         // +1+1=2 （在 then 分支里，nesting 已经是 1）
                return 1;
            }
        }
        return 0;
        // 期望: 3
    }

    // 连续 && 序列只算一次，换成 || 算新的一段
    boolean boolSeq(boolean a, boolean b, boolean c, boolean d) {
        return (a && b && c) || d;
        // 期望: && 链一次(+1) + || 一次(+1) = 2
    }

    // lambda 嵌套：本身不加分，但内部的判断要折进来，且要算 nesting 增量
    Stream<String> lambdaChain(Stream<String> s) {
        return s.filter(x -> x.length() > 0 && x.startsWith("a"))   // lambda nesting+1；内部 && 序列 +1(不叠加nesting，序列本身不吃nesting项)
                .map(x -> x.toUpperCase());
        // 期望: 1 （来自 filter 里的 && 序列；map 的 lambda 内部没有判断，0）
    }

    // provider 风格：纯委托，没有任何判断
    static Stream<Integer> pureDelegate() {
        return Stream.of(1, 2, 3);
        // 期望: 0
    }
}
