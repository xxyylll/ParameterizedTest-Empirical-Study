# Rating Guide — Parameterized Test Usage Intent

Thank you for helping validate this codebook.

You will classify **60 JUnit 5 parameterized tests**. All the code you need is in your
packet (`packet_R*.md`) — you do not need to download or build any project. Each item
shows the test method (with its annotation and parameter values), the parameter provider
or enum declaration where applicable, and any test-side helper methods the test calls.

**What we are measuring.** We want to know whether this codebook is reproducible by
someone other than its author. We are *not* testing you. If a case is genuinely
ambiguous, mark it `unclear` and say why in one line — that is a useful result, not a
failure. Please do not look up how the project itself describes the test, and please do
not confer with the other raters.


---

## How to record your answers

Fill in `[name].csv` — one row per item, matched by `item_id`. Leave a column blank
when it does not apply to that source (the table below says which apply).

| Column | Applies to | Allowed values |
|---|---|---|
| `equivalence_class` | all | `same` / `different` / `unclear` |
| `semantic_role` | Method, Value, Csv | `general` / `file-resource` / `external-language` / `unclear` |
| `methodsource_intent` | Method | `type` / `value` / `both` / `unclear` |
| `type_complexity` | Method | `project` / `jdk` / `third-party`, joined with `+` if several; `n/a` / `unclear` |
| `value_complexity` | Method | `code-derived` / `externally-sourced` / `n/a` / `unclear` |
| `behavior_carrying` | Method, Enum | `yes` / `no` / `unclear` |
| `enum_structure` | Enum | `label` / `data-carrying` / `unclear` |
| `enum_usage_intent` | Enum | `shared-contract` / `semantic-specific` / `unclear` |
| `confidence` | all | `high` / `medium` / `low` |
| `notes` | all | free text, only when useful |

---

## 1. `equivalence_class` — all sources

**Question: does the parameter value cause the test to assert something different?**

Two steps, in order:

1. **Is there parameter-dependent branching on the test side?** `if/else`, `switch`, or
   equivalent, where the condition depends (directly or indirectly) on the parameter.
   **This branching may live in a helper the test calls, not only in the test body** —
   the helpers your packet shows under *Test-side helpers* are part of the test side, so
   check them too.
2. **If yes — does that branching cause a different assertion, or a different assertion
   *structure*, to be executed?** Only then is it `different`.

- **`different`** — the branch changes which assertion runs, what it asserts against, or
  how the assertions are arranged: a different assertion method (`assertEquals` vs
  `assertThrows`), a different expected outcome computed inside the branch, or a
  different set or number of assertions along each path.
- **`same`** — everything else. This includes branching that only varies *setup* or
  *arrangement* and then converges on one common action and one common assertion
  structure. It also includes different inputs, different expected values passed in as
  parameters, different configurations, and success-vs-failure cases, as long as a single
  assertion structure handles them.

```java
// same — one assertion path; the expected value is just another parameter
void validate(String input, boolean expected) {
    assertEquals(expected, isValid(input));
}

// same — the branch only builds a different fixture, then asserts the same thing
Config c = useSsl ? sslConfig() : plainConfig();
assertTrue(client.connect(c).isOpen());

// different — the branch selects which assertion runs
if (expectedValid) assertTrue(result.isValid());
else               assertThrows(IllegalArgumentException.class, ...);

// different — same assertion method, but a different assertion structure per path
if (hasProjection) { assertEquals(2, out.size()); assertNotNull(out.get(1)); }
else               { assertNull(out); }
```

Production code behaving differently per parameter does **not** by itself make this
`different` — the question is about the test's own assertions.

---

## 2. `semantic_role` — MethodSource, ValueSource, CsvSource

**Question: what does the parameter value *represent*?** Judge by its role in the test,
not its Java type — `int`, `String`, `boolean` are all irrelevant here.

Apply in order; first match wins.

1. **`external-language`** — the value is syntax of another language that is parsed,
   compiled, matched, evaluated, or executed by grammar rules, **or** it is configuration
   written in a recognised configuration language.
   Examples: SQL, regular expressions, XPath, JSONPath, expression languages, JSON, XML,
   XSD, DSLs.
   *Not* this category: a URL or URI (it has a format but no execution semantics); a
   project-specific binary format; a plain string that merely gets matched against.

2. **`file-resource`** — the value is an address or identifier used to locate something
   that already exists: a file, resource, classpath entry, class name, directory, or URL.
   The string carries no internal logic; it is a pointer.

3. **`general`** — anything else. Ordinary data being processed or compared: inputs,
   expected results, modes, options, configuration switches, version strings, format
   strings.

Watch the distinction: **`config.json` is `file-resource`** (a filename), while
**`{"enabled": true}` is `external-language`** (the content itself).

---

## 3. MethodSource only

### 3a. `methodsource_intent` — why is a method needed at all?

Every item you receive genuinely needs `@MethodSource`; your job is to say **why**.

- **`type`** — because the parameter uses a Java type that inline annotations cannot
  express: arrays, collections, custom objects, parsers, strategies, functions, complex
  configuration objects.
- **`value`** — because the values themselves must be generated, transformed, or fetched:
  loops, stream transformations, combinations, arithmetic generation, data read from
  files or the environment.
