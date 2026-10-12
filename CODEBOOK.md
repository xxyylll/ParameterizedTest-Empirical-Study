# Codebook: Parameter-Source Usage in JUnit 5 Parameterized Tests

This codebook accompanies the paper *Parameterized Tests in Practice: Adoption, Styles, and Impact in Apache Java Projects*. It defines every category used in RQ2.2 and is the codebook that the first author and the three inter-rater-reliability (IRR) raters applied.

The codebook is organized from the general to the specific. Section 0 gives an overview of all dimensions and how they apply to each parameter source. Section 1 defines what is coded. Sections 2–5 then define the four dimensions one at a time. Each dimension starts with its guiding question and a summary table of its categories, followed by the decision rules, examples, and common pitfalls. Section 6 covers the less frequent sources, and Section 7 describes the coding procedure.

---

## 0. Overview

### 0.1 The four dimensions

| Dimension | Guiding question | Categories | How it was coded |
|---|---|---|---|
| **Construction** | How are the parameter values produced? | Inline: *Primitive* / *Class literal*; Enum: *Enum constant*; Provider: *Explicit* / *Computed*; File: *External resource file*; Framework: *Framework-generated* | Manual (Phase 1), then automated by the Parameter Source Pattern Extractor (Phase 2) |
| **Dependency** | What is the furthest test-side code that must be traced to resolve the parameters? | *L0*–*L4*; for enums also *Production* | Manual, then automated |
| **Structure** | What is the scale and internal organization of the parameter data? | Number of parameter sets; provider complexity; enum structure (*Data-carrying* / *Label-based*) | Manual, then automated |
| **Usage intent** | What problem does parameterization solve, and why this source? | Layer 1: *Same* / *Different* equivalence class. Layer 2: source-specific roles (including the enum domain, *Reused from production* / *Encapsulated in test code*) | Manual only, except the enum domain, which is derived from the dependency label (§5.4) |

Construction, dependency, and structure are defined over the source code alone, so they could be automated once their rules were fixed. Usage intent requires understanding what the test checks, so it was coded only on the manually reviewed sample.

### 0.2 Which dimensions apply to which source

JUnit 5 offers ten standard parameter sources. They fall into five groups by how their values are supplied, and each group is coded only on the dimensions that are meaningful for it.

| Source group | Sources | Construction | Dependency | Structure | Usage intent |
|---|---|---|---|---|---|
| Inline literal | `@ValueSource`, `@CsvSource` | Primitive / Class literal | L0 unless constants are referenced | # parameter sets | Equivalence class; semantic role |
| Enum selection | `@EnumSource` | Enum constant | Production / L1–L4 | # parameter sets; data-carrying / label-based | Equivalence class; enum domain; behavior-carrying |
| Provider-based | `@MethodSource`, `@FieldSource`, `@ArgumentsSource` | Explicit / Computed | L0–L4 | # parameter sets; cognitive complexity; helpers | Equivalence class; `@MethodSource` only: necessity, driver, origin, behavior-carrying |
| External file | `@CsvFileSource` | External resource file | External resource file | # parameter sets | Equivalence class |
| Framework-provided | `@NullSource`, `@EmptySource`, `@NullAndEmptySource` | Framework-generated | — | — | Equivalence class |

"—" means the dimension is not coded for that group.

### 0.3 Where each IRR dimension is defined

Appendix B of the paper reports Cohen's κ for the manually coded dimensions below.

| IRR dimension (Appendix B) | Defined in |
|---|---|
| Equivalence class | §5.1 |
| Role of inline values | §5.2 |
| Reason for `@MethodSource` (type, value, or both) | §5.3, Step 2 |
| Type-driven subtype | §5.3, Step 3 (type origin) |
| Value-driven subtype | §5.3, Step 3 (value origin) |
| Behavior-carrying | §5.5 |
| Enum structure | §4.3 |

The enum domain (§5.4) is not in this list: it is derived directly from the dependency label rather than coded by hand, so it has no inter-rater reliability to assess.

---

## 1. Unit of Coding and Valid Cases

**Unit of coding.** One JUnit 5 parameterized test, together with:
- its parameter-source annotation;
- its provider (a method, a field, or an `ArgumentsProvider` class) or its enum declaration, where applicable;
- the test-side helper methods it calls.

When a test references several providers (for example, a provider declared in an abstract base class and implemented in each subclass), the providers are pooled into a single unit.

