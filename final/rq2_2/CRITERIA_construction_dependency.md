# rq2.2 判定标准（2026-09-16 现行版，第四轮 review 后）

分析单元：一个 `@MethodSource` 参数化测试。它引用的全部 provider（多个 provider、或 #8 那种抽象测试类 + 多个子类各自的
provider）**池化**成一行。provider 是 JDK/第三方方法（`java.util.TimeZone#getAvailableIDs`）→ `EXTERNAL_PROVIDER`，
三个维度都 N/A，单独计数。

## Construction（Literal / Dynamic）— 源码 AST 判定，`ConstructionDependencyClassifier.java`

**一句话**：provider 产出的参数集在编译期就完全确定 → **Literal**；否则 **Dynamic**。多个 provider 只要有一个 Dynamic 整体 Dynamic。

Literal 必须同时满足：
1. **语句形态**：只允许 (a) 局部变量声明且初始化表达式是"字面量表达式"，(b) 对已声明的字面量局部容器的单条 `add / addAll / put / putAll / set / offer / push / append(...)` 语句（参数全是字面量表达式），(c) 简单赋值 `x = 字面量表达式`，(d) 一条 `return 字面量表达式`。出现 if / for / while / switch / try / throw / enhanced-for / 其它语句 → Dynamic。
2. **字面量表达式**（递归定义）：
   - 数字 / 字符串 / 文本块 / 布尔 / 字符 / `null` / `Foo.class`；`-1`、`!true`；字面量之间的 `+ - * /` 等中缀运算；括号；类型转换
   - 数组：`{...}` / `new T[]{...}` / `new T[3]`，元素全是字面量表达式
   - **常量引用**：全大写命名的标识符（`MAX`、`Integer.MAX_VALUE`）；`Type.MEMBER` 形式的静态成员（限定符首字母大写：枚举 `Color.RED`、`Locale.ENGLISH`、`StandardCharsets.UTF_8`、`QueryContexts.SOME_KEY`）；本类 `static final` 且初始化为字面量表达式的字段；本方法里已判为字面量的局部变量
   - **值对象 / 容器构造**：`new T(args…)` 参数全是字面量表达式且无匿名体（`new File("x")`、`new ArrayList<>()`、`new Object[]{...}`）
   - **静态工厂装箱**（A2）：方法名在白名单 {`of, asList, singletonList, singleton, emptyList/Set/Map, unmodifiableList, copyOf, arguments, argumentSet, named, entry, stream, builder, build, add, addAll, put, putAll, set, toArray, toList, boxed, tuple, pair, listOf, setOf, mapOf`}，**且接收者是类型名**（`Stream.of` / `Arrays.asList` / `Arguments.of` / `Named.of` / `Map.entry` / `java.util.List.of`）或没有接收者（静态导入的 `arguments(...)`），参数全是字面量表达式
   - 对字面量局部容器的**单层终结调用** `list.stream()` / `list.toArray()` / `builder.build()` / `boxed()` / `toList()`
   - lambda：表达式体且体是字面量表达式（`() -> null`）
3. **以下一律 Dynamic**：接收者是对象/表达式的链式调用（`new ImmutableMap.Builder<>().putAll(..).put(..).build()`、`x.stream().map(..)`）；白名单外的任何调用，包括看起来纯的静态工厂（`Date.from(...)`、`Instant.ofEpochSecond(...)`、`Paths.get(...)`——保守判 Dynamic）；helper 委托 `return helper()`；方法引用；块体 lambda；三目；字段/参数/外部变量引用（非常量命名、非 `Type.MEMBER`）；带匿名体的 `new`；`mock(...)`、IO。

注意：Construction 与 Cognitive Complexity 独立。`return helper()` 的 CC=0 但 Construction=Dynamic。

## Dependency（L0–L4）— AAA 调用轨迹判定，`build_dependency_v2.py`

**一句话**：provider 及它（递归）调用的 **test-scope helper** 离测试类最远的一个决定等级；production 代码不进等级、只标 `hits_production`。

| 等级 | 名称 | 条件 |
|---|---|---|
| L0 | Source Local | provider 在测试类自己里，且没有调用任何 test-scope helper（只调 JDK/第三方/production 代码） |
| L1 | Enclosing-Class Helper | provider 或 helper 与测试类在**同一个最外层类**里（静态嵌套类、`@Nested` 内部类、外层类互相引用都算） |
| L2 | Inheritance | provider 通过继承解析到别的类（裸方法名落在父类 / 子类 / 实现的接口里），或 helper 声明在测试类（或 provider 类）的**祖先**里（`extends` 链 / `implements` 的接口，语法解析 ≤8 层） |
| L3 | Package Helper | provider 或 helper 在同包的其它类里（通过 `#` 全限定名或指向常量的限定名**显式引用**，如 `@MethodSource(AbstractInputStreamTest.ARRAY_LENGTHS_NAME)`） |
| L4 | Cross-Package | provider 或 helper 在别的包里（同样是显式引用） |
| EXTERNAL | — | provider 是 JDK/第三方方法，N/A |

