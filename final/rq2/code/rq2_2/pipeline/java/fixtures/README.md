# 分析器的样例输入

这两个文件是**给分析器读的样例源码**，用来手工核对 construction / dependency / cognitive complexity
的判定，不参与编译：`ConstructionFixture.java` 用全限定名写了 JUnit 注解，并故意包含会被判为
Dynamic 的写法，单独编译会报错。`run_rq22.sh` 只编译上一级目录里的分析器。