**Valid cases.** Before any dimension is coded, each sampled test is checked for whether it uses parameterization meaningfully. A test is **excluded** when, for example:
- its parameters are never used in the test;
- it supplies only a single parameter set;
- it does not actually test anything, for example it only prints the parameter values without asserting on them.

All dimensions are coded only for valid cases.

```java
// Excluded: the parameter is never used
@ParameterizedTest
@ValueSource(ints = {1, 2, 3})
void runsWithoutError(int ignored) {
    assertTrue(service.isReady());
}
```

---

## 2. Construction

**Guiding question:** *How are the parameter values produced?*

The construction type is determined first by the source group. For inline and provider-based sources, it is then refined into finer categories.

### 2.1 Categories at a glance

| Source group | Category | Definition |
|---|---|---|
| Inline literal | **Primitive** | Numbers, strings, booleans, and other primitive literals written in the annotation |
| Inline literal | **Class literal** | Values that refer to program elements, such as class literals |
| Enum selection | **Enum constant** | Constants selected from an enum type, optionally filtered by name |
| Provider-based | **Explicit** | The complete parameter set is written out and fixed at compile time |
| Provider-based | **Computed** | Determining the parameter set requires executable logic |
| External file | **External resource file** | Values are read from a delimited resource file |
| Framework-provided | **Framework-generated** | `null` or an empty value supplied by JUnit itself |

### 2.2 Inline literal sources (`@ValueSource`, `@CsvSource`)

The values are written directly inside the annotation.

```java
// Primitive
@ValueSource(ints = {1, 2, 3})
@CsvSource({"1, one", "2, two"})

// Class literal
@ValueSource(classes = {IOException.class, Exception.class})
```

### 2.3 Enum selection (`@EnumSource`)

The annotation does not list values. It selects constants from an enum type, optionally filtered with `names` and `mode`.

```java
enum Codec { GZIP, ZIP, NONE }

@ParameterizedTest
@EnumSource(Codec.class)                                   // all constants
@EnumSource(value = Codec.class, names = {"GZIP", "ZIP"}) // filtered
```

### 2.4 Provider-based sources (`@MethodSource`, `@FieldSource`, `@ArgumentsSource`)

The values are supplied by test code: a provider method, a field, or the `provideArguments` method of an `ArgumentsProvider` class.

**Explicit.** The complete parameter set is fixed at compile time. It is built from literals, constants, statically defined collections or arrays, or value objects constructed from such inputs. The provider acts as an organizational wrapper around values that could not be written inside an annotation.

```java
// Explicit: every value is written out
static Stream<Arguments> cases() {
    return Stream.of(
        Arguments.of("a", 1),
        Arguments.of("b", 2));
}

// Explicit: objects, but constructed from literals
static Stream<Pair<Text, Text>> ranges() {
    return Stream.of(
        new Pair<>(null, null),
        new Pair<>(new Text("dd"), new Text("mm")));
}
```

**Computed.** Determining the parameter set requires executable logic, such as control flow, iteration, stream transformations, helper delegation, reflection, or I/O.

```java
// Computed: stream transformation over all codecs
static Stream<Arguments> cases() {
    return Stream.of(Codec.values())
        .flatMap(c -> IntStream.range(0, 4)
            .map(k -> 1 << (10 * k))
            .mapToObj(n -> arguments(c, n)));
}

// Computed: I/O
static Stream<Path> inputs() throws IOException {
    return Files.list(Path.of("src/test/resources/in"));
}
```

**Rule for pooled providers.** When several providers are pooled into one unit, the test is Computed if any pooled provider is Computed.

### 2.5 External resource file (`@CsvFileSource`)

```java
@CsvFileSource(resources = "/expected-results.csv", numLinesToSkip = 1)
```

### 2.6 Framework-provided sources

```java
@ParameterizedTest
@NullAndEmptySource
void rejectsBlank(String input) { ... }
```

---

## 3. Dependency

**Guiding question:** *What is the furthest test-side artifact that must be traced to resolve the parameter construction?*

If construction involves several artifacts, the furthest one determines the level. Only test-side code counts; calls into production code, the JDK, or third-party libraries do not raise the level.

### 3.1 Categories at a glance

| Level | Name | The furthest code reached is… |
|---|---|---|
| **L0** | Isolated | Nothing beyond the provider itself, in the source-owning test class |
| **L1** | Class-local | A helper method or nested class within the same test class |
| **L2** | Inherited | A base test class the test class extends |
| **L3** | Package-shared | Another test class in the same package |
| **L4** | Cross-package | Test code in another package, such as a shared test-utility module |
| **Production** | (`@EnumSource` only) | The enum is declared in production code (`src/main`) |

