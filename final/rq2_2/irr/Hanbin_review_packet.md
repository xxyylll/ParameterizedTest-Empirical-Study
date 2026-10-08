# Rating packet R2

60 items. For each one, classify only the dimensions that apply to its source — the rules are in `rater_guide.md`.

Record your answers in `packet_R2.csv`, one row per item, matched by `item_id`. If the code shown does not let you decide, answer `unclear` and write one line in `notes`.

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

## IRR-017  ·  ValueSource

**项目** `Maven`  **文件** `maven/impl/maven-cli/src/test/java/org/apache/maven/cling/invoker/mvnup/goals/ModelVersionUtilsTest.java`  **测试** `shouldHandleVariousNamespaceFormats`

### Test method

```java
@ParameterizedTest
        @ValueSource(
                strings = {
                    "http://maven.apache.org/POM/4.0.0",
                    "http://maven.apache.org/POM/4.1.0",
                    "https://maven.apache.org/POM/4.0.0",
                    "https://maven.apache.org/POM/4.1.0"
                })
        @DisplayName("should handle various namespace formats")
        void shouldHandleVariousNamespaceFormats(String namespace) throws Exception {
            String pomXml = PomBuilder.create()
                    .namespace(namespace)
                    .groupId("com.example")
                    .artifactId("test")
                    .version("1.0.0")
                    .build();

            // Test that the POM can be parsed successfully and namespace is preserved
            Document document = saxBuilder.build(new StringReader(pomXml));
            Element root = document.getRootElement();

            assertEquals(namespace, root.getNamespaceURI(), "POM should preserve the specified namespace");
        }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-020  ·  MethodSource

**项目** `Rat`  **文件** `creadur-rat/apache-rat-core/src/test/java/org/apache/rat/analysis/GeneratedFileTest.java`  **测试** `testMatchProcessing`

### Test method

```java
@ParameterizedTest
    @MethodSource("parameterProvider")
    public void testMatchProcessing(String name, String text) throws IOException {
        assertThat(processText(text)).as(name).isTrue();
    }
