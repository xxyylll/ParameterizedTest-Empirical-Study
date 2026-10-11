# Rating packet R3

60 items. For each one, classify only the dimensions that apply to its source — the rules are in `rater_guide.md`.

Record your answers in `packet_R3.csv`, one row per item, matched by `item_id`. If the code shown does not let you decide, answer `unclear` and write one line in `notes`.

---

## IRR-001  ·  MethodSource

**项目** `Commons-RDF`  **文件** `commons-rdf/commons-rdf-integration-tests/src/test/java/org/apache/commons/rdf/integrationtests/AllToAllTest.java`  **测试** `testAddTermsFromOtherFactory`

### Test method

```java
@MethodSource("data")
    @ParameterizedTest(name = "{index}: {0} -> {1}")
    void testAddTermsFromOtherFactory(final Class<? extends RDF> from, final Class<? extends RDF> to) throws Exception {
        RDF nodeFactory = from.getConstructor().newInstance();
        RDF graphFactory = to.newInstance();

        try (final Graph g = graphFactory.createGraph()) {
            final BlankNode s = nodeFactory.createBlankNode();
            final IRI p = nodeFactory.createIRI("http://example.com/p");
            final Literal o = nodeFactory.createLiteral("Hello");

            g.add(s, p, o);

            // blankNode should still work with g.contains()
            assertTrue(g.contains(s, p, o));
            final Triple t1 = g.stream().findAny().get();

            // Can't make assumptions about BlankNode equality - it might
            // have been mapped to a different BlankNode.uniqueReference()
            // assertEquals(s, t.getSubject());

            assertEquals(p, t1.getPredicate());
            assertEquals(o, t1.getObject());

            final IRI s2 = nodeFactory.createIRI("http://example.com/s2");
            g.add(s2, p, s);
            assertTrue(g.contains(s2, p, s));

            // This should be mapped to the same BlankNode
            // (even if it has a different identifier), e.g.
            // we should be able to do:

            final Triple t2 = g.stream(s2, p, null).findAny().get();

            final BlankNode bnode = (BlankNode) t2.getObject();
            // And that (possibly adapted) BlankNode object should
            // match the subject of t1 statement
            assertEquals(bnode, t1.getSubject());
            // And can be used as a key:
            final Triple t3 = g.stream(bnode, p, null).findAny().get();
            assertEquals(t1, t3);
        }
    }
```

### Parameter provider — 同文件内的 `data`

```java
@SuppressWarnings("rawtypes")
    public static Collection<Object[]> data() {
        final List<Class> factories = Arrays.asList(SimpleRDF.class, JenaRDF.class, RDF4J.class, JsonLdRDF.class);
        final Collection<Object[]> allToAll = new ArrayList<>();
        for (final Class from : factories) {
            for (final Class to : factories) {
                // NOTE: we deliberately include self-to-self here
                // to test two instances of the same implementation
                allToAll.add(new Object[] { from, to });
            }
        }
        return allToAll;
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-002  ·  MethodSource

**项目** `POI`  **文件** `poi/poi-ooxml/src/test/java/org/apache/poi/xssf/usermodel/TestFormulaEvaluatorOnXSSF.java`  **测试** `processFunctionRow`

### Test method

```java
@ParameterizedTest
    @MethodSource("data")
    void processFunctionRow(String targetFunctionName, int formulasRowIdx, int expectedValuesRowIdx) {
        //DOLLAR function returns a string that is locale specific
        assumeFalse(targetFunctionName.equalsIgnoreCase("DOLLAR"));

        Row formulasRow = sheet.getRow(formulasRowIdx);
        Row expectedValuesRow = sheet.getRow(expectedValuesRowIdx);

        short endcolnum = formulasRow.getLastCellNum();

        // iterate across the row for all the evaluation cases
        for (short colnum=SS.COLUMN_INDEX_FIRST_TEST_VALUE; colnum < endcolnum; colnum++) {
            Cell c = formulasRow.getCell(colnum);
            assumeTrue(c != null);
            assumeTrue(c.getCellType() == CellType.FORMULA);
            ignoredFormulaTestCase(c.getCellFormula());

            CellValue actValue = evaluator.evaluate(c);
            Cell expValue = (expectedValuesRow == null) ? null : expectedValuesRow.getCell(colnum);

            String msg = String.format(Locale.ROOT, "Function '%s': Formula: %s @ %d:%d"
                , targetFunctionName, c.getCellFormula(), formulasRow.getRowNum(), colnum);

            assertNotNull(expValue, msg + " - Bad setup data expected value is null");
            assertNotNull(actValue, msg + " - actual value was null");

            final CellType expectedCellType = expValue.getCellType();
            switch (expectedCellType) {
                case BLANK:
                    assertEquals(CellType.BLANK, actValue.getCellType(), msg);
                    break;
                case BOOLEAN:
                    assertEquals(CellType.BOOLEAN, actValue.getCellType(), msg);
                    assertEquals(expValue.getBooleanCellValue(), actValue.getBooleanValue(), msg);
                    break;
                case ERROR:
                    assertEquals(CellType.ERROR, actValue.getCellType(), msg);
//                if(false) { // TODO: fix ~45 functions which are currently returning incorrect error values
//                    assertEquals(msg, expValue.getErrorCellValue(), actValue.getErrorValue());
//                }
                    break;
                case FORMULA: // will never be used, since we will call method after formula evaluation
                    fail("Cannot expect formula as result of formula evaluation: " + msg);
                case NUMERIC:
                    assertEquals(CellType.NUMERIC, actValue.getCellType(), msg);
                    final double tolerance = targetFunctionName.equalsIgnoreCase("RATE")
                            ? 0.000001 : BaseTestNumeric.DIFF_TOLERANCE_FACTOR;
                    BaseTestNumeric.assertDouble(msg, expValue.getNumericCellValue(), actValue.getNumberValue(), BaseTestNumeric.POS_ZERO, tolerance);
                    break;
                case STRING:
                    assertEquals(CellType.STRING, actValue.getCellType(), msg);
                    assertEquals(expValue.getRichStringCellValue().getString(), actValue.getStringValue(), msg);
                    break;
                default:
                    fail("Unexpected cell type: " + expectedCellType);
            }
        }
    }