### 3.2 Provider-based sources

All examples share the same test method:

```java
@ParameterizedTest
@MethodSource("provider")
void examplePT(Foo foo) { ... }
```

```java
// L0: no test code beyond the provider
class ExampleTest {
    static Stream<Foo> provider() { return Stream.of(new Foo(1)); }
}

// L1: a helper in the same test class
class ExampleTest {
    static Stream<Foo> provider() { return Stream.of(testHelper(1)); }
    static Foo testHelper(int i) { ... }
}

// L2: provider inherited from a base test class
class ExampleTest extends BaseTestClass { /* examplePT */ }
abstract class BaseTestClass {
    static Stream<Foo> provider() { ... }
}

// L3: shared test data in the same package
//   src/test/java/samepath/ExampleTest.java
static Stream<Foo> provider() { return SharedTestData.foos(); }
//   src/test/java/samepath/SharedTestData.java

// L4: test utilities in another package
//   src/test/java/path/ExampleTest.java
static Stream<Foo> provider() { return TestUtils.foos(); }
//   src/test/java/otherpath/TestUtils.java
```

### 3.3 `@EnumSource`

The dependency of an `@EnumSource` test is where the enum is declared.
- **Production:** the enum is declared in production code (`src/main`).
- **L1–L4:** the enum is declared in test code, and the level is assigned by where it is declared relative to the test, using the same ladder as above (L1 nested in the test class, L2 in a base test class, L3 in another test class of the same package, L4 in another package).

L0 does not apply, because an enum declared in test code is at least a nested type of the test class (L1). Enums declared outside the project, such as `java.time.DayOfWeek`, are excluded.

```java
// Production
//   src/main/java/.../Codec.java
enum Codec { GZIP, ZIP }
//   src/test/java/.../CodecTest.java
@EnumSource(Codec.class)

// L1: the enum is nested in the test class
class CodecTest {
    enum Size { EMPTY, LARGE }
    @ParameterizedTest @EnumSource(Size.class) ...
}
```

### 3.4 Other sources

- **Inline literal sources** are L0, because the values are written at the test, unless they reference constants defined elsewhere (for example, `@ValueSource(strings = {TestConstants.HOST})`).
- **`@CsvFileSource`** is coded as *external resource file*.
- **Framework-provided sources** are not coded, because their values have no test-side origin.

---

## 4. Structure

**Guiding question:** *What is the scale and internal organization of the parameter data?*

Structure has three parts. The first applies to all developer-specified sources; the other two apply to one source group each.

### 4.1 Scale: number of parameter sets (all developer-specified sources)

The number of parameter sets is how many times the test runs, one run per set.

| Category | Definition |
|---|---|
| **Exact** | The count can be determined statically and is recorded |
| **Runtime-dependent** | The count depends on execution-time values, such as the number of files in a directory |
| **Unresolved** | The count could not be determined because of limitations of the extractor |

```java
// Exact: 3 parameter sets
@ValueSource(ints = {1, 2, 3})

// Runtime-dependent: the number of sets equals the number of files
static Stream<Path> inputs() throws IOException {
    return Files.list(Path.of("in"));
}
```

### 4.2 Provider complexity (provider-based sources)

| Property | Definition |
|---|---|
| **Cognitive complexity** | Cognitive Complexity (Campbell, 2018) of the provider body alone, without descending into the helpers it calls |
| **Helper depth** | The maximum depth of the test-scope helper chains reachable from the provider (the provider itself is depth 0) |
| **Number of helpers** | The number of distinct test-scope helpers involved |

```java
// Cognitive complexity 0, no helpers
static Stream<Integer> sizes() { return Stream.of(1, 2, 4); }

// Cognitive complexity > 0 (a loop and a condition), one helper
static Stream<Arguments> cases() {
    List<Arguments> list = new ArrayList<>();
    for (Codec c : Codec.values()) {          // +1
        if (c != Codec.NONE) {                // +2 (nested)
            list.add(arguments(c, sample(c))); // helper: sample()
        }
    }
    return list.stream();
}
```

### 4.3 Enum structure (`@EnumSource`)

Judged from the enum declaration.

| Category | Definition |
|---|---|
| **Data-carrying** | The constants carry per-constant fields or method implementations whose values or behavior differ between constants |
| **Label-based** | The constants are plain names, such as categories, modes, states, or flags |