```

### Parameter provider — 同文件内的 `parameterProvider`

```java
    public static Stream<Arguments> parameterProvider() {
        List<Arguments> lst = new ArrayList<>();

        for (String[] target : targets) {
            lst.add(Arguments.of(target[0], target[1]));
        }
        return lst.stream();
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`processText`**

```java
    private boolean processText(String text) throws IOException {
        try (BufferedReader in = new BufferedReader(new StringReader(text))) {
            IHeaders headers = HeaderCheckWorker.readHeader(in,
                    HeaderCheckWorker.DEFAULT_NUMBER_OF_RETAINED_HEADER_LINES);
            return matcher.matches(headers);
        }
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-023  ·  EnumSource

**项目** `Commons-RNG`  **文件** `commons-rng/commons-rng-simple/src/test/java/org/apache/commons/rng/simple/internal/RandomSourceInternalParametricTest.java`  **测试** `testCreateSeed`

### Test method

```java
@ParameterizedTest
    @EnumSource
    void testCreateSeed(RandomSourceInternal randomSourceInternal) {
        final Class<?> type = getType(randomSourceInternal);
        final Object seed = randomSourceInternal.createSeed();
        Assertions.assertNotNull(seed);
        Assertions.assertEquals(type, seed.getClass(), "Seed was not the correct class");
        Assertions.assertTrue(randomSourceInternal.isNativeSeed(seed), "Seed was not identified as the native type");
    }
```

### Enum declaration — `RandomSourceInternal` (commons-rng/commons-rng-simple/src/main/java/org/apache/commons/rng/simple/internal/ProviderBuilder.java)

```java
    public enum RandomSourceInternal {
        /** Source of randomness is {@link JDKRandom}. */
        JDK(JDKRandom.class,
            1,
            NativeSeedType.LONG),
        /** Source of randomness is {@link Well512a}. */
        WELL_512_A(Well512a.class,
                   16, 0, 16,
                   NativeSeedType.INT_ARRAY),
        /** Source of randomness is {@link Well1024a}. */
        WELL_1024_A(Well1024a.class,
                    32, 0, 32,
                    NativeSeedType.INT_ARRAY),
        /** Source of randomness is {@link Well19937a}. */
        WELL_19937_A(Well19937a.class,
                     624, 0, 623,
                     NativeSeedType.INT_ARRAY),
        /** Source of randomness is {@link Well19937c}. */
        WELL_19937_C(Well19937c.class,
                     624, 0, 623,
                     NativeSeedType.INT_ARRAY),
        /** Source of randomness is {@link Well44497a}. */
        WELL_44497_A(Well44497a.class,
                     1391, 0, 1390,
                     NativeSeedType.INT_ARRAY),
        /** Source of randomness is {@link Well44497b}. */
        WELL_44497_B(Well44497b.class,
                     1391, 0, 1390,
                     NativeSeedType.INT_ARRAY),
        /** Source of randomness is {@link MersenneTwister}. */
        MT(MersenneTwister.class,
           624,
           NativeSeedType.INT_ARRAY),
        /** Source of randomness is {@link ISAACRandom}. */
        ISAAC(ISAACRandom.class,
              256,
              NativeSeedType.INT_ARRAY),
        /** Source of randomness is {@link SplitMix64}. */
        SPLIT_MIX_64(SplitMix64.class,
                     1,
                     NativeSeedType.LONG),
        /** Source of randomness is {@link XorShift1024Star}. */
        XOR_SHIFT_1024_S(XorShift1024Star.class,
                         16, 0, 16,
                         NativeSeedType.LONG_ARRAY),
        /** Source of randomness is {@link TwoCmres}. */
        TWO_CMRES(TwoCmres.class,
                  1,
                  NativeSeedType.INT),
        /**
         * Source of randomness is {@link TwoCmres} with explicit selection
         * of the two subcycle generators.
         */
        TWO_CMRES_SELECT(TwoCmres.class,
                         1,
                         NativeSeedType.INT,
                         Integer.TYPE,
                         Integer.TYPE),
        /** Source of randomness is {@link MersenneTwister64}. */
        MT_64(MersenneTwister64.class,
              312,
              NativeSeedType.LONG_ARRAY),
        /** Source of randomness is {@link MultiplyWithCarry256}. */
        MWC_256(MultiplyWithCarry256.class,
                257, 0, 257,
                NativeSeedType.INT_ARRAY),
        /** Source of randomness is {@link KISSRandom}. */
        KISS(KISSRandom.class,
             // If zero in initial 3 positions the output is a simple LCG
             4, 0, 3,
             NativeSeedType.INT_ARRAY),
        /** Source of randomness is {@link XorShift1024StarPhi}. */
        XOR_SHIFT_1024_S_PHI(XorShift1024StarPhi.class,
                             16, 0, 16,
                             NativeSeedType.LONG_ARRAY),
        /** Source of randomness is {@link XoRoShiRo64Star}. */
        XO_RO_SHI_RO_64_S(XoRoShiRo64Star.class,
                          2, 0, 2,
                          NativeSeedType.INT_ARRAY),
        /** Source of randomness is {@link XoRoShiRo64StarStar}. */
        XO_RO_SHI_RO_64_SS(XoRoShiRo64StarStar.class,
                           2, 0, 2,
                           NativeSeedType.INT_ARRAY),
        /** Source of randomness is {@link XoShiRo128Plus}. */
        XO_SHI_RO_128_PLUS(XoShiRo128Plus.class,
                           4, 0, 4,
                           NativeSeedType.INT_ARRAY),
        /** Source of randomness is {@link XoShiRo128StarStar}. */
        XO_SHI_RO_128_SS(XoShiRo128StarStar.class,
                         4, 0, 4,
                         NativeSeedType.INT_ARRAY),
        /** Source of randomness is {@link XoRoShiRo128Plus}. */
        XO_RO_SHI_RO_128_PLUS(XoRoShiRo128Plus.class,
                              2, 0, 2,
                              NativeSeedType.LONG_ARRAY),
        /** Source of randomness is {@link XoRoShiRo128StarStar}. */
        XO_RO_SHI_RO_128_SS(XoRoShiRo128StarStar.class,
                            2, 0, 2,
                            NativeSeedType.LONG_ARRAY),
        /** Source of randomness is {@link XoShiRo256Plus}. */
        XO_SHI_RO_256_PLUS(XoShiRo256Plus.class,
                           4, 0, 4,
                           NativeSeedType.LONG_ARRAY),
        /** Source of randomness is {@link XoShiRo256StarStar}. */
        XO_SHI_RO_256_SS(XoShiRo256StarStar.class,
                         4, 0, 4,
                         NativeSeedType.LONG_ARRAY),
        /** Source of randomness is {@link XoShiRo512Plus}. */
        XO_SHI_RO_512_PLUS(XoShiRo512Plus.class,
                           8, 0, 8,
                           NativeSeedType.LONG_ARRAY),
        /** Source of randomness is {@link XoShiRo512StarStar}. */
        XO_SHI_RO_512_SS(XoShiRo512StarStar.class,
                         8, 0, 8,
                         NativeSeedType.LONG_ARRAY),
        /** Source of randomness is {@link PcgXshRr32}. */
        PCG_XSH_RR_32(PcgXshRr32.class,
                2,
                NativeSeedType.LONG_ARRAY),
        /** Source of randomness is {@link PcgXshRs32}. */
        PCG_XSH_RS_32(PcgXshRs32.class,
                2,
                NativeSeedType.LONG_ARRAY),
        /** Source of randomness is {@link PcgRxsMXs64}. */
        PCG_RXS_M_XS_64(PcgRxsMXs64.class,
                2,
                NativeSeedType.LONG_ARRAY),
        /** Source of randomness is {@link PcgMcgXshRr32}. */
        PCG_MCG_XSH_RR_32(PcgMcgXshRr32.class,
                1,
                NativeSeedType.LONG),
        /** Source of randomness is {@link PcgMcgXshRs32}. */
        PCG_MCG_XSH_RS_32(PcgMcgXshRs32.class,
                1,
                NativeSeedType.LONG),
        /** Source of randomness is {@link MiddleSquareWeylSequence}. */
        MSWS(MiddleSquareWeylSequence.class,
             // Many partially zero seeds can create low quality initial output.
             // The Weyl increment cascades bits into the random state so ideally it
             // has a high number of bit transitions. Minimally ensure it is non-zero.
             3, 2, 3,
             NativeSeedType.LONG_ARRAY) {
            @Override
            protected Object createSeed() {
                return createMswsSeed(SeedFactory.createLong());
            }

            @Override
            protected Object convertSeed(Object seed) {
                // Allow seeding with primitives to generate a good seed
                if (seed instanceof Integer) {
                    return createMswsSeed((Integer) seed);
                } else if (seed instanceof Long) {
                    return createMswsSeed((Long) seed);
                }
                // Other types (e.g. the native long[]) are handled by the default conversion
                return super.convertSeed(seed);
            }

            @Override
    // … 省略 460 行
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`getType`**

```java
    private static Class<?> getType(RandomSourceInternal randomSourceInternal) {
        // The first constructor argument is always the seed type
        return randomSourceInternal.getArgs()[0];
    }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-026  ·  EnumSource

**项目** `Causeway`  **文件** `causeway/core/mmtest/src/test/java/org/apache/causeway/core/metamodel/valuesemantics/temporal/TemporalValueSemanticsProviderTest.java`  **测试** `timeFormats`

### Test method

```java
@ParameterizedTest
    @EnumSource(TimePrecision.class)
    void timeFormats(final TimePrecision timePrecision) {

        target = new TemporalValueSemanticsProvider_forTesting(
                TemporalCharacteristic.TIME_ONLY, OffsetCharacteristic.LOCAL);

        Context context = null;
        LocalTime localTime = LocalTime.of(13, 12, 45);

        var formatter = target.getTemporalEditingFormat(context ,
                target.getTemporalCharacteristic(),
                target.getOffsetCharacteristic(),
                timePrecision,
                EditingFormatDirection.OUTPUT,
                editingPattern);

        var formattedTemporal = formatter.format(localTime);
        assertNotNull(formattedTemporal);
    }
```

### Enum declaration — `TimePrecision` (causeway/api/applib/src/main/java/org/apache/causeway/applib/annotation/TimePrecision.java)

```java
public enum TimePrecision {

    UNSPECIFIED,

    /**
     * 9 fractional digits for <i>Second</i>
     */
    NANO_SECOND,

    /**
     * 6 fractional digits for <i>Second</i>
     */
    MICRO_SECOND,

    /**
     * 3 fractional digits for <i>Second</i>
     */
    MILLI_SECOND,

    /**
     * <i>Second</i>
     */
    SECOND,

    /**
     * <i>Minute</i>
     */
    MINUTE,

    /**
     * <i>Hour</i>
     */
    HOUR;

}
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-029  ·  MethodSource

**项目** `Commons-CLI`  **文件** `commons-cli/src/test/java/org/apache/commons/cli/ConverterTests.java`  **测试** `testNumber`

### Test method

```java
@ParameterizedTest
    @MethodSource("numberTestParameters")
    void testNumber(final String str, final Number expected) throws Exception {
        if (expected != null) {
            assertEquals(expected, Converter.NUMBER.apply(str));
        } else {
            assertThrows(NumberFormatException.class, () -> Converter.NUMBER.apply(str));
        }
    }
```

### Parameter provider — 同文件内的 `numberTestParameters`

```java
    private static Stream<Arguments> numberTestParameters() {
        final List<Arguments> lst = new ArrayList<>();

        lst.add(Arguments.of("123", Long.valueOf("123")));
        lst.add(Arguments.of("12.3", Double.valueOf("12.3")));
        lst.add(Arguments.of("-123", Long.valueOf("-123")));
        lst.add(Arguments.of("-12.3", Double.valueOf("-12.3")));
        lst.add(Arguments.of(".3", Double.valueOf("0.3")));
        lst.add(Arguments.of("-.3", Double.valueOf("-0.3")));
        lst.add(Arguments.of("0x5F", null));
        lst.add(Arguments.of("2,3", null));
        lst.add(Arguments.of("1.2.3", null));

        return lst.stream();
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-032  ·  EnumSource

**项目** `Maven`  **文件** `maven/impl/maven-executor/src/test/java/org/apache/maven/cling/executor/impl/ToolboxToolTest.java`  **测试** `metadataPath3`

### Test method

```java
@ParameterizedTest
    @EnumSource(ExecutorHelper.Mode.class)
    void metadataPath3(ExecutorHelper.Mode mode) {
        ExecutorHelper helper =
                new HelperImpl(mode, mvn4Home(), userHome, EMBEDDED_MAVEN_EXECUTOR, FORKED_MAVEN_EXECUTOR);
        String path = new ToolboxTool(helper, Environment.TOOLBOX_VERSION)
                .metadataPath(getExecutorRequest(helper), "aopalliance", "someremote");
        System.out.println(mode.name() + ": " + path);
        // split repository: assert "ends with" as split may introduce prefixes
        assertTrue(path.endsWith("aopalliance" + File.separator + "maven-metadata-someremote.xml"), "path=" + path);
    }
```

### Enum declaration — `Mode` (maven/impl/maven-executor/src/main/java/org/apache/maven/cling/executor/ExecutorHelper.java)

```java
    enum Mode {
        /**
         * Automatically decide. For example, presence of {@link ExecutorRequest#environmentVariables()} or
         * {@link ExecutorRequest#jvmArguments()} will result in choosing {@link #FORKED} executor. Otherwise,
         * {@link #EMBEDDED} executor is preferred.
         */
        AUTO,
        /**
         * Forces embedded execution. May fail if {@link ExecutorRequest} contains input unsupported by executor.
         */
        EMBEDDED,
        /**
         * Forces forked execution. Always carried out, most isolated and "most correct", but is slow as it uses child process.
         */
        FORKED
    }
```

### Test-side helpers called by this test (2)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`mvn4Home`**

```java
    public Path mvn4Home() {
        return Paths.get(System.getProperty("maven4home"));
    }
```

**`getExecutorRequest`**

```java
    private ExecutorRequest.Builder getExecutorRequest(ExecutorHelper helper) {
        ExecutorRequest.Builder builder =
                helper.executorRequest().cwd(cwd).argument("-Daether.remoteRepositoryFilter.prefixes=false");
        if (System.getProperty("localRepository") != null) {
            builder.argument("-Dmaven.repo.local.tail=" + System.getProperty("localRepository"));
        }
        return builder;
    }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-035  ·  CsvSource

**项目** `Commons-Statistics`  **文件** `commons-statistics/commons-statistics-distribution/src/test/java/org/apache/commons/statistics/distribution/TruncatedNormalDistributionTest.java`  **测试** `testAdditionalMoments`

### Test method

```java
@ParameterizedTest
    @CsvSource({
        // Equal bounds
        "1.23, 1.23, 1.23, 0, 0, 0",
        "1.23, 4.56, 1.7122093853640246, 0.1739856461219162, 1e-15, 5e-15",
        // Effectively no truncation
        "-55, 60, 0, 1, 0, 0",
        // Long tail
        "-100, 101, 1.3443134677817230433408433600205167e-2172, 1, 1e-15, 1e-15",
        "-40, 101, 1.46327025083830317873709720033828097e-348, 1, 1e-15, 1e-15",
        "-30, 101, 1.47364613487854751904949326604507453e-196, 1, 1e-15, 1e-15",
        "-20, 101, 5.52094836215976318958273568278700042e-88, 1, 1e-15, 1e-15",
        "-10, 101, 7.69459862670641934633909221175249367e-23, 0.999999999999999999999230540137329438, 1e-15, 1e-15",
        "-5, 101, 1.48671994090490571244174411946057083e-06, 0.999992566398085139288753504945569711, 1e-15, 1e-15",
        "-1, 101, 0.287599970939178361228670127385217202, 0.629686285776605400861244494862843017, 1e-15, 1e-15",
        "0, 101, 0.797884560802865355879892119868763748, 0.363380227632418656924464946509942526, 1e-15, 1e-15",
        "1, 101, 1.52513527616098120908909053639057876, 0.199097665570348791553367979096726767, 1e-15, 1e-14",
        "5, 101, 5.18650396712584211561650896200523673, 0.032696434617112225345315807700917674, 1e-15, 1e-13",
        "10, 101, 10.0980932339625119628436416537120371, 0.00944537782565626116413681765035684208, 1e-15, 1e-11",
        "20, 101, 20.0497530685278505422140233087209891, 0.00246326161505216359968528619980015911, 1e-15, 1e-11",
        "30, 101, 30.033259667433677037071124100012257, 0.00110377151189009100113674138540728116, 1e-15, 1e-10",
        "40, 101, 40.0249688472072637232448709953697417, 0.000622668378591388773498879400697584317, 1e-15, 2e-9",
        "100, 101, 100.009998000999260705184902394575471, 9.99400499482634503612772420030347819e-05, 1e-15, 2e-8",
        // One-sided truncation
        "-5, Infinity, 1.4867199409049057124417441194605712e-06, 0.999992566398085139288753504945569711, 1e-14, 1e-14",
        "-3, Infinity, 0.00443783904212566379330210431090259846, 0.98666678845825919379095350748267984, 1e-15, 1e-15",
        "-1, Infinity, 0.287599970939178361228670127385217154, 0.629686285776605400861244494862843306, 1e-15, 1e-15",
        "0, Infinity, 0.797884560802865355879892119868763748, 0.363380227632418656924464946509942526, 1e-15, 1e-15",
        "1, Infinity, 1.52513527616098120908909053639057876, 0.199097665570348791553367979096726767, 1e-15, 1e-15",
        "3, Infinity, 3.28309865493043650692809222681220005, 0.0705591867852681168624020577420568271, 1e-15, 2e-14",
        "20, Infinity, 20.0497530685278505422140233087209891, 0.00246326161505216359968528619980015911, 1e-15, 1e-11",
        "100, Infinity, 100.009998000999260705184902394575471, 9.99400499482634503612772420030347819e-05, 1e-15, 4e-8",
        // The variance method is inaccurate at this extreme
        "1e4, Infinity, 10000.0000999999980000000999999925986, 9.99999940000005002391967510312099493e-09, 1e-15, 0.8",
        "1e6, Infinity, 1000000.00000099999999999800000000016, 9.99999999770471649802883928921316157e-13, 1e-15, 1.0",
        // XXX: The expected variance here is incorrect. It will be small but may be non zero.
        // The computation will return 0. This hits an edge case in the code that detects when the
        // variance computation fails.
        "1e100, Infinity, 1.00000000000000001590289110975991788e+100, 0, 1e-15, -1",
        // XXX: The expected variance here is incorrect. It will be small but may be non zero.
        // This hits an edge case where the computed variance (infinity) is above 1
        "1e290, 1e300, 1.00000000000000006172783352786715689e+290, 0, 1e-15, -1",
        // Small ranges.
        "1, 1.1000000000000001, 1.04912545221799091312759556239135752, 0.000832596851563726615564931035799390151, 1e-15, 2e-12",
        "5, 5.0999999999999996, 5.04581083165668427678725919870992629, 0.000822546087919772895415146023240560636, 1e-15, 2e-11",
        "35, 35.100000000000001, 35.025438801080858717764612789648226, 0.000494605845872597846399929727938197022, 1e-15, 2e-9",
        // (b-a) = 1 ULP
        // XXX: The expected variance here is incorrect.
        // It is upper limited to the variance of a uniform distribution.
        // The computation will return 0. This hits an edge case in the code that detects when the
        // variance computation fails.
        // Spans p=8.327e-17 of the parent normal distribution
        "1, 1.0000000000000002, 1.00000000000000011091535982917837267, 0, 1e-15, -1",
        // Spans p=1.626e-19 of the parent normal distribution
        "4, 4.0000000000000009, 4.00000000000000044406536771487238653, 0, 1e-15, -1",
        // Spans p=1.925e-37 of the parent normal distribution
        "10, 10.000000000000002, 10.0000000000000008883225369216741152, 0, 1e-15, -1",
        // Test for truncation close to zero.
        // At z <= ~1.5e-8, exp(-0.5 * z * z) / sqrt(2 pi) == 1 / sqrt(2 pi)
        // and the PDF is constant. It can be approximated as a uniform distribution.
        // Here the mean is computable but the variance computation -> 0.
        // The epsilons for the variance allow the test to pass if the second moment
        // uses a uniform distribution approximation: (b^3 - a^3) / (3b - 3a).
        // This is not done at present and the variance computes incorrectly and close to 0.
        // The largest span covers only 5.8242e-8 of the probability range of the parent normal
        // and these are not practical truncations.
        "-7.299454196351098e-8, 7.299454196351098e-8, 0, 1.77606771882092042827020676955306864e-15, 1e-15, -1e-15",
        "-7.299454196351098e-8, 3.649727098175549e-8, -1.82486354908777262111748030604612676e-08, 9.99038091836768051420202283759953002e-16, 1e-15, -1e-15",
        "-7.299454196351098e-8, 1.8248635490877744e-8, -2.7372953236316597672674778496667655e-08, 6.93776452664422342699175710737901419e-16, 1e-15, -2e-15",
        "-7.299454196351098e-8, 0, -3.64972709817554726791073610445021429e-08, 4.44016929705230343732389204118195096e-16, 1e-15, -2e-15",
        "-7.299454196351098e-8, -1.8248635490877744e-8, -4.56215887271943497112157190855901547e-08, 2.49759522957641055973442997155578316e-16, 3e-10, -5e-9",
        "-7.299454196351098e-8, -3.649727098175549e-8, -5.47459064726332272497430210977513379e-08, 1.11004232421306844799494326433537718e-16, 3e-10, -2e-8",
        "-3.649727098175549e-8, 3.649727098175549e-8, 0, 4.44016929705230343602092590994317462e-16, 1e-15, -1e-15",
        "-3.649727098175549e-8, 1.8248635490877744e-8, -9.12431774543886994224314381693928319e-09, 2.49759522959192087703300220816741702e-16, 1e-15, -1e-15",
        "-3.649727098175549e-8, 0, -1.82486354908777424165810069993271136e-08, 1.11004232426307600672725101668733634e-16, 1e-15, -2e-15",
        "-3.649727098175549e-8, -1.8248635490877744e-8, -2.73729532363166159037567578213044937e-08, 2.77510581119222125912321725734620803e-17, 3e-10, -2e-8",
        "-1.8248635490877744e-8, 1.8248635490877744e-8, 0, 1.11004232426307600757649604002272128e-16, 1e-15, -1e-15",
        "-1.8248635490877744e-8, 9.124317745438872e-9, -4.5621588727194358257035396943085424e-09, 6.24398807397980267185125584627689296e-17, 1e-15, -1e-15",
        "-1.8248635490877744e-8, 0, -9.12431774543887196791891930929818729e-09, 2.77510581065769011631256630479419225e-17, 1e-15, -1e-15",
        "-9.124317745438872e-9, 9.124317745438872e-9, 0, 2.77510581065769013145632047586655539e-17, 1e-15, -1e-15",
        "-9.124317745438872e-9, 4.562158872719436e-9, -2.28107943635971801967451582038414367e-09, 1.56099701849495071020338587207547036e-17, 1e-15, -1e-15",
        "-9.124317745438872e-9, 0, -4.5621588727194360789130116308534264e-09, 6.93776452664422554954584023114952882e-18, 1e-15, -1e-15",
        // The variance method is inaccurate at this extreme.
        // Spans p=8.858e-17 of the parent normal distribution
        "0, 2.220446049250313e-16, 1.11022302462515654042363166809081572e-16, 4.14074938043255708407035257655783112e-33, 1e-15, -1e-2",
    })
    void testAdditionalMoments(double lower, double upper,
                               double mean, double variance,
                               double meanRelativeError, double varianceRelativeError) {
        assertMean(lower, upper, mean, meanRelativeError);
        if (varianceRelativeError < 0) {
            // Known problem case.
            // Allow small absolute variances using an absolute threshold of
            // machine epsilon (2^-52) * 1.5. Any true variance approaching machine epsilon
            // is allowed to be computed as small or zero but cannot be too large.
            final double v = TruncatedNormalDistribution.variance(lower, upper);
            Assertions.assertTrue(v >= 0, () -> "Variance is not positive: " + v);
            Assertions.assertEquals(v, TruncatedNormalDistribution.variance(-upper, -lower));
            TestUtils.assertEquals(variance, v,
                    createAbsOrRelTolerance(1.5 * 0x1.0p-52, -varianceRelativeError),
                () -> String.format("variance(%s, %s)", lower, upper));
        } else {
            assertVariance(lower, upper, variance, varianceRelativeError);
        }
    }
```

### Test-side helpers called by this test (2)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`assertMean`**

```java
    private static void assertMean(double lower, double upper, double expected, double eps) {
        final double mean = TruncatedNormalDistribution.moment1(lower, upper);
        Assertions.assertEquals(0 - mean, TruncatedNormalDistribution.moment1(-upper, -lower));
        TestUtils.assertEquals(expected, mean, DoubleTolerances.relative(eps),
            () -> String.format("mean(%s, %s)", lower, upper));
    }
```

**`assertVariance`**

```java
    private static void assertVariance(double lower, double upper, double expected, double eps) {
        final double variance = TruncatedNormalDistribution.variance(lower, upper);
        Assertions.assertEquals(variance, TruncatedNormalDistribution.variance(-upper, -lower));
        TestUtils.assertEquals(expected, variance, DoubleTolerances.relative(eps),
            () -> String.format("variance(%s, %s)", lower, upper));
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-038  ·  MethodSource

**项目** `commons-rng`  **文件** `commons-rng/commons-rng-simple/src/test/java/org/apache/commons/rng/simple/internal/IntArray2LongArrayTest.java`  **测试** `testSeedSizeIsMultipleOfIntSize`

### Test method

```java
@ParameterizedTest
    @MethodSource(value = {"getLengths"})
    void testSeedSizeIsMultipleOfIntSize(int ints) {
        final int[] seed = new int[ints];

        final long[] out = new IntArray2LongArray().convert(seed);
        Assertions.assertEquals(getOutputLength(ints), out.length);
    }
```

### Parameter provider — 同文件内的 `getLengths`

```java
    static IntStream getLengths() {
        return IntStream.rangeClosed(0, (Long.BYTES / Integer.BYTES) * 2);
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`getOutputLength`**

```java
    private static int getOutputLength(int ints) {
        return (int) Math.ceil((double) ints / 2);
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-041  ·  ValueSource

**项目** `Commons-CLI`  **文件** `commons-cli/src/test/java/org/apache/commons/cli/HelpFormatterTest.java`  **测试** `testDeprecatedPrintOptionsZeroWidth`

### Test method

```java
@ParameterizedTest
    @ValueSource(ints = { -100, -1, 0 })
    void testDeprecatedPrintOptionsZeroWidth(final int width) {
        final Options options = new Options();
        options.addOption("h", "help", false, "Show help");
        final StringWriter out = new StringWriter();
        final PrintWriter pw = new PrintWriter(out);
        new HelpFormatter().printOptions(pw, width, options, 1, 3);
        final String result = out.toString();
        assertNotNull(result);
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-044  ·  ValueSource

**项目** `NiFi`  **文件** `nifi/nifi-commons/nifi-json-utils/src/test/java/org/apache/nifi/processor/TestJsonValidator.java`  **测试** `testInvalidJson`

### Test method

```java
@ParameterizedTest
    @ValueSource(strings = {"\"Name\" : \"Smith, John\"", "bncjbhjfjhj"})
    public void testInvalidJson(String invalidJson) {
        ValidationResult validationResult = validator.validate(JSON_PROPERTY, invalidJson, context);
        assertFalse(validationResult.isValid());
        assertTrue(validationResult.getExplanation().contains("not a valid JSON representation"));
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-047  ·  EnumSource

**项目** `Hadoop`  **文件** `hadoop/hadoop-hdfs-project/hadoop-hdfs/src/test/java/org/apache/hadoop/hdfs/web/TestWebHdfsTimeouts.java`  **测试** `testRedirectReadTimeout`

### Test method

```java
@MethodSource("data")
  @ParameterizedTest
  @EnumSource(TimeoutSource.class)
  @Timeout(value = 100)
  public void testRedirectReadTimeout(TimeoutSource src) throws Exception {
    setUp(src);
    startSingleTemporaryRedirectResponseThread(false);
    try {
      fs.getFileChecksum(new Path("/file"));
      fail("expected timeout");
    } catch (SocketTimeoutException e) {
      GenericTestUtils.assertExceptionContains(
          fs.getUri().getAuthority() + ": Read timed out", e);
    }
  }
```

### Enum declaration — `TimeoutSource` (hadoop/hadoop-hdfs-project/hadoop-hdfs/src/test/java/org/apache/hadoop/hdfs/web/TestWebHdfsTimeouts.java)

```java
  public enum TimeoutSource { ConnectionFactory, Configuration }
```

### Test-side helpers called by this test (5)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`setUp`**

```java
  public void setUp(TimeoutSource timeoutSource) throws Exception {
    Configuration conf = WebHdfsTestUtil.createConf();
    serverSocket = new ServerSocket(0, CONNECTION_BACKLOG);
    nnHttpAddress = new InetSocketAddress("localhost", serverSocket.getLocalPort());
    conf.set(DFSConfigKeys.DFS_NAMENODE_HTTP_ADDRESS_KEY, "localhost:" + serverSocket.getLocalPort());
    if (timeoutSource == TimeoutSource.Configuration) {
      String v = Integer.toString(SHORT_SOCKET_TIMEOUT) + "ms";
      conf.set(HdfsClientConfigKeys.DFS_WEBHDFS_SOCKET_CONNECT_TIMEOUT_KEY, v);
      conf.set(HdfsClientConfigKeys.DFS_WEBHDFS_SOCKET_READ_TIMEOUT_KEY, v);
    }

    fs = WebHdfsTestUtil.getWebHdfsFileSystem(conf, WebHdfsConstants.WEBHDFS_SCHEME);
    if (timeoutSource == TimeoutSource.ConnectionFactory) {
      fs.connectionFactory = connectionFactory;
    }

    clients = new ArrayList<SocketChannel>();
    serverThread = null;
    failedToConsumeBacklog = false;
  }
```

**`startSingleTemporaryRedirectResponseThread`**

```java
  private void startSingleTemporaryRedirectResponseThread(
      final boolean consumeConnectionBacklog) {
    fs.connectionFactory = URLConnectionFactory.DEFAULT_SYSTEM_CONNECTION_FACTORY;
    serverThread = new Thread() {
      @Override
      public void run() {
        Socket clientSocket = null;
        OutputStream out = null;
        InputStream in = null;
        InputStreamReader isr = null;
        BufferedReader br = null;
        try {
          // Accept one and only one client connection.
          clientSocket = serverSocket.accept();

          // Immediately setup conditions for subsequent connections.
          fs.connectionFactory = connectionFactory;
          if (consumeConnectionBacklog) {
            consumeConnectionBacklog();
          }

          // Consume client's HTTP request by reading until EOF or empty line.
          in = clientSocket.getInputStream();
          isr = new InputStreamReader(in);
          br = new BufferedReader(isr);
          for (;;) {
            String line = br.readLine();
            if (line == null || line.isEmpty()) {
              break;
            }
          }

          // Write response.
          out = clientSocket.getOutputStream();
          out.write(temporaryRedirect().getBytes(StandardCharsets.UTF_8));
        } catch (IOException e) {
          // Fail the test on any I/O error in the server thread.
          LOG.error("unexpected IOException in server thread", e);
          fail("unexpected IOException in server thread: " + e);
        } finally {
          // Clean it all up.
          IOUtils.cleanupWithLogger(LOG, br, isr, in, out);
          IOUtils.closeSocket(clientSocket);
        }
      }
    };
    serverThread.start();
  }
```

**`run`**

```java
@Override
      public void run() {
        Socket clientSocket = null;
        OutputStream out = null;
        InputStream in = null;
        InputStreamReader isr = null;
        BufferedReader br = null;
        try {
          // Accept one and only one client connection.
          clientSocket = serverSocket.accept();

          // Immediately setup conditions for subsequent connections.
          fs.connectionFactory = connectionFactory;
          if (consumeConnectionBacklog) {
            consumeConnectionBacklog();
          }

          // Consume client's HTTP request by reading until EOF or empty line.
          in = clientSocket.getInputStream();
          isr = new InputStreamReader(in);
          br = new BufferedReader(isr);
          for (;;) {
            String line = br.readLine();
            if (line == null || line.isEmpty()) {
              break;
            }
          }

          // Write response.
          out = clientSocket.getOutputStream();
          out.write(temporaryRedirect().getBytes(StandardCharsets.UTF_8));
        } catch (IOException e) {
          // Fail the test on any I/O error in the server thread.
          LOG.error("unexpected IOException in server thread", e);
          fail("unexpected IOException in server thread: " + e);
        } finally {
          // Clean it all up.
          IOUtils.cleanupWithLogger(LOG, br, isr, in, out);
          IOUtils.closeSocket(clientSocket);
        }
      }
```

**`consumeConnectionBacklog`**

```java
  private void consumeConnectionBacklog() throws IOException {
    for (int i = 0; i < CLIENTS_TO_CONSUME_BACKLOG; ++i) {
      SocketChannel client = SocketChannel.open();
      client.configureBlocking(false);
      client.connect(nnHttpAddress);
      clients.add(client);
    }
    try {
      GenericTestUtils.waitFor(() -> {
        try (SocketChannel c = SocketChannel.open()) {
          c.socket().connect(nnHttpAddress, 100);
        } catch (SocketTimeoutException e) {
          return true;
        } catch (IOException e) {
          LOG.debug("unexpected exception: " + e);
        }
        return false;
      }, 100, 10000);
    } catch (TimeoutException | InterruptedException e) {
      failedToConsumeBacklog = true;
      assumeBacklogConsumed();
    }
  }
```

**`temporaryRedirect`**

```java
  private String temporaryRedirect() {
    return "HTTP/1.1 307 Temporary Redirect\r\n" +
      "Location: http://" + NetUtils.getHostPortString(nnHttpAddress) + "\r\n" +
      "\r\n";
  }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-050  ·  MethodSource

**项目** `Commons-BCEL`  **文件** `commons-bcel/src/test/java/org/apache/bcel/verifier/VerifyJavaHomesTest.java`  **测试** `testJarEntryClassName`

### Test method

```java
@Disabled("Run once in a while, it takes a very long time.")
    @ParameterizedTest
    @MethodSource("org.apache.bcel.generic.JavaHome#streamJarEntryClassName")
    void testJarEntryClassName(final String name) throws ClassNotFoundException {
        // System.out.println(jarEntry.getName());
        // Skip $ classes for now
        count++;
        if (logStep) {
            System.out.printf("%,d %s%n", count, name);
        } else if (!logQuiet) {
            if (count % 10 == 0) {
                System.out.print('.');
            }
            if (count % 800 == 0) {
                System.out.println();
                System.out.print(count);
            }
        }
        if (!name.contains("$")) {
            assertTrue(doAllPasses(name));
        }
    }
```

### Parameter provider — `JavaHome#streamJarEntryClassName`（commons-bcel/src/test/java/org/apache/bcel/generic/JavaHome.java）

```java
    public static Stream<String> streamJarEntryClassName() {
        return streamJavaHome().flatMap(JavaHome::streamJarEntryByExtClassName);
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-053  ·  MethodSource

**项目** `Commons-CLI`  **文件** `commons-cli/src/test/java/org/apache/commons/cli/TypeHandlerTest.java`  **测试** `testCreateDate`

### Test method

```java
@ParameterizedTest
    @MethodSource("createDateFixtures")
    @DefaultLocale(language = "en", country = "US")
    void testCreateDate(final Date date) {
        assertEquals(date, TypeHandler.createDate(date.toString()));
    }
```

### Parameter provider — 同文件内的 `createDateFixtures`

```java
    private static Stream<Date> createDateFixtures() {
        return Stream.of(Date.from(Instant.EPOCH), Date.from(Instant.ofEpochSecond(0)), Date.from(Instant.ofEpochSecond(40_000)));

    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-056  ·  MethodSource

**项目** `Druid`  **文件** `druid/multi-stage-query/src/test/java/org/apache/druid/msq/exec/MSQInsertTest.java`  **测试** `testInsertOnFoo1WithTimePostAggregator`

### Test method

```java
@MethodSource("data")
  @ParameterizedTest(name = "{index}:with context {0}")
  public void testInsertOnFoo1WithTimePostAggregator(String contextName, Map<String, Object> context)
  {
    RowSignature rowSignature = RowSignature.builder()
                                            .add("__time", ColumnType.LONG)
                                            .add("sum_m1", ColumnType.DOUBLE)
                                            .build();

    testIngestQuery().setSql(
                         "INSERT INTO foo1 "
                         + "SELECT DATE_TRUNC('DAY', TIMESTAMP '2000-01-01' - INTERVAL '1'DAY) AS __time, SUM(m1) AS sum_m1 "
                         + "FROM foo "
                         + "PARTITIONED BY DAY"
                     )
                     .setExpectedDataSource("foo1")
                     .setExpectedRowSignature(rowSignature)
                     .setQueryContext(context)
                     .setExpectedSegments(
                         ImmutableSet.of(
                             SegmentId.of("foo1", Intervals.of("1999-12-31T/P1D"), "test", 0)
                         )
                     )
                     .setExpectedResultRows(
                         ImmutableList.of(
                             new Object[]{946598400000L, 21.0}
                         )
                     )
                     .verifyResults();

  }
```

### Parameter provider — 同文件内的 `data`

```java
  public static Collection<Object[]> data()
  {
    Object[][] data = new Object[][]{
        {DEFAULT, DEFAULT_MSQ_CONTEXT},
        {SUPERUSER, SUPERUSER_MSQ_CONTEXT},
        {DURABLE_STORAGE, DURABLE_STORAGE_MSQ_CONTEXT},
        {FAULT_TOLERANCE, FAULT_TOLERANCE_MSQ_CONTEXT},
        {PARALLEL_MERGE, PARALLEL_MERGE_MSQ_CONTEXT},
        {WITH_APPEND_LOCK, QUERY_CONTEXT_WITH_APPEND_LOCK}
    };
    return Arrays.asList(data);
  }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-059  ·  MethodSource

**项目** `POI`  **文件** `poi/poi/src/test/java/org/apache/poi/ss/formula/eval/TestFormulasFromSpreadsheet.java`  **测试** `processFunctionRow`

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
       for (int colnum=SS.COLUMN_INDEX_FIRST_TEST_VALUE; colnum < endcolnum; colnum++) {
           Cell c = formulasRow.getCell(colnum);
           if (c == null || c.getCellType() != CellType.FORMULA) {
               continue;
           }

           CellValue actValue = evaluator.evaluate(c);
           Cell expValue = (expectedValuesRow == null) ? null : expectedValuesRow.getCell(colnum);

           String msg = String.format(Locale.ROOT, "Function '%s': Formula: %s @ %d:%d (%s)"
                   , targetFunctionName, c.getCellFormula(), formulasRow.getRowNum(), colnum,
                   new CellReference(formulasRow.getRowNum(), colnum).formatAsString());

           assertNotNull(expValue, msg + " - Bad setup data expected value is null");
           assertNotNull(actValue, msg + " - actual value was null");

           final CellType cellType = expValue.getCellType();
           msg += ", cellType: " + cellType + ", actCellType: " + actValue.getCellType() + ": " + actValue.formatAsString();

           switch (cellType) {
               case BLANK:
                   assertEquals(CellType.BLANK, actValue.getCellType(), msg);
                   break;
               case BOOLEAN:
                   assertEquals(CellType.BOOLEAN, actValue.getCellType(), msg);
                   assertEquals(expValue.getBooleanCellValue(), actValue.getBooleanValue(), msg);
                   break;
               case ERROR:
                   assertEquals(CellType.ERROR, actValue.getCellType(), msg);
                   assertEquals(ErrorEval.getText(expValue.getErrorCellValue()), ErrorEval.getText(actValue.getErrorValue()), msg);
                   break;
               case FORMULA: // will never be used, since we will call method after formula evaluation
                   fail("Cannot expect formula as result of formula evaluation: " + msg);
               case NUMERIC:
                   assertEquals(CellType.NUMERIC, actValue.getCellType(), msg);
                   final double tolerance = targetFunctionName.equalsIgnoreCase("RATE")
                           ? 0.000001 : TestMathX.DIFF_TOLERANCE_FACTOR;
                   TestMathX.assertDouble(msg, expValue.getNumericCellValue(), actValue.getNumberValue(), TestMathX.POS_ZERO, tolerance);
                   break;
               case STRING:
                   assertEquals(CellType.STRING, actValue.getCellType(), msg);
                   assertEquals(expValue.getRichStringCellValue().getString(), actValue.getStringValue(), msg);
                   break;
               default:
                   fail("Unexpected cell type: " + cellType);
           }
       }
   }
```

### Parameter provider — 同文件内的 `data`

```java
    public static Stream<Arguments> data() {
        // Function "Text" uses custom-formats which are locale specific
        // can't set the locale on a per-testrun execution, as some settings have been
        // already set, when we would try to change the locale by then
        userLocale = LocaleUtil.getUserLocale();
        LocaleUtil.setUserLocale(Locale.ROOT);

        workbook = HSSFTestDataSamples.openSampleWorkbook(SS.FILENAME);
        sheet = workbook.getSheetAt( 0 );
        evaluator = new HSSFFormulaEvaluator(workbook);

        List<Arguments> data = new ArrayList<>();

        processFunctionGroup(data, SS.START_OPERATORS_ROW_INDEX);
        processFunctionGroup(data, SS.START_FUNCTIONS_ROW_INDEX);
        // example for debugging individual functions/operators:
        // processFunctionGroup(data, SS.START_OPERATORS_ROW_INDEX, "ConcatEval");
        // processFunctionGroup(data, SS.START_FUNCTIONS_ROW_INDEX, "Text");

        return data.stream();
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-062  ·  MethodSource

**项目** `mina-sshd`  **文件** `mina-sshd/sshd-sftp/src/test/java/org/apache/sshd/sftp/client/SftpVersionsTest.java`  **测试** `sftpOpenFlags`

### Test method

```java
@MethodSource("parameters")
    @ParameterizedTest(name = "version={0}") // See SSHD-749
    public void sftpOpenFlags(int version) throws Exception {
        initSftpVersionsTest(version);
        Path targetPath = detectTargetFolder();
        Path lclSftp
                = CommonTestSupportUtils.resolve(targetPath, SftpConstants.SFTP_SUBSYSTEM_NAME, getClass().getSimpleName());
        Path lclParent = assertHierarchyTargetFolderExists(lclSftp);
        Path lclFile = lclParent.resolve(getCurrentTestName() + "-" + getTestedVersion() + ".txt");
        Files.deleteIfExists(lclFile);

        Path parentPath = targetPath.getParent();
        String remotePath = CommonTestSupportUtils.resolveRelativeRemotePath(parentPath, lclFile);
        try (ClientSession session = createAuthenticatedClientSession();
             SftpClient sftp = createSftpClient(session, getTestedVersion())) {
            try (OutputStream out = sftp.write(remotePath, OpenMode.Create, OpenMode.Write)) {
                out.write(getCurrentTestName().getBytes(StandardCharsets.UTF_8));
            }
            assertTrue(Files.exists(lclFile), "File should exist on disk: " + lclFile);
            sftp.remove(remotePath);
        }
    }
```

### Parameter provider — 同文件内的 `parameters`

```java
    public static Collection<Object[]> parameters() {
        return parameterize(VERSIONS);
    }
```

### Test-side helpers called by this test (3)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`initSftpVersionsTest`**

```java
    public void initSftpVersionsTest(int version) throws Exception {
        testVersion = version;
        setUp();
    }
```

**`getTestedVersion`**

```java
    public final int getTestedVersion() {
        return testVersion;
    }
```

**`setUp`**

```java
    void setUp() throws Exception {
        setupServer();

        Map<String, Object> props = sshd.getProperties();
        Object forced = props.remove(SftpModuleProperties.SFTP_VERSION.getName());
        if (forced != null) {
            outputDebugMessage("Removed forced version=%s", forced);
        }
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-065  ·  ValueSource

**项目** `Commons-BCEL`  **文件** `commons-bcel/src/test/java/org/apache/bcel/util/BCELifierTest.java`  **测试** `testBinaryOp`

### Test method

```java
@ParameterizedTest
    @ValueSource(strings = {
    // @formatter:off
        "iadd 3 2 = 5",
        "isub 3 2 = 1",
        "imul 3 2 = 6",
        "idiv 3 2 = 1",
        "irem 3 2 = 1",
        "iand 3 2 = 2",
        "ior 3 2 = 3",
        "ixor 3 2 = 1",
        "ishl 4 1 = 8",
        "ishr 4 1 = 2",
        "iushr 4 1 = 2",
        "ladd 3 2 = 5",
        "lsub 3 2 = 1",
        "lmul 3 2 = 6",
        "ldiv 3 2 = 1",
        "lrem 3 2 = 1",
        "land 3 2 = 2",
        "lor 3 2 = 3",
        "lxor 3 2 = 1",
        "lshl 4 1 = 8",
        "lshr 4 1 = 2",
        "lushr 4 1 = 2",
        "fadd 3 2 = 5.0",
        "fsub 3 2 = 1.0",
        "fmul 3 2 = 6.0",
        "fdiv 3 2 = 1.5",
        "frem 3 2 = 1.0",
        "dadd 3 2 = 5.0",
        "dsub 3 2 = 1.0",
        "dmul 3 2 = 6.0",
        "ddiv 3 2 = 1.5",
        "drem 3 2 = 1.0"
    // @formatter:on
    })
    void testBinaryOp(final String exp) throws Exception {
        BinaryOpCreator.main(new String[] {});
        final File workDir = new File("target");
        final Pattern pattern = Pattern.compile("([a-z]{3,5}) ([-+]?\\d*\\.?\\d+) ([-+]?\\d*\\.?\\d+) = ([-+]?\\d*\\.?\\d+)");
        final Matcher matcher = pattern.matcher(exp);
        assertTrue(matcher.matches());
        final String op = matcher.group(1);
        final String a = matcher.group(2);
        final String b = matcher.group(3);
        final String expected = matcher.group(4);
        final String javaAgent = getJavaAgent();
        if (javaAgent == null) {
            assertEquals(expected + EOL, exec(workDir, getAppJava(), "-cp", CLASSPATH, "org.apache.bcel.generic.BinaryOp", op, a, b));
        } else {
            final String runtimeExecJavaAgent = javaAgent.replace("jacoco.exec", "jacoco_org.apache.bcel.generic.BinaryOp.exec");
            assertEquals(expected + EOL, exec(workDir, getAppJava(), runtimeExecJavaAgent, "-cp", CLASSPATH, "org.apache.bcel.generic.BinaryOp", op, a, b));
        }
    }
```

### Test-side helpers called by this test (3)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`exec`**

```java
    private String exec(final File workDir, final String... args) throws Exception {
        // System.out.print(workDir + ": ");
        // Stream.of(args).forEach(e -> System.out.print(e + " "));
        // System.out.println();
        final ProcessBuilder pb = new ProcessBuilder(args);
        pb.directory(workDir);
        pb.redirectErrorStream(true);
        final Process proc = pb.start();
        try (BufferedInputStream is = new BufferedInputStream(proc.getInputStream())) {
            final byte[] buff = new byte[2048];
            int len;

            final StringBuilder sb = new StringBuilder();
            while ((len = is.read(buff)) != -1) {
                sb.append(new String(buff, 0, len));
            }
            final String output = sb.toString();
            assertEquals(0, proc.waitFor(), output);
            return output;
        }
    }
```

**`getAppJava`**

```java
    private String getAppJava() {
        return getJavaHomeApp("java");
    }
```

**`getJavaHomeApp`**

```java
    private String getJavaHomeApp(final String app) {
        final Path path = getJavaHomeBinPath().resolve(app);
        if (Files.exists(path)) {
            return path.toAbsolutePath().toString();
        }
        if (SystemUtils.IS_OS_WINDOWS && Files.exists(getJavaHomeBinPath().resolve(app + ".exe"))) {
            return path.toAbsolutePath().toString();
        }
        return app;
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-068  ·  EnumSource

**项目** `Druid`  **文件** `druid/processing/src/test/java/org/apache/druid/query/metadata/SegmentMetadataQueryQueryToolChestTest.java`  **测试** `testProjections`

### Test method

```java
@EnumSource(AggregatorMergeStrategy.class)
  @ParameterizedTest(name = "{index}: with AggregatorMergeStrategy {0}")
  public void testProjections(AggregatorMergeStrategy aggregatorMergeStrategy)
  {
    final SegmentAnalysis analysis1 = new SegmentAnalysis.Builder(TEST_SEGMENT_ID1)
        .projection("channel_sum", new AggregateProjectionMetadata(PROJECTION_CHANNEL_ADDED_HOURLY, 100))
        .build();
    final SegmentAnalysis analysis2 = new SegmentAnalysis.Builder(TEST_SEGMENT_ID2)
        .projection("channel_sum", new AggregateProjectionMetadata(PROJECTION_CHANNEL_ADDED_HOURLY, 200))
        .build();

    final SegmentAnalysis expected = new SegmentAnalysis.Builder(
        "dummy_2021-01-01T00:00:00.000Z_2021-01-02T00:00:00.000Z_merged")
        .projection("channel_sum", new AggregateProjectionMetadata(PROJECTION_CHANNEL_ADDED_HOURLY, 300))
        .build();
    Assert.assertEquals(expected, mergeWithStrategy(analysis1, analysis2, aggregatorMergeStrategy));
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

## IRR-071  ·  ValueSource

**项目** `HttpComponents-Client`  **文件** `httpcomponents-client/httpclient5-testing/src/test/java/org/apache/hc/client5/testing/async/TestClassicOverAsync.java`  **测试** `testSequentialGetRequestsStreaming`

### Test method

```java
@ValueSource(ints = {0, 2048, 10240})
    @ParameterizedTest(name = "{displayName}; content length: {0}")
    void testSequentialGetRequestsStreaming(final int contentSize) throws Exception {
        configureServer(bootstrap -> bootstrap.register("/random/*", AsyncRandomHandler::new));
        final HttpHost target = startServer();
        final CloseableHttpClient client = startClient();
        final int n = 10;
        for (int i = 0; i < n; i++) {
            final AtomicReference<MockInputStream> contentRef = new AtomicReference<>();
            final MockHttpEntityWrapper result = (MockHttpEntityWrapper) client.execute(
                    ClassicRequestBuilder.get()
                            .setHttpHost(target)
                            .setPath("/random/" + contentSize)
                            .build(),
                    response -> {
                        Assertions.assertEquals(200, response.getCode());
                        final MockHttpEntityWrapper entity = new MockHttpEntityWrapper(response.getEntity(), true);
                        contentRef.set((MockInputStream) entity.getContent());
                        response.setEntity(entity);
                        return response.getEntity();
                    });
            // The plain use case where the entity and its input stream are closed.
            Assertions.assertTrue(result.closed);
            Assertions.assertTrue(contentRef.get().closed);
        }
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`getContent`**

```java
@Override
        public synchronized InputStream getContent() throws IOException {
            return content;
        }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-074  ·  MethodSource

**项目** `Calcite`  **文件** `calcite/testkit/src/main/java/org/apache/calcite/test/SqlOperatorTest.java`  **测试** `testCastStringToDecimal`

### Test method

```java
@ParameterizedTest
  @MethodSource("safeParameters")
  void testCastStringToDecimal(CastType castType, SqlOperatorFixture f) {
    f.setFor(SqlStdOperatorTable.CAST, VmName.EXPAND);
    // string to decimal
    f.checkScalarExact("cast('1.29' as decimal(2,1))",
        "DECIMAL(2, 1) NOT NULL",
        "1.2");
    f.checkScalarExact("cast(' 1.25 ' as decimal(2,1))",
        "DECIMAL(2, 1) NOT NULL",
        "1.2");
    f.checkScalarExact("cast('1.21' as decimal(2,1))",
        "DECIMAL(2, 1) NOT NULL",
        "1.2");
    f.checkScalarExact("cast(' -1.29 ' as decimal(2,1))",
        "DECIMAL(2, 1) NOT NULL",
        "-1.2");
    f.checkScalarExact("cast('-1.25' as decimal(2,1))",
        "DECIMAL(2, 1) NOT NULL",
        "-1.2");
    f.checkScalarExact("cast(' -1.21 ' as decimal(2,1))",
        "DECIMAL(2, 1) NOT NULL",
        "-1.2");
    String shouldFail = "cast(' -1.21e' as decimal(2,1))";
    if (castType == CastType.CAST) {
      f.checkFails(shouldFail, INVALID_CHAR_MESSAGE, true);
    } else {
      // safe casts never fail
      f.checkNull(shouldFail);
    }
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

## IRR-077  ·  EnumSource

**项目** `Causeway`  **文件** `causeway/commons/src/test/java/org/apache/causeway/commons/collections/CanTest.java`  **测试** `toMap_emptyCan`

### Test method

```java
@ParameterizedTest
    @EnumSource(MapScenario.class)
    void toMap_emptyCan(final MapScenario scenario) {
        final Can<Customer> origin = Can.empty();
        var map = scenario.toMapConverterUnderTest.apply(origin);
        assertNotNull(map);
        assertEquals(0, map.size());
        scenario.assertUnmodifiable(map);
    }
```

### Enum declaration — `MapScenario` (causeway/commons/src/test/java/org/apache/causeway/commons/collections/CanTest.java)

```java
    enum MapScenario {
        HASH_MAP(customers->customers.toMap(Customer::name)),
        TREE_MAP(customers->customers.toMap(Customer::name, (a, b)->a, TreeMap::new));
        final Function<Can<Customer>, Map<String, Customer>> toMapConverterUnderTest;
        void assertUnmodifiable(final Map<String, Customer> map) {
            assertThrows(Exception.class, ()->{
                map.put("John", new Customer("John"));
            });
        }
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`assertUnmodifiable`**

```java
        void assertUnmodifiable(final Map<String, Customer> map) {
            assertThrows(Exception.class, ()->{
                map.put("John", new Customer("John"));
            });
        }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-080  ·  MethodSource

**项目** `Hive`  **文件** `hive/ql/src/test/org/apache/hadoop/hive/ql/io/parquet/serde/TestParquetTimestampsHive2Compatibility.java`  **测试** `testWriteHive2ReadHive2`

### Test method

```java
@ParameterizedTest(name = "{0}")
  @MethodSource("generateTimestamps")
  void testWriteHive2ReadHive2(String timestampString) {
    NanoTime nt = writeHive2(timestampString);
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

## IRR-083  ·  MethodSource

**项目** `ozone`  **文件** `ozone/hadoop-ozone/ozone-manager/src/test/java/org/apache/hadoop/ozone/om/snapshot/filter/TestReclaimableFilter.java`  **测试** `testInitWithInactiveSnapshots`

### Test method

```java
@ParameterizedTest
  @MethodSource("testInvalidSnapshotArgs")
  public void testInitWithInactiveSnapshots(
      int numberOfPreviousSnapshotsFromChain, int actualNumberOfSnapshots, int index, int snapIndex)
      throws IOException, RocksDBException {
    SnapshotInfo currentSnapshotInfo = setup(numberOfPreviousSnapshotsFromChain, actualNumberOfSnapshots, index,
        1, 1, (snapshotInfo) -> {
          if (snapshotInfo.getVolumeName().equals(getVolumes().get(0)) &&
              snapshotInfo.getBucketName().equals(getBuckets().get(0))
              && snapshotInfo.getName().equals("snap" + snapIndex)) {
            snapshotInfo.setSnapshotStatus(SnapshotInfo.SnapshotStatus.SNAPSHOT_DELETED);
          }
          return snapshotInfo;
        }, BucketLayout.FILE_SYSTEM_OPTIMIZED);

    AtomicReference<String> volume = new AtomicReference<>(getVolumes().get(0));
    AtomicReference<String> bucket = new AtomicReference<>(getBuckets().get(0));
    int endIndex = Math.min(index - 1, actualNumberOfSnapshots - 1);
    int beginIndex = Math.max(0, endIndex - numberOfPreviousSnapshotsFromChain + 1);
    if (snapIndex < beginIndex || snapIndex > endIndex) {
      testSnapshotInitAndLocking(volume.get(), bucket.get(), numberOfPreviousSnapshotsFromChain, index,
          currentSnapshotInfo, true, true);
      testSnapshotInitAndLocking(volume.get(), bucket.get(), numberOfPreviousSnapshotsFromChain, index,
          currentSnapshotInfo, false, false);
    } else {
      IOException ex = assertThrows(IOException.class, () ->
          testSnapshotInitAndLocking(volume.get(), bucket.get(), numberOfPreviousSnapshotsFromChain, index,
              currentSnapshotInfo, true, true));

      assertEquals(String.format("Unable to load snapshot. Snapshot with table key '/%s/%s/%s' is no longer active",
          volume.get(), bucket.get(), "snap" + snapIndex), ex.getMessage());
    }
  }
```

### Parameter provider — 同文件内的 `testInvalidSnapshotArgs`

```java
  List<Arguments> testInvalidSnapshotArgs() {
    List<Arguments> arguments = testReclaimableFilterArguments();
    return arguments.stream().flatMap(args -> IntStream.range(0, (int) args.get()[1])
            .mapToObj(i -> Arguments.of(args.get()[0], args.get()[1], args.get()[2], i)))
        .collect(Collectors.toList());
  }
```

### Test-side helpers called by this test (3)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`getVolumeName`**

```java
@Override
      protected String getVolumeName(Table.KeyValue<String, Boolean> keyValue) throws IOException {
        return keyValue.getKey().split("/")[0];
      }
```

**`getBucketName`**

```java
@Override
      protected String getBucketName(Table.KeyValue<String, Boolean> keyValue) throws IOException {
        return keyValue.getKey().split("/")[1];
      }
```

**`testSnapshotInitAndLocking`**

```java
  private void testSnapshotInitAndLocking(
      String volume, String bucket, int numberOfPreviousSnapshotsFromChain, int index, SnapshotInfo currentSnapshotInfo,
      Boolean reclaimable, Boolean expectedReturnValue) throws IOException {
    List<SnapshotInfo> infos = getLastSnapshotInfos(volume, bucket, numberOfPreviousSnapshotsFromChain, index);
    assertEquals(expectedReturnValue,
        getReclaimableFilter().apply(Table.newKeyValue(getKey(volume, bucket), reclaimable)));
    Assertions.assertEquals(infos, getReclaimableFilter().getPreviousSnapshotInfos());
    Assertions.assertEquals(infos.size(), getReclaimableFilter().getPreviousOmSnapshots().size());
    Assertions.assertEquals(infos.stream().map(si -> si == null ? null : si.getSnapshotId())
        .collect(Collectors.toList()), getReclaimableFilter().getPreviousOmSnapshots().stream()
        .map(i -> i == null ? null : ((UncheckedAutoCloseableSupplier<OmSnapshot>) i).get().getSnapshotID())
        .collect(Collectors.toList()));
    infos.add(currentSnapshotInfo);
    Assertions.assertEquals(infos.stream().filter(Objects::nonNull).map(SnapshotInfo::getSnapshotId).collect(
        Collectors.toList()), getLockIds().get());
  }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-086  ·  ValueSource

**项目** `Hadoop`  **文件** `hadoop/hadoop-tools/hadoop-gcp/src/test/java/org/apache/hadoop/fs/gs/TestStorageResourceId.java`  **测试** `testFromStringPathObject`

### Test method

```java
@ParameterizedTest
  @ValueSource(strings = {
      "gs://my-bucket/object",
      "gs://my-bucket/folder/file.txt",
      "gs://my-bucket/folder/"
  })
  public void testFromStringPathObject(String path) {
    String expectedBucket = path.split("/")[2];
    String expectedObject =
        path.substring(path.indexOf(expectedBucket) + expectedBucket.length() + 1);

    StorageResourceId id = StorageResourceId.fromStringPath(path);
    assertTrue(id.isStorageObject());
    assertEquals(expectedBucket, id.getBucketName());
    assertEquals(expectedObject, id.getObjectName());
    assertEquals(StorageResourceId.UNKNOWN_GENERATION_ID, id.getGenerationId());
  }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-089  ·  ValueSource

**项目** `POI`  **文件** `poi/poi-scratchpad/src/test/java/org/apache/poi/hslf/model/TestShapes.java`  **测试** `textBoxSet`

### Test method

```java
@ParameterizedTest
    @ValueSource(strings = {
        "with_textbox.ppt",
        "basic_test_ppt_file.ppt",
        "next_test_ppt_file.ppt",
        "Single_Coloured_Page.ppt",
        "Single_Coloured_Page_With_Fonts_and_Alignments.ppt",
        "incorrect_slide_order.ppt"
    })
    void textBoxSet(String filename) throws IOException {
        try (HSLFSlideShow ppt = getSlideShow(filename)) {
            for (HSLFSlide sld : ppt.getSlides()) {
                ArrayList<String> lst1 = new ArrayList<>();
                for (List<HSLFTextParagraph> txt : sld.getTextParagraphs()) {
                    for (HSLFTextParagraph p : txt) {
                        for (HSLFTextRun r : p) {
                            lst1.add(r.getRawText());
                        }
                    }
                }

                ArrayList<String> lst2 = new ArrayList<>();
                for (HSLFShape sh : sld.getShapes()) {
                    if (sh instanceof HSLFTextShape) {
                        HSLFTextShape tbox = (HSLFTextShape) sh;
                        for (HSLFTextParagraph p : tbox.getTextParagraphs()) {
                            for (HSLFTextRun r : p) {
                                lst2.add(r.getRawText());
                            }
                        }
                    }
                }
                assertTrue(lst1.containsAll(lst2));
                assertTrue(lst2.containsAll(lst1));
            }
        }
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-092  ·  EnumSource

**项目** `Commons-RNG`  **文件** `commons-rng/commons-rng-simple/src/test/java/org/apache/commons/rng/simple/internal/NativeSeedTypeParametricTest.java`  **测试** `testConvertSeedToBytes`

### Test method

```java
@ParameterizedTest
    @EnumSource
    void testConvertSeedToBytes(NativeSeedType nativeSeedType) {
        final int size = 3;
        final Object seed = nativeSeedType.createSeed(size);
        Assertions.assertNotNull(seed, "Null seed");

        final byte[] bytes = NativeSeedType.convertSeedToBytes(seed);
        Assertions.assertNotNull(bytes, "Null byte[] seed");

        final Object seed2 = nativeSeedType.convertSeed(bytes, size);
        if (nativeSeedType.getType().isArray()) {
            // This handles nested primitive arrays
            Assertions.assertArrayEquals(new Object[] {seed}, new Object[] {seed2},
                "byte[] seed was not converted back");
        } else {
            Assertions.assertEquals(seed, seed2, "byte[] seed was not converted back");
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

## IRR-095  ·  MethodSource

**项目** `ZooKeeper`  **文件** `zookeeper/zookeeper-server/src/test/java/org/apache/zookeeper/common/X509UtilTest.java`  **测试** `testLoadPEMTrustStoreNullPassword`

### Test method

```java
@ParameterizedTest
    @MethodSource("data")
    public void testLoadPEMTrustStoreNullPassword(
            X509KeyType caKeyType, X509KeyType certKeyType, String keyPassword, Integer paramIndex)
            throws Exception {
        init(caKeyType, certKeyType, keyPassword, paramIndex);
        if (!x509TestContext.getTrustStorePassword().isEmpty()) {
            return;
        }
        // Make sure that empty password and null password are treated the same
        X509TrustManager tm = X509Util.createTrustManager(
            x509TestContext.getTrustStoreFile(KeyStoreFileType.PEM).getAbsolutePath(),
            null,
            KeyStoreFileType.PEM.getPropertyValue(),
            false,
            false,
            true,
            true,
            false,
            false);

    }
```

### Parameter provider — `data`（zookeeper/zookeeper-contrib/zookeeper-contrib-rest/src/test/java/org/apache/zookeeper/server/jersey/CreateTest.java）

```java
@Parameters
    public static Collection<Object[]> data() throws Exception {
        String baseZnode = Base.createBaseZNode();

        return Arrays.asList(new Object[][] {
          {MediaType.APPLICATION_JSON,
              baseZnode, "foo bar", "utf8",
              ClientResponse.Status.CREATED,
              new ZPath(baseZnode + "/foo bar"), null,
              false },
          {MediaType.APPLICATION_JSON, baseZnode, "c-t1", "utf8",
              ClientResponse.Status.CREATED, new ZPath(baseZnode + "/c-t1"),
              null, false },
          {MediaType.APPLICATION_JSON, baseZnode, "c-t1", "utf8",
              ClientResponse.Status.CONFLICT, null, null, false },
          {MediaType.APPLICATION_JSON, baseZnode, "c-t2", "utf8",
              ClientResponse.Status.CREATED, new ZPath(baseZnode + "/c-t2"),
              "".getBytes(), false },
          {MediaType.APPLICATION_JSON, baseZnode, "c-t2", "utf8",
              ClientResponse.Status.CONFLICT, null, null, false },
          {MediaType.APPLICATION_JSON, baseZnode, "c-t3", "utf8",
              ClientResponse.Status.CREATED, new ZPath(baseZnode + "/c-t3"),
              "foo".getBytes(), false },
          {MediaType.APPLICATION_JSON, baseZnode, "c-t3", "utf8",
              ClientResponse.Status.CONFLICT, null, null, false },
          {MediaType.APPLICATION_JSON, baseZnode, "c-t4", "base64",
              ClientResponse.Status.CREATED, new ZPath(baseZnode + "/c-t4"),
              "foo".getBytes(), false },
          {MediaType.APPLICATION_JSON, baseZnode, "c-", "utf8",
              ClientResponse.Status.CREATED, new ZPath(baseZnode + "/c-"), null,
              true },
          {MediaType.APPLICATION_JSON, baseZnode, "c-", "utf8",
              ClientResponse.Status.CREATED, new ZPath(baseZnode + "/c-"), null,
              true }
          });
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`init`**

```java
    public void init(
            X509KeyType caKeyType, X509KeyType certKeyType, String keyPassword, Integer paramIndex)
            throws Exception {
        super.init(caKeyType, certKeyType, keyPassword, paramIndex);
        try (X509Util x509util = new ClientX509Util()) {
            x509TestContext.setSystemProperties(x509util, KeyStoreFileType.JKS, KeyStoreFileType.JKS);
        }
        System.setProperty(ServerCnxnFactory.ZOOKEEPER_SERVER_CNXN_FACTORY, "org.apache.zookeeper.server.NettyServerCnxnFactory");
        System.setProperty(ZKClientConfig.ZOOKEEPER_CLIENT_CNXN_SOCKET, "org.apache.zookeeper.ClientCnxnSocketNetty");
        x509Util = new ClientX509Util();
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-098  ·  ValueSource

**项目** `POI`  **文件** `poi/poi-scratchpad/src/test/java/org/apache/poi/hwpf/usermodel/TestPictures.java`  **测试** `testPictures`

### Test method

```java
@ParameterizedTest
    @ValueSource(strings = {"Bug44603.doc", "header_image.doc"})
    void testPictures(String file) throws IOException {
        try (HWPFDocument doc = openSampleFile(file)) {
            List<Picture> pics = doc.getPicturesTable().getAllPictures();
            assertEquals(2, pics.size());
        }
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-101  ·  CsvSource

**项目** `POI`  **文件** `poi/poi/src/test/java/org/apache/poi/poifs/filesystem/TestPOIFSFileSystem.java`  **测试** `testShortLastBlock`

### Test method

```java
@ParameterizedTest
    @CsvSource({ "ShortLastBlock.qwp, 1303681", "ShortLastBlock.wps, 140787" })
    void testShortLastBlock(String file, int size) throws Exception {
        // Open the file up
        try (POIFSFileSystem fs = new POIFSFileSystem(_samples.openResourceAsStream(file))) {

            // Write it into a temp output array
            UnsynchronizedByteArrayOutputStream baos = UnsynchronizedByteArrayOutputStream.builder().get();
            fs.writeFilesystem(baos);

            // Check sizes
            assertEquals(size, baos.size());
        }
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-104  ·  CsvSource

**项目** `Log4j`  **文件** `logging-log4j2/log4j-layout-template-json-test/src/test/java/org/apache/logging/log4j/layout/template/json/resolver/CaseConverterResolverTest.java`  **测试** `test_errorHandlingStrategy`

### Test method

```java
@ParameterizedTest
    @CsvSource({
        // failure message              | locale    | input     | strategy      | replacement   | output
        "" + ",nl" + ",1" + ",pass" + ",null" + ",1",
        "" + ",nl" + ",[2]" + ",pass" + ",null" + ",[2]",
        "was expecting a string value" + ",nl" + ",1" + ",fail" + ",null" + ",null",
        "" + ",nl" + ",1" + ",replace" + ",null" + ",null",
        "" + ",nl" + ",1" + ",replace" + ",2" + ",2",
        "" + ",nl" + ",1" + ",replace" + ",\"s\"" + ",\"s\""
    })
    void test_errorHandlingStrategy(
            final String failureMessage,
            final String locale,
            final String inputJson,
            final String errorHandlingStrategy,
            final String replacementJson,
            final String outputJson) {

        // Parse arguments.
        final Object input = readJson(inputJson);
        final Object replacement = readJson(replacementJson);
        final Object output = readJson(outputJson);

        // Create the event template.
        final String eventTemplate = writeJson(asMap(
                "output",
                asMap(
                        "$resolver", "caseConverter",
                        "case", "lower",
                        "locale", locale,
                        "input", input,
                        "errorHandlingStrategy", errorHandlingStrategy,
                        "replacement", replacement)));

        // Create the layout.
        final JsonTemplateLayout layout = JsonTemplateLayout.newBuilder()
                .setConfiguration(CONFIGURATION)
                .setEventTemplate(eventTemplate)
                .build();

        // Create the log event.
        final LogEvent logEvent = Log4jLogEvent.newBuilder().build();

        // Check the serialized event.
        final boolean failureExpected = Strings.isNotBlank(failureMessage);
        if (failureExpected) {
            assertThatThrownBy(() -> layout.toSerializable(logEvent)).hasMessageContaining(failureMessage);
        } else {
            usingSerializedLogEventAccessor(layout, logEvent, accessor -> assertThat(accessor.getObject("output"))
                    .isEqualTo(output));
        }
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-107  ·  CsvSource

**项目** `JAMES`  **文件** `james-project/server/protocols/webadmin/webadmin-data/src/test/java/org/apache/james/webadmin/routes/DropListRoutesTest.java`  **测试** `shouldGetDropListWithQueryParams`

### Test method

```java
@ParameterizedTest(name = "{index} Owner: {0}, DeniedEntityType: {1}")
    @CsvSource(value = {
        "global, domain, evil.com",
        "global, address, attacker@evil.com",
        "domain/owner.com, domain, evil.com",
        "domain/owner.com, address, attacker@evil.com",
        "user/owner@owner.com, domain, evil.com",
        "user/owner@owner.com, address, attacker@evil.com"})
    void shouldGetDropListWithQueryParams(String pathParam, String queryParam, String expected) {
        given()
            .queryParam("deniedEntityType", queryParam)
        .when()
            .get(DropListRoutes.DROP_LIST + SEPARATOR + pathParam)
        .then()
            .statusCode(HttpStatus.OK_200)
            .contentType(ContentType.JSON)
            .body(".", containsInAnyOrder(expected));
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-110  ·  CsvSource

**项目** `Accumulo`  **文件** `accumulo/test/src/main/java/org/apache/accumulo/test/WriteAfterCloseIT.java`  **测试** `testWriteAfterClose`

### Test method

```java
@ParameterizedTest
  @CsvSource(
      value = {"time,   kill,  timeout, conditional",
              "MILLIS,  false, 0,       false",
              "LOGICAL, false, 0,       false",
              "MILLIS,  true,  0,       false",
              "MILLIS,  false, 2000,    false",
              "MILLIS,  false, 0,       true",
              "LOGICAL, false, 0,       true",
              "MILLIS,  true,  0,       true",
              "MILLIS,  false, 2000,    true"},
      useHeadersInDisplayName = true)
  // @formatter:on
  public void testWriteAfterClose(TimeType timeType, boolean killTservers, long timeout,
      boolean useConditionalWriter) throws Exception {
    // re #3721 test that tries to cause a write event to happen after a batch writer is closed
    String table = getUniqueNames(1)[0];
    var props = new Properties();
    props.putAll(getClientProps());
    props.setProperty(Property.GENERAL_RPC_TIMEOUT.getKey(), "1s");

    NewTableConfiguration ntc = new NewTableConfiguration().setTimeType(timeType);
    ntc.setProperties(
        Map.of(Property.TABLE_CONSTRAINT_PREFIX.getKey() + "1", SleepyConstraint.class.getName()));

    // The short rpc timeout and the random sleep in the constraint can cause some of the writes
    // done by a batch writer to timeout. The batch writer will internally retry the write, but the
    // timed out write could still go through at a later time.

    var executor = Executors.newCachedThreadPool();

    try (AccumuloClient c = Accumulo.newClient().from(props).build()) {
      c.tableOperations().create(table, ntc);

      int numTasks = 100;
      List<Future<?>> futures = new ArrayList<>(numTasks);
      // synchronize start of a portion of the tasks
      CountDownLatch startLatch = new CountDownLatch(32);
      assertTrue(numTasks >= startLatch.getCount(),
          "Not enough tasks to satisfy latch count - deadlock risk");

      for (int i = 0; i < numTasks; i++) {
        final int row = i * 1000;
        futures.add(executor.submit(() -> {
          try {
            startLatch.countDown();
            startLatch.await();
            createWriteTask(row, c, table, timeout, useConditionalWriter).call();
          } catch (Exception e) {
            throw new RuntimeException(e);
          }
        }));
      }
      assertEquals(numTasks, futures.size());

      if (killTservers) {
        Thread.sleep(250);
        getCluster().getClusterControl().stopAllServers(ServerType.TABLET_SERVER);
        // sleep longer than ZK timeout to let ephemeral lock nodes expire in ZK
        Thread.sleep(11000);
        getCluster().getClusterControl().startAllServers(ServerType.TABLET_SERVER);
      }

      int errorCount = 0;

      // wait for all futures to complete
      for (var future : futures) {
        try {
          future.get();
        } catch (ExecutionException e) {
          var cause = e.getCause();
          while (cause != null && !(cause instanceof TimedOutException)) {
            cause = cause.getCause();
          }

          assertNotNull(cause);
          errorCount++;
        }
      }

      boolean expectErrors = timeout > 0;
      if (expectErrors) {
        assertTrue(errorCount > 0);
      } else {
        assertEquals(0, errorCount);
        // allow potential out-of-order writes on a tserver to run
        Thread.sleep(SleepyConstraint.SLEEP_TIME);
        try (Scanner scanner = c.createScanner(table)) {
          // every insertion was deleted so table should be empty unless there were out of order
          // writes
          assertEquals(0, scanner.stream().count());
        }
      }
    } finally {
      executor.shutdownNow();
    }
  }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`createWriteTask`**

```java
  private static Callable<Void> createWriteTask(int row, AccumuloClient c, String table,
      long timeout, boolean useConditionalWriter) {
    return () -> {
      if (useConditionalWriter) {
        ConditionalWriterConfig cwc =
            new ConditionalWriterConfig().setTimeout(timeout, TimeUnit.MILLISECONDS);
        try (ConditionalWriter writer = c.createConditionalWriter(table, cwc)) {
          ConditionalMutation m = new ConditionalMutation("r" + row);
          m.addCondition(new Condition("f1", "q1"));
          m.put("f1", "q1", new Value("v1"));
          ConditionalWriter.Result result = writer.write(m);
          var status = result.getStatus();
          assertTrue(status == ConditionalWriter.Status.ACCEPTED
              || status == ConditionalWriter.Status.UNKNOWN);
        }
      } else {
        BatchWriterConfig bwc = new BatchWriterConfig().setTimeout(timeout, TimeUnit.MILLISECONDS);
        try (BatchWriter writer = c.createBatchWriter(table, bwc)) {
          Mutation m = new Mutation("r" + row);
          m.put("f1", "q1", new Value("v1"));
          writer.addMutation(m);
        }
      }
      // Relying on the internal retries of the batch writer, trying to create a situation where
      // some of the writes from above actually happen after the delete below which would negate the
      // delete.

      try (BatchWriter writer = c.createBatchWriter(table)) {
        Mutation m = new Mutation("r" + row);
        m.putDelete("f1", "q1");
        writer.addMutation(m);
      }
      return null;
    };
  }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-113  ·  CsvSource

**项目** `POI`  **文件** `poi/poi/src/test/java/org/apache/poi/hssf/usermodel/TestBugs.java`  **测试** `bug35897`

### Test method

```java
@ParameterizedTest
    @CsvSource({
        "xor-encryption-abc.xls, abc",
        "35897-type4.xls, freedom"
    })
    void bug35897(String file, String pass) throws Exception {
        Biff8EncryptionKey.setCurrentUserPassword(pass);
        try {
            simpleTest(file, null);
        } finally {
            Biff8EncryptionKey.setCurrentUserPassword(null);
        }
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`simpleTest`**

```java
@ParameterizedTest
    @CsvSource({
        "15228.xls", "13796.xls", "14460.xls", "14330-1.xls", "14330-2.xls", "12561-1.xls", "12561-2.xls",
        "12843-1.xls", "12843-2.xls", "13224.xls", "19599-1.xls", "19599-2.xls", "32822.xls", "15573.xls",
        "33082.xls", "34775.xls", "37630.xls", "25183.xls", "26100.xls", "27933.xls", "29675.xls", "29982.xls",
        "31749.xls", "37376.xls", "SimpleWithAutofilter.xls", "44201.xls", "37684-1.xls", "37684-2.xls",
        "41139.xls", "ex42564-21435.xls", "ex42564-21503.xls", "28774.xls", "44891.xls", "44235.xls", "36947.xls",
        "39634.xls", "47701.xls", "48026.xls", "47251.xls", "47251_1.xls", "50020.xls", "50426.xls", "50779_1.xls",
        "50779_2.xls", "51670.xls", "54016.xls", "57456.xls", "53109.xls", "com.aida-tour.www_SPO_files_maldives%20august%20october.xls",
        "named-cell-in-formula-test.xls", "named-cell-test.xls", "bug55505.xls", "chinese-provinces.xls",
        "SUBSTITUTE.xls", "64261.xls"
    })
    void simpleTest(String fileName) throws IOException {
        simpleTest(fileName, null);
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-116  ·  MethodSource

**项目** `Commons-JEXL`  **文件** `commons-jexl/src/test/java/org/apache/commons/jexl3/JXLTTest.java`  **测试** `test311i`

### Test method

```java
@ParameterizedTest
    @MethodSource("engines")
    void test311i(final JexlBuilder builder) {
        init(builder);
        final JexlContext ctx311 = new Context311();
        // @formatter:off
        final String rpt
                = "$$var u = 'Universe'; exec('4').execute((a, b)->{"
                + "\n<p>${u} ${a}${b}</p>"
                + "\n$$}, '2')";
        // @formatter:on
        final JxltEngine.Template t = JXLT.createTemplate("$$", new StringReader(rpt));
        final StringWriter strw = new StringWriter();
        t.evaluate(ctx311, strw, 42);
        final String output = strw.toString();
        assertEquals("<p>Universe 42</p>\n", output);
    }
```

### Parameter provider — 同文件内的 `engines`

```java
   public static List<JexlBuilder> engines() {
       final JexlFeatures f = new JexlFeatures();
       f.lexical(true).lexicalShade(true);
      return Arrays.asList(
              new JexlBuilder().silent(false).lexical(true).lexicalShade(true).cache(128).strict(true),
              new JexlBuilder().features(f).silent(false).cache(128).strict(true),
              new JexlBuilder().silent(false).cache(128).strict(true));
   }
```

### Test-side helpers called by this test (2)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`init`**

```java
    private void init(final JexlBuilder builder) {
        BUILDER = builder;
        ENGINE = BUILDER.create();
        JXLT = ENGINE.createJxltEngine();
    }
```

**`toString`**

```java
@Override
        public String toString() {
            return out.toString();
        }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-119  ·  CsvSource

**项目** `POI`  **文件** `poi/poi-scratchpad/src/test/java/org/apache/poi/hslf/usermodel/TestBugs.java`  **测试** `testFile`

### Test method

```java
@ParameterizedTest
    @CsvSource({
        // bug47261.ppt has actually 16 slides, but also non-conforming multiple document records
        "bug47261.ppt, 1",
        "bug56240.ppt, 105",
        "bug58516.ppt, 5",
        "57272_corrupted_usereditatom.ppt, 6",
        "37625.ppt, 29",
        // Bug 41246: AIOOB with illegal note references
        "41246-1.ppt, 36",
        "41246-2.ppt, 16",
        // Bug 44770: java.lang.RuntimeException: Couldn't instantiate the class for
        // type with id 1036 on class class org.apache.poi.hslf.record.PPDrawing
        "44770.ppt, 19",
        // Bug 42486:  Failure parsing a seemingly valid PPT
        "42486.ppt, 33"
    })
    void testFile(String file, int slideCnt) throws IOException {
        try (HSLFSlideShow ppt = open(file)) {
            for (HSLFSlide slide : ppt.getSlides()) {
                List<HSLFShape> shape = slide.getShapes();
                assertFalse(shape.isEmpty());
            }

            assertNotNull(ppt.getSlides().get(0));
            ppt.removeSlide(0);
            ppt.createSlide();
            try (HSLFSlideShow ppt2 = writeOutAndReadBack(ppt)) {
                assertEquals(slideCnt, ppt2.getSlides().size());
            };
        }
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`open`**

```java
    private static HSLFSlideShow open(String fileName) throws IOException {
        File sample = HSLFTestDataSamples.getSampleFile(fileName);
        // Note: don't change the code here, it is required for Eclipse to compile the code
        SlideShow<?,?> slideShowOrig = SlideShowFactory.create(sample, null, false);
        return (HSLFSlideShow)slideShowOrig;
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-122  ·  ValueSource

**项目** `Qpid`  **文件** `qpid-broker-j/broker-plugins/access-control/src/test/java/org/apache/qpid/server/security/access/config/AclFileParserTest.java`  **测试** `whitespaces`

### Test method

```java
@ParameterizedTest
    @ValueSource(strings =
    {
            "ACL\tDENY-LOG\t\t user1\t \tACCESS VIRTUALHOST",
            "ACL\u000B DENY-LOG\t\t user1\t \tACCESS VIRTUALHOST\u001E"
    })
    void whitespaces(final String arg)
    {
        final RuleSet rules = writeACLConfig(arg);
        assertEquals(1, rules.size());

        final Rule rule = rules.get(0);
        assertEquals("user1", rule.getIdentity(), "Rule has unexpected identity");
        assertEquals(LegacyOperation.ACCESS, rule.getOperation(), "Rule has unexpected operation");
        assertEquals(ObjectType.VIRTUALHOST, rule.getObjectType(), "Rule has unexpected object type");
        assertEquals(EMPTY, rule.getPredicates(), "Rule has unexpected predicates");
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`writeACLConfig`**

```java
    private RuleSet writeACLConfig(final String... aclData)
    {
        try
        {
            final File acl = File.createTempFile(getClass().getName() + getTestName(), "acl");
            acl.deleteOnExit();

            // Write ACL file
            try (final PrintWriter aclWriter = new PrintWriter(new FileWriter(acl)))
            {
                Arrays.stream(aclData).forEach(aclWriter::println);
            }

            // Load ruleset
            return AclFileParser.parse(acl.toURI().toURL().toString(), mock(EventLoggerProvider.class));
        }
        catch (IllegalConfigurationException e)
        {
            throw e;
        }
        catch (Exception e)
        {
           throw new RuntimeException(e);
        }
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-125  ·  MethodSource

**项目** `Commons-Codec`  **文件** `commons-codec/src/test/java/org/apache/commons/codec/digest/HmacAlgorithmsTest.java`  **测试** `testGetHmacEmptyKey`

### Test method

```java
@ParameterizedTest
    @MethodSource("data")
    void testGetHmacEmptyKey(final HmacAlgorithms hmacAlgorithm, final byte[] standardResultBytes, final String standardResultString) {
        assumeTrue(HmacUtils.isAvailable(hmacAlgorithm));
        assertThrows(IllegalArgumentException.class, () -> HmacUtils.getInitializedMac(hmacAlgorithm, EMPTY_BYTE_ARRAY));
    }
```

### Parameter provider — 同文件内的 `data`

```java
    public static Stream<Arguments> data() {
        List<Arguments> list = Arrays.asList(
        // @formatter:off
                Arguments.of(HmacAlgorithms.HMAC_MD5, STANDARD_MD5_RESULT_BYTES, STANDARD_MD5_RESULT_STRING),
                Arguments.of(HmacAlgorithms.HMAC_SHA_1, STANDARD_SHA1_RESULT_BYTES, STANDARD_SHA1_RESULT_STRING),
                Arguments.of(HmacAlgorithms.HMAC_SHA_256, STANDARD_SHA256_RESULT_BYTES, STANDARD_SHA256_RESULT_STRING),
                Arguments.of(HmacAlgorithms.HMAC_SHA_384, STANDARD_SHA384_RESULT_BYTES, STANDARD_SHA384_RESULT_STRING),
                Arguments.of(HmacAlgorithms.HMAC_SHA_512, STANDARD_SHA512_RESULT_BYTES, STANDARD_SHA512_RESULT_STRING));
        // @formatter:on
        if (SystemUtils.isJavaVersionAtLeast(JavaVersion.JAVA_1_8)) {
            list = new ArrayList<>(list);
            list.add(Arguments.of(HmacAlgorithms.HMAC_SHA_224, STANDARD_SHA224_RESULT_BYTES, STANDARD_SHA224_RESULT_STRING));
        }
        return list.stream();
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-128  ·  ValueSource

**项目** `Storm`  **文件** `storm/external/storm-hdfs-blobstore/src/test/java/org/apache/storm/hdfs/blobstore/BlobStoreTest.java`  **测试** `testWithAuthenticationDummy`

### Test method

```java
@ParameterizedTest
    @ValueSource(booleans = {true, false})
    void testWithAuthenticationDummy(boolean securityEnabled) throws Exception {
        try (AutoCloseableBlobStoreContainer container = initHdfs("/storm/blobstore-auth-dummy-sec-" + securityEnabled)) {
            BlobStore store = container.blobStore;
            Subject who = getSubject("test_subject");
            assertStoreHasExactly(store);

            // Tests for case when subject != null (security turned on) and
            // acls for the blob are set to WORLD_EVERYTHING
            SettableBlobMeta metadata = new SettableBlobMeta(securityEnabled ? BlobStoreAclHandler.DEFAULT : BlobStoreAclHandler.WORLD_EVERYTHING);
            try (AtomicOutputStream out = store.createBlob("test", metadata, who)) {
                out.write(1);
            }
            assertStoreHasExactly(store, "test");
            if (securityEnabled) {
                // Testing whether acls are set to WORLD_EVERYTHING. Here the acl should not contain WORLD_EVERYTHING because
                // the subject is neither null nor empty. The ACL should however contain USER_EVERYTHING as user needs to have
                // complete access to the blob
                assertFalse(metadata.toString().contains("AccessControl(type:OTHER, access:7)"), "ACL contains WORLD_EVERYTHING");
            } else {
                // Testing whether acls are set to WORLD_EVERYTHING
                assertTrue(metadata.toString().contains("AccessControl(type:OTHER, access:7)"), "ACL does not contain WORLD_EVERYTHING");
            }
            
            readAssertEqualsWithAuth(store, who, "test", 1);

            LOG.info("Deleting test");
            store.deleteBlob("test", who);
            assertStoreHasExactly(store);
        }
    }
```

### Test-side helpers called by this test (5)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`initHdfs`**

```java
    private AutoCloseableBlobStoreContainer initHdfs(String dirName) {
        Map<String, Object> conf = new HashMap<>();
        conf.put(Config.BLOBSTORE_DIR, dirName);
        conf.put(Config.STORM_PRINCIPAL_TO_LOCAL_PLUGIN, "org.apache.storm.security.auth.DefaultPrincipalToLocal");
        conf.put(Config.STORM_BLOBSTORE_REPLICATION_FACTOR, 3);
        HdfsBlobStore store = new HdfsBlobStore();
        store.prepareInternal(conf, null, DFS_CLUSTER_EXTENSION.getDfscluster().getConfiguration(0));
        return new AutoCloseableBlobStoreContainer(store);
    }
```

**`getSubject`**

```java
    public static Subject getSubject(String name) {
        Subject subject = new Subject();
        SingleUserPrincipal user = new SingleUserPrincipal(name);
        subject.getPrincipals().add(user);
        return subject;
    }
```

**`assertStoreHasExactly`**

```java
    public static void assertStoreHasExactly(BlobStore store, Subject who, String... keys) {
        Set<String> expected = new HashSet<>(Arrays.asList(keys));
        Set<String> found = new HashSet<>();
        Iterator<String> c = store.listKeys();
        while (c.hasNext()) {
            String keyName = c.next();
            found.add(keyName);
        }
        Set<String> extra = new HashSet<>(found);
        extra.removeAll(expected);
        assertTrue(extra.isEmpty(), "Found extra keys in the blob store " + extra);
        Set<String> missing = new HashSet<>(expected);
        missing.removeAll(found);
        assertTrue(missing.isEmpty(), "Found keys missing from the blob store " + missing);
    }
```

**`readAssertEqualsWithAuth`**

```java
    public void readAssertEqualsWithAuth(BlobStore store, Subject who, String key, int value)
        throws IOException, KeyNotFoundException, AuthorizationException {
        assertEquals(value, readInt(store, who, key));
    }
```

**`readInt`**

```java
    public static int readInt(BlobStore store, Subject who, String key) throws IOException, KeyNotFoundException, AuthorizationException {
        try (InputStream in = store.getBlob(key, who)) {
            return in.read();
        }
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-131  ·  CsvSource

**项目** `OpenNLP`  **文件** `opennlp/opennlp-tools/src/test/java/opennlp/tools/monitoring/IterDeltaAccuracyUnderToleranceTest.java`  **测试** `testCriteria`

### Test method

```java
@ParameterizedTest
  @CsvSource( {"0.01,false", "-0.01,false", "0.00001,true", "-0.00001,true"})
  void testCriteria(double val, String expectedVal) {
    assertEquals(Boolean.parseBoolean(expectedVal), stopCriteria.test(val));
  }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-134  ·  CsvSource

**项目** `SeaTunnel`  **文件** `seatunnel/seatunnel-ci-tools/src/test/java/org/apache/seatunnel/api/SpotlessImportReplacementTest.java`  **测试** `testAllImportReplacements`

### Test method

```java
@ParameterizedTest
    @CsvSource({
        "import com.google.common.collect.Lists;, import org.apache.seatunnel.shade.com.google.common.collect.Lists;",
        "import static com.google.common.base.Preconditions.checkNotNull;, import static org.apache.seatunnel.shade.com.google.common.base.Preconditions.checkNotNull;",
        "import org.eclipse.jetty.server.Server;, import org.apache.seatunnel.shade.org.eclipse.jetty.server.Server;",
        "import static org.eclipse.jetty.http.HttpStatus.OK_200;, import static org.apache.seatunnel.shade.org.eclipse.jetty.http.HttpStatus.OK_200;",
        "import com.zaxxer.hikari.HikariDataSource;, import org.apache.seatunnel.shade.com.zaxxer.hikari.HikariDataSource;",
        "import static com.zaxxer.hikari.HikariConfig.MINIMUM_IDLE;, import static org.apache.seatunnel.shade.com.zaxxer.hikari.HikariConfig.MINIMUM_IDLE;",
        "import org.codehaus.janino.ExpressionEvaluator;, import org.apache.seatunnel.shade.org.codehaus.janino.ExpressionEvaluator;",
        "import org.codehaus.commons.compiler.CompileException;, import org.apache.seatunnel.shade.org.codehaus.commons.compiler.CompileException;"
    })
    public void testAllImportReplacements(String input, String expected) {
        String result = input + "\n";

        // Apply all replacement patterns
        result = Pattern.compile(GUAVA_REGEX).matcher(result).replaceAll(GUAVA_REPLACEMENT);
        result = Pattern.compile(JETTY_REGEX).matcher(result).replaceAll(JETTY_REPLACEMENT);
        result = Pattern.compile(HIKARI_REGEX).matcher(result).replaceAll(HIKARI_REPLACEMENT);
        result = Pattern.compile(JANINO_REGEX).matcher(result).replaceAll(JANINO_REPLACEMENT);

        // Remove trailing newline for comparison
        result = result.trim();

        Assertions.assertEquals(expected, result);
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-137  ·  ValueSource

**项目** `opennlp`  **文件** `opennlp/opennlp-extensions/opennlp-uima/src/test/java/opennlp/uima/SingleAnnotatorIT.java`  **测试** `testInitializationExecutionAndReconfigure`

### Test method

```java
@ParameterizedTest
  @ValueSource(strings = {
      "Chunker.xml", "DateNameFinder.xml", "DictionaryNameFinder.xml",
      "LocationNameFinder.xml", "MoneyNameFinder.xml", "OrganizationNameFinder.xml",
      "Parser.xml", "PercentageNameFinder.xml", "PersonNameFinder.xml", "PosTagger.xml",
      "SentenceDetector.xml", "SimpleTokenizer.xml", "Tokenizer.xml", "TimeNameFinder.xml",
      "WhitespaceTokenizer.xml"
  })
  public void testInitializationExecutionAndReconfigure(String descName) {
    AnalysisEngine ae = null;
    try {
      ae = produceAE(descName);
      assertNotNull(ae);
      CAS cas = ae.newCAS();
      cas.setDocumentLanguage("en");
      cas.setDocumentText(DOCUMENT_TEXT);
      ae.process(cas);
      ae.reconfigure();
      /*
      CasIterator casIterator = ae.processAndOutputNewCASes(cas);
      while (casIterator.hasNext()) {
        CAS outCas = casIterator.next();

        //dump the document text and annotations for this segment
        System.out.println("********* NEW SEGMENT *********");
        System.out.println(outCas.getDocumentText());
        printAnnotations(outCas, System.out);
        //release the CAS (important)
        outCas.release();
      }
       */
    } catch (IOException | InvalidXMLException | AnalysisEngineProcessException |
             ResourceConfigurationException | ResourceInitializationException e) {
      fail(e.getLocalizedMessage() + " for desc " + descName +
              ", cause: " + e.getCause().getLocalizedMessage());
    } finally {
      if (ae != null) {
        ae.destroy();
      }
    }
  }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-140  ·  MethodSource

**项目** `Directory-Studio`  **文件** `directory-studio/tests/test.integration.ui/src/main/java/org/apache/directory/studio/test/integration/ui/ValueEditorTest.java`  **测试** `testGetRawValue`

### Test method

```java
@ParameterizedTest
    @MethodSource("data")
    public void testGetRawValue( String name, Data data ) throws Exception
    {
        setup( name, data );
        if ( data.expectedRawValue instanceof byte[] )
        {
            assertArrayEquals( ( byte[] ) data.expectedRawValue, ( byte[] ) editor.getRawValue( value ) );
        }
        else
        {
            assertEquals( data.expectedRawValue, editor.getRawValue( value ) );
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

## IRR-143  ·  ValueSource

**项目** `Hop`  **文件** `hop/plugins/actions/movefiles/src/test/java/org/apache/hop/workflow/actions/movefiles/AzureMoveFilesIT.java`  **测试** `whenCreateDestinationFolderNotFlagged_shouldNotMoveFile`

### Test method

```java
@ParameterizedTest
  @ValueSource(strings = {"azfs:///${currentAccount}/", "azure:///"})
  void whenCreateDestinationFolderNotFlagged_shouldNotMoveFile(String basePath)
      throws HopException {
    this.basePath = basePath;
    ActionMoveFiles action = defaultAction();
    action.sourceFileFolder[0] = getFilePath("artists3.csv");
    action.destinationFileFolder[0] = getFilePath("fakecontainer", "artists-do-not-create-folder");
    action.setCreateDestinationFolder(false);

    action.execute(new Result(), 1);

    assertThatFileExists(CONTAINER_NAME, "artists3.csv");
    assertThatFileDoesNotExist("fakecontainer", "artists3.csv");
  }
```

### Test-side helpers called by this test (3)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`getFilePath`**

```java
  private String getFilePath(String filename) {
    return basePath + CONTAINER_NAME + "/" + filename;
  }
```

**`assertThatFileExists`**

```java
  private void assertThatFileExists(String containerName, String blobName) {
    // Get a BlobClient object which represents a blob in the container
    BlobClient blobClient =
        blobServiceClient.getBlobContainerClient(containerName).getBlobClient(blobName);

    // Get the properties of the blob
    var blobProperties = blobClient.getProperties();

    // Get the size of the blob
    long blobSize = blobProperties.getBlobSize();

    assertEquals(true, blobClient.exists());
    assertTrue(blobSize >= 140);
  }
```

**`assertThatFileDoesNotExist`**

```java
  private void assertThatFileDoesNotExist(String containerName, String blobName) {
    // Get a BlobClient object which represents a blob in the container
    BlobClient blobClient =
        blobServiceClient.getBlobContainerClient(containerName).getBlobClient(blobName);

    assertEquals(false, blobClient.exists());
  }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-146  ·  EnumSource

**项目** `hudi`  **文件** `hudi/hudi-spark-datasource/hudi-spark/src/test/java/org/apache/hudi/functional/TestSavepointRestoreMergeOnRead.java`  **测试** `testRestoreWithFileGroupCreatedWithDeltaCommits`

### Test method

```java
@ParameterizedTest
  @EnumSource(value = HoodieTableVersion.class, names = {"SIX", "EIGHT"})
  public void testRestoreWithFileGroupCreatedWithDeltaCommits(HoodieTableVersion tableVersion) throws IOException {
    HoodieWriteConfig hoodieWriteConfig = getHoodieWriteConfigAndInitializeTable(HoodieCompactionConfig.newBuilder()
        .withMaxNumDeltaCommitsBeforeCompaction(4)
        .withInlineCompaction(true).build(), tableVersion);
    final int numRecords = 100;
    String firstCommit;
    String secondCommit;
    try (SparkRDDWriteClient client = getHoodieWriteClient(hoodieWriteConfig)) {
      // 1st commit insert
      String newCommitTime = client.startCommit();
      List<HoodieRecord> records = dataGen.generateInserts(newCommitTime, numRecords);
      JavaRDD<HoodieRecord> writeRecords = jsc.parallelize(records, 1);
      client.commit(newCommitTime, client.insert(writeRecords, newCommitTime));
      firstCommit = newCommitTime;

      // 2nd commit with inserts and updates which will create new file slice due to small file handling.
      newCommitTime = client.startCommit();
      List<HoodieRecord> records2 = dataGen.generateUniqueUpdates(newCommitTime, numRecords);
      JavaRDD<HoodieRecord> writeRecords2 = jsc.parallelize(records2, 1);
      List<HoodieRecord> records3 = dataGen.generateInserts(newCommitTime, 30);
      JavaRDD<HoodieRecord> writeRecords3 = jsc.parallelize(records3, 1);

      client.commit(newCommitTime, client.upsert(writeRecords2.union(writeRecords3), newCommitTime));
      secondCommit = newCommitTime;
      // add savepoint to 2nd commit
      client.savepoint(firstCommit, "test user","test comment");
    }
    assertRowNumberEqualsTo(130);
    // verify there are new base files created matching the 2nd commit timestamp.
    StoragePathFilter filter = (path) -> path.toString().contains(secondCommit);
    for (String pPath : dataGen.getPartitionPaths()) {
      assertEquals(1, storage.listDirectEntries(
              FSUtils.constructAbsolutePath(hoodieWriteConfig.getBasePath(), pPath), filter)
          .size());
    }

    // disable small file handling so that updates go to log files.
    hoodieWriteConfig = getConfigBuilder(HoodieFailedWritesCleaningPolicy.EAGER) // eager cleaning
        .withCompactionConfig(HoodieCompactionConfig.newBuilder()
            .withMaxNumDeltaCommitsBeforeCompaction(4) // the 4th delta_commit triggers compaction
            .withInlineCompaction(true)
            .compactionSmallFileSize(0)
            .build())
        .withRollbackUsingMarkers(true)
        .withAutoUpgradeVersion(false)
        .withWriteTableVersion(tableVersion.versionCode())
        .withMetadataConfig(HoodieMetadataConfig.newBuilder()
            .withStreamingWriteEnabled(tableVersion.greaterThanOrEquals(HoodieTableVersion.EIGHT))
            .build())
        .build();

    // add 2 more updates which will create log files.
    try (SparkRDDWriteClient client = getHoodieWriteClient(hoodieWriteConfig)) {
      String newCommitTime = client.startCommit();
      List<HoodieRecord> records = dataGen.generateUniqueUpdates(newCommitTime, numRecords);
      JavaRDD<HoodieRecord> writeRecords = jsc.parallelize(records, 1);
      client.commit(newCommitTime, client.upsert(writeRecords, newCommitTime));

      newCommitTime = client.startCommit();
      records = dataGen.generateUniqueUpdates(newCommitTime, numRecords);
      writeRecords = jsc.parallelize(records, 1);
      client.commit(newCommitTime, client.upsert(writeRecords, newCommitTime));
    }
    assertRowNumberEqualsTo(130);

    // restore to 2nd commit.
    try (SparkRDDWriteClient client = getHoodieWriteClient(hoodieWriteConfig)) {
      client.restoreToSavepoint(firstCommit);
    }
    assertRowNumberEqualsTo(100);
    // verify that entire file slice created w/ base instant time of 2nd commit is completely rolledback.
    filter = (path) -> path.toString().contains(secondCommit);
    for (String pPath : dataGen.getPartitionPaths()) {
      assertEquals(0, storage.listDirectEntries(
              FSUtils.constructAbsolutePath(hoodieWriteConfig.getBasePath(), pPath), filter)
          .size());
    }
    // ensure files matching 1st commit is intact
    filter = (path) -> path.toString().contains(firstCommit);
    for (String pPath : dataGen.getPartitionPaths()) {
      assertEquals(1,
          storage.listDirectEntries(
              FSUtils.constructAbsolutePath(hoodieWriteConfig.getBasePath(), pPath),
              filter).size());
    }
    validateFilesMetadata(hoodieWriteConfig);
    Map<String, Integer> actualCommitToRowCount = getRecordCountPerCommit();
    assertEquals(Collections.singletonMap(firstCommit, numRecords), actualCommitToRowCount);
  }
```

### Enum declaration — `HoodieTableVersion` (hudi/hudi-common/src/main/java/org/apache/hudi/common/table/HoodieTableVersion.java)

```java
public enum HoodieTableVersion {
  // < 0.6.0 versions
  ZERO(0, CollectionUtils.createImmutableList("0.3.0"), TimelineLayoutVersion.LAYOUT_VERSION_0),
  // 0.6.0 onwards
  ONE(1, CollectionUtils.createImmutableList("0.6.0"), TimelineLayoutVersion.LAYOUT_VERSION_1),
  // 0.9.0 onwards
  TWO(2, CollectionUtils.createImmutableList("0.9.0"), TimelineLayoutVersion.LAYOUT_VERSION_1),
  // 0.10.0 onwards
  THREE(3, CollectionUtils.createImmutableList("0.10.0"), TimelineLayoutVersion.LAYOUT_VERSION_1),
  // 0.11.0 onwards
  FOUR(4, CollectionUtils.createImmutableList("0.11.0"), TimelineLayoutVersion.LAYOUT_VERSION_1),
  // 0.12.0 onwards
  FIVE(5, CollectionUtils.createImmutableList("0.12.0", "0.13.0"), TimelineLayoutVersion.LAYOUT_VERSION_1),
  // 0.14.0 onwards
  SIX(6, CollectionUtils.createImmutableList("0.14.0"), TimelineLayoutVersion.LAYOUT_VERSION_1),
  // 0.16.0
  SEVEN(7, CollectionUtils.createImmutableList("0.16.0"), TimelineLayoutVersion.LAYOUT_VERSION_1),
  // 1.0
  EIGHT(8, CollectionUtils.createImmutableList("1.0.0"), TimelineLayoutVersion.LAYOUT_VERSION_2),
  // 1.1
  NINE(9, CollectionUtils.createImmutableList("1.1.0"), TimelineLayoutVersion.LAYOUT_VERSION_2);

  private final int versionCode;

  private final List<String> releaseVersions;

  private final TimelineLayoutVersion timelineLayoutVersion;

  HoodieTableVersion(int versionCode, List<String> releaseVersions, TimelineLayoutVersion timelineLayoutVersion) {
    this.versionCode = versionCode;
    this.releaseVersions = releaseVersions;
    this.timelineLayoutVersion = timelineLayoutVersion;
  }

  public TimelineLayoutVersion getTimelineLayoutVersion() {
    return timelineLayoutVersion;
  }

  public int versionCode() {
    return versionCode;
  }

  public static HoodieTableVersion current() {
    return NINE;
  }

  public static HoodieTableVersion fromVersionCode(int versionCode) {
    return Arrays.stream(HoodieTableVersion.values())
        .filter(v -> v.versionCode == versionCode).findAny()
        .orElseThrow(() -> new HoodieException("Unknown table versionCode:" + versionCode));
  }

  public static HoodieTableVersion fromReleaseVersion(String releaseVersion) {
    return Arrays.stream(HoodieTableVersion.values())
        .filter(v -> v.releaseVersions.contains(releaseVersion)).findAny()
        .orElseThrow(() -> new HoodieException("Unknown table firstReleaseVersion:" + releaseVersion));
  }

  public boolean greaterThanOrEquals(HoodieTableVersion other) {
    return greaterThan(other) || this.versionCode == other.versionCode;
  }

  public boolean greaterThan(HoodieTableVersion other) {
    return this.versionCode > other.versionCode;
  }

  public boolean lesserThan(HoodieTableVersion other) {
    return this.versionCode < other.versionCode;
  }
}
```

### Test-side helpers called by this test (3)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`getHoodieWriteConfigAndInitializeTable`**

```java
  private HoodieWriteConfig getHoodieWriteConfigAndInitializeTable(HoodieCompactionConfig compactionConfig, HoodieTableVersion tableVersion) throws IOException {
    return getHoodieWriteConfigAndInitializeTable(compactionConfig, HoodieClusteringConfig.newBuilder().build(), tableVersion);
  }
```

**`validateFilesMetadata`**

```java
  private void validateFilesMetadata(HoodieWriteConfig writeConfig) {
    HoodieTableFileSystemView fileListingBasedView = FileSystemViewManager.createInMemoryFileSystemView(context, metaClient,
        HoodieMetadataConfig.newBuilder().enable(false).build());
    FileSystemViewStorageConfig viewStorageConfig = FileSystemViewStorageConfig.newBuilder().fromProperties(writeConfig.getProps())
        .withStorageType(FileSystemViewStorageType.MEMORY).build();
    HoodieTableFileSystemView metadataBasedView = (HoodieTableFileSystemView) FileSystemViewManager
        .createViewManager(context, writeConfig.getMetadataConfig(), viewStorageConfig, writeConfig.getCommonConfig(),
            (SerializableFunctionUnchecked<HoodieTableMetaClient, HoodieTableMetadata>) v1 ->
                metaClient.getTableFormat().getMetadataFactory().create(context, metaClient.getStorage(), writeConfig.getMetadataConfig(), writeConfig.getBasePath()))
        .getFileSystemView(basePath);
    assertForFSVEquality(fileListingBasedView, metadataBasedView, true, Option.empty());
  }
```

**`getRecordCountPerCommit`**

```java
  private Map<String, Integer> getRecordCountPerCommit() {
    Dataset<Row> dataset = sparkSession.read().format("hudi").load(basePath);
    List<Row> rows = dataset.collectAsList();
    int index = dataset.schema().fieldIndex(HoodieRecord.HoodieMetadataField.COMMIT_TIME_METADATA_FIELD.getFieldName());
    Map<String, Integer> actualCommitToRowCount = new HashMap<>();
    rows.forEach(row -> {
      actualCommitToRowCount.compute(row.getString(index), (k, v) -> (v == null) ? 1 : v + 1);
    });
    return actualCommitToRowCount;
  }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-149  ·  CsvSource

**项目** `JMeter`  **文件** `jmeter/src/core/src/test/java/org/apache/jmeter/util/XPathUtilTest.java`  **测试** `testMakeDocument`

### Test method

```java
@ParameterizedTest
    @CsvSource(value = {
            "/book,false,false,false",
            "/book/error,false,false,true",
            "/book/error,true,false,false",
            "/book/preface,true,false,true",
            "count(/book/page)=2,false,false,false",
            "count(/book/page)=2,true,false,true",
            "count(/book/page)=1,false,false,true",
            "count(/book/page)=1,true,false,false",
            "///book,false,true,false"
    })
    public void testMakeDocument(String xpathquery, boolean isNegated, boolean isError, boolean isFailure)
            throws ParserConfigurationException, SAXException, IOException, TidyException {
        String responseData = "<book><preface>zero</preface><page>one</page><page>two</page><empty></empty><a><b></b></a></book>";
        Document testDoc = XPathUtil.makeDocument(
                new ByteArrayInputStream(responseData.getBytes(StandardCharsets.UTF_8)),
                false, false, false, false,
                false, false, false, false, false);
        AssertionResult res = new AssertionResult("test");
        XPathUtil.computeAssertionResult(res, testDoc, xpathquery, isNegated);
        assertEquals(isError, res.isError(), "test isError");
        assertEquals(isFailure, res.isFailure(), "test isFailure");
    }
```

### To classify

`equivalence_class` / `semantic_role`

---