- **`both`** — both reasons apply independently.

Trace the provider before deciding. A provider that merely calls a helper is not
automatically `value` — look at what the helper actually does. A provider that lists
`Arguments.of(new Foo(1), new Foo(2))` is `type`, not `value`: the values are written out,
only the type is complex.

### 3b. `type_complexity` — only when you answered `type` or `both`

**Question: where do the non-trivial parameter types come from?**

Look at the provider's return type and at the test method's parameter declarations. List
every origin that the *complex* types come from — plain primitives and `String` are not an
origin, they are just ordinary co-parameters.

- **`project`** — a type defined by the project under test, whether in its production code
  or in its test code.
- **`jdk`** — a type from the Java standard library: `File`, `Path`, `Duration`, `Stream`,
  `Function`, collections, `Class`, and so on.
- **`third-party`** — a type from an external library the project depends on (Avro, Calcite,
  Guava, Mockito, AWS SDK, …).

If several origins appear, join them with `+` in any order — `project+jdk`. Most cases have
exactly one.

```java
// project          — SegmentAnalysis is defined by the project
Stream.of(Arguments.of(new SegmentAnalysis(...), 3))

// jdk              — Path and Duration are both JDK types
Stream.of(Arguments.of(Paths.get("a.txt"), Duration.ofSeconds(1)))

// project+jdk      — one of each (the int is a primitive and does not count)
Stream.of(Arguments.of(new HoodieConfig(...), StandardCharsets.UTF_8, 3))
```

Answer `n/a` when you classified the item as `value` only.

### 3c. `value_complexity` — only when you answered `value` or `both`

- **`code-derived`** — values come from program logic: loops, streams, combinations,
  arithmetic, helper generation.
- **`externally-sourced`** — values come from outside the source code: files, runtime
  resources, environment data, external fixtures.

Otherwise `n/a`.

### 3d. `behavior_carrying`

**Question: is the parameter supplying behaviour to execute, or describing the
circumstances under which fixed behaviour executes?**

`yes` requires both: the parameter is **executable**, and the behaviour it supplies is
**itself part of the tested action**.

```java
// yes — the parameter IS the thing being exercised
void test(Parser parser) {
    assertEquals(expected, parser.parse(input));
}

// no — the parameter only selects which parser gets built
void test(ParserType type) {
    Parser parser = createParser(type);
    parser.parse(input);
}
```

`no` covers: input values, state, configuration, implementation *selectors*, metadata,
expected outcomes, expected exceptions, failure conditions.

A lambda or functional object counts as `yes` only when it is invoked as part of the
action under test. A lambda that merely materialises a data value during setup is `no`.

---

## 4. EnumSource only

### 4a. `enum_structure` — look at the enum **declaration** (included in your packet)

- **`label`** — the constants are symbolic names: categories, modes, states, flags.
- **`data-carrying`** — the constants carry meaningful per-constant data, via constructor
  arguments or fields that differ between constants.

```java
enum Format { JSON, XML, CSV }                       // label

enum Case {                                          // data-carrying
    VALID("abc", true), INVALID("", false);
    final String input; final boolean expected;
}
```

Inherited `name()` and `ordinal()` do **not** make an enum data-carrying.

### 4b. `enum_usage_intent` — look at the **test side**

**Question: does the test side treat the enum constants differently?**

- **`semantic-specific`** — there is test-side, enum-dependent differentiation:
  `if/else`, `switch`, different assertions, or different actions keyed on the enum value.
  **This differentiation counts whether it sits in the test body or in a helper the test
  calls** — check the *Test-side helpers* section of the item before deciding.
- **`shared-contract`** — no such differentiation; the same logic is applied uniformly
  across the selected constants, asserting a contract that should hold for all of them.

Production code that behaves differently per constant does **not** make this
`semantic-specific`. The differentiation has to be on the test side.

> **How this relates to `equivalence_class`.** They are two steps of the same enquiry, so
> answer `enum_usage_intent` first:
>
> - no test-side differentiation → `shared-contract`, and `equivalence_class` is `same`.
> - differentiation exists → `semantic-specific`; then ask whether that differentiation
>   *further changes the tested assertion*. If it does, `equivalence_class` is
>   `different`; if it only varies setup, it stays `same`.
>
> So `different` implies `semantic-specific`, but not the other way round.

### 4c. `behavior_carrying`

Same rule as 3d. An enum is `yes` only when it supplies executable behaviour that is
itself exercised — typically constant-specific method bodies that the test invokes
directly.

```java
enum Operation {
    ADD { int apply(int a, int b) { return a + b; } },
    SUB { int apply(int a, int b) { return a - b; } }
}
```
`yes` if the test calls `operation.apply(...)`. An enum supplying only labels, expected
values, configuration, or selectors is `no`.

---

## 5. When to use `unclear`

Use it when the code in your packet does not give you enough evidence — not when the case
is merely hard. If you can make a defensible call, make it and set `confidence` to
`medium` or `low` instead.

Please write one line in `notes` for every `unclear`, and for anything where you felt the
guide did not cover the case. Those notes are the most useful thing you can give us.