```java
// Data-carrying: each constant carries its own values
enum Codec {
    GZIP("gz", true), ZIP("zip", true), NONE("", false);
    final String ext; final boolean compresses;
    Codec(String ext, boolean compresses) { ... }
}

// Label-based
enum Order { ASC, DESC }
```

**Pitfall.** The inherited `name()` and `ordinal()` methods do not make an enum data-carrying. Every enum has them.

---

## 5. Usage Intent

Usage intent is coded in two layers.
- **Layer 1** applies to every valid case and asks *what problem parameterization solves in the test*: running more instances of one scenario, or merging behaviorally different scenarios.
- **Layer 2** is source-specific and asks *why developers use this particular source*. It is coded for the four main sources; the others occur too rarely for source-specific categories and are coded at Layer 1 only.

| Layer | Applies to | Sub-dimensions | Section |
|---|---|---|---|
| Layer 1 | All sources | Equivalence class | §5.1 |
| Layer 2 | `@ValueSource`, `@CsvSource` | Semantic role | §5.2 |
| Layer 2 | `@MethodSource` | Necessity → driver → origin | §5.3 |
| Layer 2 | `@EnumSource` | Enum domain | §5.4 |
| Layer 2 | `@MethodSource`, `@EnumSource` | Behavior-carrying | §5.5 |

### 5.1 Layer 1: Equivalence class (all sources)

**Guiding question:** *Does the parameter value cause the test to assert something different?*

| Category | Definition |
|---|---|
| **Same** | All parameter sets run through one assertion structure. The test runs more instances of a single scenario |
| **Different** | A parameter-dependent branch changes which assertion runs, what it asserts against, or how the assertions are arranged |

**Decision rule (two steps).**
1. Determine whether the test side contains branching (`if/else`, `switch`, or an equivalent) whose condition depends, directly or indirectly, on a parameter. Branching inside a test-side helper that the test calls counts as test-side branching.
2. If such branching exists, determine whether it causes a different assertion or a different assertion structure to be executed: a different assertion method (for example, `assertEquals` versus `assertThrows`), an expected outcome computed inside the branch, or a different set or number of assertions along each path.

If either step fails, the test is **Same**. This includes branching that only varies the setup and then converges on a common action and assertion structure, as well as different inputs, different expected values supplied as parameters, different configurations, and success-versus-failure cases handled by a single assertion structure.

```java
// Same: one assertion path; the expected value is another parameter
void validate(String input, boolean expected) {
    assertEquals(expected, isValid(input));
}

// Same: the branch only builds a different fixture
void connects(boolean useSsl) {
    Config c = useSsl ? sslConfig() : plainConfig();
    assertTrue(client.connect(c).isOpen());
}

// Different: the branch selects which assertion runs
void parse(String input, boolean expectedValid) {
    if (expectedValid) assertTrue(parser.parse(input).isValid());
    else               assertThrows(IllegalArgumentException.class,
                                    () -> parser.parse(input));
}
```

**Pitfall.** Production code behaving differently for different parameters does not, by itself, make a test *Different*. Only differences on the test side count.

### 5.2 Layer 2: `@ValueSource` and `@CsvSource` — semantic role

**Guiding question:** *What does the parameter value represent in the test?*

| Category | Definition |
|---|---|
| **External language** | Syntax of another language that is parsed, compiled, matched, evaluated, or executed according to grammar rules, or configuration written in a recognized configuration language |
| **File / resource** | An address or identifier used to locate something that already exists; the value is a pointer and carries no internal logic |
| **General test data** | All other values: ordinary inputs and expected results, modes, options, switches, version strings, format strings |

**Decision rule.** The role is judged from how the value is used, not from its Java type. The categories are checked **in the order above**, and the first matching category is assigned.

**External language** includes SQL, regular expressions, XPath, JSONPath, expression languages, JSON, XML, XSD, and domain-specific languages. It excludes URLs and URIs, project-specific binary formats, and plain strings that are merely matched against.

**File / resource** includes file names, resource paths, classpath entries, class names, directories, and URLs.

```java
// External language: SQL that the system under test parses
@ValueSource(strings = {"SELECT a FROM t", "SELECT a, b FROM t"})
void parsesQuery(String sql) { assertNotNull(parser.parse(sql)); }

// File / resource: names used to load test files
@CsvSource({"empty.csv, 0", "nested.csv, 3"})
void readsTable(String file, int rows) {
    assertEquals(rows, load(file).size());
}

// General test data
@ValueSource(ints = {0, -1, 42})
void absIsNonNegative(int x) { assertTrue(Math.abs(x) >= 0); }
```

