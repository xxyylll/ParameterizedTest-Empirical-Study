# Analysis tools

本研究用到两个独立的静态分析器。两者的产物都不在 Git 里（体积过大），
见仓库根 README 的数据归档说明。

---

## 1. Lightweight annotation-level parser  — RQ1 / RQ2.1 / RQ2.2

**`test-parser-1.0-SNAPSHOT-jar-with-dependencies.jar`**（本目录，8.1 MB）

基于 [JavaParser](https://javaparser.org/) 的注解级抽取器。只看注解与方法签名，
不做符号解析，因此可以在不编译项目的前提下扫完整个语料。

| | |
|---|---|
| Main class | `com.testparser.TestParserApp` |
| Build date | 2025-12-11 |
| SHA-256 | 见 `test-parser.jar.sha256` |

它产出每个项目一个 JSON，字段包括 `isParameterized`、`parameterSources`、
`testCaseSourceCode`、`importedPackages`。

```bash
java -cp test-parser-1.0-SNAPSHOT-jar-with-dependencies.jar \
     com.testparser.TestParserApp <project-dir> <output.json>
```

> **源码状态**：这个 jar 的 Java 源码目录在后续的工作区整理中丢失，只剩可执行的
> fat jar。jar 里保留了完整的 class 文件（含 `JUnit5ParameterSourceExtractor`
> 等），行为可复现、可反编译核验，但无法直接重新编译。jar 校验和已固定在本目录，
> 供复现者确认用的是同一个二进制。
> 注解级抽取的准确性另有人工核验：`../rq1/results/parser_validation/`（200 条分层样本）。

## 2. AAA trace analyzer — RQ3.1 / RQ3.2

**第三方开源工具，未随本仓库分发**，请自行取用：

| | |
|---|---|
| Repository | https://github.com/Codegass/Javalang-analyzing-cli |
| Version | **v1.3.2** |
| Commit | `46a90c6baaf8977c336492c336c30240cf5fa8f3` |
| Engine | Eclipse JDT |

```bash
git clone https://github.com/Codegass/Javalang-analyzing-cli
cd Javalang-analyzing-cli && git checkout v1.3.2 && ./gradlew shadowJar
java -jar build/libs/Javalang-analyzing-cli-1.3.2-all.jar <project-dir>
```

它做完整的符号解析，输出每个测试方法的 Arrange–Act–Assert 语句序列
（`parsedStatementsSequence`），这是 RQ3 复杂度与重复度指标的输入。
因为要解析符号，项目必须先构建成功 —— 这是 RQ3 语料只有 46 个项目的原因。
解析成功率见 `../rq3/code/rq3_1/parse_success_rate.py`。

## 3. Clone detection — RQ3.1 duplication

[CCFinderSW 1.0](https://github.com/YuichiSemura/CCFinderSW)，classwise 模式：

```bash
java -jar CCFinderSW-1.0.jar -d <dir> -l java -t 50 -ccf -o <out>
```

`-t 50` 为最小 token 数阈值。dupPerc 按行比例计算，细节见
`../rq3/code/rq3_1/build_test_dup_metrics.py`。
