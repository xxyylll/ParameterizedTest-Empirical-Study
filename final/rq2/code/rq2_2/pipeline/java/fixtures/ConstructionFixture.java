import java.util.*;
import java.util.stream.Stream;

public class ConstructionFixture {

    @org.junit.jupiter.params.ParameterizedTest
    @org.junit.jupiter.params.provider.MethodSource("pureLiteral")
    void testPureLiteral(Object[] x) {}

    // Literal, L0
    static Stream<Object[]> pureLiteral() {
        return Stream.of(new Object[]{1, "a"}, new Object[]{2, "b"});
    }

    @org.junit.jupiter.params.ParameterizedTest
    @org.junit.jupiter.params.provider.MethodSource("dynamicLoop")
    void testDynamicLoop(int x) {}

    // Dynamic (loop), L0 (没有调用别的类)
    static Stream<Integer> dynamicLoop() {
        List<Integer> l = new ArrayList<>();
        for (int i = 0; i < 5; i++) l.add(i);
        return l.stream();
    }

    @org.junit.jupiter.params.ParameterizedTest
    @org.junit.jupiter.params.provider.MethodSource("classHelper")
    void testClassHelper(Object[] x) {}

    // Dynamic (纯委托给同类另一个方法), L1
    static Stream<Object[]> classHelper() {
        return buildArgs();
    }

    private static Stream<Object[]> buildArgs() {
        return Stream.of(new Object[]{1});
    }

    @org.junit.jupiter.params.ParameterizedTest
    @org.junit.jupiter.params.provider.MethodSource("withConstant")
    void testWithConstant(double x) {}

    // Literal 但用了常量字段（Double.NaN 风格），仍判 Literal
    static Stream<Double> withConstant() {
        return Stream.of(-1.0, 101.0, Double.NaN);
    }
}