**Pitfall.** `"config.json"` is *File / resource*, because it is the name of a file. `{"enabled": true}` is *External language*, because it is the configuration content itself.

### 5.3 Layer 2: `@MethodSource` — necessity, driver, and origin

`@MethodSource` is coded in up to three steps. Each step is coded only when the previous one applies.

```
Step 1  Necessity        Replaceable ──► record the replacing source (Value / Csv / Enum)
                         Necessary   ──► Step 2
Step 2  Driver           Type-driven and/or Value-driven ──► Step 3
Step 3  Origin           Type origin (multi-select) / Value origin (single choice)
```

#### Step 1: Necessity

**Guiding question:** *Could a simpler source express the same parameters?*

| Category | Definition |
|---|---|
| **Replaceable** | The parameter sets could be expressed directly with an annotation-based source without changing the test |
| **Necessary** | Otherwise |

For replaceable tests, the replacing source is recorded:
- `@ValueSource`: a single parameter whose values are literals of a supported type;
- `@CsvSource`: several parameters whose values are literals convertible by JUnit's implicit argument conversion;
- `@EnumSource`: the values are constants of a single enum type.

```java
// Replaceable by @ValueSource(ints = {1, 2, 3})
static Stream<Integer> sizes() { return Stream.of(1, 2, 3); }

// Replaceable by @CsvSource({"a, 1", "b, 2"})
static Stream<Arguments> cases() {
    return Stream.of(Arguments.of("a", 1), Arguments.of("b", 2));
}

// Necessary: the parameter is a project type
static Stream<ProjectConfig> configs() {
    return Stream.of(new ProjectConfig(8), new ProjectConfig(16));
}
```

#### Step 2: Necessity driver (necessary cases only)

**Guiding question:** *Why is a provider method needed?*

| Category | Definition |
|---|---|
| **Type-driven** | The parameters use Java types that annotation-based sources cannot express, such as arrays, collections, custom objects, parsers, strategies, functions, or complex configuration objects |
| **Value-driven** | The parameter values must be generated, transformed, or fetched, for example through loops, stream transformations, combinations, arithmetic generation, or data read from files or the environment |

**Decision rule.** The provider, including any helper it calls, is traced before deciding. The two drivers are **not mutually exclusive**: a test is coded with both when both reasons apply independently.

```java
// Type-driven only: the values are written out; only the type is complex
static Stream<Foo> foos() {
    return Stream.of(new Foo(1), new Foo(2));
}

// Value-driven only: int values that must be generated
static IntStream sizes() {
    return IntStream.range(0, 8).map(i -> 1 << i);   // 1, 2, 4, ..., 128
}

// Both: Path is a type annotations cannot express,
// and the values are read from disk
static Stream<Path> inputs() throws IOException {
    return Files.list(Path.of("in"));
}
```

**Pitfalls.**
- A provider that merely delegates to a helper is not automatically value-driven. The helper's behavior determines the label.
- A provider that lists values explicitly, such as `Arguments.of(new Foo(1), new Foo(2))`, is type-driven only, however many values it lists. The values are written out; only the type is complex.
- Types that annotation-based sources can express (primitives, `String`, enum constants, class literals) do not make a provider type-driven.

#### Step 3: Origin

**Type origin (type-driven cases; multi-select).** *Where do the non-trivial parameter types come from?* All origins that apply are recorded. Primitives and `String` are not counted.

| Category | Definition | Examples |
|---|---|---|
| **Project** | A type defined by the project under test, in production or test code | `ProjectConfig`, `CommandLineParser` |
| **JDK** | A type from the Java standard library | `File`, `Path`, `Duration`, `Function`, collections, `Class` |
| **Third-party** | A type from an external library the project depends on | a Guava or Hadoop type used in another Apache project |

```java
// Project + JDK
static Stream<Arguments> cases() {
    return Stream.of(arguments(new ProjectConfig(8), Path.of("a.txt")));
}
```

**Value origin (value-driven cases; single choice).**

| Category | Definition |
|---|---|
| **Code-derived** | Values are produced by program logic, such as loops, streams, combinations, arithmetic, or helper-based generation |
| **Externally sourced** | Values originate outside the source code, such as files, runtime resources, environment data, or external fixtures |

```java
// Code-derived
static IntStream sizes() { return IntStream.range(0, 8).map(i -> 1 << i); }

// Externally sourced
static Stream<Path> inputs() throws IOException { return Files.list(Path.of("in")); }
```