```

### Parameter provider — 同文件内的 `data`

```java
    public static Stream<Arguments> data() throws Exception {
        // Function "Text" uses custom-formats which are locale specific
        // can't set the locale on a per-testrun execution, as some settings have been
        // already set, when we would try to change the locale by then
        userLocale = LocaleUtil.getUserLocale();
        LocaleUtil.setUserLocale(Locale.ROOT);

        workbook = new XSSFWorkbook( OPCPackage.open(HSSFTestDataSamples.getSampleFile(SS.FILENAME), PackageAccess.READ) );
        sheet = workbook.getSheetAt( 0 );
        evaluator = new XSSFFormulaEvaluator(workbook);

        List<Arguments> data = new ArrayList<>();

        processFunctionGroup(data, SS.START_OPERATORS_ROW_INDEX, null);
        processFunctionGroup(data, SS.START_FUNCTIONS_ROW_INDEX, null);
        // example for debugging individual functions/operators:
        // processFunctionGroup(data, SS.START_OPERATORS_ROW_INDEX, "ConcatEval");
        // processFunctionGroup(data, SS.START_FUNCTIONS_ROW_INDEX, "Text");

        return data.stream();
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`ignoredFormulaTestCase`**

```java
    private static void ignoredFormulaTestCase(String cellFormula) {
        // full row ranges are not parsed properly yet.
        // These cases currently work in svn trunk because of another bug which causes the
        // formula to get rendered as COLUMN($A$1:$IV$2) or ROW($A$2:$IV$3)
        assumeFalse("COLUMN(1:2)".equals(cellFormula));
        assumeFalse("ROW(2:3)".equals(cellFormula));

        // currently throws NPE because unknown function "currentcell" causes name lookup
        // Name lookup requires some equivalent object of the Workbook within xSSFWorkbook.
        assumeFalse("ISREF(currentcell())".equals(cellFormula));
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-003  ·  EnumSource

**项目** `jena`  **文件** `jena/jena-ontapi/src/test/java/org/apache/jena/ontapi/OntClassIndividualsTest.java`  **测试** `testListIndividuals7a`

### Test method

```java
@ParameterizedTest
    @EnumSource(names = {
            "OWL2_MEM",
            "OWL1_MEM",
            "RDFS_MEM",
    })
    public void testListIndividuals7a(TestSpec spec) {
        //  A   B
        //  .\ /.
        //  . C .
        //  . | .
        //  . D .
        //  ./  .
        //  A   .   E
        //   \  .  |
        //    \ . /
        //      B

        OntModel m = createClassesABCDAEB(OntModelFactory.createModel(spec.inst));
        OntClass A = m.getResource(NS + "A").as(OntClass.class);
        OntClass B = m.getResource(NS + "B").as(OntClass.class);
        OntClass C = m.getResource(NS + "C").as(OntClass.class);
        m.getResource(NS + "D").as(OntClass.class);
        OntClass E = m.getResource(NS + "E").as(OntClass.class);

        A.createIndividual(NS + "iA");
        B.createIndividual(NS + "iB");
        OntIndividual CE = C.createIndividual(NS + "iCE");
        CE.attachClass(E);
        OntIndividual DBA = B.createIndividual(NS + "iDBA");
        DBA.attachClass(B);
        DBA.attachClass(A);

        Set<String> directA = individuals(m, "A", true);
        Set<String> indirectA = individuals(m, "A", false);

        Set<String> directB = individuals(m, "B", true);
        Set<String> indirectB = individuals(m, "B", false);

        Set<String> directC = individuals(m, "C", true);
        Set<String> indirectC = individuals(m, "C", false);

        Set<String> directD = individuals(m, "D", true);
        Set<String> indirectD = individuals(m, "D", false);

        Set<String> directE = individuals(m, "E", true);
        Set<String> indirectE = individuals(m, "E", false);

        Assertions.assertEquals(Set.of("iA"), directA);
        Assertions.assertEquals(Set.of("iB", "iDBA"), directB);
        Assertions.assertEquals(Set.of("iCE"), directC);
        Assertions.assertEquals(Set.of(), directD);
        Assertions.assertEquals(Set.of("iCE"), directE);
        Assertions.assertEquals(Set.of("iA", "iDBA"), indirectA);
        Assertions.assertEquals(Set.of("iB", "iDBA"), indirectB);
        Assertions.assertEquals(Set.of("iCE"), indirectC);
        Assertions.assertEquals(Set.of(), indirectD);
        Assertions.assertEquals(Set.of("iCE"), indirectE);
    }
```

### Enum declaration — `TestSpec` (jena/jena-ontapi/src/test/java/org/apache/jena/ontapi/TestSpec.java)

```java
public enum TestSpec {
    OWL2_MEM(OntSpecification.OWL2_FULL_MEM),
    OWL2_MEM_RDFS_INF(OntSpecification.OWL2_FULL_MEM_RDFS_INF),
    OWL2_MEM_TRANS_INF(OntSpecification.OWL2_FULL_MEM_TRANS_INF),
    OWL2_MEM_RULES_INF(OntSpecification.OWL2_FULL_MEM_RULES_INF),
    OWL2_MEM_MINI_RULES_INF(OntSpecification.OWL2_FULL_MEM_MINI_RULES_INF),
    OWL2_MEM_MICRO_RULES_INF(OntSpecification.OWL2_FULL_MEM_MICRO_RULES_INF),

    OWL2_DL_MEM_RDFS_BUILTIN_INF(OntSpecification.OWL2_DL_MEM_BUILTIN_RDFS_INF),
    OWL2_DL_MEM(OntSpecification.OWL2_DL_MEM),
    OWL2_DL_MEM_RDFS_INF(OntSpecification.OWL2_DL_MEM_RDFS_INF),
    OWL2_DL_MEM_TRANS_INF(OntSpecification.OWL2_DL_MEM_TRANS_INF),
    OWL2_DL_MEM_RULES_INF(OntSpecification.OWL2_DL_MEM_RULES_INF),

    OWL2_EL_MEM(OntSpecification.OWL2_EL_MEM),
    OWL2_EL_MEM_RDFS_INF(OntSpecification.OWL2_EL_MEM_RDFS_INF),
    OWL2_EL_MEM_TRANS_INF(OntSpecification.OWL2_EL_MEM_TRANS_INF),
    OWL2_EL_MEM_RULES_INF(OntSpecification.OWL2_EL_MEM_RULES_INF),

    OWL2_QL_MEM(OntSpecification.OWL2_QL_MEM),
    OWL2_QL_MEM_RDFS_INF(OntSpecification.OWL2_QL_MEM_RDFS_INF),
    OWL2_QL_MEM_TRANS_INF(OntSpecification.OWL2_QL_MEM_TRANS_INF),
    OWL2_QL_MEM_RULES_INF(OntSpecification.OWL2_QL_MEM_RULES_INF),

    OWL2_RL_MEM(OntSpecification.OWL2_RL_MEM),
    OWL2_RL_MEM_RDFS_INF(OntSpecification.OWL2_RL_MEM_RDFS_INF),
    OWL2_RL_MEM_TRANS_INF(OntSpecification.OWL2_RL_MEM_TRANS_INF),
    OWL2_RL_MEM_RULES_INF(OntSpecification.OWL2_RL_MEM_RULES_INF),

    OWL1_MEM(OntSpecification.OWL1_FULL_MEM),
    OWL1_MEM_RDFS_INF(OntSpecification.OWL1_FULL_MEM_RDFS_INF),
    OWL1_MEM_TRANS_INF(OntSpecification.OWL1_FULL_MEM_TRANS_INF),
    OWL1_MEM_RULES_INF(OntSpecification.OWL1_FULL_MEM_RULES_INF),
    OWL1_MEM_MINI_RULES_INF(OntSpecification.OWL1_FULL_MEM_MINI_RULES_INF),
    OWL1_MEM_MICRO_RULES_INF(OntSpecification.OWL1_FULL_MEM_MICRO_RULES_INF),

    OWL1_DL_MEM(OntSpecification.OWL1_DL_MEM),
    OWL1_DL_MEM_RDFS_INF(OntSpecification.OWL1_DL_MEM_RDFS_INF),
    OWL1_DL_MEM_TRANS_INF(OntSpecification.OWL1_DL_MEM_TRANS_INF),
    OWL1_DL_MEM_RULES_INF(OntSpecification.OWL1_DL_MEM_RULES_INF),

    OWL1_LITE_MEM(OntSpecification.OWL1_LITE_MEM),
    OWL1_LITE_MEM_RDFS_INF(OntSpecification.OWL1_LITE_MEM_RDFS_INF),
    OWL1_LITE_MEM_TRANS_INF(OntSpecification.OWL1_LITE_MEM_TRANS_INF),
    OWL1_LITE_MEM_RULES_INF(OntSpecification.OWL1_LITE_MEM_RULES_INF),

    RDFS_MEM(OntSpecification.RDFS_MEM),
    RDFS_MEM_RDFS_INF(OntSpecification.RDFS_MEM_RDFS_INF),
    RDFS_MEM_TRANS_INF(OntSpecification.RDFS_MEM_TRANS_INF),
    ;
    public final OntSpecification inst;

    TestSpec(OntSpecification inst) {
        this.inst = inst;
    }

    boolean isOWL1() {
        return name().startsWith("OWL1");
    }

    boolean isOWL1Lite() {
        return name().startsWith("OWL1_LITE");
    }

    boolean isOWL2() {
        return name().startsWith("OWL2");
    }

    boolean isOWL2EL() {
        return name().startsWith("OWL2_EL");
    }

    boolean isOWL2QL() {
        return name().startsWith("OWL2_QL");
    }

    boolean isOWL2RL() {
        return name().startsWith("OWL2_RL");
    }

    boolean isRules() {
        return name().endsWith("_RULES_INF");
    }

    boolean isRDFS() {
        return name().endsWith("_RDFS_INF");
    }
}
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`individuals`**

```java
    private static Set<String> individuals(OntModel m, String name, boolean direct) {
        return m.getOntClass(NS + name).individuals(direct).map(Resource::getLocalName).collect(Collectors.toSet());
    }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-004  ·  EnumSource

**项目** `Zeppelin`  **文件** `zeppelin/elasticsearch/src/test/java/org/apache/zeppelin/elasticsearch/client/ElasticsearchClientTypeTest.java`  **测试** `shouldNotBeHttpWhenTypeIsTransportOrUnknown`

### Test method

```java
@ParameterizedTest
  @EnumSource(value = ElasticsearchClientType.class, names = {"TRANSPORT", "UNKNOWN"})
  @DisplayName("should NOT be marked as HTTP-based when client type is TRANSPORT or UNKNOWN")
  void shouldNotBeHttpWhenTypeIsTransportOrUnknown(ElasticsearchClientType type) {
    assertFalse(type.isHttp(), type + " should NOT be marked as HTTP-based");
  }
```

### Enum declaration — `ElasticsearchClientType` (zeppelin/elasticsearch/src/main/java/org/apache/zeppelin/elasticsearch/client/ElasticsearchClientType.java)

```java
public enum ElasticsearchClientType {
  HTTP(true), HTTPS(true), TRANSPORT(false), UNKNOWN(false);

  private final boolean isHttp;

  ElasticsearchClientType(boolean isHttp) {
    this.isHttp = isHttp;
  }

  public boolean isHttp() {
    return isHttp;
  }
}
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-005  ·  ValueSource

**项目** `Maven`  **文件** `maven/impl/maven-core/src/test/java/org/apache/maven/plugin/PluginParameterExpressionEvaluatorTest.java`  **测试** `testValueExtractionOfMissingPrefixedSuffixedProperty`

### Test method

```java
@ParameterizedTest
    @ValueSource(
            strings = {
                "prefix-${PPEET_nonexisting_ps_property}",
                "${PPEET_nonexisting_ps_property}-suffix",
                "prefix-${PPEET_nonexisting_ps_property}-suffix",
            })
    void testValueExtractionOfMissingPrefixedSuffixedProperty(String missingPropertyExpression) throws Exception {
        Properties executionProperties = new Properties();

        ExpressionEvaluator ee = createExpressionEvaluator(null, null, executionProperties);

        Object value = ee.evaluate(missingPropertyExpression);

        assertEquals(missingPropertyExpression, value);
    }
```

### Test-side helpers called by this test (2)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`createExpressionEvaluator`**

```java
    private ExpressionEvaluator createExpressionEvaluator(
            MavenProject project, PluginDescriptor pluginDescriptor, Properties executionProperties) throws Exception {
        ArtifactRepository repo = getLocalRepository();

        MutablePlexusContainer container = (MutablePlexusContainer) getContainer();
        MavenSession session = createSession(container, repo, executionProperties);
        session.setCurrentProject(project);
        session.getRequest().setRootDirectory(rootDirectory);

        MojoDescriptor mojo = new MojoDescriptor();
        mojo.setPluginDescriptor(pluginDescriptor);
        mojo.setGoal("goal");

        MojoExecution mojoExecution = new MojoExecution(mojo);

        return new PluginParameterExpressionEvaluator(session, mojoExecution);
    }
```

**`createSession`**

```java
@SuppressWarnings("deprecation")
    private static MavenSession createSession(PlexusContainer container, ArtifactRepository repo, Properties properties)
            throws CycleDetectedException, DuplicateProjectException {
        MavenExecutionRequest request = new DefaultMavenExecutionRequest()
                .setSystemProperties(properties)
                .setGoals(Collections.emptyList())
                .setBaseDirectory(new File(""))
                .setLocalRepository(repo);

        return new MavenSession(container, request, new DefaultMavenExecutionResult(), Collections.emptyList());
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-006  ·  ValueSource

**项目** `commons-rng`  **文件** `commons-rng/commons-rng-sampling/src/test/java/org/apache/commons/rng/sampling/ArraySamplerTest.java`  **测试** `testShuffleIsRandom`

### Test method

```java
@ParameterizedTest
    @ValueSource(ints = {13, 16})
    void testShuffleIsRandom(int length) {
        final int[] array = PermutationSampler.natural(length);
        final UniformRandomProvider rng = RandomAssert.createRNG();
        final long[][] counts = new long[length][length];
        for (int j = 1; j <= 1000; j++) {
            ArraySampler.shuffle(rng, array);
            for (int i = 0; i < length; i++) {
                counts[i][array[i]]++;
            }
        }
        final double p = new ChiSquareTest().chiSquareTest(counts);
        Assertions.assertFalse(p < 1e-3, () -> "p-value too small: " + p);
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`natural`**

```java
    private static int[] natural(int from, int to, int length) {
        final int[] array = new int[length];
        for (int i = 0; i < from; i++) {
            array[i] = i - from;
        }
        for (int i = from; i < to; i++) {
            array[i] = i - from;
        }
        for (int i = to; i < length; i++) {
            array[i] = i - from;
        }
        return array;
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-007  ·  MethodSource

**项目** `Commons-Compress`  **文件** `commons-compress/src/test/java/org/apache/commons/compress/changes/ChangeSetSafeTypesTest.java`  **测试** `testDeleteFileCpio`

### Test method

```java
@ParameterizedTest
    @MethodSource("org.apache.commons.compress.changes.TestFixtures#getOutputArchiveNames")
    void testDeleteFileCpio(final String archiverName) throws Exception {
        final Path input = createArchive(archiverName);
        final File result = createTempFile("test", "." + archiverName);
        try (InputStream inputStream = Files.newInputStream(input);
                ArchiveInputStream<E> ais = createArchiveInputStream(archiverName, inputStream);
                OutputStream outputStream = Files.newOutputStream(result.toPath());
                ArchiveOutputStream<E> out = createArchiveOutputStream(archiverName, outputStream)) {
            final ChangeSet<E> changeSet = createChangeSet();
            changeSet.delete("bla/test5.xml");
            archiveListDelete("bla/test5.xml");
            new ChangeSetPerformer<>(changeSet).perform(ais, out);
        }
        checkArchiveContent(result, archiveList);
    }
```

### Parameter provider — `TestFixtures#getOutputArchiveNames`（commons-compress/src/test/java/org/apache/commons/compress/changes/TestFixtures.java）

```java
    static Set<String> getOutputArchiveNames() {
        final Set<String> outputStreamArchiveNames = ArchiveStreamFactory.DEFAULT.getOutputStreamArchiveNames();
        outputStreamArchiveNames.remove(ArchiveStreamFactory.AR); // TODO BUG?
        outputStreamArchiveNames.remove(ArchiveStreamFactory.SEVEN_Z); // TODO Does not support streaming.
        return outputStreamArchiveNames;
    }
```

### Test-side helpers called by this test (2)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`createChangeSet`**

```java
    private <A extends ArchiveEntry> ChangeSet<A> createChangeSet() {
        return new ChangeSet<>();
    }
```

**`archiveListDelete`**

```java
    private void archiveListDelete(final String prefix) {
        archiveList.removeIf(entry -> entry.equals(prefix));
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-008  ·  EnumSource

**项目** `Druid`  **文件** `druid/processing/src/test/java/org/apache/druid/query/metadata/SegmentMetadataQueryQueryToolChestTest.java`  **测试** `testInvalidMergeAggregatorsWithNullOrEmptyDatasource`

### Test method

```java
@EnumSource(AggregatorMergeStrategy.class)
  @ParameterizedTest(name = "{index}: with AggregatorMergeStrategy {0}")
  public void testInvalidMergeAggregatorsWithNullOrEmptyDatasource(AggregatorMergeStrategy aggregatorMergeStrategy)
  {
    final SegmentAnalysis analysis1 = new SegmentAnalysis.Builder(TEST_SEGMENT_ID1).build();
    final SegmentAnalysis analysis2 = new SegmentAnalysis.Builder(TEST_SEGMENT_ID2).build();

    MatcherAssert.assertThat(
        Assert.assertThrows(
            DruidException.class,
            () -> SegmentMetadataQueryQueryToolChest.mergeAnalyses(
                null,
                analysis1,
                analysis2,
                aggregatorMergeStrategy
            )
        ),
        DruidExceptionMatcher.defensive().expectMessageIs("SegementMetadata queries require at least one datasource.")
    );

    MatcherAssert.assertThat(
        Assert.assertThrows(
            DruidException.class,
            () -> SegmentMetadataQueryQueryToolChest.mergeAnalyses(
                ImmutableSet.of(),
                analysis1,
                analysis2,
                aggregatorMergeStrategy
            )
        ),
        DruidExceptionMatcher
            .defensive()
            .expectMessageIs(
                "SegementMetadata queries require at least one datasource.")
    );
  }
```

### Enum declaration — `AggregatorMergeStrategy` (druid/processing/src/main/java/org/apache/druid/query/metadata/metadata/AggregatorMergeStrategy.java)

```java
public enum AggregatorMergeStrategy
{
  STRICT,
  LENIENT,
  EARLIEST,
  LATEST;

  @JsonValue
  @Override
  public String toString()
  {
    return StringUtils.toLowerCase(this.name());
  }

  @JsonCreator
  public static AggregatorMergeStrategy fromString(String name)
  {
    return valueOf(StringUtils.toUpperCase(name));
  }
}
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-009  ·  MethodSource

**项目** `Log4j`  **文件** `logging-log4j2/log4j-api-test/src/test/java/org/apache/logging/log4j/util/PropertySourceTokenizerTest.java`  **测试** `testTokenize`

### Test method

```java
@ParameterizedTest
    @MethodSource("data")
    void testTokenize(final String value, final List<CharSequence> expectedTokens) {
        final List<CharSequence> tokens = PropertySource.Util.tokenize(value);
        assertEquals(expectedTokens, tokens);
    }
```

### Parameter provider — 同文件内的 `data`

```java
    public static Object[][] data() {
        return new Object[][] {
            {"log4j.simple", Collections.singletonList("simple")},
            {"log4j_simple", Collections.singletonList("simple")},
            {"log4j-simple", Collections.singletonList("simple")},
            {"log4j/simple", Collections.singletonList("simple")},
            {"log4j2.simple", Collections.singletonList("simple")},
            {"Log4jSimple", Collections.singletonList("simple")},
            {"LOG4J_simple", Collections.singletonList("simple")},
            {"org.apache.logging.log4j.simple", Collections.singletonList("simple")},
            {"log4j.simpleProperty", Arrays.asList("simple", "property")},
            {"log4j.simple_property", Arrays.asList("simple", "property")},
            {"LOG4J_simple_property", Arrays.asList("simple", "property")},
            {"LOG4J_SIMPLE_PROPERTY", Arrays.asList("simple", "property")},
            {"log4j2-dashed-propertyName", Arrays.asList("dashed", "property", "name")},
            {"Log4jProperty_with.all-the/separators", Arrays.asList("property", "with", "all", "the", "separators")},
            {"org.apache.logging.log4j.config.property", Arrays.asList("config", "property")},
            // LOG4J2-3413
            {"level", Collections.emptyList()},
            {"user.home", Collections.emptyList()},
            {"CATALINA_BASE", Collections.emptyList()}
        };
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-010  ·  EnumSource

**项目** `Druid`  **文件** `druid/processing/src/test/java/org/apache/druid/query/metadata/SegmentMetadataQueryQueryToolChestTest.java`  **测试** `testProjectionsWithNull`

### Test method

```java
@EnumSource(AggregatorMergeStrategy.class)
  @ParameterizedTest(name = "{index}: with AggregatorMergeStrategy {0}")
  public void testProjectionsWithNull(AggregatorMergeStrategy aggregatorMergeStrategy)
  {
    final SegmentAnalysis analysis1 = new SegmentAnalysis.Builder(TEST_SEGMENT_ID1)
        .projection("channel_sum", new AggregateProjectionMetadata(PROJECTION_CHANNEL_ADDED_HOURLY, 100))
        .build();
    final SegmentAnalysis analysis1NullProjection = new SegmentAnalysis.Builder(TEST_SEGMENT_ID1).build();
    final SegmentAnalysis analysis2 = new SegmentAnalysis.Builder(TEST_SEGMENT_ID2)
        .projection("channel_sum", new AggregateProjectionMetadata(PROJECTION_CHANNEL_ADDED_HOURLY, 200))
        .build();
    final SegmentAnalysis analysis2NullProjection = new SegmentAnalysis.Builder(TEST_SEGMENT_ID2).build();

    Assert.assertNull(mergeWithStrategy(analysis1NullProjection, analysis2, aggregatorMergeStrategy).getProjections());
    Assert.assertNull(mergeWithStrategy(analysis1, analysis2NullProjection, aggregatorMergeStrategy).getProjections());
    Assert.assertNull(
        mergeWithStrategy(analysis1NullProjection, analysis2NullProjection, aggregatorMergeStrategy).getProjections()
    );
  }
```

### Enum declaration — `AggregatorMergeStrategy` (druid/processing/src/main/java/org/apache/druid/query/metadata/metadata/AggregatorMergeStrategy.java)

```java
public enum AggregatorMergeStrategy
{
  STRICT,
  LENIENT,
  EARLIEST,
  LATEST;

  @JsonValue
  @Override
  public String toString()
  {
    return StringUtils.toLowerCase(this.name());
  }

  @JsonCreator
  public static AggregatorMergeStrategy fromString(String name)
  {
    return valueOf(StringUtils.toUpperCase(name));
  }
}
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`mergeWithStrategy`**

```java
  private static SegmentAnalysis mergeWithStrategy(
      SegmentAnalysis analysis1,
      SegmentAnalysis analysis2,
      AggregatorMergeStrategy strategy
  )
  {
    return SegmentMetadataQueryQueryToolChest.finalizeAnalysis(
        SegmentMetadataQueryQueryToolChest.mergeAnalyses(
            TEST_DATASOURCE.getTableNames(),
            analysis1,
            analysis2,
            strategy
        ));
  }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-011  ·  CsvSource

**项目** `Commons-Lang`  **文件** `commons-lang/src/test/java/org/apache/commons/lang3/math/FractionTest.java`  **测试** `testHashCodeNotEquals`

### Test method

```java
@ParameterizedTest
    // @formatter:off
    @CsvSource({
        "0,          37,         -464320789,  46",
        "0,          37,         -464320788,  9",
        "0,          37,         1857283155,  38",
        "0,          25185704,   1161454280,  1050304",
        "0,          38817068,   1509581512,  18875972",
        "0,          38817068,   -2146369536, 2145078572",
        "1400217380, 128,        2092630052,  150535040",
        "1400217380, 128,        -580400986,  268435638",
        "1400217380, 2147483592, -2147483648, 268435452",
        "1756395909, 4194598,    1174949894,  42860673"
    })
    // @formatter:on
    void testHashCodeNotEquals(final int f1n, final int f1d, final int f2n, final int f2d) {
        assertNotEquals(Fraction.getFraction(f1n, f1d), Fraction.getFraction(f2n, f2d));
        assertNotEquals(Fraction.getFraction(f1n, f1d).hashCode(), Fraction.getFraction(f2n, f2d).hashCode());
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-012  ·  MethodSource

**项目** `Hadoop`  **文件** `hadoop/hadoop-hdfs-project/hadoop-hdfs/src/test/java/org/apache/hadoop/hdfs/server/datanode/checker/TestDatasetVolumeChecker.java`  **测试** `testInvalidConfigurationValues`

### Test method

```java
@ParameterizedTest(name="{0}")
  @MethodSource("data")
  public void testInvalidConfigurationValues(VolumeCheckResult pExpectedVolumeHealth)
      throws Exception {
    initTestDatasetVolumeChecker(pExpectedVolumeHealth);
    HdfsConfiguration conf = new HdfsConfiguration();
    conf.setInt(DFS_DATANODE_DISK_CHECK_TIMEOUT_KEY, 0);
    intercept(HadoopIllegalArgumentException.class,
        "Invalid value configured for dfs.datanode.disk.check.timeout"
            + " - 0 (should be > 0)",
        () -> new DatasetVolumeChecker(conf, new FakeTimer()));
    conf.unset(DFS_DATANODE_DISK_CHECK_TIMEOUT_KEY);

    conf.setInt(DFS_DATANODE_DISK_CHECK_MIN_GAP_KEY, -1);
    intercept(HadoopIllegalArgumentException.class,
        "Invalid value configured for dfs.datanode.disk.check.min.gap"
            + " - -1 (should be >= 0)",
        () -> new DatasetVolumeChecker(conf, new FakeTimer()));
    conf.unset(DFS_DATANODE_DISK_CHECK_MIN_GAP_KEY);

    conf.setInt(DFS_DATANODE_DISK_CHECK_TIMEOUT_KEY, -1);
    intercept(HadoopIllegalArgumentException.class,
        "Invalid value configured for dfs.datanode.disk.check.timeout"
            + " - -1 (should be > 0)",
        () -> new DatasetVolumeChecker(conf, new FakeTimer()));
    conf.unset(DFS_DATANODE_DISK_CHECK_TIMEOUT_KEY);

    conf.setInt(DFS_DATANODE_FAILED_VOLUMES_TOLERATED_KEY, -2);
    intercept(HadoopIllegalArgumentException.class,
        "Invalid value configured for dfs.datanode.failed.volumes.tolerated"
            + " - -2 should be greater than or equal to -1",
        () -> new DatasetVolumeChecker(conf, new FakeTimer()));
  }
```

### Parameter provider — 同文件内的 `data`

```java
  public static Collection<Object[]> data() {
    List<Object[]> values = new ArrayList<>();
    for (VolumeCheckResult result : VolumeCheckResult.values()) {
      values.add(new Object[] {result});
    }
    values.add(new Object[] {null});
    return values;
  }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`initTestDatasetVolumeChecker`**

```java
  public void initTestDatasetVolumeChecker(VolumeCheckResult pExpectedVolumeHealth) {
    this.expectedVolumeHealth = pExpectedVolumeHealth;
  }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-013  ·  ValueSource

**项目** `Commons-BCEL`  **文件** `commons-bcel/src/test/java/org/apache/bcel/generic/EmptyVisitorTest.java`  **测试** `test`

### Test method

```java
@ParameterizedTest
    @ValueSource(strings = {
    // @formatter:off
        "java.math.BigInteger",                          // contains instructions [AALOAD, AASTORE, ACONST_NULL, ALOAD, ANEWARRAY, ARETURN, ARRAYLENGTH,
                                                         //   ASTORE, ATHROW, BALOAD, BASTORE, BIPUSH, CALOAD, CHECKCAST, D2I, DADD, DALOAD, DASTORE, DCONST
                                                         //   DDIV, DMUL, DRETURN, DSUB, DUP, DUP2, DUP_X2, FCONST, FRETURN, GETFIELD, GETSTATIC, GOTO, I2B,
                                                         //   I2D, I2L, IADD, IALOAD, IAND, IASTORE, ICONST, IDIV, IFEQ, IFGE, IFGT, IFLE, IFLT, IFNE,
                                                         //   IFNONNULL, IFNULL, IF_ACMPNE, IF_ICMPEQ, IF_ICMPGE, IF_ICMPGT, IF_ICMPLE, IF_ICMPLT, IF_ICMPNE,
                                                         //   IINC, ILOAD, IMUL, INEG, INSTANCEOF, INVOKESPECIAL, INVOKESTATIC, INVOKEVIRTUAL, IOR, IREM,
                                                         //   IRETURN, ISHL, ISHR, ISTORE, ISUB, IUSHR, IXOR, L2D, L2F, L2I, LADD, LALOAD, LAND, LASTORE, LCMP,
                                                         //   LCONST, LDC, LDC2_W, LDC_W, LDIV, LLOAD, LMUL, LNEG, LOOKUPSWITCH, LOR, LREM, LRETURN, LSHL, LSHR,
                                                         //   LSTORE, LSUB, LUSHR, NEW, NEWARRAY, POP, PUTFIELD, PUTSTATIC, RETURN, SIPUSH]
        "java.math.BigDecimal",                          // contains instructions [CASTORE, D2L, DLOAD, FALOAD, FASTORE, FDIV, FMUL, I2S, IF_ACMPEQ, LXOR,
                                                         //   MONITORENTER, MONITOREXIT, TABLESWITCH]
        "java.awt.Color",                                // contains instructions [D2F, DCMPG, DCMPL, F2D, F2I, FADD, FCMPG, FCMPL, FLOAD, FSTORE, FSUB, I2F,
                                                         //   INVOKEDYNAMIC]
        "java.util.Map",                                 // contains instruction INVOKEINTERFACE
        "java.io.Bits",                                  // contains instruction I2C
        "java.io.BufferedInputStream",                   // contains instruction DUP_X1
        "java.io.StreamTokenizer",                       // contains instruction DNEG, DSTORE
        "java.lang.Float",                               // contains instruction F2L
        "java.lang.invoke.LambdaForm",                   // contains instruction MULTIANEWARRAY,
        "java.nio.Bits",                                 // contains instruction POP2,
        "java.nio.HeapShortBuffer",                      // contains instruction SALOAD, SASTORE
        "Java8Example2",                                 // contains instruction FREM
        "java.awt.GradientPaintContext",                 // contains instruction DREM
        "java.util.concurrent.atomic.DoubleAccumulator", // contains instruction DUP2_X1
        "java.util.Hashtable",                           // contains instruction FNEG
        "javax.swing.text.html.CSS",                     // contains instruction DUP2_X2
        "org.apache.bcel.generic.LargeJump",             // contains instruction GOTO_W
        "org.apache.commons.lang.SerializationUtils"     // contains instruction JSR
    // @formatter:on
    })
    void test(final String className) throws ClassNotFoundException {
        // "java.io.Bits" is not in Java 21.
        assumeFalse(SystemUtils.isJavaVersionAtLeast(JavaVersion.JAVA_21) && className.equals("java.io.Bits"));
        final JavaClass javaClass = SyntheticRepository.getInstance().loadClass(className);
        for (final Method method : javaClass.getMethods()) {
            final Code code = method.getCode();
            if (code != null) {
                final InstructionList instructionList = new InstructionList(code.getCode());
                for (final InstructionHandle instructionHandle : instructionList) {
                    instructionHandle.accept(new EmptyVisitor() {
                        @Override
                        public void visitBREAKPOINT(final BREAKPOINT obj) {
                            fail(RESERVED_OPCODE);
                        }

                        @Override
                        public void visitIMPDEP1(final IMPDEP1 obj) {
                            fail(RESERVED_OPCODE);
                        }

                        @Override
                        public void visitIMPDEP2(final IMPDEP2 obj) {
                            fail(RESERVED_OPCODE);
                        }
                    });
                }
            }
        }
    }
```

### Test-side helpers called by this test (3)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`visitBREAKPOINT`**

```java
@Override
                        public void visitBREAKPOINT(final BREAKPOINT obj) {
                            fail(RESERVED_OPCODE);
                        }
```

**`visitIMPDEP1`**

```java
@Override
                        public void visitIMPDEP1(final IMPDEP1 obj) {
                            fail(RESERVED_OPCODE);
                        }
```

**`visitIMPDEP2`**

```java
@Override
                        public void visitIMPDEP2(final IMPDEP2 obj) {
                            fail(RESERVED_OPCODE);
                        }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-014  ·  CsvSource

**项目** `Commons-RNG`  **文件** `commons-rng/commons-rng-client-api/src/test/java/org/apache/commons/rng/UniformRandomProviderTest.java`  **测试** `testNextDoubleUniform`

### Test method

```java
@ParameterizedTest
    @CsvSource({
        // Note: If the range limits are integers above 2^53 (9007199254740992) it is not possible
        // to represent all the values with a double. This has no effect on sampling into bins
        // but should be avoided when generating integers for use in production code.
        // No lower bound.
        "2673846826, 0, 11",
        "-23658268, 0, 19",
        "263478624, 0, 31",
        "1278332, 0, 32",
        "99734765, 0, 1234",
        "-63485384, 0, 578",
        "3876457638, 0, 10000",
        "-126784782, 0, 2983423",
        "2637846, 0, 9007199254740992",
        // Range
        "2634682, 567576, 567586",
        "-56757798989, -1000, -100",
        "-97324785, -54656, 12",
        "23423235, -526783468, 257",
        "-2634682, -688689797, -516827",
        "6786868132, -67, 67",
        "-263846723, -5678, 42",
        "7352352, 678687, 61523457",
    })
    void testNextDoubleUniform(long seed, double origin, double bound) {
        Assertions.assertEquals((long) origin, origin, "origin");
        Assertions.assertEquals((long) bound, bound, "bound");
        final UniformRandomProvider rng = createRNG(seed);
        // Note casting as long will round towards zero.
        // If the upper bound is negative then this can create a domain error so use floor.
        final LongSupplier nextMethod = origin == 0 ?
                () -> (long) rng.nextDouble(bound) :
                () -> (long) Math.floor(rng.nextDouble(origin, bound));
        checkNextInRange("nextDouble", (long) origin, (long) bound, nextMethod);
    }
```

### Test-side helpers called by this test (3)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`createRNG`**

```java
    private static UniformRandomProvider createRNG(long seed) {
        // The algorithm for SplittableRandom with the default increment passes:
        // - Test U01 BigCrush
        // - PractRand with at least 2^42 bytes (4 TiB) of output
        return new SplittableRandom(seed)::nextLong;
    }
```

**`nextDouble`**

```java
@Override
            public double nextDouble() {
                return Math.nextDown(1.0);
            }
```

**`checkNextInRange`**

```java
    private static void checkNextInRange(String method,
                                         long origin,
                                         long bound,
                                         LongSupplier nextMethod) {
        // Do not change
        // (statistical test assumes that 500 repeats are made with dof = 9).
        final int numTests = 500;
        final int numBins = 10; // dof = numBins - 1

        // Set up bins.
        final long[] binUpperBounds = new long[numBins];
        // Range may be above a positive long: step = (bound - origin) / bins
        final BigDecimal range = BigDecimal.valueOf(bound)
                .subtract(BigDecimal.valueOf(origin));
        final double step = range.divide(BigDecimal.TEN).doubleValue();
        for (int k = 1; k < numBins; k++) {
            binUpperBounds[k - 1] = origin + (long) (k * step);
        }
        // Final bound
        binUpperBounds[numBins - 1] = bound;

        // Create expected frequencies
        final double[] expected = new double[numBins];
        long previousUpperBound = origin;
        final double scale = SAMPLE_SIZE_BD.divide(range, MathContext.DECIMAL128).doubleValue();
        double sum = 0;
        for (int k = 0; k < numBins; k++) {
            final long binWidth = binUpperBounds[k] - previousUpperBound;
            expected[k] = scale * binWidth;
            sum += expected[k];
            previousUpperBound = binUpperBounds[k];
        }
        Assertions.assertEquals(SAMPLE_SIZE, sum, SAMPLE_SIZE * RELATIVE_ERROR, "Invalid expected frequencies");

        final int[] observed = new int[numBins];
        // Chi-square critical value with 9 degrees of freedom
        // and 1% significance level.
        final double chi2CriticalValue = 21.665994333461924;

        // For storing chi2 larger than the critical value.
        final List<Double> failedStat = new ArrayList<>();
        try {
            final int lastDecileIndex = numBins - 1;
            for (int i = 0; i < numTests; i++) {
                Arrays.fill(observed, 0);
                SAMPLE: for (int j = 0; j < SAMPLE_SIZE; j++) {
                    final long value = nextMethod.getAsLong();
                    if (value < origin) {
                        Assertions.fail(String.format("Sample %d not within bound [%d, %d)",
                                                      value, origin, bound));
                    }

                    for (int k = 0; k < lastDecileIndex; k++) {
                        if (value < binUpperBounds[k]) {
                            ++observed[k];
                            continue SAMPLE;
                        }
                    }
                    if (value >= bound) {
                        Assertions.fail(String.format("Sample %d not within bound [%d, %d)",
                                                      value, origin, bound));
                    }
                    ++observed[lastDecileIndex];
                }

                // Compute chi-square.
                double chi2 = 0;
                for (int k = 0; k < numBins; k++) {
                    final double diff = observed[k] - expected[k];
                    chi2 += diff * diff / expected[k];
    // … 省略 29 行
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-015  ·  EnumSource

**项目** `Avro`  **文件** `avro/lang/java/avro/src/test/java/org/apache/avro/TestReadingWritingDataInEvolvedSchemas.java`  **测试** `floatWrittenWithUnionSchemaIsNotConvertedToLongSchema`

### Test method

```java
@ParameterizedTest
  @EnumSource(EncoderType.class)
  void floatWrittenWithUnionSchemaIsNotConvertedToLongSchema(EncoderType encoderType) throws Exception {
    Schema writer = UNION_INT_LONG_FLOAT_DOUBLE_RECORD;
    Record record = defaultRecordWithSchema(writer, FIELD_A, 42.0f);
    byte[] encoded = encodeGenericBlob(record, encoderType);
    AvroTypeException exception = Assertions.assertThrows(AvroTypeException.class,
        () -> decodeGenericBlob(LONG_RECORD, writer, encoded, encoderType));
    Assertions.assertEquals("Found float, expecting long", exception.getMessage());
  }
```

### Enum declaration — `EncoderType` (avro/lang/java/avro/src/test/java/org/apache/avro/TestReadingWritingDataInEvolvedSchemas.java)

```java
  enum EncoderType {
    BINARY, JSON
  }
```

### Test-side helpers called by this test (3)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`defaultRecordWithSchema`**

```java
  private <T> Record defaultRecordWithSchema(Schema schema, String key, T value) {
    Record data = new GenericData.Record(schema);
    data.put(key, value);
    return data;
  }
```

**`encodeGenericBlob`**

```java
  private byte[] encodeGenericBlob(GenericRecord data, EncoderType encoderType) throws IOException {
    DatumWriter<GenericRecord> writer = new GenericDatumWriter<>(data.getSchema());
    ByteArrayOutputStream outStream = new ByteArrayOutputStream();
    Encoder encoder = encoderType == EncoderType.BINARY ? EncoderFactory.get().binaryEncoder(outStream, null)
        : EncoderFactory.get().jsonEncoder(data.getSchema(), outStream);
    writer.write(data, encoder);
    encoder.flush();
    outStream.close();
    return outStream.toByteArray();
  }
```

**`decodeGenericBlob`**

```java
  private Record decodeGenericBlob(Schema expectedSchema, Schema schemaOfBlob, byte[] blob, EncoderType encoderType)
      throws IOException {
    if (blob == null) {
      return null;
    }
    GenericData data = new GenericData();
    data.setFastReaderEnabled(true);
    GenericDatumReader<Record> reader = new GenericDatumReader<>(null, null, data);
    reader.setExpected(expectedSchema);
    reader.setSchema(schemaOfBlob);
    Decoder decoder = encoderType == EncoderType.BINARY ? DecoderFactory.get().binaryDecoder(blob, null)
        : DecoderFactory.get().jsonDecoder(schemaOfBlob, new ByteArrayInputStream(blob));
    return reader.read(null, decoder);
  }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-018  ·  MethodSource

**项目** `uima-uimaj`  **文件** `uima-uimaj/uimaj-core/src/test/java/org/apache/uima/cas/serdes/CasSerializationDeserialization_XCAS_Test.java`  **测试** `roundTripDeserializeSerializeTest`

### Test method

```java
@ParameterizedTest
  @MethodSource("roundTripDesSerScenarios")
  void roundTripDeserializeSerializeTest(Runnable aScenario) throws Exception {
    assumeNotKnownToFail(aScenario, //
            ".*casWithSofaDataArray",
            "XCAS does not suport SofA data arrays during deserialiaztion");

    aScenario.run();
  }
```

### Parameter provider — 同文件内的 `roundTripDesSerScenarios`

```java
  private static List<DesSerTestScenario> roundTripDesSerScenarios() throws Exception {
    return SerDesCasIOTestUtils.roundTripDesSerScenariosComparingCasContents(desSerCycles,
            CAS_FILE_NAME);
  }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-021  ·  MethodSource

**项目** `commons-numbers`  **文件** `commons-numbers/commons-numbers-examples/examples-jmh/src/test/java/org/apache/commons/numbers/examples/jmh/arrays/KthSelectorTest.java`  **测试** `testSelectSPN`

### Test method

```java
@ParameterizedTest
    @MethodSource(value = {"testSelect"})
    void testSelectSPN(double[] values) {
        final double[] sorted = values.clone();
        Arrays.sort(sorted);
        final KthSelector selector = new KthSelector();
        final double[] kp1 = new double[1];
        for (int i = 0; i < sorted.length; i++) {
            final int k = i;
            double[] x = values.clone();
            Assertions.assertEquals(sorted[k], selector.selectSPN(x, k, null), () -> "k[" + k + "]");
            Arrays.sort(x);
            Assertions.assertArrayEquals(sorted, x, () -> "Data destroyed: k[" + k + "]");
            if (k + 1 < sorted.length) {
                x = values.clone();
                Assertions.assertEquals(sorted[k], selector.selectSPN(x, k, kp1), () -> "k[" + k + "] with k+1");
                Assertions.assertEquals(sorted[k + 1], kp1[0], () -> "k+1[" + (k + 1) + "]");
                Arrays.sort(x);
                Assertions.assertArrayEquals(sorted, x, () -> "Data destroyed: k[" + k + "] with k+1");
            }
        }
    }
```

### Parameter provider — 同文件内的 `testSelect`

```java
@ParameterizedTest
    @MethodSource
    void testSelect(double[] values) {
        final double[] sorted = values.clone();
        Arrays.sort(sorted);
        final KthSelector selector = new KthSelector();
        final double[] kp1 = new double[1];
        for (int i = 0; i < sorted.length; i++) {
            final int k = i;
            double[] x = values.clone();
            Assertions.assertEquals(sorted[k], selector.selectSP(x, k, null), () -> "k[" + k + "]");
            Arrays.sort(x);
            Assertions.assertArrayEquals(sorted, x, () -> "Data destroyed: k[" + k + "]");
            if (k + 1 < sorted.length) {
                x = values.clone();
                Assertions.assertEquals(sorted[k], selector.selectSP(x, k, kp1), () -> "k[" + k + "] with k+1");
                Assertions.assertEquals(sorted[k + 1], kp1[0], () -> "k+1[" + (k + 1) + "]");
                Arrays.sort(x);
                Assertions.assertArrayEquals(sorted, x, () -> "Data destroyed: k[" + k + "] with k+1");
            }
        }
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-024  ·  MethodSource

**项目** `SkyWalking`  **文件** `skywalking/oap-server/analyzer/meter-analyzer/src/test/java/org/apache/skywalking/oap/meter/analyzer/dsl/ScopeTest.java`  **测试** `test`

### Test method

```java
@ParameterizedTest(name = "{0}")
    @MethodSource("data")
    public void test(final String name,
                     final ImmutableMap<String, SampleFamily> input,
                     final String expression,
                     final boolean isThrow,
                     final Map<MeterEntity, Sample[]> want) {
        Expression e = DSL.parse(name, expression);
        Result r = null;
        try {
            r = e.run(input);
        } catch (Throwable t) {
            if (isThrow) {
                return;
            }
            log.error("Test failed", t);
            fail("Should not throw anything");
        }
        if (isThrow) {
            fail("Should throw something");
        }
        assertThat(r.isSuccess()).isEqualTo(true);
        Map<MeterEntity, Sample[]> meterSamplesR = r.getData().context.getMeterSamples();
        meterSamplesR.forEach((meterEntity, samples) -> {
            assertThat(samples).isEqualTo(want.get(meterEntity));
        });
    }
```

### Parameter provider — 同文件内的 `data`

```java
    public static Collection<Object[]> data() {
        // This method is called before `@BeforeAll`.
        MeterEntity.setNamingControl(
            new NamingControl(512, 512, 512, new EndpointNameGrouping()));

        return Arrays.asList(new Object[][] {
            {
                "sum_service",
                of("http_success_request", SampleFamilyBuilder.newBuilder(
                    Sample.builder().labels(of("idc", "t1")).value(50).name("http_success_request").build(),
                    Sample.builder()
                          .labels(of("idc", "t3", "region", "cn", "svc", "catalog"))
                          .value(51)
                          .name("http_success_request")
                          .build(),
                    Sample.builder()
                          .labels(of("idc", "t1", "region", "us", "svc", "product"))
                          .value(50)
                          .name("http_success_request")
                          .build(),
                    Sample.builder()
                          .labels(of("idc", "t1", "region", "us", "instance", "10.0.0.1"))
                          .value(100)
                          .name("http_success_request")
                          .build(),
                    Sample.builder()
                          .labels(of("idc", "t3", "region", "cn", "instance", "10.0.0.1"))
                          .value(3)
                          .name("http_success_request")
                          .build()
                ).build()),
                "http_success_request.sum(['idc']).service(['idc'], Layer.GENERAL)",
                false,
                new HashMap<MeterEntity, Sample[]>() {
                    {
                        put(
                            MeterEntity.newService("t1", Layer.GENERAL),
                            new Sample[] {Sample.builder().labels(of()).value(200).name("http_success_request").build()}
                        );
                        put(
                            MeterEntity.newService("t3", Layer.GENERAL),
                            new Sample[] {Sample.builder().labels(of()).value(54).name("http_success_request").build()}
                        );
                    }
                }
            },
            {
                "sum_service_labels",
                of("http_success_request", SampleFamilyBuilder.newBuilder(
                    Sample.builder().labels(of("idc", "t1")).value(50).name("http_success_request").build(),
                    Sample.builder()
                          .labels(of("idc", "t3", "region", "cn", "svc", "catalog"))
                          .value(51)
                          .name("http_success_request")
                          .build(),
                    Sample.builder()
                          .labels(of("idc", "t1", "region", "us", "svc", "product"))
                          .value(50)
                          .name("http_success_request")
                          .build(),
                    Sample.builder()
                          .labels(of("idc", "t1", "region", "us", "instance", "10.0.0.1"))
                          .value(100)
                          .name("http_success_request")
                          .build(),
                    Sample.builder()
                          .labels(of("idc", "t3", "region", "cn", "instance", "10.0.0.1"))
                          .value(3)
                          .name("http_success_request")
                          .build()
                ).build()),
                "http_success_request.sum(['region', 'idc']).service(['idc'], Layer.GENERAL)",
                false,
                new HashMap<MeterEntity, Sample[]>() {
                    {
                        put(
                            MeterEntity.newService("t1", Layer.GENERAL),
                            new Sample[] {
                                Sample.builder()
                                      .labels(of("region", ""))
                                      .value(50)
                                      .name("http_success_request").build(),
                                Sample.builder()
                                      .labels(of("region", "us"))
                                      .value(150)
                                      .name("http_success_request").build()
                            }
                        );
                        put(
                            MeterEntity.newService("t3", Layer.GENERAL),
                            new Sample[] {
                                Sample.builder()
                                      .labels(of("region", "cn"))
                                      .value(54)
                                      .name("http_success_request").build()
                            }
                        );
                    }
                }
            },
            {
                "sum_service_m",
                of("http_success_request", SampleFamilyBuilder.newBuilder(
                    Sample.builder().labels(of("idc", "t1")).value(50).name("http_success_request").build(),
                    Sample.builder()
                          .labels(of("idc", "t3", "region", "cn", "svc", "catalog"))
                          .value(51)
                          .name("http_success_request")
                          .build(),
                    Sample.builder()
                          .labels(of("idc", "t1", "region", "us", "svc", "product"))
                          .value(50)
                          .name("http_success_request")
                          .build(),
                    Sample.builder()
                          .labels(of("idc", "t1", "region", "us", "instance", "10.0.0.1"))
                          .value(100)
                          .name("http_success_request")
                          .build(),
                    Sample.builder()
                          .labels(of("idc", "t3", "region", "cn", "instance", "10.0.0.1"))
                          .value(3)
                          .name("http_success_request")
                          .build()
                ).build()),
                "http_success_request.sum(['idc', 'region']).service(['idc' , 'region'], Layer.GENERAL)",
                false,
                new HashMap<MeterEntity, Sample[]>() {
                    {
                        put(
                            MeterEntity.newService("t1.us", Layer.GENERAL),
                            new Sample[] {Sample.builder().labels(of()).value(150).name("http_success_request").build()}
                        );
                        put(
                            MeterEntity.newService("t3.cn", Layer.GENERAL),
                            new Sample[] {Sample.builder().labels(of()).value(54).name("http_success_request").build()}
                        );
                        put(
                            MeterEntity.newService("t1", Layer.GENERAL),
                            new Sample[] {Sample.builder().labels(of()).value(50).name("http_success_request").build()}
                        );
                    }
                }
            },
            {
                "sum_service_endpoint",
                of("http_success_request", SampleFamilyBuilder.newBuilder(
                    Sample.builder().labels(of("idc", "t1")).value(50).name("http_success_request").build(),
                    Sample.builder()
                          .labels(of("idc", "t3", "region", "cn", "svc", "catalog"))
                          .value(51)
                          .name("http_success_request")
                          .build(),
                    Sample.builder()
                          .labels(of("idc", "t1", "region", "us", "svc", "product"))
                          .value(50)
                          .name("http_success_request")
                          .build(),
                    Sample.builder()
                          .labels(of("idc", "t1", "region", "us", "instance", "10.0.0.1"))
    // … 省略 394 行
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-027  ·  MethodSource

**项目** `PLC4X`  **文件** `plc4x/plc4j/drivers/opcua/src/test/java/org/apache/plc4x/java/opcua/OpcuaPlcDriverTest.java`  **测试** `readVariables`

### Test method

```java
@ParameterizedTest
        @MethodSource("org.apache.plc4x.java.opcua.OpcuaPlcDriverTest#getConnectionSecurityPolicies")
        public void readVariables(SecurityPolicy policy, MessageSecurity messageSecurity) throws Exception {
            String connectionString = getConnectionString(policy, messageSecurity);
            PlcConnection opcuaConnection = new DefaultPlcDriverManager().getConnection(connectionString);
            Condition<PlcConnection> is_connected = new Condition<>(PlcConnection::isConnected, "is connected");
            assertThat(opcuaConnection).is(is_connected);

            PlcReadRequest.Builder builder = opcuaConnection.readRequestBuilder();
            tags.forEach((tagName, tagEntry) -> builder.addTagAddress(tagName, tagEntry.getKey()));
            PlcReadRequest request = builder.build();
            PlcReadResponse response = request.execute().get();

            SoftAssertions softly = new SoftAssertions();
            tags.keySet().forEach(tag -> {
                if (DOES_NOT_EXISTS_TAG_NAME.equals(tag)) {
                    softly.assertThat(response.getResponseCode(tag))
                        .describedAs("Tag %s should not exist and return NOT_FOUND status", tag)
                        .isEqualTo(PlcResponseCode.NOT_FOUND);
                } else {
                    softly.assertThat(response.getResponseCode(tag))
                        .describedAs("Tag %s should exist and return OK status", tag)
                        .isEqualTo(PlcResponseCode.OK);
                }
            });
            softly.assertAll();

            opcuaConnection.close();
            assertThat(opcuaConnection.isConnected()).isFalse();
        }
```

### Parameter provider — `OpcuaPlcDriverTest#getConnectionSecurityPolicies`（plc4x/plc4j/drivers/opcua/src/test/java/org/apache/plc4x/java/opcua/OpcuaPlcDriverTest.java）

```java
    private static Stream<Arguments> getConnectionSecurityPolicies() {
        return Stream.of(
            Arguments.of(SecurityPolicy.NONE, MessageSecurity.NONE),
            Arguments.of(SecurityPolicy.NONE, MessageSecurity.SIGN),
            Arguments.of(SecurityPolicy.NONE, MessageSecurity.SIGN_ENCRYPT),
            //Arguments.of(SecurityPolicy.Basic256Sha256, MessageSecurity.NONE),
            Arguments.of(SecurityPolicy.Basic256Sha256, MessageSecurity.SIGN),
            Arguments.of(SecurityPolicy.Basic256Sha256, MessageSecurity.SIGN_ENCRYPT),
            //Arguments.of(SecurityPolicy.Basic256, MessageSecurity.NONE),
            Arguments.of(SecurityPolicy.Basic256, MessageSecurity.SIGN),
            Arguments.of(SecurityPolicy.Basic256, MessageSecurity.SIGN_ENCRYPT),
            //Arguments.of(SecurityPolicy.Basic128Rsa15, MessageSecurity.NONE),
            Arguments.of(SecurityPolicy.Basic128Rsa15, MessageSecurity.SIGN),
            Arguments.of(SecurityPolicy.Basic128Rsa15, MessageSecurity.SIGN_ENCRYPT),
            //Arguments.of(SecurityPolicy.Aes128_Sha256_RsaOaep, MessageSecurity.NONE),
            Arguments.of(SecurityPolicy.Aes128_Sha256_RsaOaep, MessageSecurity.SIGN),
            Arguments.of(SecurityPolicy.Aes128_Sha256_RsaOaep, MessageSecurity.SIGN_ENCRYPT),
            //Arguments.of(SecurityPolicy.Aes256_Sha256_RsaPss, MessageSecurity.NONE),
            Arguments.of(SecurityPolicy.Aes256_Sha256_RsaPss, MessageSecurity.SIGN),
            Arguments.of(SecurityPolicy.Aes256_Sha256_RsaPss, MessageSecurity.SIGN_ENCRYPT)
        );
    }
```

### Test-side helpers called by this test (2)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`getConnectionString`**

```java
    private String getConnectionString(SecurityPolicy policy, MessageSecurity messageSecurity) throws Exception {
        switch (policy) {
            case NONE:
                return tcpConnectionAddress;

            case Basic256:
            case Basic128Rsa15:
            case Basic256Sha256:
            case Aes128_Sha256_RsaOaep:
            case Aes256_Sha256_RsaPss:
                String connectionParams = params(
                    entry("key-store-file", CLIENT_KEY_STORE.getAbsoluteFile().toString().replace("\\", "/")), // handle windows paths
                    entry("key-store-password", "changeit"),
                    entry("key-store-type", "pkcs12"),
                    entry("security-policy", policy.name()),
                    entry("message-security", messageSecurity.name())
                );

                return tcpConnectionAddress + PARAM_DIVIDER + connectionParams;
            default:
                throw new IllegalStateException();
        }
    }
```

**`params`**

```java
    private static String params(Entry<String, String> ... entries) {
        return Stream.of(entries)
            .map(entry -> entry.getKey() + "=" + URLEncoder.encode(entry.getValue(), Charset.defaultCharset()))
            .collect(Collectors.joining(PARAM_DIVIDER));
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-030  ·  ValueSource

**项目** `Commons-Numbers`  **文件** `commons-numbers/commons-numbers-gamma/src/test/java/org/apache/commons/numbers/gamma/BoostGammaTest.java`  **测试** `testGammaQLargeX`

### Test method

```java
@ParameterizedTest
    @ValueSource(strings = {"igamma_int_data.csv", "igamma_med_data.csv", "igamma_big_data.csv"})
    @Order(1)
    void testGammaQLargeX(String datafile) throws Exception {
        assertIgammaLargeX("Commons", datafile, true, getLargeXTarget(), getUseAsymApprox(), true);
    }
```

### Test-side helpers called by this test (6)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`assertIgammaLargeX`**

```java
    private static void assertIgammaLargeX(String name, String datafile, boolean invert,
            DoubleDoubleBiPredicate targetData,
            DoubleDoubleBiPredicate useAsymp,
            boolean expectImprovement) throws Exception {
        final TestUtils.ErrorStatistics e1 = new TestUtils.ErrorStatistics();
        final TestUtils.ErrorStatistics e2 = new TestUtils.ErrorStatistics();

        final Policy pol = Policy.getDefault();
        final DoubleBinaryOperator without = (a, x) -> gammaIncompleteImp(a, x, invert, pol, NO_ASYM_APPROX);
        final DoubleBinaryOperator with = (a, x) -> gammaIncompleteImp(a, x, invert, pol, useAsymp);
        final int expectedField = invert ? 3 : 5;

        // Count how many times the asymptotic approximation was used
        int count = 0;

        final String functionName = datafile + " " + name + (invert ? " Q" : " P");

        // Set this to allow all data to be processed.
        // If set to negative any failures will be output to stdout (useful to debugging).
        final double tolerance = 1000;

        try (DataReader in = new DataReader(datafile)) {
            while (in.next()) {
                final double a = in.getDouble(0);
                final double x = in.getDouble(1);

                // Test if this is target data
                if (targetData.test(a, x)) {
                    final BigDecimal expected = in.getBigDecimal(expectedField);

                    // Ignore 0 or 1 results.
                    // This test is interested in values that can be computed.
                    final double value = expected.doubleValue();
                    if ((int) value != value) {
                        final double v1 = without.applyAsDouble(a, x);
                        final double v2 = with.applyAsDouble(a, x);
                        // Check if the asymptoptic approximation is used
                        if (useAsymp.test(a, x)) {
                            count++;
                        }

                        TestUtils.assertEquals(expected, v1, tolerance, e1::add,
                            () -> functionName + " " + a + ", x=" + x);
                        TestUtils.assertEquals(expected, v2, tolerance, e2::add,
                            () -> functionName + " asymp " + a + ", x=" + x);
                    }
                }
            }
        }
        // Use relaxed tolerances to allow the big data to pass.
        // This test is mainly interested in checking a switch to the asymptotic approximation
        // does not make the computation worse.
        final double maxTolerance = 600;
        final double rmsTolerance = 600;
        if (e1.size() != 0) {
            assertRms(TestError.of(functionName + "           ", maxTolerance, rmsTolerance), e1);
            assertRms(TestError.of(functionName + " asymp " +
                    String.format("%4d", count), maxTolerance, rmsTolerance), e2);
            if (expectImprovement) {
                // Better or equal. Equal applies if the asymptotic approximation was not used
                // or computed the same result.
                Assertions.assertTrue(e2.getRMS() <= e1.getRMS());
            } else {
                // Worse
                Assertions.assertTrue(e2.getRMS() > e1.getRMS());
            }
        }
    }
```

**`getLargeXTarget`**

```java
    private static DoubleDoubleBiPredicate getLargeXTarget() {
        // Target the data that is computed using this method in Boost.
        // It will test that the method switch is an improvement.
        return USE_ASYM_APPROX;

        // Target all data that is computed using this method in Commons numbers.
        // It will test that when the method is switched it
        // will not make the computation worse.
        //return getUseAsymApprox();

        // Allow more data to be tested.
        // This predicate returns all valid data. Use it for testing but note that
        // most data is not suitable for the large x approximation.
        //return (a, x) -> !isIntOrHalfInt(a, x) && x >= 1.1 && (a < x);
    }
```

**`getUseAsymApprox`**

```java
    private static DoubleDoubleBiPredicate getUseAsymApprox() {
        // The asymptotic approximation is suitable for large x.
        // It sums terms starting from 1 until convergence.
        // term_n = term_(n-1) * (a-n) / z
        // term_0 = 1
        // Terms will get smaller if a < z.
        // The Boost condition is:
        // (x > 1000) && ((a < x) || (Math.abs(a - 50) / x < 1))
        //
        // This is not suitable if a ~ x and x is very large. The series takes
        // too many iterations to converge. With limited precision it may not be
        // possible to reduce the size of a, e.g. 1e16 - 1 == 1e16, thus
        // the terms do not reduce in size if decremented directly and take
        // many iterations to build a counter n that can be subtracted: a - n

        // Experimental:
        // Estimate the number of iterations.
        //
        // Assuming the term is reduced by a/z:
        // term_n = (a/z)^n
        // Setting the limit for term_n == epsilon (2^-52):
        // n = log(epsilon) / log(a/z)
        // Note: log(2^-52) is approximately -36.
        // Estimate of n is high given the factor is (a-i)/z for iteration i.

        // int limit = 1000;
        // return (a, x) -> (x > 1000) && (a < x) && (-36 / Math.log(a / x) < limit);

        // Simple:
        //
        // Target only data that will quickly converge.
        // Not that there is loss of precision in the terms when a ~ z.
        // The closer a/z is to 1 the more bits are lost in the result as the
        // terms are inexact and this error is compounded by a large number of terms
        // in the series.
        // This condition ensures the asymptotic approximation is used when x -> infinity
        // and a << x.
        // Using the logic from above an overestimate of the maximum iterations is:
        // threshold   value      iterations
        // 1 - 2^-1    0.5        52
        // 1 - 2^-2    0.75       125
        // 1 - 2^-3    0.875      270
        // 1 - 2^-4    0.9375     558
        // 1 - 2^-5    0.96875    1135
        // 1 - 2^-6    0.984375   2289
        return (a, x) -> (x > 1000) && (a < x * 0.75);
    }
```

**`gammaIncompleteImp`**

```java
    private static double gammaIncompleteImp(double a, double x,
            boolean invert, Policy pol, DoubleDoubleBiPredicate useAsymApprox) {
        if (Double.isNaN(a) || Double.isNaN(x) || a <= 0 || x < 0) {
            return Double.NaN;
        }

        // Assumption for testing.
        // Do not support int or half-int a.
        // Do not support small x.
        // These evaluations methods have been removed.
        Assertions.assertFalse(isIntOrHalfInt(a, x), () -> "Invalid a : " + a);
        Assertions.assertFalse(x < 1.1, () -> "Invalid x : " + x);

        double result = 0;
        int evalMethod;

        // Configurable switch to the asymptotic approximation.
        // The branch is used in Boost when:
        // ((x > 1000) && ((a < x) || (Math.abs(a - 50) / x < 1)))
        if (useAsymApprox.test(a, x)) {
            // This case was added after Boost 1_68_0.
            // See: https://github.com/boostorg/math/issues/168
            // It is a source of error when a ~ z as the asymptotic approximation
            // sums terms t_n+1 = t_n * (a - n - 1) / z starting from t_0 = 1.
            // These terms are close to 1 when a ~ z and the sum has many terms
            // with reduced precision.

            // calculate Q via asymptotic approximation:
            invert = !invert;
            evalMethod = 7;
        } else {
            //
            // Begin by testing whether we're in the "bad" zone
            // where the result will be near 0.5 and the usual
            // series and continued fractions are slow to converge:
            //
            boolean useTemme = false;
            if (a > 20) {
                final double sigma = Math.abs((x - a) / a);
                if (a > 200) {
                    //
                    // This limit is chosen so that we use Temme's expansion
                    // only if the result would be larger than about 10^-6.
                    // Below that the regular series and continued fractions
                    // converge OK, and if we use Temme's method we get increasing
                    // errors from the dominant erfc term as it's (inexact) argument
                    // increases in magnitude.
                    //
                    if (20 / a > sigma * sigma) {
                        useTemme = true;
                    }
                } else {
                    // Note in this zone we can't use Temme's expansion for
                    // types longer than an 80-bit real:
                    // it would require too many terms in the polynomials.
                    if (sigma < 0.4) {
                        useTemme = true;
                    }
                }
            }
            if (useTemme) {
                evalMethod = 5;
            } else {
                //
                // Regular case where the result will not be too close to 0.5.
                //
                // Changeover here occurs at P ~ Q ~ 0.5
                // Note that series computation of P is about x2 faster than continued fraction
                // calculation of Q, so try and use the CF only when really necessary,
                // especially for small x.
    // … 省略 80 行
```

**`assertEquals`**

```java
    private static void assertEquals(DoubleBinaryOperator fun, double x, double y, double expected) {
        final double actual = fun.applyAsDouble(x, y);
        Assertions.assertEquals(expected, actual, () -> x + ", " + y);
    }
```

**`assertRms`**

```java
    private static void assertRms(TestError te, TestUtils.ErrorStatistics stats) {
        final double rms = stats.getRMS();
        //debugRms(te.toString(), stats.getMaxAbs(), rms, stats.getMean(), stats.size());
        Assertions.assertTrue(rms <= te.getRmsTolerance(),
            () -> String.format("%s RMS %s < %s", te, rms, te.getRmsTolerance()));
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-033  ·  EnumSource

**项目** `ZooKeeper`  **文件** `zookeeper/zookeeper-server/src/test/java/org/apache/zookeeper/server/admin/CommandAuthTest.java`  **测试** `testAuthCheck_authorized`

### Test method

```java
@ParameterizedTest
    @EnumSource(AuthSchema.class)
    public void testAuthCheck_authorized(final AuthSchema authSchema) throws Exception {
        setupRootACL(authSchema);
        try {
            final HttpURLConnection authTestConn = sendAuthTestCommandRequest(authSchema, true);
            assertEquals(HttpURLConnection.HTTP_OK, authTestConn.getResponseCode());
        } finally {
            addAuthInfo(zk, authSchema);
            resetRootACL(zk);
        }
    }
```

### Enum declaration — `AuthSchema` (zookeeper/zookeeper-server/src/test/java/org/apache/zookeeper/server/admin/CommandAuthTest.java)

```java
    public enum AuthSchema {
        DIGEST,
        X509,
        IP
    }
```

### Test-side helpers called by this test (6)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`setupRootACL`**

```java
    private void setupRootACL(final AuthSchema authSchema) throws Exception {
        setupRootACL(authSchema, Collections.<ACL>emptyList());
    }
```

**`sendAuthTestCommandRequest`**

```java
    private HttpURLConnection sendAuthTestCommandRequest(final AuthSchema authSchema, final boolean validAuthInfo) throws Exception  {
        final URL authTestURL = new URL(String.format(HTTPS_URL_FORMAT + "/" + AUTH_TEST_COMMAND_NAME, jettyAdminPort));
        final HttpURLConnection authTestConn = (HttpURLConnection) authTestURL.openConnection();
        addAuthHeader(authTestConn, authSchema, validAuthInfo);
        authTestConn.setRequestMethod("GET");
        return authTestConn;
    }
```

**`addAuthInfo`**

```java
    private void addAuthInfo(final ZooKeeper zk, final AuthSchema authSchema) {
        switch (authSchema) {
            case DIGEST:
                addAuthInfoForDigest(zk);
                break;
            case X509:
                addAuthInfoForX509(zk);
                break;
            case IP:
                addAuthInfoForIP(zk);
                break;
            default:
                throw new IllegalArgumentException("Unknown auth schema");
        }
    }
```

**`resetRootACL`**

```java
    public static void resetRootACL(final ZooKeeper zk) throws Exception {
        zk.setACL(Commands.ROOT_PATH, OPEN_ACL_UNSAFE, -1);
    }
```

**`addAuthHeader`**

```java
    public static void addAuthHeader(final HttpURLConnection conn, final AuthSchema authSchema, final boolean validAuthInfo) {
        String authInfo;
        switch (authSchema) {
            case DIGEST:
                authInfo = validAuthInfo ? buildAuthorizationForDigest() : buildInvalidAuthorizationForDigest();
                break;
            case X509:
                authInfo = buildAuthorizationForX509();
                break;
            case IP:
                authInfo = buildAuthorizationForIP();
                break;
            default:
                throw new IllegalArgumentException("Unknown auth schema");
        }
        conn.setRequestProperty(HttpHeader.AUTHORIZATION.asString(), authInfo);
    }
```

**`addAuthInfoForDigest`**

```java
    public static void addAuthInfoForDigest(final ZooKeeper zk) {
        final String idPassword = String.format("%s:%s", ROOT_USER, ROOT_PASSWORD);
        zk.addAuthInfo(DIGEST_SCHEMA, idPassword.getBytes(StandardCharsets.UTF_8));
    }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-036  ·  EnumSource

**项目** `Avro`  **文件** `avro/lang/java/avro/src/test/java/org/apache/avro/TestReadingWritingDataInEvolvedSchemas.java`  **测试** `doubleWrittenWithUnionSchemaIsNotConvertedToFloatSchema`

### Test method

```java
@ParameterizedTest
  @EnumSource(EncoderType.class)
  void doubleWrittenWithUnionSchemaIsNotConvertedToFloatSchema(EncoderType encoderType) throws Exception {
    Schema writer = UNION_INT_LONG_FLOAT_DOUBLE_RECORD;
    Record record = defaultRecordWithSchema(writer, FIELD_A, 42.0);
    byte[] encoded = encodeGenericBlob(record, encoderType);
    AvroTypeException exception = Assertions.assertThrows(AvroTypeException.class,
        () -> decodeGenericBlob(FLOAT_RECORD, writer, encoded, encoderType));
    Assertions.assertEquals("Found double, expecting float", exception.getMessage());
  }
```

### Enum declaration — `EncoderType` (avro/lang/java/avro/src/test/java/org/apache/avro/TestReadingWritingDataInEvolvedSchemas.java)

```java
  enum EncoderType {
    BINARY, JSON
  }
```

### Test-side helpers called by this test (3)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`defaultRecordWithSchema`**

```java
  private <T> Record defaultRecordWithSchema(Schema schema, String key, T value) {
    Record data = new GenericData.Record(schema);
    data.put(key, value);
    return data;
  }
```

**`encodeGenericBlob`**

```java
  private byte[] encodeGenericBlob(GenericRecord data, EncoderType encoderType) throws IOException {
    DatumWriter<GenericRecord> writer = new GenericDatumWriter<>(data.getSchema());
    ByteArrayOutputStream outStream = new ByteArrayOutputStream();
    Encoder encoder = encoderType == EncoderType.BINARY ? EncoderFactory.get().binaryEncoder(outStream, null)
        : EncoderFactory.get().jsonEncoder(data.getSchema(), outStream);
    writer.write(data, encoder);
    encoder.flush();
    outStream.close();
    return outStream.toByteArray();
  }
```

**`decodeGenericBlob`**

```java
  private Record decodeGenericBlob(Schema expectedSchema, Schema schemaOfBlob, byte[] blob, EncoderType encoderType)
      throws IOException {
    if (blob == null) {
      return null;
    }
    GenericData data = new GenericData();
    data.setFastReaderEnabled(true);
    GenericDatumReader<Record> reader = new GenericDatumReader<>(null, null, data);
    reader.setExpected(expectedSchema);
    reader.setSchema(schemaOfBlob);
    Decoder decoder = encoderType == EncoderType.BINARY ? DecoderFactory.get().binaryDecoder(blob, null)
        : DecoderFactory.get().jsonDecoder(schemaOfBlob, new ByteArrayInputStream(blob));
    return reader.read(null, decoder);
  }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-039  ·  MethodSource

**项目** `Calcite`  **文件** `calcite/testkit/src/main/java/org/apache/calcite/test/QuidemTest.java`  **测试** `test`

### Test method

```java
@ParameterizedTest
  @MethodSource("getPath")
  public void test(String path) throws Exception {
    final Method method = findMethod(path);
    if (method != null) {
      try {
        method.invoke(this, path);
      } catch (InvocationTargetException e) {
        Throwable cause = e.getCause();
        if (cause instanceof Exception) {
          throw (Exception) cause;
        }
        if (cause instanceof Error) {
          throw (Error) cause;
        }
        throw e;
      }
    } else {
      checkRun(path);
    }
  }
```

### Parameter provider — `getPath`（calcite/core/src/main/java/org/apache/calcite/jdbc/CalciteSchema.java）

```java
  public List<? extends List<String>> getPath() {
    if (path != null) {
      return path;
    }
    // Return a path consisting of just this schema.
    return ImmutableList.of(path(null));
  }
```

### Test-side helpers called by this test (6)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`checkRun`**

```java
  protected void checkRun(String path) throws Exception {
    final File inFile;
    final File outFile;
    final File f = new File(path);
    if (f.isAbsolute()) {
      // e.g. path = "/tmp/foo.iq"
      inFile = f;
      outFile = new File(path + ".out");
    } else {
      // e.g. path = "sql/agg.iq"
      // inUrl = "file:/home/fred/calcite/core/build/resources/test/sql/agg.iq"
      // inFile = "/home/fred/calcite/core/build/resources/test/sql/agg.iq"
      // outDir = "/home/fred/calcite/core/build/quidem/test/sql"
      // outFile = "/home/fred/calcite/core/build/quidem/test/sql/agg.iq"
      final URL inUrl = QuidemTest.class.getResource("/" + n2u(path));
      inFile = Sources.of(requireNonNull(inUrl, "inUrl")).file();
      outFile = replaceDir(inFile, "resources", "quidem");
    }
    Util.discard(outFile.getParentFile().mkdirs());
    try (Reader reader = Util.reader(inFile);
         Writer writer = Util.printWriter(outFile);
         Closer closer = new Closer()) {
      final Quidem.Config config = Quidem.configBuilder()
          .withReader(reader)
          .withWriter(writer)
          .withConnectionFactory(createConnectionFactory())
          .withCommandHandler(createCommandHandler())
          .withPropertyHandler((propertyName, value) -> {
            if (propertyName.equals("bindable")) {
              final boolean b = value instanceof Boolean
                  && (Boolean) value;
              closer.add(Hook.ENABLE_BINDABLE.addThread(Hook.propertyJ(b)));
            }
            if (propertyName.equals("expand")) {
              final boolean b = value instanceof Boolean
                  && (Boolean) value;
              closer.add(Prepare.THREAD_EXPAND.push(b));
            }
            if (propertyName.equals("insubquerythreshold")) {
              int thresholdValue = ((BigDecimal) value).intValue();
              closer.add(Prepare.THREAD_INSUBQUERY_THRESHOLD.push(thresholdValue));
            }
            // Configures query planner rules via "!set planner-rules" command.
            // The value can be set as follows:
            // - Add rule:       "+EnumerableRules.ENUMERABLE_INTERSECT_RULE"
            // - Remove rule:    "-CoreRules.INTERSECT_TO_DISTINCT"
            // - Short form:     "+INTERSECT_TO_DISTINCT" (CoreRules prefix may be omitted)
            // - Reset defaults: "original"
            if (propertyName.equals("planner-rules")) {
              if (value.equals("original")) {
                closer.add(Hook.PLANNER.addThread(QuidemTest::resetPlanner));
              } else {
                closer.add(
                    Hook.PLANNER.addThread((Consumer<RelOptPlanner>)
                        planner -> {
                          if (originalRules == null) {
                            originalRules = planner.getRules();
                          }
                          updatePlanner(planner, (String) value);
                        }));
              }
            }
          })
          .withEnv(QuidemTest::getEnv)
          .build();
      new Quidem(config).execute();
    }
    // Sanity check: we do not allow an empty input file, it may indicate that it was overwritten
    if (inFile.length() == 0) {
      fail("Input file was empty: " + inFile + "\n");
    // … 省略 7 行
```

**`n2u`**

```java
  private static String n2u(String s) {
    return File.separatorChar == '\\'
        ? s.replace('\\', '/')
        : s;
  }
```

**`replaceDir`**

```java
  private static File replaceDir(File file, String target, String replacement) {
    return new File(
        n2u(file.getAbsolutePath()).replace(n2u('/' + target + '/'),
            n2u('/' + replacement + '/')));
  }
```

**`createConnectionFactory`**

```java
  protected Quidem.ConnectionFactory createConnectionFactory() {
    return new QuidemConnectionFactory();
  }
```

**`createCommandHandler`**

```java
  protected CommandHandler createCommandHandler() {
    return Quidem.EMPTY_COMMAND_HANDLER;
  }
```

**`updatePlanner`**

```java
  private static void updatePlanner(RelOptPlanner planner, String value) {
    List<RelOptRule> rulesAdd = new ArrayList<>();
    List<RelOptRule> rulesRemove = new ArrayList<>();
    parseRules(value, rulesAdd, rulesRemove);
    rulesRemove.forEach(planner::removeRule);
    rulesAdd.forEach(planner::addRule);
  }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-042  ·  MethodSource

**项目** `Commons-Pool`  **文件** `commons-pool/src/test/java/org/apache/commons/pool3/impl/CallStackTest.java`  **测试** `testPrintFilledStackTrace`

### Test method

```java
@ParameterizedTest
    @MethodSource("data")
    void testPrintFilledStackTrace(final CallStack stack) {
        stack.fillInStackTrace();
        stack.printStackTrace(new PrintWriter(writer));
        final String stackTrace = writer.toString();
        assertTrue(stackTrace.contains(getClass().getName()));
    }
```

### Parameter provider — 同文件内的 `data`

```java
    public static Stream<Arguments> data() {
        // @formatter:off
        return Stream.of(
                Arguments.arguments(new ThrowableCallStack("Test", false)),
                Arguments.arguments(new ThrowableCallStack("yyyy-MM-dd'T'HH:mm:ss.SSSXXX", true)),
                Arguments.arguments(new SecurityManagerCallStack("Test", false)),
                Arguments.arguments(new SecurityManagerCallStack("yyyy-MM-dd'T'HH:mm:ss.SSSXXX", true))
        );
        // @formatter:on
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-045  ·  MethodSource

**项目** `Commons-CLI`  **文件** `commons-cli/src/test/java/org/apache/commons/cli/TypeHandlerTest.java`  **测试** `testCreateValue`

### Test method

```java
@SuppressWarnings("unchecked")
    @ParameterizedTest(name = "{0} as {1}")
    @MethodSource("createValueTestParameters")
    void testCreateValue(final String str, final Class<?> type, final Object expected) throws Exception {
        @SuppressWarnings("cast")
        final Object objectApiTest = type; // KEEP this cast
        if (expected instanceof Class<?> && Throwable.class.isAssignableFrom((Class<?>) expected)) {
            assertThrows((Class<Throwable>) expected, () -> TypeHandler.createValue(str, type));
            assertThrows((Class<Throwable>) expected, () -> TypeHandler.createValue(str, objectApiTest));
        } else {
            assertEquals(expected, TypeHandler.createValue(str, type));
            assertEquals(expected, TypeHandler.createValue(str, objectApiTest));
        }
    }
```

### Parameter provider — 同文件内的 `createValueTestParameters`

```java
    private static Stream<Arguments> createValueTestParameters() throws MalformedURLException {
        // force the PatternOptionBuilder to load / modify the TypeHandler table.
        @SuppressWarnings("unused")
        final Class<?> loadStatic = PatternOptionBuilder.FILES_VALUE;
        // reset the type handler table.
        // TypeHandler.resetConverters();
        final List<Arguments> list = new ArrayList<>();

        /*
         * Dates calculated from strings are dependent upon configuration and environment settings for the machine on which the test is running. To avoid this
         * problem, convert the time into a string and then unparse that using the converter. This produces strings that always match the correct time zone.
         */
        final Date date = new Date(1023400137000L);
        final DateFormat dateFormat = new SimpleDateFormat("EEE MMM dd HH:mm:ss zzz yyyy");

        list.add(Arguments.of(Instantiable.class.getName(), PatternOptionBuilder.CLASS_VALUE, Instantiable.class));
        list.add(Arguments.of("what ever", PatternOptionBuilder.CLASS_VALUE, ParseException.class));

        list.add(Arguments.of("what ever", PatternOptionBuilder.DATE_VALUE, ParseException.class));
        list.add(Arguments.of(dateFormat.format(date), PatternOptionBuilder.DATE_VALUE, date));
        list.add(Arguments.of("Jun 06 17:48:57 EDT 2002", PatternOptionBuilder.DATE_VALUE, ParseException.class));

        list.add(Arguments.of("non-existing.file", PatternOptionBuilder.EXISTING_FILE_VALUE, ParseException.class));

        list.add(Arguments.of("some-file.txt", PatternOptionBuilder.FILE_VALUE, new File("some-file.txt")));

        list.add(Arguments.of("some-path.txt", Path.class, new File("some-path.txt").toPath()));

        // the PatternOptionBuilder.FILES_VALUE is not registered so it should just return the string
        list.add(Arguments.of("some.files", PatternOptionBuilder.FILES_VALUE, "some.files"));

        list.add(Arguments.of("just-a-string", Integer.class, ParseException.class));
        list.add(Arguments.of("5", Integer.class, 5));
        list.add(Arguments.of("5.5", Integer.class, ParseException.class));
        list.add(Arguments.of(Long.toString(Long.MAX_VALUE), Integer.class, ParseException.class));

        list.add(Arguments.of("just-a-string", Long.class, ParseException.class));
        list.add(Arguments.of("5", Long.class, 5L));
        list.add(Arguments.of("5.5", Long.class, ParseException.class));

        list.add(Arguments.of("just-a-string", Short.class, ParseException.class));
        list.add(Arguments.of("5", Short.class, (short) 5));
        list.add(Arguments.of("5.5", Short.class, ParseException.class));
        list.add(Arguments.of(Integer.toString(Integer.MAX_VALUE), Short.class, ParseException.class));

        list.add(Arguments.of("just-a-string", Byte.class, ParseException.class));
        list.add(Arguments.of("5", Byte.class, (byte) 5));
        list.add(Arguments.of("5.5", Byte.class, ParseException.class));
        list.add(Arguments.of(Short.toString(Short.MAX_VALUE), Byte.class, ParseException.class));

        list.add(Arguments.of("just-a-string", Character.class, 'j'));
        list.add(Arguments.of("5", Character.class, '5'));
        list.add(Arguments.of("5.5", Character.class, '5'));
        list.add(Arguments.of("\\u0124", Character.class, Character.toChars(0x0124)[0]));

        list.add(Arguments.of("just-a-string", Double.class, ParseException.class));
        list.add(Arguments.of("5", Double.class, 5d));
        list.add(Arguments.of("5.5", Double.class, 5.5));

        list.add(Arguments.of("just-a-string", Float.class, ParseException.class));
        list.add(Arguments.of("5", Float.class, 5f));
        list.add(Arguments.of("5.5", Float.class, 5.5f));
        list.add(Arguments.of(Double.toString(Double.MAX_VALUE), Float.class, Float.POSITIVE_INFINITY));

        list.add(Arguments.of("just-a-string", BigInteger.class, ParseException.class));
        list.add(Arguments.of("5", BigInteger.class, new BigInteger("5")));
        list.add(Arguments.of("5.5", BigInteger.class, ParseException.class));

        list.add(Arguments.of("just-a-string", BigDecimal.class, ParseException.class));
        list.add(Arguments.of("5", BigDecimal.class, new BigDecimal("5")));
        list.add(Arguments.of("5.5", BigDecimal.class, new BigDecimal(5.5)));

        list.add(Arguments.of("1.5", PatternOptionBuilder.NUMBER_VALUE, Double.valueOf(1.5)));
        list.add(Arguments.of("15", PatternOptionBuilder.NUMBER_VALUE, Long.valueOf(15)));
        list.add(Arguments.of("not a number", PatternOptionBuilder.NUMBER_VALUE, ParseException.class));

        list.add(Arguments.of(Instantiable.class.getName(), PatternOptionBuilder.OBJECT_VALUE, new Instantiable()));
        list.add(Arguments.of(NotInstantiable.class.getName(), PatternOptionBuilder.OBJECT_VALUE, ParseException.class));
        list.add(Arguments.of("unknown", PatternOptionBuilder.OBJECT_VALUE, ParseException.class));

        list.add(Arguments.of("String", PatternOptionBuilder.STRING_VALUE, "String"));

        final String urlString = "https://commons.apache.org";
        list.add(Arguments.of(urlString, PatternOptionBuilder.URL_VALUE, new URL(urlString)));
        list.add(Arguments.of("Malformed-url", PatternOptionBuilder.URL_VALUE, ParseException.class));

        return list.stream();

    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-048  ·  MethodSource

**项目** `Hive`  **文件** `hive/ql/src/test/org/apache/hadoop/hive/ql/io/parquet/serde/TestParquetTimestampsHive2Compatibility.java`  **测试** `testWriteHive2ReadHive4UsingLegacyConversionWithZone`

### Test method

```java
@ParameterizedTest(name = "{0}")
  @MethodSource("generateTimestamps")
  void testWriteHive2ReadHive4UsingLegacyConversionWithZone(String timestampString) {
    TimeZone original = TimeZone.getDefault();
    try {
      String zoneId = "US/Pacific";
      TimeZone.setDefault(TimeZone.getTimeZone(zoneId));
      NanoTime nt = writeHive2(timestampString);
      Timestamp ts = readHive4(nt, zoneId, true);
      assertEquals(timestampString, ts.toString());
    } finally {
      TimeZone.setDefault(original);
    }
  }
```

### Parameter provider — 同文件内的 `generateTimestamps`

```java
  private static Stream<String> generateTimestamps() {
    return Stream.concat(Stream.generate(new Supplier<String>() {
      int i = 0;

      @Override
      public String get() {
        StringBuilder sb = new StringBuilder(29);
        int year = (i % 9999) + 1;
        sb.append(zeros(4 - digits(year)));
        sb.append(year);
        sb.append('-');
        int month = (i % 12) + 1;
        sb.append(zeros(2 - digits(month)));
        sb.append(month);
        sb.append('-');
        int day = (i % 28) + 1;
        sb.append(zeros(2 - digits(day)));
        sb.append(day);
        sb.append(' ');
        int hour = i % 24;
        sb.append(zeros(2 - digits(hour)));
        sb.append(hour);
        sb.append(':');
        int minute = i % 60;
        sb.append(zeros(2 - digits(minute)));
        sb.append(minute);
        sb.append(':');
        int second = i % 60;
        sb.append(zeros(2 - digits(second)));
        sb.append(second);
        sb.append('.');
        // Bitwise OR with one to avoid times with trailing zeros
        int nano = (i % 1000000000) | 1;
        sb.append(zeros(9 - digits(nano)));
        sb.append(nano);
        i++;
        return sb.toString();
      }
    })
    // Exclude dates falling in the default Gregorian change date since legacy code does not handle that interval
    // gracefully. It is expected that these do not work well when legacy APIs are in use. 
    .filter(s -> !s.startsWith("1582-10"))
    .limit(3000), Stream.of("9999-12-31 23:59:59.999"));
  }
```

### Test-side helpers called by this test (4)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`writeHive2`**

```java
  private static NanoTime writeHive2(String str) {
    java.sql.Timestamp ts = toTimestampHive2(str);
    Calendar calendar = Calendar.getInstance(TimeZone.getTimeZone(ZoneId.of("GMT")));
    calendar.setTime(ts);
    int year = calendar.get(Calendar.YEAR);
    if (calendar.get(Calendar.ERA) == GregorianCalendar.BC) {
      year = 1 - year;
    }
    JulianDate jDateTime = JulianDate.of(year, calendar.get(Calendar.MONTH) + 1,  //java calendar index starting at 1.
        calendar.get(Calendar.DAY_OF_MONTH), 0, 0, 0, 0);
    int days = jDateTime.getJulianDayNumber();

    long hour = calendar.get(Calendar.HOUR_OF_DAY);
    long minute = calendar.get(Calendar.MINUTE);
    long second = calendar.get(Calendar.SECOND);
    long nanos = ts.getNanos();
    long nanosOfDay = nanos + NANOS_PER_SECOND * second + NANOS_PER_MINUTE * minute + NANOS_PER_HOUR * hour;

    return new NanoTime(days, nanosOfDay);
  }
```

**`readHive4`**

```java
  private static Timestamp readHive4(NanoTime nt, String targetZone, boolean legacyConversion) {
    return NanoTimeUtils.getTimestamp(nt, ZoneId.of(targetZone), legacyConversion);
  }
```

**`toTimestampHive2`**

```java
  private static java.sql.Timestamp toTimestampHive2(String s) {
    java.sql.Timestamp result;
    s = s.trim();

    // Throw away extra if more than 9 decimal places
    int periodIdx = s.indexOf(".");
    if (periodIdx != -1) {
      if (s.length() - periodIdx > 9) {
        s = s.substring(0, periodIdx + 10);
      }
    }
    if (s.indexOf(' ') < 0) {
      s = s.concat(" 00:00:00");
    }
    try {
      result = java.sql.Timestamp.valueOf(s);
    } catch (IllegalArgumentException e) {
      result = null;
    }
    return result;
  }
```

**`get`**

```java
@Override
      public String get() {
        StringBuilder sb = new StringBuilder(29);
        int year = (i % 9999) + 1;
        sb.append(zeros(4 - digits(year)));
        sb.append(year);
        sb.append('-');
        int month = (i % 12) + 1;
        sb.append(zeros(2 - digits(month)));
        sb.append(month);
        sb.append('-');
        int day = (i % 28) + 1;
        sb.append(zeros(2 - digits(day)));
        sb.append(day);
        sb.append(' ');
        int hour = i % 24;
        sb.append(zeros(2 - digits(hour)));
        sb.append(hour);
        sb.append(':');
        int minute = i % 60;
        sb.append(zeros(2 - digits(minute)));
        sb.append(minute);
        sb.append(':');
        int second = i % 60;
        sb.append(zeros(2 - digits(second)));
        sb.append(second);
        sb.append('.');
        // Bitwise OR with one to avoid times with trailing zeros
        int nano = (i % 1000000000) | 1;
        sb.append(zeros(9 - digits(nano)));
        sb.append(nano);
        i++;
        return sb.toString();
      }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-051  ·  MethodSource

**项目** `Hop`  **文件** `hop/plugins/tech/azure/src/test/java/org/apache/hop/vfs/azure/AzureFileNameParserTest.java`  **测试** `parseUri`

### Test method

```java
@ParameterizedTest
  @MethodSource("azureUris")
  void parseUri(
      String inputUri,
      String expectedScheme,
      String expectedContainer,
      String expectedPathAfterContainer,
      FileType expectedType)
      throws FileSystemException {
    VfsComponentContext context = Mockito.mock(VfsComponentContext.class);

    AzureFileName actual = (AzureFileName) parser.parseUri(context, null, inputUri);

    System.out.println(inputUri);
    System.out.println("Scheme: " + actual.getScheme());
    System.out.println("Container: " + actual.getContainer());
    System.out.println("Path: " + actual.getPath());
    System.out.println("--------------------------");

    Assertions.assertEquals(expectedScheme, actual.getScheme());
    Assertions.assertEquals(expectedContainer, actual.getContainer());
    Assertions.assertEquals(expectedPathAfterContainer, actual.getPathAfterContainer());
    Assertions.assertEquals(expectedType, actual.getType());
  }
```

### Parameter provider — 同文件内的 `azureUris`

```java
  static Stream<Arguments> azureUris() {
    return Stream.of(
        Arguments.of(
            "azfs://hopsa/container/folder1/parquet-test-delo2-azfs-00-0001.parquet",
            "azfs",
            "container",
            "/folder1/parquet-test-delo2-azfs-00-0001.parquet",
            FileType.FILE),
        Arguments.of(
            "azfs:/hopsa/container/folder1/", "azfs", "container", "/folder1", FileType.FOLDER),
        Arguments.of("azure://test/folder1/", "azure", "test", "/folder1", FileType.FOLDER),
        Arguments.of(
            "azure://mycontainer/folder1/parquet-test-delo2-azfs-00-0001.parquet",
            "azure",
            "mycontainer",
            "/folder1/parquet-test-delo2-azfs-00-0001.parquet",
            FileType.FILE),
        Arguments.of(
            "azfs://hopsa/delo/delo3-azfs-00-0001.parquet",
            "azfs",
            "delo",
            "/delo3-azfs-00-0001.parquet",
            FileType.FILE),
        Arguments.of(
            "azfs://hopsa/container/folder1/", "azfs", "container", "/folder1", FileType.FOLDER),
        Arguments.of("azfs://account/container/", "azfs", "container", "", FileType.FOLDER),
        Arguments.of(
            "azfs://otheraccount/container/myfile.txt",
            "azfs",
            "container",
            "/myfile.txt",
            FileType.FILE),
        Arguments.of(
            "azfs:///account1/container/myfile.txt",
            "azfs",
            "container",
            "/myfile.txt",
            FileType.FILE),
        Arguments.of(
            "azfs:///fake/container/path/to/resource/myfile.txt",
            "azfs",
            "container",
            "/path/to/resource/myfile.txt",
            FileType.FILE));
  }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-054  ·  CsvSource

**项目** `Commons-Statistics`  **文件** `commons-statistics/commons-statistics-inference/src/test/java/org/apache/commons/statistics/inference/HypergeomTest.java`  **测试** `testDistribution`

### Test method

```java
@ParameterizedTest
    @CsvSource({
        "10, 5, 5",
        "10, 3, 5",
        "12, 5, 3",
    })
    void testDistribution(int n, int k, int m) {
        final HypergeometricDistribution d1 = HypergeometricDistribution.of(n, k, m);
        final Hypergeom d2 = new Hypergeom(n, k, m);
        final int lo = d1.getSupportLowerBound();
        final int hi = d2.getSupportUpperBound();
        Assertions.assertEquals(lo, d2.getSupportLowerBound(), "lower bound");
        Assertions.assertEquals(hi, d2.getSupportUpperBound(), "upper bound");
        // Out of bounds will throw
        Assertions.assertThrows(IndexOutOfBoundsException.class, () -> d2.pmf(-1), "pmf(-1)");
        Assertions.assertThrows(IndexOutOfBoundsException.class, () -> d2.pmf(hi + 1), "pmf(hi + 1)");
        // Out of bounds for the cumulative functions is supported
        Assertions.assertEquals(d1.cumulativeProbability(lo - 1), d2.cdf(lo - 1), "cdf(lo - 1)");
        Assertions.assertEquals(d1.cumulativeProbability(hi + 1), d2.cdf(hi + 1), "cdf(hi + 1)");
        Assertions.assertEquals(d1.survivalProbability(lo - 1), d2.sf(lo - 1), "sf(lo - 1)");
        Assertions.assertEquals(d1.survivalProbability(hi + 1), d2.sf(hi + 1), "sf(hi + 1)");
        for (int x = lo; x <= hi; x++) {
            Assertions.assertEquals(d1.probability(x), d2.pmf(x), "pmf");
            Assertions.assertEquals(d1.cumulativeProbability(x), d2.cdf(x), "cdf");
            Assertions.assertEquals(d1.survivalProbability(x), d2.sf(x), "sf");
        }
        // Test the mode is the highest pmf
        double p = d2.pmf(lo);
        for (int x = lo + 1;; x++) {
            final double p2 = d2.pmf(x);
            if (p2 > p) {
                p = p2;
            } else {
                Assertions.assertEquals(d2.getLowerMode(), x - 1, "lower mode");
                break;
            }
        }
        p = d2.pmf(hi);
        for (int x = hi - 1;; x--) {
            final double p2 = d2.pmf(x);
            if (p2 > p) {
                p = p2;
            } else {
                Assertions.assertEquals(d2.getUpperMode(), x + 1, "upper mode");
                break;
            }
        }
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-057  ·  ValueSource

**项目** `Ozone`  **文件** `ozone/hadoop-ozone/integration-test/src/test/java/org/apache/hadoop/ozone/om/TestOMDbCheckpointServletInodeBasedXfer.java`  **测试** `testWriteDBToArchive`

### Test method

```java
@ParameterizedTest
  @ValueSource(booleans = {true, false})
  public void testWriteDBToArchive(boolean expectOnlySstFiles) throws Exception {
    setupMocks();
    Path dbDir = folder.resolve("db_data");
    Files.createDirectories(dbDir);
    // Create dummy files: one SST, one non-SST
    Path sstFile = dbDir.resolve("test.sst");
    Files.write(sstFile, "sst content".getBytes(StandardCharsets.UTF_8)); // Write some content to make it non-empty

    Path nonSstFile = dbDir.resolve("test.log");
    Files.write(nonSstFile, "log content".getBytes(StandardCharsets.UTF_8));
    Set<String> sstFilesToExclude = new HashSet<>();
    AtomicLong maxTotalSstSize = new AtomicLong(1000000); // Sufficient size
    Map<String, String> hardLinkFileMap = new java.util.HashMap<>();
    Path tmpDir = folder.resolve("tmp");
    Files.createDirectories(tmpDir);
    TarArchiveOutputStream mockArchiveOutputStream = mock(TarArchiveOutputStream.class);
    List<String> fileNames = new ArrayList<>();
    try (MockedStatic<Archiver> archiverMock = mockStatic(Archiver.class)) {
      archiverMock.when(() -> Archiver.linkAndIncludeFile(any(), any(), any(), any())).thenAnswer(invocation -> {
        // Get the actual mockArchiveOutputStream passed from writeDBToArchive
        TarArchiveOutputStream aos = invocation.getArgument(2);
        File sourceFile = invocation.getArgument(0);
        String fileId = invocation.getArgument(1);
        fileNames.add(sourceFile.getName());
        aos.putArchiveEntry(new TarArchiveEntry(sourceFile, fileId));
        aos.write(new byte[100], 0, 100); // Simulate writing
        aos.closeArchiveEntry();
        return 100L;
      });
      boolean success = omDbCheckpointServletMock.writeDBToArchive(
          sstFilesToExclude, dbDir, maxTotalSstSize, mockArchiveOutputStream,
              tmpDir, hardLinkFileMap, expectOnlySstFiles);
      assertTrue(success);
      verify(mockArchiveOutputStream, times(fileNames.size())).putArchiveEntry(any());
      verify(mockArchiveOutputStream, times(fileNames.size())).closeArchiveEntry();
      verify(mockArchiveOutputStream, times(fileNames.size())).write(any(byte[].class), anyInt(),
          anyInt()); // verify write was called once

      boolean containsNonSstFile = false;
      for (String fileName : fileNames) {
        if (expectOnlySstFiles) {
          assertTrue(fileName.endsWith(".sst"), "File is not an SST File");
        } else {
          containsNonSstFile = true;
        }
      }

      if (!expectOnlySstFiles) {
        assertTrue(containsNonSstFile, "SST File is not expected");
      }
    }
  }
```

### Test-side helpers called by this test (6)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`setupMocks`**

```java
  private void setupMocks() throws Exception {
    final Path tempPath = folder.resolve("temp" + COUNTER.incrementAndGet() + ".tar");
    tempFile = tempPath.toFile();

    servletOutputStream = new ServletOutputStream() {
      private final OutputStream fileOutputStream = Files.newOutputStream(tempPath);

      @Override
      public boolean isReady() {
        return true;
      }

      @Override
      public void setWriteListener(WriteListener writeListener) {
      }

      @Override
      public void close() throws IOException {
        fileOutputStream.close();
        super.close();
      }

      @Override
      public void write(int b) throws IOException {
        fileOutputStream.write(b);
      }
    };

    omDbCheckpointServletMock = mock(OMDBCheckpointServletInodeBasedXfer.class);

    BootstrapStateHandler.Lock lock = null;
    if (om != null) {
      lock = new OMDBCheckpointServlet.Lock(om);
    }
    doCallRealMethod().when(omDbCheckpointServletMock).init();
    assertNull(doCallRealMethod().when(omDbCheckpointServletMock).getDbStore());

    requestMock = mock(HttpServletRequest.class);
    // Return current user short name when asked
    when(requestMock.getRemoteUser())
        .thenReturn(UserGroupInformation.getCurrentUser().getShortUserName());
    responseMock = mock(HttpServletResponse.class);

    ServletContext servletContextMock = mock(ServletContext.class);
    when(omDbCheckpointServletMock.getServletContext())
        .thenReturn(servletContextMock);

    when(servletContextMock.getAttribute(OzoneConsts.OM_CONTEXT_ATTRIBUTE))
        .thenReturn(om);
    when(requestMock.getParameter(OZONE_DB_CHECKPOINT_REQUEST_FLUSH))
        .thenReturn("true");

    doCallRealMethod().when(omDbCheckpointServletMock).doGet(requestMock,
        responseMock);
    doCallRealMethod().when(omDbCheckpointServletMock).doPost(requestMock,
        responseMock);

    doCallRealMethod().when(omDbCheckpointServletMock)
        .writeDbDataToStream(any(), any(), any(), any(), any());
    doCallRealMethod().when(omDbCheckpointServletMock)
        .writeDBToArchive(any(), any(), any(), any(), any(), any(), anyBoolean());

    when(omDbCheckpointServletMock.getBootstrapStateLock())
        .thenReturn(lock);
    doCallRealMethod().when(omDbCheckpointServletMock).getCheckpoint(any(), anyBoolean());
    assertNull(doCallRealMethod().when(omDbCheckpointServletMock).getBootstrapTempData());
    doCallRealMethod().when(omDbCheckpointServletMock).getSnapshotDirs(any());
    doCallRealMethod().when(omDbCheckpointServletMock).
        processMetadataSnapshotRequest(any(), any(), anyBoolean(), anyBoolean());
    doCallRealMethod().when(omDbCheckpointServletMock).writeDbDataToStream(any(), any(), any(), any());
    // … 省略 3 行
```

**`write`**

```java
@Override
      public void write(int b) throws IOException {
        fileOutputStream.write(b);
      }
```

**`isReady`**

```java
@Override
      public boolean isReady() {
        return true;
      }
```

**`setWriteListener`**

```java
@Override
      public void setWriteListener(WriteListener writeListener) {
      }
```

**`close`**

```java
@Override
      public void close() throws IOException {
        fileOutputStream.close();
        super.close();
      }
```

**`init`**

```java
@BeforeEach
  void init() throws Exception {
    conf = new OzoneConfiguration();
    // ensure cache entries are not evicted thereby snapshot db's are not closed
    conf.setTimeDuration(OMConfigKeys.OZONE_OM_SNAPSHOT_CACHE_CLEANUP_SERVICE_RUN_INTERVAL,
        100, TimeUnit.MINUTES);
  }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-060  ·  MethodSource

**项目** `Hive`  **文件** `hive/ql/src/test/org/apache/hadoop/hive/ql/io/parquet/serde/TestParquetTimestampsHive2Compatibility.java`  **测试** `testWriteHive2ReadHive4UsingLegacyConversionWithJulianLeapYears`

### Test method

```java
@ParameterizedTest(name = "{0}")
  @MethodSource("generateTimestampsAndZoneIds")
  void testWriteHive2ReadHive4UsingLegacyConversionWithJulianLeapYears(String timestampString, String zoneId) {
    TimeZone original = TimeZone.getDefault();
    try {
      TimeZone.setDefault(TimeZone.getTimeZone(zoneId));
      NanoTime nt = writeHive2(timestampString);
      Timestamp ts = readHive4(nt, zoneId, true);
      assertEquals(timestampString, ts.toString());
    } finally {
      TimeZone.setDefault(original);
    }
  }
```

### Parameter provider — 同文件内的 `generateTimestampsAndZoneIds`

```java
  private static Stream<Arguments> generateTimestampsAndZoneIds() {
    return generateJulianLeapYearTimestamps().flatMap(
        timestampString -> Stream.of("Asia/Singapore", "Pacific/Kiritimati", "Etc/GMT+12", "Pacific/Niue")
            .map(zoneId -> Arguments.of(timestampString, zoneId)));
  }
```

### Test-side helpers called by this test (4)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`writeHive2`**

```java
  private static NanoTime writeHive2(String str) {
    java.sql.Timestamp ts = toTimestampHive2(str);
    Calendar calendar = Calendar.getInstance(TimeZone.getTimeZone(ZoneId.of("GMT")));
    calendar.setTime(ts);
    int year = calendar.get(Calendar.YEAR);
    if (calendar.get(Calendar.ERA) == GregorianCalendar.BC) {
      year = 1 - year;
    }
    JulianDate jDateTime = JulianDate.of(year, calendar.get(Calendar.MONTH) + 1,  //java calendar index starting at 1.
        calendar.get(Calendar.DAY_OF_MONTH), 0, 0, 0, 0);
    int days = jDateTime.getJulianDayNumber();

    long hour = calendar.get(Calendar.HOUR_OF_DAY);
    long minute = calendar.get(Calendar.MINUTE);
    long second = calendar.get(Calendar.SECOND);
    long nanos = ts.getNanos();
    long nanosOfDay = nanos + NANOS_PER_SECOND * second + NANOS_PER_MINUTE * minute + NANOS_PER_HOUR * hour;

    return new NanoTime(days, nanosOfDay);
  }
```

**`readHive4`**

```java
  private static Timestamp readHive4(NanoTime nt, String targetZone, boolean legacyConversion) {
    return NanoTimeUtils.getTimestamp(nt, ZoneId.of(targetZone), legacyConversion);
  }
```

**`toTimestampHive2`**

```java
  private static java.sql.Timestamp toTimestampHive2(String s) {
    java.sql.Timestamp result;
    s = s.trim();

    // Throw away extra if more than 9 decimal places
    int periodIdx = s.indexOf(".");
    if (periodIdx != -1) {
      if (s.length() - periodIdx > 9) {
        s = s.substring(0, periodIdx + 10);
      }
    }
    if (s.indexOf(' ') < 0) {
      s = s.concat(" 00:00:00");
    }
    try {
      result = java.sql.Timestamp.valueOf(s);
    } catch (IllegalArgumentException e) {
      result = null;
    }
    return result;
  }
```

**`get`**

```java
@Override
      public String get() {
        StringBuilder sb = new StringBuilder(29);
        int year = (i % 9999) + 1;
        sb.append(zeros(4 - digits(year)));
        sb.append(year);
        sb.append('-');
        int month = (i % 12) + 1;
        sb.append(zeros(2 - digits(month)));
        sb.append(month);
        sb.append('-');
        int day = (i % 28) + 1;
        sb.append(zeros(2 - digits(day)));
        sb.append(day);
        sb.append(' ');
        int hour = i % 24;
        sb.append(zeros(2 - digits(hour)));
        sb.append(hour);
        sb.append(':');
        int minute = i % 60;
        sb.append(zeros(2 - digits(minute)));
        sb.append(minute);
        sb.append(':');
        int second = i % 60;
        sb.append(zeros(2 - digits(second)));
        sb.append(second);
        sb.append('.');
        // Bitwise OR with one to avoid times with trailing zeros
        int nano = (i % 1000000000) | 1;
        sb.append(zeros(9 - digits(nano)));
        sb.append(nano);
        i++;
        return sb.toString();
      }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-063  ·  CsvSource

**项目** `POI`  **文件** `poi/poi-scratchpad/src/test/java/org/apache/poi/hwpf/converter/TestWordToHtmlConverter.java`  **测试** `testFile`

### Test method

```java
@ParameterizedTest
    @CsvSource({
        "AIOOB-Tap.doc, <table class=\"t1\">",
        "Bug33519.doc, " +
            "\u041F\u043B\u0430\u043D\u0438\u043D\u0441\u043A\u0438 \u0442\u0443\u0440\u043E\u0432\u0435|" +
            "\u042F\u0432\u043E\u0440 \u0410\u0441\u0435\u043D\u043E\u0432",
        "Bug46610_2.doc, 012345678911234567892123456789312345678941234567890123456789112345678921234567893123456789412345678",
        "Bug46817.doc, <table class=\"t1\">",
        "Bug47286.doc, " +
            "!FORMTEXT|" +
            "color:#4f6228;|" +
            "Passport No and the date of expire|" +
            "mfa.gov.cy",
        "Bug48075.doc, \u041F\u0440\u0438\u043B\u043E\u0436\u0435\u043D\u0438\u0435 \u21162",
        "innertable.doc, <span>A</span>",
        "o_kurs.doc, \u0412\u0441\u0435 \u0441\u0442\u0440\u0430\u043D\u0438\u0446\u044B \u043D\u0443\u043C\u0435\u0440\u0443\u044E\u0442\u0441\u044F",
        "Bug52583.doc, <select><option selected>riri</option><option>fifi</option><option>loulou</option></select>",
        "Bug53182.doc, !italic",
        "documentProperties.doc, " +
            "<title>This is document title</title>|" +
            "<meta content=\"This is document keywords\" name=\"keywords\">",
        // email hyperlink
        "Bug47286.doc, provisastpet@mfa.gov.cy",
        "endingnote.doc, " +
            "<a class=\"a1 endnoteanchor\" href=\"#endnote_1\" name=\"endnote_back_1\">1</a>|" +
            "<a class=\"a1 endnoteindex\" href=\"#endnote_back_1\" name=\"endnote_1\">1</a><span|" +
            "Ending note text",
        "equation.doc, <!--Image link to '0.emf' can be here-->",
        "hyperlink.doc, " +
            "<span>Before text; </span><a |" +
            "<a href=\"http://testuri.org/\"><span class=\"s1\">Hyperlink text</span></a>|" +
            "</a><span>; after text</span>",
        "lists-margins.doc, " +
            ".s1{display: inline-block; text-indent: 0; min-width: 0.4861111in;}|" +
            ".s2{display: inline-block; text-indent: 0; min-width: 0.23055555in;}|" +
            ".s3{display: inline-block; text-indent: 0; min-width: 0.28541666in;}|" +
            ".s4{display: inline-block; text-indent: 0; min-width: 0.28333333in;}|" +
            ".p4{text-indent:-0.59652776in;margin-left:-0.70069444in;",
        "pageref.doc, " +
            "<a href=\"#userref\">|" +
            "<a name=\"userref\">|" +
            "1",
        "table-merges.doc, " +
            "<td class=\"td1\" colspan=\"3\">|" +
            "<td class=\"td2\" colspan=\"2\">",
        "52420.doc, " +
            "!FORMTEXT|" +
            "\u0417\u0410\u0414\u0410\u041d\u0418\u0415|" +
            "\u041f\u0440\u0435\u043f\u043e\u0434\u0430\u0432\u0430\u0442\u0435\u043b\u044c",
        "picture.doc, " +
            "src=\"0.emf\"|" +
            "width:3.1293333in;height:1.7247736in;|" +
            "left:-0.09433333;top:-0.2573611;|" +
            "width:3.4125in;height:2.3253334in;",
        "pictures_escher.doc, " +
            "<img src=\"s0.PNG\">|" +
            "<img src=\"s808.PNG\">",
        "bug65255.doc, meta content=\"王久君\""
    })
    void testFile(String file, String contains) throws Exception {
        boolean emulatePictureStorage = !file.contains("equation");

        String result = getHtmlText(file, emulatePictureStorage);
        assertNotNull(result);
        // starting with JDK 9 such unimportant whitespaces may be trimmed
        result = result.replace("</a> <span", "</a><span");

        for (String match : contains.split("\\|")) {
            if (match.startsWith("!")) {
                assertNotContained(result, match.substring(1));
            } else {
                assertContains(result, match);
            }
        }
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`getHtmlText`**

```java
    private static String getHtmlText(final String sampleFileName, boolean emulatePictureStorage) throws Exception {
        Document newDocument = XMLHelper.newDocumentBuilder().newDocument();
        WordToHtmlConverter wordToHtmlConverter = new WordToHtmlConverter(newDocument);

        try (HWPFDocument hwpfDocument = new HWPFDocument(SAMPLES.openResourceAsStream(sampleFileName))) {
            if (emulatePictureStorage) {
                wordToHtmlConverter.setPicturesManager((content, pictureType, suggestedName, widthInches, heightInches) -> suggestedName);
            }

            wordToHtmlConverter.processDocument(hwpfDocument);

            StringWriter stringWriter = new StringWriter();

            Transformer transformer = XMLHelper.newTransformer();
            transformer.setOutputProperty(OutputKeys.METHOD, "html");
            transformer.transform(
                new DOMSource(wordToHtmlConverter.getDocument()),
                new StreamResult(stringWriter));

            return stringWriter.toString();
        }
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-066  ·  MethodSource

**项目** `Calcite`  **文件** `calcite/testkit/src/main/java/org/apache/calcite/test/SqlOperatorTest.java`  **测试** `testCastDecimalToDoubleToInteger`

### Test method

```java
@ParameterizedTest
  @MethodSource("safeParameters")
  void testCastDecimalToDoubleToInteger(CastType castType, SqlOperatorFixture f) {
    f.setFor(SqlStdOperatorTable.CAST, VmName.EXPAND);

    f.checkScalar("cast( cast(1.25 as double) as integer)", 1, "INTEGER NOT NULL");
    f.checkScalar("cast( cast(-1.25 as double) as integer)", -1, "INTEGER NOT NULL");
    f.checkScalar("cast( cast(1.75 as double) as integer)", 1, "INTEGER NOT NULL");
    f.checkScalar("cast( cast(-1.75 as double) as integer)", -1, "INTEGER NOT NULL");
    f.checkScalar("cast( cast(1.5 as double) as integer)", 1, "INTEGER NOT NULL");
    f.checkScalar("cast( cast(-1.5 as double) as integer)", -1, "INTEGER NOT NULL");
  }
```

### Parameter provider — 同文件内的 `safeParameters`

```java
@SuppressWarnings("unused")
  private Stream<Arguments> safeParameters() {
    SqlOperatorFixture f = fixture();
    SqlOperatorFixture f2 =
        SqlOperatorFixtures.safeCastWrapper(f.withLibrary(SqlLibrary.BIG_QUERY), "SAFE_CAST");
    SqlOperatorFixture f3 =
        SqlOperatorFixtures.safeCastWrapper(f.withLibrary(SqlLibrary.MSSQL), "TRY_CAST");
    return Stream.of(
        () -> new Object[] {CastType.CAST, f},
        () -> new Object[] {CastType.SAFE_CAST, f2},
        () -> new Object[] {CastType.TRY_CAST, f3});
  }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-069  ·  ValueSource

**项目** `Maven`  **文件** `maven/impl/maven-core/src/test/java/org/apache/maven/graph/FilteredProjectDependencyGraphTest.java`  **测试** `downstreamProjectsShouldBeCached`

### Test method

```java
@ParameterizedTest
    @ValueSource(booleans = {true, false})
    void downstreamProjectsShouldBeCached(boolean transitive) {
        FilteredProjectDependencyGraph graph =
                new FilteredProjectDependencyGraph(projectDependencyGraph, List.of(aProject));

        when(projectDependencyGraph.getDownstreamProjects(bProject, transitive)).thenReturn(List.of(cProject));

        graph.getDownstreamProjects(bProject, transitive);
        graph.getDownstreamProjects(bProject, transitive);

        verify(projectDependencyGraph).getDownstreamProjects(bProject, transitive);
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-072  ·  ValueSource

**项目** `JAMES`  **文件** `james-project/server/protocols/webadmin/webadmin-mailbox/src/test/java/org/apache/james/webadmin/routes/DomainQuotaRoutesNoVirtualHostingTest.java`  **测试** `allDeleteEndpointsShouldReturnNotAllowed`

### Test method

```java
@ParameterizedTest
    @ValueSource(strings = {
        QUOTA_DOMAINS + "/" + FOUND_LOCAL + "/" + COUNT,
        QUOTA_DOMAINS + "/" + FOUND_LOCAL + "/" + SIZE })
    void allDeleteEndpointsShouldReturnNotAllowed(String endpoint) {
        given()
            .delete(endpoint)
        .then()
            .statusCode(HttpStatus.METHOD_NOT_ALLOWED_405);
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-075  ·  MethodSource

**项目** `Commons-Compress`  **文件** `commons-compress/src/test/java/org/apache/commons/compress/changes/ChangeSetRawTypesTest.java`  **测试** `testDeletePlusAddSame`

### Test method

```java
@ParameterizedTest
    @MethodSource("org.apache.commons.compress.changes.TestFixtures#getOutputArchiveNames")
    @SuppressWarnings({ "unchecked", "rawtypes" })
    void testDeletePlusAddSame(final String archiverName) throws Exception {
        final Path inputPath = createArchive(archiverName);
        final File testTxt = getFile("test.txt");
        final Path result = Files.createTempFile("test", "." + archiverName);
        try {
            try (InputStream inputStream = Files.newInputStream(inputPath);
                    ArchiveInputStream archiveInputStream = factory.createArchiveInputStream(archiverName, inputStream);
                    OutputStream newOutputStream = Files.newOutputStream(result);
                    ArchiveOutputStream archiveOutputStream = factory.createArchiveOutputStream(archiverName, newOutputStream);
                    InputStream csInputStream = Files.newInputStream(testTxt.toPath())) {
                setLongFileMode(archiveOutputStream);
                final ChangeSet changes = new ChangeSet();
                changes.delete("test/test3.xml");
                archiveListDelete("test/test3.xml");
                // Add a file
                final ArchiveEntry entry = archiveOutputStream.createArchiveEntry(testTxt, "test/test3.xml");
                changes.add(entry, csInputStream);
                archiveList.add("test/test3.xml");
                new ChangeSetPerformer(changes).perform(archiveInputStream, archiveOutputStream);
            }
            // Checks
            try (BufferedInputStream buf = new BufferedInputStream(Files.newInputStream(result));
                    ArchiveInputStream in = factory.createArchiveInputStream(buf)) {
                final File check = checkArchiveContent(in, archiveList, false);
                final File test3xml = new File(check, "result/test/test3.xml");
                assertEquals(testTxt.length(), test3xml.length());

                try (BufferedReader reader = new BufferedReader(Files.newBufferedReader(test3xml.toPath()))) {
                    String str;
                    while ((str = reader.readLine()) != null) {
                        // All lines look like this
                        "111111111111111111111111111000101011".equals(str);
                    }
                }
                forceDelete(check);
            }
        } finally {
            forceDelete(result);
        }
    }
```

### Parameter provider — `TestFixtures#getOutputArchiveNames`（commons-compress/src/test/java/org/apache/commons/compress/changes/TestFixtures.java）

```java
    static Set<String> getOutputArchiveNames() {
        final Set<String> outputStreamArchiveNames = ArchiveStreamFactory.DEFAULT.getOutputStreamArchiveNames();
        outputStreamArchiveNames.remove(ArchiveStreamFactory.AR); // TODO BUG?
        outputStreamArchiveNames.remove(ArchiveStreamFactory.SEVEN_Z); // TODO Does not support streaming.
        return outputStreamArchiveNames;
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`archiveListDelete`**

```java
    private void archiveListDelete(final String prefix) {
        archiveList.removeIf(entry -> entry.equals(prefix));
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-078  ·  MethodSource

**项目** `Druid`  **文件** `druid/sql/src/test/java/org/apache/druid/sql/calcite/CalciteJoinQueryTest.java`  **测试** `testInnerJoinOnTwoInlineDataSourcesWithOuterWhere_withLeftDirectAccess`

### Test method

```java
@DecoupledTestConfig(quidemReason = QuidemTestCaseReason.JOIN_LEFT_DIRECT_ACCESS)
  @MethodSource("provideQueryContexts")
  @ParameterizedTest(name = "{0}")
  public void testInnerJoinOnTwoInlineDataSourcesWithOuterWhere_withLeftDirectAccess(Map<String, Object> queryContext)
  {
    queryContext = withLeftDirectAccessEnabled(queryContext);
    testQuery(
        "with abc as\n"
        + "(\n"
        + "  SELECT dim1, \"__time\", m1 from foo WHERE \"dim1\" = '10.1'\n"
        + ")\n"
        + "SELECT t1.dim1, t1.\"__time\" from abc as t1 INNER JOIN abc as t2 on t1.dim1 = t2.dim1 WHERE t1.dim1 = '10.1'\n",
        queryContext,
        ImmutableList.of(
            newScanQueryBuilder()
                .dataSource(
                    join(
                        new TableDataSource(CalciteTests.DATASOURCE1),
                        new QueryDataSource(
                            newScanQueryBuilder()
                                .dataSource(CalciteTests.DATASOURCE1)
                                .intervals(querySegmentSpec(Filtration.eternity()))
                                .filters(equality("dim1", "10.1", ColumnType.STRING))
                                .columns(ImmutableList.of("dim1"))
                                .columnTypes(ColumnType.STRING)
                                .resultFormat(ScanQuery.ResultFormat.RESULT_FORMAT_COMPACTED_LIST)
                                .context(queryContext)
                                .build()
                        ),
                        "j0.",
                        equalsCondition(
                            makeExpression("'10.1'"),
                            makeColumnExpression("j0.dim1")
                        ),
                        JoinType.INNER,
                        equality("dim1", "10.1", ColumnType.STRING)
                    )
                )
                .intervals(querySegmentSpec(Filtration.eternity()))
                .virtualColumns(expressionVirtualColumn("v0", "\'10.1\'", ColumnType.STRING))
                .columns("v0", "__time")
                .columnTypes(ColumnType.STRING, ColumnType.LONG)
                .context(queryContext)
                .build()
        ),
        ImmutableList.of(
            new Object[]{"10.1", 946771200000L}
        )
    );
  }
```

### Parameter provider — `provideQueryContexts`（druid/sql/src/test/java/org/apache/druid/sql/calcite/BaseCalciteQueryTest.java）

```java
  public static Object[] provideQueryContexts()
  {
    return new Object[] {
        // default behavior
        Named.of("default", QUERY_CONTEXT_DEFAULT),
        // all rewrites enabled
        Named.of("all_enabled", new ImmutableMap.Builder<String, Object>()
            .putAll(QUERY_CONTEXT_DEFAULT)
            .put(QueryContexts.JOIN_FILTER_REWRITE_VALUE_COLUMN_FILTERS_ENABLE_KEY, true)
            .put(QueryContexts.JOIN_FILTER_REWRITE_ENABLE_KEY, true)
            .put(QueryContexts.REWRITE_JOIN_TO_FILTER_ENABLE_KEY, true)
            .build()),
        // filter-on-value-column rewrites disabled, everything else enabled
        Named.of("filter-on-value-column_disabled", new ImmutableMap.Builder<String, Object>()
            .putAll(QUERY_CONTEXT_DEFAULT)
            .put(QueryContexts.JOIN_FILTER_REWRITE_VALUE_COLUMN_FILTERS_ENABLE_KEY, false)
            .put(QueryContexts.JOIN_FILTER_REWRITE_ENABLE_KEY, true)
            .put(QueryContexts.REWRITE_JOIN_TO_FILTER_ENABLE_KEY, true)
            .build()),
        // filter rewrites fully disabled, join-to-filter enabled
        Named.of("join-to-filter", new ImmutableMap.Builder<String, Object>()
            .putAll(QUERY_CONTEXT_DEFAULT)
            .put(QueryContexts.JOIN_FILTER_REWRITE_VALUE_COLUMN_FILTERS_ENABLE_KEY, false)
            .put(QueryContexts.JOIN_FILTER_REWRITE_ENABLE_KEY, false)
            .put(QueryContexts.REWRITE_JOIN_TO_FILTER_ENABLE_KEY, true)
            .build()),
        // filter rewrites disabled, but value column filters still set to true
        // (it should be ignored and this should
        // behave the same as the previous context)
        Named.of("filter-rewrites-disabled", new ImmutableMap.Builder<String, Object>()
            .putAll(QUERY_CONTEXT_DEFAULT)
            .put(QueryContexts.JOIN_FILTER_REWRITE_VALUE_COLUMN_FILTERS_ENABLE_KEY, true)
            .put(QueryContexts.JOIN_FILTER_REWRITE_ENABLE_KEY, false)
            .put(QueryContexts.REWRITE_JOIN_TO_FILTER_ENABLE_KEY, true)
            .build()),
        // filter rewrites fully enabled, join-to-filter disabled
        Named.of("filter-rewrites", new ImmutableMap.Builder<String, Object>()
            .putAll(QUERY_CONTEXT_DEFAULT)
            .put(QueryContexts.JOIN_FILTER_REWRITE_VALUE_COLUMN_FILTERS_ENABLE_KEY, true)
            .put(QueryContexts.JOIN_FILTER_REWRITE_ENABLE_KEY, true)
            .put(QueryContexts.REWRITE_JOIN_TO_FILTER_ENABLE_KEY, false)
            .build()),
        // all rewrites disabled
        Named.of("all_disabled", new ImmutableMap.Builder<String, Object>()
            .putAll(QUERY_CONTEXT_DEFAULT)
            .put(QueryContexts.JOIN_FILTER_REWRITE_VALUE_COLUMN_FILTERS_ENABLE_KEY, false)
            .put(QueryContexts.JOIN_FILTER_REWRITE_ENABLE_KEY, false)
            .put(QueryContexts.REWRITE_JOIN_TO_FILTER_ENABLE_KEY, false)
            .build()),
    };
  }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-081  ·  ValueSource

**项目** `SeaTunnel`  **文件** `seatunnel/seatunnel-connectors-v2/connector-fake/src/test/java/org/apache/seatunnel/connectors/seatunnel/fake/source/FakeDataGeneratorTest.java`  **测试** `testAutoIncrementId`

### Test method

```java
@ParameterizedTest
    @ValueSource(strings = {"fake-auto-increment-id.conf", "fake-auto-increment-id.conf"})
    public void testAutoIncrementId(String conf) throws FileNotFoundException, URISyntaxException {
        ReadonlyConfig testConfig = getTestConfigFile(conf);
        int parallelism = testConfig.getOptional(EnvCommonOptions.PARALLELISM).orElse(1);
        FakeConfig fakeConfig = FakeConfig.buildWithConfig(testConfig);
        List<CompletableFuture<List<SeaTunnelRow>>> futures = new ArrayList<>();
        String jobId = UUID.randomUUID().toString();
        for (int i = 0; i < parallelism; i++) {
            CompletableFuture<List<SeaTunnelRow>> uCompletableFuture =
                    CompletableFuture.supplyAsync(
                            () -> {
                                FakeDataGenerator fakeDataGenerator =
                                        new FakeDataGenerator(fakeConfig, jobId);
                                return fakeDataGenerator.generateFakedRows(fakeConfig.getRowNum());
                            });
            futures.add(uCompletableFuture);
        }
        CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]));
        List<SeaTunnelRow> seaTunnelRows =
                futures.stream()
                        .map(CompletableFuture::join)
                        .flatMap(List::stream)
                        .collect(Collectors.toList());
        List<Integer> ids =
                seaTunnelRows.stream()
                        .map(seaTunnelRow -> (int) seaTunnelRow.getField(0))
                        .distinct()
                        .sorted(Integer::compareTo)
                        .collect(Collectors.toList());
        Assertions.assertEquals(200, ids.size());
        ids.stream().min(Integer::compareTo).ifPresent(min -> Assertions.assertEquals(100, min));
        ids.stream().max(Integer::compareTo).ifPresent(max -> Assertions.assertEquals(299, max));
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`getTestConfigFile`**

```java
    private ReadonlyConfig getTestConfigFile(String configFile)
            throws FileNotFoundException, URISyntaxException {
        if (!configFile.startsWith("/")) {
            configFile = "/" + configFile;
        }
        URL resource = FakeDataGeneratorTest.class.getResource(configFile);
        if (resource == null) {
            throw new FileNotFoundException("Can't find config file: " + configFile);
        }
        String path = Paths.get(resource.toURI()).toString();
        Config config = ConfigFactory.parseFile(new File(path));
        assert config.hasPath("FakeSource");
        return ReadonlyConfig.fromConfig(config.getConfig("FakeSource"));
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-084  ·  MethodSource

**项目** `Commons-CSV`  **文件** `commons-csv/src/test/java/org/apache/commons/csv/CSVDuplicateHeaderTest.java`  **测试** `testCSVFormat`

### Test method

```java
@ParameterizedTest
    @MethodSource(value = {"duplicateHeaderAllowsMissingColumnsNamesData"})
    void testCSVFormat(final DuplicateHeaderMode duplicateHeaderMode,
                              final boolean allowMissingColumnNames,
                              final boolean ignoreHeaderCase,
                              final String[] headers,
                              final boolean valid) {
        final CSVFormat.Builder builder =
            CSVFormat.DEFAULT.builder()
                             .setDuplicateHeaderMode(duplicateHeaderMode)
                             .setAllowMissingColumnNames(allowMissingColumnNames)
                             .setIgnoreHeaderCase(ignoreHeaderCase)
                             .setHeader(headers);
        if (valid) {
            final CSVFormat format = builder.get();
            Assertions.assertEquals(duplicateHeaderMode, format.getDuplicateHeaderMode(), "DuplicateHeaderMode");
            Assertions.assertEquals(allowMissingColumnNames, format.getAllowMissingColumnNames(), "AllowMissingColumnNames");
            Assertions.assertArrayEquals(headers, format.getHeader(), "Header");
        } else {
            Assertions.assertThrows(IllegalArgumentException.class, builder::get);
        }
    }
```

### Parameter provider — 同文件内的 `duplicateHeaderAllowsMissingColumnsNamesData`

```java
    static Stream<Arguments> duplicateHeaderAllowsMissingColumnsNamesData() {
        return duplicateHeaderData()
            .filter(arg -> Boolean.TRUE.equals(arg.get()[1]) && Boolean.FALSE.equals(arg.get()[2]))
            .flatMap(arg -> {
                // Return test case with flags as all true/false combinations
                final Object[][] data = new Object[4][];
                final Boolean[] flags = {Boolean.TRUE, Boolean.FALSE};
                int i = 0;
                for (final Boolean a : flags) {
                    for (final Boolean b : flags) {
                        data[i] = arg.get().clone();
                        data[i][1] = a;
                        data[i][2] = b;
                        i++;
                    }
                }
                return Arrays.stream(data).map(Arguments::of);
            });
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-087  ·  EnumSource

**项目** `Avro`  **文件** `avro/lang/java/avro/src/test/java/org/apache/avro/TestReadingWritingDataInEvolvedSchemas.java`  **测试** `longWrittenWithUnionSchemaIsConvertedToLongFloatUnionSchema`

### Test method

```java
@ParameterizedTest
  @EnumSource(EncoderType.class)
  void longWrittenWithUnionSchemaIsConvertedToLongFloatUnionSchema(EncoderType encoderType) throws Exception {
    Schema writer = UNION_LONG_RECORD;
    Record record = defaultRecordWithSchema(writer, FIELD_A, 42L);
    byte[] encoded = encodeGenericBlob(record, encoderType);
    Record decoded = decodeGenericBlob(UNION_LONG_FLOAT_RECORD, writer, encoded, encoderType);
    assertEquals(42L, decoded.get(FIELD_A));
  }
```

### Enum declaration — `EncoderType` (avro/lang/java/avro/src/test/java/org/apache/avro/TestReadingWritingDataInEvolvedSchemas.java)

```java
  enum EncoderType {
    BINARY, JSON
  }
```

### Test-side helpers called by this test (3)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`defaultRecordWithSchema`**

```java
  private <T> Record defaultRecordWithSchema(Schema schema, String key, T value) {
    Record data = new GenericData.Record(schema);
    data.put(key, value);
    return data;
  }
```

**`encodeGenericBlob`**

```java
  private byte[] encodeGenericBlob(GenericRecord data, EncoderType encoderType) throws IOException {
    DatumWriter<GenericRecord> writer = new GenericDatumWriter<>(data.getSchema());
    ByteArrayOutputStream outStream = new ByteArrayOutputStream();
    Encoder encoder = encoderType == EncoderType.BINARY ? EncoderFactory.get().binaryEncoder(outStream, null)
        : EncoderFactory.get().jsonEncoder(data.getSchema(), outStream);
    writer.write(data, encoder);
    encoder.flush();
    outStream.close();
    return outStream.toByteArray();
  }
```

**`decodeGenericBlob`**

```java
  private Record decodeGenericBlob(Schema expectedSchema, Schema schemaOfBlob, byte[] blob, EncoderType encoderType)
      throws IOException {
    if (blob == null) {
      return null;
    }
    GenericData data = new GenericData();
    data.setFastReaderEnabled(true);
    GenericDatumReader<Record> reader = new GenericDatumReader<>(null, null, data);
    reader.setExpected(expectedSchema);
    reader.setSchema(schemaOfBlob);
    Decoder decoder = encoderType == EncoderType.BINARY ? DecoderFactory.get().binaryDecoder(blob, null)
        : DecoderFactory.get().jsonDecoder(schemaOfBlob, new ByteArrayInputStream(blob));
    return reader.read(null, decoder);
  }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-090  ·  MethodSource

**项目** `Directory-Studio`  **文件** `directory-studio/tests/test.integration.ui/src/main/java/org/apache/directory/studio/test/integration/ui/ValueEditorTest.java`  **测试** `testGetStringOrBinaryValue`

### Test method

```java
@ParameterizedTest
    @MethodSource("data")
    public void testGetStringOrBinaryValue( String name, Data data ) throws Exception
    {
        setup( name, data );
        if ( data.expectedStringOrBinaryValue instanceof byte[] )
        {
            assertArrayEquals( ( byte[] ) data.expectedStringOrBinaryValue,
                ( byte[] ) editor.getStringOrBinaryValue( editor.getRawValue( value ) ) );
        }
        else
        {
            assertEquals( data.expectedStringOrBinaryValue,
                editor.getStringOrBinaryValue( editor.getRawValue( value ) ) );
        }
    }
```

### Parameter provider — 同文件内的 `data`

```java
    public static Stream<Arguments> data()
    {
        return Stream.of( new Object[][]
            {
                /*
                 * InPlaceTextValueEditor can handle string values and binary values that can be decoded as UTF-8.
                 */

                {
                    "InPlaceTextValueEditor - empty value",
                    Data.data().valueEditorClass( InPlaceTextValueEditor.class ).attribute( CN )
                        .rawValue( IValue.EMPTY_STRING_VALUE ).expectedRawValue( EMPTY_STRING )
                        .expectedDisplayValue( EMPTY_STRING ).expectedHasValue( true )
                        .expectedStringOrBinaryValue( EMPTY_STRING ) },

                {
                    "InPlaceTextValueEditor - empty string",
                    Data.data().valueEditorClass( InPlaceTextValueEditor.class ).attribute( CN )
                        .rawValue( EMPTY_STRING ).expectedRawValue( EMPTY_STRING ).expectedDisplayValue( EMPTY_STRING )
                        .expectedHasValue( true ).expectedStringOrBinaryValue( EMPTY_STRING ) },

                {
                    "InPlaceTextValueEditor - ascii",
                    Data.data().valueEditorClass( InPlaceTextValueEditor.class ).attribute( CN ).rawValue( ASCII )
                        .expectedRawValue( ASCII ).expectedDisplayValue( ASCII ).expectedHasValue( true )
                        .expectedStringOrBinaryValue( ASCII ) },

                {
                    "InPlaceTextValueEditor - unicode",
                    Data.data().valueEditorClass( InPlaceTextValueEditor.class ).attribute( CN ).rawValue( UNICODE )
                        .expectedRawValue( UNICODE ).expectedDisplayValue( UNICODE ).expectedHasValue( true )
                        .expectedStringOrBinaryValue( UNICODE ) },

                {
                    "InPlaceTextValueEditor - bytearray UTF8",
                    Data.data().valueEditorClass( InPlaceTextValueEditor.class ).attribute( USER_PWD ).rawValue( UTF8 )
                        .expectedRawValue( UNICODE ).expectedDisplayValue( UNICODE ).expectedHasValue( true )
                        .expectedStringOrBinaryValue( UNICODE ) },

                // text editor always tries to decode byte[] as UTF-8, so it can not handle ISO-8859-1 encoded byte[] 
                {
                    "InPlaceTextValueEditor - bytearray ISO-8859-1",
                    Data.data().valueEditorClass( InPlaceTextValueEditor.class ).attribute( USER_PWD )
                        .rawValue( ISO88591 ).expectedRawValue( null ).expectedDisplayValue( IValueEditor.NULL )
                        .expectedHasValue( true ).expectedStringOrBinaryValue( null ) },

                // text editor always tries to decode byte[] as UTF-8, so it can not handle arbitrary byte[] 
                {
                    "InPlaceTextValueEditor - bytearray PNG",
                    Data.data().valueEditorClass( InPlaceTextValueEditor.class ).attribute( USER_PWD ).rawValue( PNG )
                        .expectedRawValue( null ).expectedDisplayValue( IValueEditor.NULL ).expectedHasValue( true )
                        .expectedStringOrBinaryValue( null ) },

                /*
                 * InPlaceBooleanValueEditor can only handle TRUE or FALSE values.
                 */

                {
                    "InPlaceBooleanValueEditor - TRUE",
                    Data.data().valueEditorClass( InPlaceBooleanValueEditor.class ).attribute( CN ).rawValue( TRUE )
                        .expectedRawValue( TRUE ).expectedDisplayValue( TRUE ).expectedHasValue( true )
                        .expectedStringOrBinaryValue( TRUE ) },

                {
                    "InPlaceBooleanValueEditor - FALSE",
                    Data.data().valueEditorClass( InPlaceBooleanValueEditor.class ).attribute( CN ).rawValue( FALSE )
                        .expectedRawValue( FALSE ).expectedDisplayValue( FALSE ).expectedHasValue( true )
                        .expectedStringOrBinaryValue( FALSE ) },

                {
                    "InPlaceBooleanValueEditor - INVALID",
                    Data.data().valueEditorClass( InPlaceBooleanValueEditor.class ).attribute( CN )
                        .rawValue( "invalid" ).expectedRawValue( null ).expectedDisplayValue( IValueEditor.NULL )
                        .expectedHasValue( true ).expectedStringOrBinaryValue( null ) },

                {
                    "InPlaceBooleanValueEditor - bytearray TRUE",
                    Data.data().valueEditorClass( InPlaceBooleanValueEditor.class ).attribute( USER_PWD )
                        .rawValue( TRUE.getBytes( UTF_8 ) ).expectedRawValue( TRUE ).expectedDisplayValue( TRUE )
                        .expectedHasValue( true ).expectedStringOrBinaryValue( TRUE ) },

                {
                    "InPlaceBooleanValueEditor - bytearray FALSE",
                    Data.data().valueEditorClass( InPlaceBooleanValueEditor.class ).attribute( USER_PWD )
                        .rawValue( FALSE.getBytes( UTF_8 ) ).expectedRawValue( FALSE ).expectedDisplayValue( FALSE )
                        .expectedHasValue( true ).expectedStringOrBinaryValue( FALSE ) },

                {
                    "InPlaceBooleanValueEditor - bytearray INVALID",
                    Data.data().valueEditorClass( InPlaceBooleanValueEditor.class ).attribute( USER_PWD )
                        .rawValue( "invalid".getBytes( UTF_8 ) ).expectedRawValue( null )
                        .expectedDisplayValue( IValueEditor.NULL ).expectedHasValue( true )
                        .expectedStringOrBinaryValue( null ) },

                /*
                 * InPlaceOidValueEditor can only handle OIDs
                 */

                {
                    "InPlaceOidValueEditor - numeric OID",
                    Data.data().valueEditorClass( InPlaceOidValueEditor.class ).attribute( CN ).rawValue( NUMERIC_OID )
                        .expectedRawValue( NUMERIC_OID ).expectedDisplayValue( NUMERIC_OID + " (Start TLS)" )
                        .expectedHasValue( true ).expectedStringOrBinaryValue( NUMERIC_OID ) },

                {
                    "InPlaceOidValueEditor - descr OID",
                    Data.data().valueEditorClass( InPlaceOidValueEditor.class ).attribute( CN ).rawValue( DESCR_OID )
                        .expectedRawValue( DESCR_OID ).expectedDisplayValue( DESCR_OID ).expectedHasValue( true )
                        .expectedStringOrBinaryValue( DESCR_OID ) },

                {
                    "InPlaceOidValueEditor - relaxed descr OID",
                    Data.data().valueEditorClass( InPlaceOidValueEditor.class ).attribute( CN )
                        .rawValue( "orclDBEnterpriseRole_82" ).expectedRawValue( "orclDBEnterpriseRole_82" )
                        .expectedDisplayValue( "orclDBEnterpriseRole_82" ).expectedHasValue( true )
                        .expectedStringOrBinaryValue( "orclDBEnterpriseRole_82" ) },

                {
                    "InPlaceOidValueEditor - INVALID",
                    Data.data().valueEditorClass( InPlaceOidValueEditor.class ).attribute( CN ).rawValue( "in valid" )
                        .expectedRawValue( null ).expectedDisplayValue( IValueEditor.NULL ).expectedHasValue( true )
                        .expectedStringOrBinaryValue( null ) },

                {
                    "InPlaceOidValueEditor - bytearray numeric OID",
                    Data.data().valueEditorClass( InPlaceOidValueEditor.class ).attribute( USER_PWD )
                        .rawValue( NUMERIC_OID.getBytes( UTF_8 ) ).expectedRawValue( NUMERIC_OID )
                        .expectedDisplayValue( NUMERIC_OID + " (Start TLS)" ).expectedHasValue( true )
                        .expectedStringOrBinaryValue( NUMERIC_OID ) },

                {
                    "InPlaceOidValueEditor - bytearray INVALID",
                    Data.data().valueEditorClass( InPlaceOidValueEditor.class ).attribute( USER_PWD )
                        .rawValue( "in valid".getBytes( UTF_8 ) ).expectedRawValue( null )
                        .expectedDisplayValue( IValueEditor.NULL ).expectedHasValue( true )
                        .expectedStringOrBinaryValue( null ) },

                /*
                 * TextValueEditor can handle string values and binary values that can be decoded as UTF-8.
                 */

                {
                    "TextValueEditor - empty string value",
                    Data.data().valueEditorClass( TextValueEditor.class ).attribute( CN )
                        .rawValue( IValue.EMPTY_STRING_VALUE ).expectedRawValue( EMPTY_STRING )
                        .expectedDisplayValue( EMPTY_STRING ).expectedHasValue( true )
                        .expectedStringOrBinaryValue( EMPTY_STRING ) },

                {
                    "TextValueEditor - empty string",
                    Data.data().valueEditorClass( TextValueEditor.class ).attribute( CN ).rawValue( EMPTY_STRING )
                        .expectedRawValue( EMPTY_STRING ).expectedDisplayValue( EMPTY_STRING ).expectedHasValue( true )
                        .expectedStringOrBinaryValue( EMPTY_STRING ) },

                {
                    "TextValueEditor - ascii",
                    Data.data().valueEditorClass( TextValueEditor.class ).attribute( CN ).rawValue( ASCII )
                        .expectedRawValue( ASCII ).expectedDisplayValue( ASCII ).expectedHasValue( true )
                        .expectedStringOrBinaryValue( ASCII ) },

    // … 省略 105 行
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`setup`**

```java
    public void setup( String name, Data data ) throws Exception
    {
        IEntry entry = new DummyEntry( new Dn(), new DummyConnection( Schema.DEFAULT_SCHEMA ) );
        IAttribute attribute = new Attribute( entry, data.attribute );
        value = new Value( attribute, data.rawValue );
        editor = data.valueEditorClass.newInstance();
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-093  ·  ValueSource

**项目** `Flink`  **文件** `flink/flink-table/flink-table-planner/src/test/java/org/apache/flink/table/planner/operations/SqlOtherOperationConverterTest.java`  **测试** `testHelpCommands`

### Test method

```java
@ParameterizedTest
    @ValueSource(strings = {"HELP", "HELP;", "HELP ;", "HELP\t;", "HELP\n;"})
    void testHelpCommands(String command) {
        ExtendedParser extendedParser = new ExtendedParser();
        assertThat(extendedParser.parse(command)).get().isInstanceOf(HelpOperation.class);
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-096  ·  ValueSource

**项目** `Rat`  **文件** `creadur-rat/apache-rat-core/src/test/java/org/apache/rat/commandline/ArgTests.java`  **测试** `outputFleNameNoDirectoryTest`

### Test method

```java
@ParameterizedTest(name = "{0}")
    @ValueSource(strings = { "rat.txt", "./rat.txt", "/rat.txt", "target/rat.test" })
    public void outputFleNameNoDirectoryTest(String name) throws ParseException, IOException {
        class OutputFileConfig extends ReportConfiguration  {
            private File actual = null;
            @Override
            public void setOut(File file) {
                actual = file;
            }
        }
        String fileName = name.replace("/", DocumentName.FSInfo.getDefault().dirSeparator());
        File expected = new File(fileName);

        CommandLine commandLine = createCommandLine(new String[] {"--output-file", fileName});
        OutputFileConfig configuration = new OutputFileConfig();
        ArgumentContext ctxt = new ArgumentContext(new File("."), configuration, commandLine);
        Arg.processArgs(ctxt);
        assertThat(configuration.actual.getAbsolutePath()).isEqualTo(expected.getCanonicalPath());
    }
```

### Test-side helpers called by this test (2)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`setOut`**

```java
@Override
            public void setOut(File file) {
                actual = file;
            }
```

**`createCommandLine`**

```java
    private CommandLine createCommandLine(String[] args) throws ParseException {
        Options opts = OptionCollection.buildOptions();
        return DefaultParser.builder().setDeprecatedHandler(DeprecationReporter.getLogReporter())
                .setAllowPartialMatching(true).build().parse(opts, args);
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-099  ·  MethodSource

**项目** `hadoop`  **文件** `hadoop/hadoop-cloud-storage-project/hadoop-tos/src/test/java/org/apache/hadoop/fs/tosfs/object/TestObjectStorage.java`  **测试** `testDeleteNonEmptyDir`

### Test method

```java
@ParameterizedTest
  @MethodSource("provideArguments")
  public void testDeleteNonEmptyDir(ObjectStorage store) throws IOException {
    setEnv(store);
    storage.put("a/", new byte[0]);
    storage.put("a/b/", new byte[0]);
    assertArrayEquals(new byte[0], IOUtils.toByteArray(getStream("a/b/", 0, 256)));

    ListObjectsResponse response = list("a/b/", "a/b/", 100, "/");
    assertEquals(0, response.objects().size());
    assertEquals(0, response.commonPrefixes().size());

    if (!storage.bucket().isDirectory()) {
      // Directory bucket only supports list with delimiter = '/'.
      response = list("a/b/", "a/b/", 100, null);
      assertEquals(0, response.objects().size());
      assertEquals(0, response.commonPrefixes().size());
    }

    storage.delete("a/b/");
    assertNull(storage.head("a/b/"));
    assertNull(storage.head("a/b"));
    assertNotNull(storage.head("a/"));
  }
```

### Parameter provider — 同文件内的 `provideArguments`

```java
  public static Stream<Arguments> provideArguments() {
    assumeTrue(TestEnv.checkTestEnabled());

    List<Arguments> values = new ArrayList<>();
    for (ObjectStorage store : TestUtility.createTestObjectStorage(FILE_STORE_ROOT)) {
      values.add(Arguments.of(store));
    }
    return values.stream();
  }
```

### Test-side helpers called by this test (3)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`setEnv`**

```java
  private void setEnv(ObjectStorage objectStore) {
    this.storage = objectStore;
  }
```

**`getStream`**

```java
  private InputStream getStream(String key) {
    return storage.get(key).stream();
  }
```

**`list`**

```java
  private ListObjectsResponse list(String prefix, String startAfter, int limit, String delimiter) {
    Preconditions.checkArgument(limit <= 1000, "Cannot list more than 1000 objects.");
    ListObjectsRequest request = ListObjectsRequest.builder()
        .prefix(prefix)
        .startAfter(startAfter)
        .maxKeys(limit)
        .delimiter(delimiter)
        .build();
    Iterator<ListObjectsResponse> iterator = storage.list(request).iterator();
    if (iterator.hasNext()) {
      return iterator.next();
    } else {
      return new ListObjectsResponse(new ArrayList<>(), new ArrayList<>());
    }
  }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-102  ·  MethodSource

**项目** `Commons-Statistics`  **文件** `commons-statistics/commons-statistics-descriptive/src/test/java/org/apache/commons/statistics/descriptive/BaseLongStatisticTest.java`  **测试** `testCombineEmpty`

### Test method

```java
@ParameterizedTest
    @MethodSource(value = "testAccept")
    final void testCombineEmpty(long[] values) {
        final S empty = create();
        final S nonEmpty = Statistics.add(create(), values);
        final StatisticResult expected = Statistics.add(create(), values);
        final S result = assertCombine(nonEmpty, empty);
        TestHelper.assertEquals(expected, result, null,
            () -> statisticName + " nonEmpty.combine(empty)");
    }
```

### Parameter provider — 同文件内的 `testAccept`

```java
    final Stream<Arguments> testAccept() {
        return streamSingleArrayData(getToleranceAccept(), StatisticTestData::getTolAccept);
    }
```

### Test-side helpers called by this test (3)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`assertCombine`**

```java
    final S assertCombine(Function<long[], S> constructor,
                          long[][] values, StatisticResult expected, DoubleTolerance tol) {
        int n = values.length;
        Assertions.assertNotEquals(0, n, "No data");
        final List<S> stats = Arrays.stream(values)
            .map(constructor::apply)
            .collect(Collectors.toList());
        List<S> stats2;
        // If the combine is symmetric we perform the same algorithm
        // but swap a+b to b+a at each step.
        if (isCombineSymmetric()) {
            stats2 = Arrays.stream(values)
                .map(constructor::apply)
                .collect(Collectors.toList());
        } else {
            stats2 = Collections.emptyList();
        }
        while (n != 1) {
            // Process pairs (ending at an even size)
            final int end = n & ~1;
            for (int i = 0; i < end; i += 2) {
                final int target = i >> 1;
                final int lhs = i;
                final int rhs = i + 1;
                combine(stats, stats2, target, lhs, rhs);
            }
            // final value
            if (end != n) {
                // Merging with the previous pair will make the the end statistic
                // progressively larger than the others. However the final merge should
                // be limited to below a 1:2 ratio.
                // Note: Set up the indices and copy the above code.
                final int target = (n >> 1) - 1;
                final int lhs = target;
                final int rhs = end;
                combine(stats, stats2, target, lhs, rhs);
            }
            n >>= 1;
        }
        final S stat = stats.get(0);
        TestHelper.assertEquals(expected, stat, tol, () -> statisticName + ": " + format(values));
        return stat;
    }
```

**`combine`**

```java
    private void combine(final List<S> stats, List<S> stats2, int target, int lhs, int rhs) {
        final S s1 = assertCombine(stats.get(lhs), stats.get(rhs));
        stats.set(target, s1);
        if (isCombineSymmetric()) {
            final S s2 = assertCombine(stats2.get(rhs), stats2.get(lhs));
            TestHelper.assertEquals(s1, s2, null,
                () -> statisticName + ": Non-symmetric combine");
            stats2.set(target, s2);
        }
    }
```

**`format`**

```java
    static String format(long[] values) {
        if (values.length > MAX_FORMAT_VALUES) {
            return Arrays.stream(values)
                         .limit(MAX_FORMAT_VALUES)
                         .mapToObj(Long::toString)
                         .collect(Collectors.joining(", ", "[", ", ...]"));
        }
        return Arrays.toString(values);
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-105  ·  MethodSource

**项目** `Zeppelin`  **文件** `zeppelin/elasticsearch/src/test/java/org/apache/zeppelin/elasticsearch/ElasticsearchInterpreterTest.java`  **测试** `testMisc`

### Test method

```java
@ParameterizedTest
  @MethodSource("provideInterpreter")
  void testMisc(ElasticsearchInterpreter interpreter) {
    InterpreterResult res = interpreter.interpret(null, null);
    assertEquals(Code.SUCCESS, res.code());

    res = interpreter.interpret("   \n \n ", null);
    assertEquals(Code.SUCCESS, res.code());
  }
```

### Parameter provider — 同文件内的 `provideInterpreter`

```java
  private static Stream<Arguments> provideInterpreter() {
    return Stream.of(
      Arguments.of(transportInterpreter),
      Arguments.of(httpInterpreter));
  }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-108  ·  EnumSource

**项目** `ZooKeeper`  **文件** `zookeeper/zookeeper-server/src/test/java/org/apache/zookeeper/server/quorum/LearnerSyncThrottlerTest.java`  **测试** `testTryWithResourceThrottle`

### Test method

```java
@ParameterizedTest
    @EnumSource(LearnerSyncThrottler.SyncType.class)
    public void testTryWithResourceThrottle(LearnerSyncThrottler.SyncType syncType) throws Exception {
        LearnerSyncThrottler throttler = new LearnerSyncThrottler(1, syncType);
        try {
            throttler.beginSync(true);
            try {
                throttler.beginSync(false);
                fail("shouldn't be able to have both syncs open");
            } catch (SyncThrottleException e) {
            }
            throttler.endSync();
        } catch (SyncThrottleException e) {
            fail("First sync shouldn't be throttled");
        }
    }
```

### Enum declaration — `SyncType` (zookeeper/zookeeper-server/src/main/java/org/apache/zookeeper/server/quorum/LearnerSyncThrottler.java)

```java
    public enum SyncType {
        DIFF,
        SNAP
    }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-111  ·  CsvSource

**项目** `Fineract`  **文件** `fineract/fineract-core/src/test/java/org/apache/fineract/util/LoopGuardTest.java`  **测试** `testSafeWhileLoopExecutesCorrectly`

### Test method

```java
@ParameterizedTest
    // target value, max iterations
    @CsvSource({ "2, 5", //
            "4, 5", //
            "6, 10", //
            "2, 2" //
    })
    void testSafeWhileLoopExecutesCorrectly(int targetValue, int maxIterations) {
        TestContext context = new TestContext();

        Predicate<TestContext> condition = ctx -> ctx.iteration < targetValue;
        LoopGuard.LoopBody<TestContext> body = ctx -> ctx.iteration++;

        LoopGuard.runSafeWhileLoop(maxIterations, context, condition, body);

        Assertions.assertEquals(targetValue, context.iteration);
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-114  ·  ValueSource

**项目** `ORC`  **文件** `orc/java/mapreduce/src/test/org/apache/orc/mapred/TestOrcFileEvolution.java`  **测试** `testPreHive4243AddColumnWithFix`

### Test method

```java
@ParameterizedTest
  @ValueSource(booleans = {true, false})
  public void testPreHive4243AddColumnWithFix(boolean addSarg) {
    checkEvolution("struct<_col0:int,_col1:string>",
                   "struct<a:int,b:string,c:double>",
                   struct(1, "foo"),
                   struct(1, "foo", null), true, addSarg, false);
  }
```

### Test-side helpers called by this test (3)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`checkEvolution`**

```java
  private void checkEvolution(String writerType, String readerType,
                              Object inputRow, Object expectedOutput,
                              boolean tolerateSchema, boolean addSarg,
                              boolean positional) {
    SearchArgument sArg = null;
    String[] sCols = null;
    if (addSarg) {
      sArg = SearchArgumentFactory
        .newBuilder()
        .lessThan("a", PredicateLeaf.Type.LONG, 10L)
        .build();
      sCols = new String[]{null, "a", null};
    }

    checkEvolution(writerType, readerType,
                   inputRow, expectedOutput,
                   tolerateSchema,
                   sArg, sCols, positional);
  }
```

**`struct`**

```java
  private List<Object> struct(Object... fields) {
    return list(fields);
  }
```

**`list`**

```java
  private List<Object> list(Object... elements) {
    return Arrays.asList(elements);
  }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-117  ·  EnumSource

**项目** `ZooKeeper`  **文件** `zookeeper/zookeeper-server/src/test/java/org/apache/zookeeper/server/quorum/LearnerSyncThrottlerTest.java`  **测试** `testParallelNoThrottle`

### Test method

```java
@ParameterizedTest
    @EnumSource(LearnerSyncThrottler.SyncType.class)
    public void testParallelNoThrottle(LearnerSyncThrottler.SyncType syncType) {
        final int numThreads = 50;

        final LearnerSyncThrottler throttler = new LearnerSyncThrottler(numThreads, syncType);
        ExecutorService threadPool = Executors.newFixedThreadPool(numThreads);
        final CountDownLatch threadStartLatch = new CountDownLatch(numThreads);
        final CountDownLatch syncProgressLatch = new CountDownLatch(numThreads);

        List<Future<Boolean>> results = new ArrayList<>(numThreads);
        for (int i = 0; i < numThreads; i++) {
            results.add(threadPool.submit(new Callable<Boolean>() {

                @Override
                public Boolean call() {
                    threadStartLatch.countDown();
                    try {
                        threadStartLatch.await();

                        throttler.beginSync(false);

                        syncProgressLatch.countDown();
                        syncProgressLatch.await();

                        throttler.endSync();
                    } catch (Exception e) {
                        return false;
                    }

                    return true;
                }
            }));
        }

        try {
            for (Future<Boolean> result : results) {
                assertTrue(result.get());
            }
        } catch (Exception e) {

        } finally {
            threadPool.shutdown();
        }
    }
```

### Enum declaration — `SyncType` (zookeeper/zookeeper-server/src/main/java/org/apache/zookeeper/server/quorum/LearnerSyncThrottler.java)

```java
    public enum SyncType {
        DIFF,
        SNAP
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`call`**

```java
@Override
                public Boolean call() {
                    threadStartLatch.countDown();
                    try {
                        threadStartLatch.await();

                        throttler.beginSync(false);

                        syncProgressLatch.countDown();
                        syncProgressLatch.await();

                        throttler.endSync();
                    } catch (Exception e) {
                        return false;
                    }

                    return true;
                }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-120  ·  EnumSource

**项目** `Commons-RNG`  **文件** `commons-rng/commons-rng-simple/src/test/java/org/apache/commons/rng/simple/internal/NativeSeedTypeParametricTest.java`  **测试** `testCreateSeed`

### Test method

```java
@ParameterizedTest
    @EnumSource
    void testCreateSeed(NativeSeedType nativeSeedType) {
        final int size = 3;
        final Object seed = nativeSeedType.createSeed(size);
        Assertions.assertNotNull(seed);
        final Class<?> type = nativeSeedType.getType();
        Assertions.assertEquals(type, seed.getClass(), "Seed was not the correct class");
        if (type.isArray()) {
            Assertions.assertEquals(size, Array.getLength(seed), "Seed was not created the correct length");
        }
    }
```

### Enum declaration — `NativeSeedType` (commons-rng/commons-rng-simple/src/main/java/org/apache/commons/rng/simple/internal/NativeSeedType.java)

```java
public enum NativeSeedType {
    /** The seed type is {@code Integer}. */
    INT(Integer.class, 4) {
        @Override
        public Integer createSeed(int size, int from, int to) {
            return SeedFactory.createInt();
        }
        @Override
        protected Integer convert(Integer seed, int size) {
            return seed;
        }
        @Override
        protected Integer convert(Long seed, int size) {
            return Conversions.long2Int(seed);
        }
        @Override
        protected Integer convert(int[] seed, int size) {
            return Conversions.intArray2Int(seed);
        }
        @Override
        protected Integer convert(long[] seed, int size) {
            return Conversions.longArray2Int(seed);
        }
        @Override
        protected Integer convert(byte[] seed, int size) {
            return Conversions.byteArray2Int(seed);
        }
    },
    /** The seed type is {@code Long}. */
    LONG(Long.class, 8) {
        @Override
        public Long createSeed(int size, int from, int to) {
            return SeedFactory.createLong();
        }
        @Override
        protected Long convert(Integer seed, int size) {
            return Conversions.int2Long(seed);
        }
        @Override
        protected Long convert(Long seed, int size) {
            return seed;
        }
        @Override
        protected Long convert(int[] seed, int size) {
            return Conversions.intArray2Long(seed);
        }
        @Override
        protected Long convert(long[] seed, int size) {
            return Conversions.longArray2Long(seed);
        }
        @Override
        protected Long convert(byte[] seed, int size) {
            return Conversions.byteArray2Long(seed);
        }
    },
    /** The seed type is {@code int[]}. */
    INT_ARRAY(int[].class, 4) {
        @Override
        public int[] createSeed(int size, int from, int to) {
            // Limit the number of calls to the synchronized method. The generator
            // will support self-seeding.
            return SeedFactory.createIntArray(Math.min(size, RANDOM_SEED_ARRAY_SIZE),
                                              from, to);
        }
        @Override
        protected int[] convert(Integer seed, int size) {
            return Conversions.int2IntArray(seed, size);
        }
        @Override
        protected int[] convert(Long seed, int size) {
            return Conversions.long2IntArray(seed, size);
        }
        @Override
        protected int[] convert(int[] seed, int size) {
            return seed;
        }
        @Override
        protected int[] convert(long[] seed, int size) {
            // Avoid zero filling seeds that are too short
            return Conversions.longArray2IntArray(seed,
                Math.min(size, Conversions.intSizeFromLongSize(seed.length)));
        }
        @Override
        protected int[] convert(byte[] seed, int size) {
            // Avoid zero filling seeds that are too short
            return Conversions.byteArray2IntArray(seed,
                Math.min(size, Conversions.intSizeFromByteSize(seed.length)));
        }
    },
    /** The seed type is {@code long[]}. */
    LONG_ARRAY(long[].class, 8) {
        @Override
        public long[] createSeed(int size, int from, int to) {
            // Limit the number of calls to the synchronized method. The generator
            // will support self-seeding.
            return SeedFactory.createLongArray(Math.min(size, RANDOM_SEED_ARRAY_SIZE),
                                               from, to);
        }
        @Override
        protected long[] convert(Integer seed, int size) {
            return Conversions.int2LongArray(seed, size);
        }
        @Override
        protected long[] convert(Long seed, int size) {
            return Conversions.long2LongArray(seed, size);
        }
        @Override
        protected long[] convert(int[] seed, int size) {
            // Avoid zero filling seeds that are too short
            return Conversions.intArray2LongArray(seed,
                Math.min(size, Conversions.longSizeFromIntSize(seed.length)));
        }
        @Override
        protected long[] convert(long[] seed, int size) {
            return seed;
        }
        @Override
        protected long[] convert(byte[] seed, int size) {
            // Avoid zero filling seeds that are too short
            return Conversions.byteArray2LongArray(seed,
                Math.min(size, Conversions.longSizeFromByteSize(seed.length)));
        }
    };

    /** Error message for unrecognized seed types. */
    private static final String UNRECOGNISED_SEED = "Unrecognized seed type: ";
    /** Maximum length of the seed array (for creating array seeds). */
    private static final int RANDOM_SEED_ARRAY_SIZE = 128;

    /** Define the class type of the native seed. */
    private final Class<?> type;

    /**
     * Define the number of bytes required to represent the native seed. If the type is
     * an array then this represents the size of a single value of the type.
     */
    private final int bytes;

    /**
     * Instantiates a new native seed type.
     *
     * @param type Define the class type of the native seed.
     * @param bytes Define the number of bytes required to represent the native seed.
     */
    NativeSeedType(Class<?> type, int bytes) {
        this.type = type;
        this.bytes = bytes;
    }

    /**
     * Gets the class type of the native seed.
     *
     * @return the type
     */
    public Class<?> getType() {
        return type;
    }

    /**
     * Gets the number of bytes required to represent the native seed type. If the type is
    // … 省略 141 行
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-123  ·  MethodSource

**项目** `JMeter`  **文件** `jmeter/src/dist-check/src/test/java/org/apache/jmeter/junit/JMeterTest.java`  **测试** `elementShouldNotBeModifiedWithConfigureModify`

### Test method

```java
@ParameterizedTest
    @MethodSource("guiComponents")
    public void elementShouldNotBeModifiedWithConfigureModify(GuiComponentHolder componentHolder) {
        JMeterGUIComponent guiItem = componentHolder.getComponent();
        TestElement expected = guiItem.createTestElement();
        TestElement actual = guiItem.createTestElement();
        guiItem.configure(actual);
        if (!Objects.equals(expected, actual)) {
            boolean breakpointForDebugging = Objects.equals(expected, actual);
            String expectedStr = new DslPrinterTraverser(DslPrinterTraverser.DetailLevel.ALL).append(expected).toString();
            String actualStr = new DslPrinterTraverser(DslPrinterTraverser.DetailLevel.ALL).append(actual).toString();
            assertEquals(
                    expectedStr,
                    actualStr,
                    () -> "TestElement should not be modified by " + guiItem.getClass().getName() + ".configure(element)"
            );
        }
        guiItem.modifyTestElement(actual);
        if (guiItem.getClass() == GraphQLHTTPSamplerGui.class) {
            // GraphQL sampler computes its arguments, so we don't compare them
            // See org.apache.jmeter.protocol.http.config.gui.GraphQLUrlConfigGui.modifyTestElement
            expected.removeProperty(HTTPSamplerBaseSchema.INSTANCE.getArguments());
            actual.removeProperty(HTTPSamplerBaseSchema.INSTANCE.getArguments());
        }
        if (!Objects.equals(expected, actual)) {
            if (improperlyUsesUiPlaceholders(guiItem.getClass())) {
                return;
            }
            boolean breakpointForDebugging = Objects.equals(expected, actual);
            String expectedStr = new DslPrinterTraverser(DslPrinterTraverser.DetailLevel.ALL).append(expected).toString();
            String actualStr = new DslPrinterTraverser(DslPrinterTraverser.DetailLevel.ALL).append(actual).toString();
            assertEquals(
                    expectedStr,
                    actualStr,
                    () -> "TestElement should not be modified by " + guiItem.getClass().getName() + ".configure(element); gui.modifyTestElement(element)"
            );
        }
    }
```

### Parameter provider — 同文件内的 `guiComponents`

```java
    static Collection<GuiComponentHolder> guiComponents() throws Throwable {
        List<GuiComponentHolder> components = new ArrayList<>(customGuiComponents());
        for (Object o : getObjects(TestBean.class)) {
            Class<?> c = o.getClass();
            JMeterGUIComponent item = new TestBeanGUI(c);
            components.add(new GuiComponentHolder(item));
        }
        return components;
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`improperlyUsesUiPlaceholders`**

```java
    private static boolean improperlyUsesUiPlaceholders(Class<? extends JMeterGUIComponent> klass) {
        if (klass == JavaConfigGui.class || klass == JavaTestSamplerGui.class) {
            // TODO: JavaConfigGui modifies UI when classname combobox changes, and it causes inconsistency between the
            //   element state and the UI state. We ignore the discrepancy for now
            return true;
        }
        if (klass == JUnitTestSamplerGui.class) {
            // TODO: fix org.apache.jmeter.protocol.java.control.gui.JUnitTestSamplerGui.configure to use placeholders
            return true;
        }
        if (klass == BackendListenerGui.class) {
            // TODO: fix handling of default arguments in org.apache.jmeter.visualizers.backend.BackendListenerGui.actionPerformed
            return true;
        }
        return false;
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-126  ·  EnumSource

**项目** `Log4j`  **文件** `logging-log4j2/log4j-core-test/src/test/java/org/apache/logging/log4j/core/async/AsyncThreadContextGarbageFreeTest.java`  **测试** `testAsyncLogWritesToLog`

### Test method

```java
@ParameterizedTest
    @EnumSource
    void testAsyncLogWritesToLog(final Mode asyncMode) throws Exception {
        testAsyncLogWritesToLog(ContextImpl.GARBAGE_FREE, asyncMode, loggingPath);
    }
```

### Enum declaration — `Mode` (logging-log4j2/log4j-core/src/main/java/org/apache/logging/log4j/core/appender/rewrite/MapRewritePolicy.java)

```java
    public enum Mode {

        /**
         * Keys should be added.
         */
        Add,

        /**
         * Keys should be updated.
         */
        Update
    }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-129  ·  MethodSource

**项目** `Commons-RNG`  **文件** `commons-rng/commons-rng-core/src/test/java/org/apache/commons/rng/core/SplittableProvidersParametricTest.java`  **测试** `testSplitsMethodsUseSameSpliterator`

### Test method

```java
@ParameterizedTest
    @MethodSource("getSplittableProviders")
    void testSplitsMethodsUseSameSpliterator(SplittableUniformRandomProvider generator) {
        final long size = 10;
        final Spliterator<SplittableUniformRandomProvider> s = generator.splits(size, generator).spliterator();
        Assertions.assertEquals(s.getClass(), generator.splits().spliterator().getClass());
        Assertions.assertEquals(s.getClass(), generator.splits(size).spliterator().getClass());
        Assertions.assertEquals(s.getClass(), generator.splits(ThreadLocalGenerator.INSTANCE).spliterator().getClass());
    }
```

### Parameter provider — 同文件内的 `getSplittableProviders`

```java
    private static Iterable<SplittableUniformRandomProvider> getSplittableProviders() {
        return ProvidersList.listSplittable();
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-132  ·  MethodSource

**项目** `Hive`  **文件** `hive/ql/src/test/org/apache/hadoop/hive/ql/io/parquet/serde/TestParquetTimestampsHive2Compatibility.java`  **测试** `testWriteHive4UsingLegacyConversionReadHive2`

### Test method

```java
@ParameterizedTest(name = "{0}")
  @MethodSource("generateTimestamps")
  void testWriteHive4UsingLegacyConversionReadHive2(String timestampString) {
    NanoTime nt = writeHive4(timestampString, TimeZone.getDefault().getID(), true);
    java.sql.Timestamp ts = readHive2(nt);
    assertEquals(timestampString, ts.toString());
  }
```

### Parameter provider — 同文件内的 `generateTimestamps`

```java
  private static Stream<String> generateTimestamps() {
    return Stream.concat(Stream.generate(new Supplier<String>() {
      int i = 0;

      @Override
      public String get() {
        StringBuilder sb = new StringBuilder(29);
        int year = (i % 9999) + 1;
        sb.append(zeros(4 - digits(year)));
        sb.append(year);
        sb.append('-');
        int month = (i % 12) + 1;
        sb.append(zeros(2 - digits(month)));
        sb.append(month);
        sb.append('-');
        int day = (i % 28) + 1;
        sb.append(zeros(2 - digits(day)));
        sb.append(day);
        sb.append(' ');
        int hour = i % 24;
        sb.append(zeros(2 - digits(hour)));
        sb.append(hour);
        sb.append(':');
        int minute = i % 60;
        sb.append(zeros(2 - digits(minute)));
        sb.append(minute);
        sb.append(':');
        int second = i % 60;
        sb.append(zeros(2 - digits(second)));
        sb.append(second);
        sb.append('.');
        // Bitwise OR with one to avoid times with trailing zeros
        int nano = (i % 1000000000) | 1;
        sb.append(zeros(9 - digits(nano)));
        sb.append(nano);
        i++;
        return sb.toString();
      }
    })
    // Exclude dates falling in the default Gregorian change date since legacy code does not handle that interval
    // gracefully. It is expected that these do not work well when legacy APIs are in use. 
    .filter(s -> !s.startsWith("1582-10"))
    .limit(3000), Stream.of("9999-12-31 23:59:59.999"));
  }
```

### Test-side helpers called by this test (2)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`writeHive4`**

```java
  private static NanoTime writeHive4(String str, String sourceZone, boolean legacyConversion) {
    Timestamp newTs = PrimitiveObjectInspectorUtils.getTimestampFromString(str);
    return NanoTimeUtils.getNanoTime(newTs, ZoneId.of(sourceZone), legacyConversion);
  }
```

**`readHive2`**

```java
  private static java.sql.Timestamp readHive2(NanoTime nt) {
    //Current Hive parquet timestamp implementation stores it in UTC, but other components do not do that.
    //If this file written by current Hive implementation itself, we need to do the reverse conversion, else skip the conversion.
    int julianDay = nt.getJulianDay();
    long nanosOfDay = nt.getTimeOfDayNanos();

    long remainder = nanosOfDay;
    julianDay += remainder / NANOS_PER_DAY;
    remainder %= NANOS_PER_DAY;
    if (remainder < 0) {
      remainder += NANOS_PER_DAY;
      julianDay--;
    }

    JulianDate jDateTime = JulianDate.of((double) julianDay);
    Calendar calendar = Calendar.getInstance(TimeZone.getTimeZone(ZoneId.of("GMT")));
    calendar.set(Calendar.YEAR, jDateTime.toLocalDateTime().getYear());
    calendar.set(Calendar.MONTH, jDateTime.toLocalDateTime().getMonthValue() - 1); //java calendar index starting at 1.
    calendar.set(Calendar.DAY_OF_MONTH, jDateTime.toLocalDateTime().getDayOfMonth());

    int hour = (int) (remainder / (NANOS_PER_HOUR));
    remainder = remainder % (NANOS_PER_HOUR);
    int minutes = (int) (remainder / (NANOS_PER_MINUTE));
    remainder = remainder % (NANOS_PER_MINUTE);
    int seconds = (int) (remainder / (NANOS_PER_SECOND));
    long nanos = remainder % NANOS_PER_SECOND;

    calendar.set(Calendar.HOUR_OF_DAY, hour);
    calendar.set(Calendar.MINUTE, minutes);
    calendar.set(Calendar.SECOND, seconds);
    java.sql.Timestamp ts = new java.sql.Timestamp(calendar.getTimeInMillis());
    ts.setNanos((int) nanos);
    return ts;
  }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-135  ·  ValueSource

**项目** `Commons-HttpClient`  **文件** `httpcomponents-client/httpclient5-testing/src/test/java/org/apache/hc/client5/testing/async/TestConnectionClosureRace.java`  **测试** `testSpacedOutBatchesOfRequests`

### Test method

```java
@ParameterizedTest(name = "Validation: {0}")
    @ValueSource(booleans = { false, true })
    @Timeout(5)
    @Order(5)
    void testSpacedOutBatchesOfRequests(final boolean validateConnections) throws Exception {
        try (final CloseableHttpAsyncClient client = asyncClient(validateConnections)) {
            final List<Future<SimpleHttpResponse>> futures = new ArrayList<>();
            for (int i = 0; i < 5; i++) {
                final List<Future<SimpleHttpResponse>> batchFutures = sendRequestBatch(client, 3);
                futures.addAll(batchFutures);
            }

            checkResults(getValidationPrefix(validateConnections) + "Multiple small batches", futures);
        }
    }
```

### Test-side helpers called by this test (6)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`asyncClient`**

```java
    private CloseableHttpAsyncClient asyncClient(final boolean validateConnections) throws Exception {
        final PoolingAsyncClientConnectionManager connManager = PoolingAsyncClientConnectionManagerBuilder.create()
            .setTlsStrategy(new DefaultClientTlsStrategy(SSLTestContexts.createClientSSLContext()))
            .setDefaultTlsConfig(TlsConfig.custom()
                .setSupportedProtocols(TLS.V_1_2)
                .setVersionPolicy(httpVersionPolicy)
                .build())
            .build();
        connManager.setDefaultConnectionConfig(getConnectionConfig(validateConnections));
        connManager.setDefaultMaxPerRoute(1);
        connManager.setMaxTotal(1);
        final CloseableHttpAsyncClient client = HttpAsyncClients.custom()
            .setIOReactorConfig(IOReactorConfig.custom()
                .setSelectInterval(TimeValue.ofMilliseconds(1000))
                .setIoThreadCount(1)
                .build())
            .setConnectionManager(connManager)
            .disableAutomaticRetries()
            .build();
        client.start();
        return client;
    }
```

**`sendRequestBatch`**

```java
    private List<Future<SimpleHttpResponse>> sendRequestBatch(
        final CloseableHttpAsyncClient client,
        final int batchSize
    ) {
        final List<Future<SimpleHttpResponse>> futures = new ArrayList<>();
        for (int i = 0; i < batchSize; i++) {
            futures.add(sendPing(client));
        }
        waitForCompletion(futures);
        return futures;
    }
```

**`checkResults`**

```java
    private void checkResults(final String name, final List<Future<SimpleHttpResponse>> futures) {
        int ok = 0, error = 0, notExecuted = 0, closed = 0, reset = 0, other = 0;
        for (final Future<SimpleHttpResponse> future : futures) {
            try {
                future.get();
                ok++;
            } catch (final Exception ex) {
                error++;
                if (ex.getCause() instanceof RequestNotExecutedException) {
                    notExecuted++;
                } else if (ex.getCause() instanceof ConnectionClosedException) {
                    closed++;
                } else if (ex.getCause() instanceof SocketException && ex.getCause().getMessage().contains("reset")) {
                    reset++;
                } else {
                    other++;
                }
            }
        }

        if (error > 0) {
            System.out.printf("%s: %s: %,d succeeded; %,d failed (%.2f%% success rate, %.2f%% retriable)%n",
                getClass().getSimpleName().toLowerCase(), name, ok, error,
                (double) ok / (ok + error) * 100d,
                (double) notExecuted / (ok + error) * 100d);
        } else {
            System.out.printf("%s: %s: %,d succeeded; %,d failed (%.2f%% success rate)%n",
                getClass().getSimpleName().toLowerCase(), name, ok, error, (((double) ok) / (ok + error)) * 100d);
        }
        if (false) {
            System.out.printf("  %,d not executed, %,d closed, %,d reset, %,d other%n", notExecuted, closed, reset,
                other);
        }
    }
```

**`getValidationPrefix`**

```java
    private static String getValidationPrefix(final boolean validateConnections) {
        if (validateConnections) {
            return "Validation enabled:  ";
        } else {
            return "Validation disabled: ";
        }
    }
```

**`getConnectionConfig`**

```java
    private static ConnectionConfig getConnectionConfig(final boolean validateConnections) {
        return ConnectionConfig.custom()
            .setTimeToLive(MAX_VALUE)
            .setValidateAfterInactivity(validateConnections ? ZERO_MILLISECONDS : NEG_ONE_MILLISECOND)
            .build();
    }
```

**`sendPing`**

```java
    private Future<SimpleHttpResponse> sendPing(final CloseableHttpAsyncClient client) {
        final HttpHost target = new HttpHost(scheme, "localhost", port);
        final SimpleHttpRequest request = SimpleRequestBuilder.get().setHttpHost(target).setPath("/ping").build();

        return client.execute(request, null);
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-138  ·  ValueSource

**项目** `Commons-Compress`  **文件** `commons-compress/src/test/java/org/apache/commons/compress/harmony/pack200/NewAttributeBandsTest.java`  **测试** `testIntegralLayouts`

### Test method

```java
@ParameterizedTest
    @ValueSource(strings = { "B", "FB", "SB", "H", "FH", "SH", "I", "FI", "SI", "PB", "OB", "OSB", "POB", "PH", "OH", "OSH", "POH", "PI", "OI", "OSI", "POI" })
    void testIntegralLayouts(final String layoutStr) throws IOException {
        final CPUTF8 name = new CPUTF8("TestAttribute");
        final CPUTF8 layout = new CPUTF8(layoutStr);
        final MockNewAttributeBands newAttributeBands = new MockNewAttributeBands(1, null, null,
                new AttributeDefinition(35, AttributeDefinitionBands.CONTEXT_CLASS, name, layout));
        final List<AttributeLayoutElement> layoutElements = newAttributeBands.getLayoutElements();
        assertEquals(1, layoutElements.size());
        final Integral element = (Integral) layoutElements.get(0);
        assertEquals(layoutStr, element.getTag());
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`getLayoutElements`**

```java
        public List<AttributeLayoutElement> getLayoutElements() {
            return attributeLayoutElements;
        }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-141  ·  MethodSource

**项目** `Commons-Numbers`  **文件** `commons-numbers/commons-numbers-arrays/src/test/java/org/apache/commons/numbers/arrays/SelectionTest.java`  **测试** `testIntDualPivotQuickSelectMaxRecursion`

### Test method

```java
@ParameterizedTest
    @MethodSource(value = {"testIntPartition", "testIntPartitionBigData"})
    void testIntDualPivotQuickSelectMaxRecursion(int[] values, int[] indices) {
        assertPartition(values, indices, (a, k, n) -> {
            final int right = a.length - 1;
            if (right < 1 || k.length == 0) {
                return;
            }
            QuickSelect.dualPivotQuickSelect(a, 0, right,
                IndexSupport.createUpdatingInterval(k, k.length),
                QuickSelect.dualPivotFlags(2, 5));
        }, false);
    }
```

### Parameter provider — 同文件内的 `testIntPartition`

```java
    static Stream<Arguments> testIntPartition() {
        final Stream.Builder<Arguments> builder = Stream.builder();
        UniformRandomProvider rng = RandomSource.XO_SHI_RO_128_PP.create(123);
        // Sizes above and below the threshold for partitioning.
        // The largest size should trigger single-pivot sub-sampling for pivot selection.
        for (final int size : new int[] {5, 47, SU + 10}) {
            final int halfSize = size >>> 1;
            final int from = -halfSize;
            final int to = -halfSize + size;
            final int[] values = IntStream.range(from, to).toArray();
            final int[] zeros = values.clone();
            final int quarterSize = size >>> 2;
            Arrays.fill(zeros, quarterSize, halfSize + quarterSize, 0);
            for (final int k : new int[] {1, 2, 3, size}) {
                for (int i = 0; i < 15; i++) {
                    // Note: Duplicate indices do not matter
                    final int[] indices = rng.ints(k, 0, size).toArray();
                    builder.add(Arguments.of(
                        ArraySampler.shuffle(rng, values.clone()),
                        indices.clone()));
                    builder.add(Arguments.of(
                        ArraySampler.shuffle(rng, zeros.clone()),
                        indices.clone()));
                }
            }
            // Test sequential processing by creating potential ranges
            // after an initial low point. This should be high enough
            // so any range analysis that joins indices will leave the initial
            // index as a single point.
            final int limit = 50;
            if (size > limit) {
                for (int i = 0; i < 10; i++) {
                    final int[] indices = rng.ints(size - limit, limit, size).toArray();
                    // This sets a low index
                    indices[rng.nextInt(indices.length)] = rng.nextInt(0, limit >>> 1);
                    builder.add(Arguments.of(
                        ArraySampler.shuffle(rng, values.clone()),
                        indices.clone()));
                }
            }
            // min; max; min/max
            builder.add(Arguments.of(values.clone(), new int[] {0}));
            builder.add(Arguments.of(values.clone(), new int[] {size - 1}));
            builder.add(Arguments.of(values.clone(), new int[] {0, size - 1}));
            builder.add(Arguments.of(zeros.clone(), new int[] {0}));
            builder.add(Arguments.of(zeros.clone(), new int[] {size - 1}));
            builder.add(Arguments.of(zeros.clone(), new int[] {0, size - 1}));
        }
        final int value = Integer.MIN_VALUE;
        builder.add(Arguments.of(new int[] {}, new int[0]));
        builder.add(Arguments.of(new int[] {value}, new int[] {0}));
        builder.add(Arguments.of(new int[] {0, value}, new int[] {1}));
        builder.add(Arguments.of(new int[] {value, value, value}, new int[] {2}));
        builder.add(Arguments.of(new int[] {value, 0, 0, value}, new int[] {3}));
        builder.add(Arguments.of(new int[] {value, 0, 0, value}, new int[] {1, 2}));
        builder.add(Arguments.of(new int[] {value, 0, 1, 0, value}, new int[] {1, 3}));
        builder.add(Arguments.of(new int[] {value, 0, 0}, new int[] {0, 2}));
        builder.add(Arguments.of(new int[] {value, 123, 0, -456, 0, value}, new int[] {0, 1, 3}));
        // Dual-pivot with a large middle region (> 5 / 8) requires equal elements loop
        final int n = 128;
        final int[] x = IntStream.range(0, n).toArray();
        // Put equal elements in the central region:
        //          2/16      6/16             10/16      14/16
        // |  <P1    |    P1   |   P1< & < P2    |    P2    |    >P2    |
        final int sixteenth = n / 16;
        final int i2 = 2 * sixteenth;
        final int i6 = 6 * sixteenth;
        final int p1 = x[i2];
        final int p2 = x[n - i2];
        // Lots of values equal to the pivots
        Arrays.fill(x, i2, i6, p1);
        Arrays.fill(x, n - i6, n - i2, p2);
        // Equal value in between the pivots
        Arrays.fill(x, i6, n - i6, (p1 + p2) / 2);
        // ArraySampler.shuffle this and partition in the middle.
        // Also partition with the pivots in P1 and P2 using thirds.
        final int third = (int) (n / 3.0);
        // Use a fix seed to ensure we hit coverage with only 5 loops.
        rng = RandomSource.XO_SHI_RO_128_PP.create(-8111061151820577011L);
        for (int i = 0; i < 5; i++) {
            builder.add(Arguments.of(ArraySampler.shuffle(rng, x.clone()), new int[] {n >> 1}));
            builder.add(Arguments.of(ArraySampler.shuffle(rng, x.clone()),
                new int[] {third, 2 * third}));
        }
        // A single value smaller/greater than the pivot at the left/right/both ends
        Arrays.fill(x, 1);
        for (int i = 0; i <= 2; i++) {
            for (int j = 0; j <= 2; j++) {
                x[n - 1] = i;
                x[0] = j;
                builder.add(Arguments.of(x.clone(), new int[] {50}));
            }
        }
        // Reverse data. Makes it simple to detect failed range selection.
        final int[] a = IntStream.range(0, 50).toArray();
        for (int i = -1, j = a.length; ++i < --j;) {
            final int v = a[i];
            a[i] = a[j];
            a[j] = v;
        }
        builder.add(Arguments.of(a, new int[] {1, 1}));
        builder.add(Arguments.of(a, new int[] {1, 2}));
        builder.add(Arguments.of(a, new int[] {10, 12}));
        builder.add(Arguments.of(a, new int[] {10, 42}));
        builder.add(Arguments.of(a, new int[] {1, 48}));
        builder.add(Arguments.of(a, new int[] {48, 49}));
        return builder.build();
    }
```

### Parameter provider — 同文件内的 `testIntPartitionBigData`

```java
    static Stream<Arguments> testIntPartitionBigData() {
        final Stream.Builder<Arguments> builder = Stream.builder();
        final UniformRandomProvider rng = RandomSource.XO_SHI_RO_128_PP.create(123);
        // Sizes above the threshold (1200) for recursive partitioning
        for (final int size : new int[] {1000, 5000, 10000}) {
            final int[] a = IntStream.range(0, size).toArray();
            // With repeat elements
            final int[] b = rng.ints(size, 0, size >> 3).toArray();
            for (int i = 0; i < 15; i++) {
                builder.add(Arguments.of(
                    ArraySampler.shuffle(rng, a.clone()),
                    new int[] {rng.nextInt(size)}));
                builder.add(Arguments.of(b.clone(),
                    new int[] {rng.nextInt(size)}));
            }
        }
        // Hit Floyd-Rivest sub-sampling conditions.
        // Close to edge but outside edge select size.
        final int n = 7000;
        final int[] x = IntStream.range(0, n).toArray();
        builder.add(Arguments.of(x.clone(), new int[] {20}));
        builder.add(Arguments.of(x.clone(), new int[] {n - 1 - 20}));
        // Constant value when using FR partitioning
        Arrays.fill(x, 123);
        builder.add(Arguments.of(x, new int[] {x.length >>> 1}));
        return builder.build();
    }
```

### Test-side helpers called by this test (2)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`assertPartition`**

```java
    static void assertPartition(double[] values, int[] indices, DoublePartitionFunction function,
        boolean sortedRange) {
        final double[] data = values.clone();
        final double[] sorted = sort(values);
        // Indices may be destructively modified
        function.partition(data, indices.clone(), indices.length);
        if (indices.length == 0) {
            return;
        }
        for (final int k : indices) {
            Assertions.assertEquals(sorted[k], data[k], () -> "k[" + k + "]");
        }
        // Check partial ordering
        Arrays.sort(indices);
        int i = 0;
        for (final int k : indices) {
            final double value = sorted[k];
            while (i < k) {
                final int j = i;
                Assertions.assertTrue(Double.compare(data[i], value) <= 0,
                    () -> j + " < " + k + " : " + data[j] + " < " + value);
                i++;
            }
        }
        final int k = indices[indices.length - 1];
        final double value = sorted[k];
        while (i < data.length) {
            final int j = i;
            Assertions.assertTrue(Double.compare(data[i], value) >= 0,
                () -> k + " < " + j);
            i++;
        }
        if (sortedRange) {
            final double[] a = Arrays.copyOfRange(sorted, indices[0], k + 1);
            final double[] b = Arrays.copyOfRange(data, indices[0], k + 1);
            Assertions.assertArrayEquals(a, b, "Entire range of indices is not sorted");
        }
        Arrays.sort(data);
        Assertions.assertArrayEquals(sorted, data, "Data destroyed");
    }
```

**`sort`**

```java
    private static double[] sort(double[] values) {
        final double[] sorted = values.clone();
        Arrays.sort(sorted);
        return sorted;
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-144  ·  CsvSource

**项目** `JMeter`  **文件** `jmeter/src/protocol/http/src/test/java/org/apache/jmeter/protocol/http/proxy/DefaultSamplerCreatorTest.java`  **测试** `computeSamplerNameWithCounter`

### Test method

```java
@ParameterizedTest
    @CsvSource({
            "3,#{name} - #{counter} - #{scheme}://#{host}:#{port}#{path},prefix| - 42 - https://jmeter.invalid:443/some/path",
            "3,#{counter} - #{path},42 - /some/path",
            "3,#{url},https://jmeter.invalid/some/path",
            "3,{0},{0}",
            "3,'{0,number,#.##}','{0,number,#.##}'",
            "0,,prefix|/some/path-42",
            "1,,prefix|-42",
            "2,,prefix|-42 /some/path",
            "4,,/some/path"
    })
    void computeSamplerNameWithCounter(int sampleNameMode, String format, String expectedName) {
        DefaultSamplerCreator samplerCreator = new DefaultSamplerCreator();
        HTTPSamplerBase sampler = new HTTPSampler();
        sampler.setPath("/some/path");
        sampler.setDomain("jmeter.invalid");
        sampler.setMethod("GET");
        sampler.setPort(443);
        sampler.setProtocol("https");
        HttpRequestHdr request = new HttpRequestHdr(
                "prefix|",
                "samplerName",
                sampleNameMode,
                format
        );
        samplerCreator.setCounter(41);
        samplerCreator.computeSamplerName(sampler, request);
        assertEquals(expectedName, sampler.getName());
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-147  ·  CsvSource

**项目** `JMeter`  **文件** `jmeter/src/components/src/test/java/org/apache/jmeter/assertions/TestJSONPathAssertion.java`  **测试** `testGetResult_pathsWithOneResult`

### Test method

```java
@ParameterizedTest
    @CsvSource(value={
        "{\"myval\": 123}; $.myval; 123",
        "{\"myval\": [{\"test\":1},{\"test\":2},{\"test\":3}]}; $.myval[*].test; 2",
        "{\"myval\": []}; $.myval; []",
        "{\"myval\": {\"key\": \"val\"}}; $.myval; \\{\"key\":\"val\"\\}"
    }, delimiterString=";")
    void testGetResult_pathsWithOneResult(String data, String jsonPath, String expectedResult) {
        SampleResult samplerResult = new SampleResult();
        samplerResult.setResponseData(data.getBytes(Charset.defaultCharset()));

        JSONPathAssertion instance = new JSONPathAssertion();
        instance.setJsonPath(jsonPath);
        instance.setJsonValidationBool(true);
        instance.setExpectedValue(expectedResult);
        AssertionResult expResult = new AssertionResult("");
        AssertionResult result = instance.getResult(samplerResult);
        assertEquals(expResult.getName(), result.getName());
        assertFalse(result.isFailure());
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-150  ·  MethodSource

**项目** `Avro`  **文件** `avro/lang/java/avro/src/test/java/org/apache/avro/io/TestResolvingIO.java`  **测试** `testIdentical`

### Test method

```java
@ParameterizedTest
  @MethodSource("data2")
  public void testIdentical(Encoding encoding, int skip, String jsonWriterSchema, String writerCalls,
      String jsonReaderSchema, String readerCalls) throws IOException {
    performTest(encoding, skip, jsonWriterSchema, writerCalls, jsonWriterSchema, writerCalls);
  }
```

### Parameter provider — 同文件内的 `data2`

```java
  public static Stream<Arguments> data2() {
    return TestValidatingIO.convertTo2dStream(encodings, skipLevels, testSchemas());
  }
```

### Test-side helpers called by this test (2)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`performTest`**

```java
  private void performTest(Encoding encoding, int skipLevel, String jsonWriterSchema, String writerCalls,
      String jsonReaderSchema, String readerCalls) throws IOException {
    for (int i = 0; i < COUNT; i++) {
      testOnce(jsonWriterSchema, writerCalls, jsonReaderSchema, readerCalls, encoding, skipLevel);
    }
  }
```

**`testOnce`**

```java
  private void testOnce(String jsonWriterSchema, String writerCalls, String jsonReaderSchema, String readerCalls,
      Encoding encoding, int skipLevel) throws IOException {
    Object[] values = TestValidatingIO.randomValues(writerCalls);
    Object[] expected = TestValidatingIO.randomValues(readerCalls);

    Schema writerSchema = new Schema.Parser().parse(jsonWriterSchema);
    byte[] bytes = TestValidatingIO.make(writerSchema, writerCalls, values, encoding);
    Schema readerSchema = new Schema.Parser().parse(jsonReaderSchema);
    TestValidatingIO.print(encoding, skipLevel, writerSchema, readerSchema, values, expected);
    check(writerSchema, readerSchema, bytes, readerCalls, expected, encoding, skipLevel);
  }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---