判定细则：
- **provider 位置**：与测试类同类 → 不加级；同最外层类 → L1；注解值是裸名却落在别的类 → L2（继承）；注解值是显式引用 → 按 provider 类相对测试类的位置 L1/L2(祖先)/L3/L4。池化时每个 provider 各算取最大。
- **helper 位置**：对 provider 子树里每一行 `TEST / TEST GET / TEST SET / METHOD_REF_TEST` 的声明类，相对**它所属 provider 的类**判：同最外层类 L1 → 祖先 L2 → 同包 L3 → 跨包 L4，取最大。
- **哪些行算 helper 调用**：只有 test-scope tag。`THIRD*`、`NEW_JDK_CLASS`、`ASSERT`、`MOCK`、`METHOD_REF_THIRD`、`METHODSOURCE_EXTERNAL`、枚举合成方法 `values()/valueOf()` 排除；`NEW`（项目内构造函数）不算 helper；`LOCAL_METHOD`（匿名/局部类内部方法）本身不算、其子行照常算；递归标记 `DIRECT_RECURSIVE / RECURSIVE_TO_ENTRY / INDIRECT_RECURSIVE` 单独计数；`UNRESOLVED_* / *_NOT_FOUND / MAX_DEPTH_REACHED` 记 unresolved、单独计数，不猜等级。
- **方法引用（③b）**：`METHOD_REF_*` 行只有在 provider 自己的流水线里被调用时才算（`ctx=call:map / flatMap / forEach / collect / apply / assertThrows …` 或 `ctx=target:`）；作为数据传出去的（`ctx=call:of / arguments / asList / add / put / build / named …`、`new:*`、`return`、`assign`、`array`、`lambda`、`conditional`）连同其展开子树一起剔除。**lambda 体内的普通调用照常算**（内联代码）。
- **production 代码**：裸签名 / `GET` / `SET` / `METHOD_REF_PROD`（非数据上下文）→ `hits_production = True`，不影响 L 级。
- **helper depth**（Structure 维度，同一套行过滤）：`depth` = 缩进层数（provider 直接调用 = 1）；`max_depth_test / distinct_helpers_test / total_calls_test` 在 test-scope 行上算，`*_prod` 在 production 行上算。

## 匹配与失败类别
- 样本行 (project, 测试类, 方法名) → AAA 文件：先精确名；再 `-p<参数个数>` 重载名和 `Outer.Inner_方法` 嵌套名；多个候选时优先唯一的 MethodSource PT；仍多个则按源码声明顺序取第一个（`OVERLOAD_PICKED_FIRST_DECLARED`，与 Java 侧一致）。
- 失败类别：`json_not_found`（当前 checkout 里已不存在）、`EXTERNAL_PROVIDER`、`AMBIGUOUS_NESTED_OR_OVERLOAD`（理论上仍可能，样本里目前 0）。


---
## 2026-09-16 晚：口径升级（覆盖上文中与之冲突的部分）

### Dependency = 参数构造对 test-code artifacts 的传递依赖
从 provider 出发，沿"参数构造相关的 test-code 依赖"一直追到 production/JDK 边界；在走过的**全部 test-code artifact**里取离测试类
最远的等级。artifact 包括：方法调用（含 helper 的 helper）、**字段/常量引用及其初始化器**、`new` 的 test 类型、`Type.class`、
静态导入的成员、provider 流水线里调用的方法引用。等级：同类 L0 / 同最外层类 L1 / 祖先（父类链+接口）L2 / 同包 L3 / 跨包 L4。
production 类型的引用只标 `hits_production`。

实现 = AAA 调用链（有 binding，`dependency_aaa`）与源码侧 `ArtifactWalker`（无 binding，`dependency_src`，负责字段/常量/构造/
字段初始化器）各算一个，取最大（`dependency`）。structure / helper depth **不变**，仍只数方法调用。

### Construction = 参数值是否静态可确定
不需要执行任何生成 / 变换 / 运行时逻辑就能从代码里读出最终参数值 → Literal；否则 Dynamic。评估是**传递**的：helper 体按同样规则
递归评估（参数按实参是否静态代入），字段按其初始化器评估。

Literal：字面量 / 枚举与 `Type.MEMBER` / class token / static final 常量（初始化器静态）/ 显式数组 / `List.of` `Arrays.asList`
`Arguments.of` `Named.of` 等静态工厂装箱 / `new ValueObject(静态…)`（production/JDK 类型；test 类型须是 record 或构造函数体只有
`this.f = 参数/静态值` 的纯数据持有者）/ 字面量间的拼接算术 / 由上述值构成的字段 / 多条显式 `add(...)` / 表达式体为字面量的 lambda /
production/JDK 类型上的静态字段访问（`SnmpConstants.version1`）。

Dynamic：if/for/switch/try；map/filter/flatMap/generate 等变换（对象上的链式调用）；helper 体不满足静态规则；builder/配置突变；
IO / 资源读取；环境依赖；random；反射；块体 lambda / 方法引用（可执行行为）；white-list 外的 production/test API 调用；
字段无初始化器或在 `static {}` 块里被填充；test 类型的构造函数含逻辑；找不到的名字（非常量命名）。