### 5.4 Layer 2: `@EnumSource` — enum domain

**Guiding question:** *Does the test reuse an existing domain of the system under test, or define its own set of test scenarios?*

| Category | Definition | Dependency label (§3.3) |
|---|---|---|
| **Reused from production** | The test reuses an enum of the system under test, so the parameter space follows the input domain that production code already defines | Production |
| **Encapsulated in test code** | The test defines its own enum, typically to group test scenarios into named categories when no suitable production enum exists | L1–L4 |

**Decision rule.** The category is not coded by hand; it is derived directly from the dependency label in §3.3: an enum at *Production* is *Reused from production*, and an enum at L1–L4 is *Encapsulated in test code*. The dependency label records *where* the enum is declared; this dimension records what that location means for the intent of the test. Because it is derived, it was not part of the reliability study (§7).

```java
// Reused from production: the test follows the codecs the system supports
//   src/main/java/.../Codec.java
enum Codec { GZIP, ZIP }
//   src/test/java/.../CodecTest.java
@ParameterizedTest @EnumSource(Codec.class)
void roundTrip(Codec c) {
    assertArrayEquals(data, decode(encode(data, c), c));
}

// Encapsulated in test code: the test names its own input scenarios
class CodecTest {
    enum Size { EMPTY, LARGE }
    @ParameterizedTest @EnumSource(Size.class)
    void roundTrip(Size s) {
        byte[] d = sample(s);
        assertArrayEquals(d, decode(encode(d)));
    }
}
```

### 5.5 Layer 2: `@MethodSource` and `@EnumSource` — behavior-carrying

**Guiding question:** *Does the parameter supply behavior to execute, or does it describe the circumstances under which fixed behavior executes?*

| Category | Definition |
|---|---|
| **Behavior-carrying** | The parameter is executable **and** the behavior it supplies is itself part of the tested action |
| **Not behavior-carrying** | Otherwise |

**Decision rule.** Both conditions must hold. The following are **not** behavior-carrying: input values, state, configuration, implementation selectors, metadata, expected outcomes, and expected exceptions. A lambda or functional object is behavior-carrying only when it is invoked as part of the action under test; a lambda that merely produces a data value during setup is not.

```java
// Behavior-carrying: the parameter is the thing being exercised
static Stream<Parser> parsers() {
    return Stream.of(new JsonParser(), new YamlParser());
}
void parses(Parser parser) {
    assertEquals(expected, parser.parse(input));
}

// Not behavior-carrying: the parameter only selects what is built
void parses(ParserType type) {
    Parser parser = createParser(type);
    assertEquals(expected, parser.parse(input));
}

// Not behavior-carrying: the same builder class with different settings
// (configuration, not a different implementation)
static Stream<Builder> builders() {
    return Stream.of(new Builder().strict(true), new Builder().strict(false));
}
```

**`@MethodSource` subtypes.** Behavior-carrying parameters of `@MethodSource` are further distinguished as **strategy objects** (instances of different implementations of an interface or abstract class, as in the `Parser` example above) or **lambdas and functional values** (for example, `Function<RouteBuilder, RouteDefinition>` values invoked by the test). For `@MethodSource`, behavior-carrying is always a subset of type-driven cases.

**`@EnumSource`.** An enum is behavior-carrying only when the test invokes constant-specific behavior as part of the tested action. A data-carrying enum (§4.3) is therefore not behavior-carrying by itself.

```java
enum Operation {
    ADD { int apply(int a, int b) { return a + b; } },
    SUB { int apply(int a, int b) { return a - b; } }
}

// Behavior-carrying: the test calls the constant-specific method
void applies(Operation op) {
    assertEquals(expected(op), op.apply(3, 2));
}

// Not behavior-carrying: the constant's data is only read
void hasExtension(Codec c) {
    assertTrue(fileName(c).endsWith(c.ext));
}
```

---

## 6. Other Sources

`@FieldSource`, `@ArgumentsSource`, `@CsvFileSource`, and the framework-provided sources are coded at Layer 1 (equivalence class) only. Their source-specific use is described qualitatively in the paper:

| Source | Typical use |
|---|---|
| `@FieldSource` | Reusable named parameter collections |
| `@ArgumentsSource` | A class-based argument factory |
| `@CsvFileSource` | Externally maintained reference datasets |
| `@NullSource`, `@EmptySource`, `@NullAndEmptySource` | Boundary-value scenarios |

---

## 7. Coding Procedure

**Developing the codebook.** The categories were developed iteratively on a stratified sample of 1,604 parameterized tests. The first author coded all cases; ambiguous and contested cases were reviewed jointly with two other authors in weekly meetings, disagreements were resolved by discussion, and the decision rules were revised until no new categories emerged.

**Reliability assessment.** Three raters who were not involved in developing the codebook each coded 60 cases from a stratified sample of 150 valid cases (15 cases were coded by all three), using this codebook. Each rater's labels were compared with the first author's using Cohen's κ, per dimension. The results are reported in Appendix B of the paper. Three judgments were not part of the reliability study: whether a `@MethodSource` test is replaceable (§5.3, Step 1), the enum domain (§5.4), which is derived from the dependency label rather than coded by hand, and the manual domain assignment used in RQ1. `@MethodSource` cases coded as replaceable carry no further label and were therefore not included in the reliability sample.

**The *unclear* label.** For every manually coded dimension, a rater could mark a case as *unclear* when the codebook did not allow a confident decision, for example because a provider could not be traced without running the code. In the reliability analysis, *unclear* labels are reported both counted as disagreements and excluded.

**General rules for all dimensions.**
- Code each dimension independently; a label on one dimension does not imply a label on another, except where this codebook states a dependency (for example, Step 2 of §5.3 is coded only for necessary cases).
- Judge a provider by its own logic and by the helpers it calls, not by how referenced constants are built elsewhere. When one test references several providers, they are pooled into one unit (§1).
- When in doubt about whether code is test-side or production-side, use the source directory: `src/test` is test code, `src/main` is production code.

---

## Appendix: Label names in the data files

The data files in this repository were produced while the codebook was being developed and keep the
labels used at the time. **This codebook is authoritative**; the tables below map each codebook category to
the column and value that represents it in the data.

### A.1 Automated classification (`rq2/results/rq2_2/rq22_*_all.csv`)

| Codebook (section) | Column | Value in the data |
|---|---|---|
| Construction: Primitive (§2.2) | `construction` (ValueSource, CsvSource) | `Literal-Primitive` |
| Construction: Class literal (§2.2) | `construction` (ValueSource, CsvSource) | `Literal-Metadata` |
| Construction: Enum constant (§2.3) | — (implied by the source); `names_mode` records `ALL` constants or a `SUBSET` filtered by `names` | — |
| Construction: Explicit (§2.4) | `construction` (MethodSource, FieldSource, ArgumentsSource) | `Literal` |
| Construction: Computed (§2.4) | `construction` (MethodSource, FieldSource, ArgumentsSource) | `Dynamic` |
| Construction: External resource file (§2.5) | `construction` (CsvFileSource) | `File` |
| Construction: Framework-generated (§2.6) | `construction` (`rq22_null_empty_standalone.csv`) | `None(annotation)` |
| Dependency: L0–L4 (§3) | `dependency` | `L0` … `L4` |
| Dependency: Production (§3.3) | `dependency` (EnumSource) | `Production` (`enum_location` = `production` or `production(generated)`) |
| Dependency: external resource file (§3.4) | `dependency` (CsvFileSource) | `File` |
| Excluded: enum declared outside the project (§3.3) | `dependency` (EnumSource) | `External` |
| Not coded: provider is a JDK / third-party method | `dependency` (MethodSource), `status` | `EXTERNAL`, `EXTERNAL_PROVIDER` |
| Not coded: framework-provided sources (§3.4) | `dependency` (`rq22_null_empty_standalone.csv`) | `L0` (ignored) |
| Number of parameter sets (§4.1) | `n_sets`; `n_sets_total` adds sets contributed by `@NullSource`/`@EmptySource` | — |
| Exact (§4.1) | `n_sets_status` | `EXACT` |
| Runtime-dependent (§4.1) | `n_sets_status` | `RUNTIME_DEPENDENT` |
| Unresolved (§4.1) | `n_sets_status` | `STATIC_UNSUPPORTED` (rule not implemented by the extractor) or `UNRESOLVED_SOURCE` (code to count is unavailable, e.g. an abstract provider) |
| Cognitive complexity (§4.2) | `cognitive_complexity` | — |
| Helper depth (§4.2) | `max_helper_depth_test` | — |
| Number of helpers (§4.2) | `distinct_helpers_test` | — |
| Data-carrying / Label-based (§4.3) | `enum_structure` | `Data-carrying` / `Label-based` |
| Enum domain: Reused from production / Encapsulated in test code (§5.4) | derived from `dependency` (EnumSource) | `Production` / `L1`–`L4` |

`rq2/results/rq2_2/pt_methodsource_structure_validated379.csv` and the RQ3.2 outputs (`rq3/results/rq3_2/`)
use the same `Literal` / `Dynamic` and `L0`–`L4` values. In `cross_source/`, the source families `inline`,
`type`, `file` and `provider` correspond to the source groups Inline literal, Enum selection, External file
and Provider-based (§0.2).

### A.2 Manual coding (`rq2/results/rq2_2/manual_coding/`)

| Codebook (section) | Column | Value in the data |
|---|---|---|
| Valid case (§1) | `Good Cases?` | empty = valid; `no` = excluded, reason in `prerequisite (reason not good)` |
| Construction: Explicit / Computed (§2.4) | `Construction` (MethodSource) | `literal` / `dynamic` |
| Construction: Primitive / Class literal (§2.2) | `Construction` (ValueSource) | `Primitive_string`, `Boolean`, `Int`, `Long`, `Double/Float` / `class: metadata`; CsvSource rows are all `literal` (Primitive) |
| Dependency L0 / L1 / L2 / L3 / L4 (§3) | `Dependency (parameter)` | `L0: Method Local` / `L1: Class Helper` / `L2: Inheritance` / `L3: Package Helper` / `L4: Cross-Pkg` |
| Dependency: Production (§3.3) | `Dependency (parameter)` (EnumSource) | `production code` |
| — | `Dependency (parameter)` | `L5: System Resource` was used during codebook development and has no codebook equivalent; the dependency labels used in the paper are the automated ones (A.1) |
| Equivalence class: Same / Different (§5.1) | `Strategic Layer` | `same equivalence class` / `different equivalence class` |
| Semantic role: External language / File / resource / General test data (§5.2) | `Semantic layer` (`Semantic Layer` in CsvSource) | `external language` / `file / resource lookup` / `general` (also `General`, `Generic`) |
| Necessity: Replaceable (§5.3, Step 1) | `Methodsource Intent` | `could be replaced by ValueSource` / `CsvSource` / `EnumSource` |
| Driver: Type-driven / Value-driven / both (§5.3, Step 2) | `Methodsource Intent` | `type complexity` / `value complexity` / `both type & value` |
| Type origin: Project / JDK / Third-party (§5.3, Step 3) | `Type Complexity Subcategory` | free text listing the origins, e.g. `1 project's own type, 1 jdk, 3 primitive`: `project's own type` = Project, `jdk` = JDK, `third-party framework` = Third-party; primitives are not counted |
| Value origin: Code-derived / Externally sourced (§5.3, Step 3) | `Value Complexity` | `code-derived` / `externally sourced` |
| Behavior-carrying, `@MethodSource` (§5.5) | `Behavior Carring` | `strategy-object-based` (strategy objects) / `lambda based` (lambdas and functional values); empty = not behavior-carrying |
| Behavior-carrying, `@EnumSource` (§5.5) | `Behavior？` | `yes`; empty = not behavior-carrying |
| Enum structure (§4.3) | `Enum representation` | `data-carring` / `label` |

Values are compared case-insensitively. Seven `Semantic layer` cells keep working labels that predate the
final categories (`config` 4, `format` 1, `Behavior-carrying Parameter` 2); none is in the IRR sample.
Free-text columns (`Usage Intent`, `Note`, `Group discussion`, …) are working notes from codebook development.

### A.3 Inter-rater reliability (`rq2/results/rq2_2/irr/`)

`sample_items.csv` carries the first author's labels in the manual-coding columns of A.2;
`rater_answers.xlsx` and `irr_kappa.csv` use the following names.

| IRR dimension (Appendix B, §0.3) | Column in `rater_answers.xlsx` / `irr_kappa.csv` | Values |
|---|---|---|
| Equivalence class | `equivalence_class` | `same` / `different` |
| Role of inline values | `semantic_role` | `general` / `file-resource` / `external-language` |
| Reason for `@MethodSource` | `methodsource_intent` | `type` / `value` / `both` |
| Type-driven subtype | `type_complexity` | `project` / `jdk` / `third-party`, joined with `+` |
| Value-driven subtype | `value_complexity` | `code-derived` / `externally-sourced` |
| Behavior-carrying | `behavior_carrying` | `yes` / `no` |
| Enum structure | `enum_structure` | `data-carrying` / `label` |

Every column also allows `unclear`. `rater_answers.xlsx` additionally has an `enum_usage_intent` column (`shared-contract` / `semantic-specific`); it is not a codebook dimension and is not analysed.
