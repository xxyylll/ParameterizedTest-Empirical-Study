# Rating packet R1

60 items. For each one, classify only the dimensions that apply to its source — the rules are in `rater_guide.md`.

Record your answers in `packet_R1.csv`, one row per item, matched by `item_id`. If the code shown does not let you decide, answer `unclear` and write one line in `notes`.

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

## IRR-016  ·  CsvSource

**项目** `Flink`  **文件** `flink/flink-table/flink-table-planner/src/test/java/org/apache/flink/table/planner/plan/nodes/exec/serde/StateMetadataTest.java`  **测试** `testDeserializeFromMalformedJson`

### Test method

```java
@CsvSource(
            value = {
                "{\"index\":0,\"name\":\"fooState\"}|state ttl should not be null",
                "{\"index\":-1,\"ttl\":\"3600000ms\",\"name\":\"barState\"}|state index should start from 0",
                "{\"ttl\":\"3600000ms\",\"index\":1}|state name should not be null"
            },
            delimiterString = "|")
    @ParameterizedTest
    public void testDeserializeFromMalformedJson(String malformedJson, String expectedMsg) {
        assertThatThrownBy(
                        () ->
                                toObject(
                                        configuredSerdeContext(),
                                        malformedJson,
                                        StateMetadata.class))
                .hasMessageContaining(expectedMsg);
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-019  ·  MethodSource

**项目** `Zeppelin`  **文件** `zeppelin/zeppelin-plugins/notebookrepo/gcs/src/test/java/org/apache/zeppelin/notebook/repo/GCSNotebookRepoTest.java`  **测试** `testSave_create`

### Test method

```java
@ParameterizedTest
  @MethodSource("buckets")
  void testSave_create(String bucketName, Optional<String> basePath, String uriPath) throws Exception {
    zConf.setProperty(ConfVars.ZEPPELIN_NOTEBOOK_GCS_STORAGE_DIR.getVarName(), uriPath);
    this.notebookRepo = new GCSNotebookRepo(zConf, noteParser, storage);
    notebookRepo.save(runningNote, AUTH_INFO);
    // Output is saved
    assertThat(storage.readAllBytes(makeBlobId(runningNote.getId(), runningNote.getPath(), bucketName, basePath)))
        .isEqualTo(runningNote.toJson().getBytes("UTF-8"));
  }
```

### Parameter provider — 同文件内的 `buckets`

```java
  private static Stream<Arguments> buckets() {
    return Stream.of(
      Arguments.of("bucketname", Optional.empty(), "gs://bucketname"),
      Arguments.of("bucketname-with-slash", Optional.empty(), "gs://bucketname-with-slash/"),
      Arguments.of("bucketname", Optional.of("path/to/dir"), "gs://bucketname/path/to/dir"),
      Arguments.of("bucketname", Optional.of("trailing/slash"), "gs://bucketname/trailing/slash/"));
  }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`makeBlobId`**

```java
  private BlobId makeBlobId(String noteId, String notePath, String bucketName, Optional<String> basePath) {
    if (basePath.isPresent()) {
      return BlobId.of(bucketName, basePath.get() + notePath + "_" + noteId +".zpln");
    } else {
      return BlobId.of(bucketName, notePath.substring(1) + "_" + noteId +".zpln");
    }
  }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-022  ·  MethodSource

**项目** `ZooKeeper`  **文件** `zookeeper/zookeeper-server/src/test/java/org/apache/zookeeper/common/JKSFileLoaderTest.java`  **测试** `testLoadKeyStoreWithNullFilePath`

### Test method

```java
@ParameterizedTest
    @MethodSource("data")
    public void testLoadKeyStoreWithNullFilePath(
            X509KeyType caKeyType, X509KeyType certKeyType, String keyPassword, Integer paramIndex)
            throws Exception {
        init(caKeyType, certKeyType, keyPassword, paramIndex);
        assertThrows(NullPointerException.class, () -> {
            new JKSFileLoader.Builder().setKeyStorePassword(x509TestContext.getKeyStorePassword()).build().loadKeyStore();
        });
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

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-025  ·  MethodSource

**项目** `Accumulo`  **文件** `accumulo/core/src/test/java/org/apache/accumulo/core/data/RowRangeTest.java`  **测试** `testClip`

### Test method

```java
@ParameterizedTest
    @MethodSource("clipTestArguments")
    void testClip(RowRange fence, RowRange range, RowRange expected) {
      if (expected != null) {
        RowRange clipped = fence.clip(range);
        assertEquals(expected, clipped);
      } else {
        assertThrows(IllegalArgumentException.class, () -> fence.clip(range));
      }
    }
```

### Parameter provider — 同文件内的 `clipTestArguments`

```java
    private Stream<Arguments> clipTestArguments() {
      RowRange fenceOpen = RowRange.open("a", "c");
      RowRange fenceClosedOpen = RowRange.closedOpen("a", "c");
      RowRange fenceOpenClosed = RowRange.openClosed("a", "c");
      RowRange fenceClosed = RowRange.closed("a", "c");

      RowRange fenceOpenCN = RowRange.open("c", "n");
      RowRange fenceClosedCN = RowRange.closed("c", "n");
      RowRange fenceClosedB = RowRange.closed("b");

      return Stream.of(
          // (a,c) (a,c) -> (a,c)
          Arguments.of(fenceOpen, RowRange.open("a", "c"), RowRange.open("a", "c")),
          // (a,c) [a,c) -> (a,c)
          Arguments.of(fenceOpen, RowRange.closedOpen("a", "c"), RowRange.open("a", "c")),
          // (a,c) (a,c] -> (a,c)
          Arguments.of(fenceOpen, RowRange.openClosed("a", "c"), RowRange.open("a", "c")),
          // (a,c) [a,c] -> (a,c)
          Arguments.of(fenceOpen, RowRange.closed("a", "c"), RowRange.open("a", "c")),

          // [a,c) (a,c) -> (a,c)
          Arguments.of(fenceClosedOpen, RowRange.open("a", "c"), RowRange.open("a", "c")),
          // [a,c) [a,c) -> [a,c)
          Arguments.of(fenceClosedOpen, RowRange.closedOpen("a", "c"),
              RowRange.closedOpen("a", "c")),
          // [a,c) (a,c] -> (a,c)
          Arguments.of(fenceClosedOpen, RowRange.openClosed("a", "c"), RowRange.open("a", "c")),
          // [a,c) [a,c] -> [a,c)
          Arguments.of(fenceClosedOpen, RowRange.closed("a", "c"), RowRange.closedOpen("a", "c")),

          // (a,c] (a,c) -> (a,c)
          Arguments.of(fenceOpenClosed, RowRange.open("a", "c"), RowRange.open("a", "c")),
          // (a,c] [a,c) -> (a,c)
          Arguments.of(fenceOpenClosed, RowRange.closedOpen("a", "c"), RowRange.open("a", "c")),
          // (a,c] (a,c] -> (a,c]
          Arguments.of(fenceOpenClosed, RowRange.openClosed("a", "c"),
              RowRange.openClosed("a", "c")),
          // (a,c] [a,c] -> (a,c]
          Arguments.of(fenceOpenClosed, RowRange.closed("a", "c"), RowRange.openClosed("a", "c")),
          // (a,c] (-inf, c) -> (a,c)
          Arguments.of(fenceOpenClosed, RowRange.lessThan("c"), RowRange.open("a", "c")),
          // (a,c] (-inf, a) -> empty
          Arguments.of(fenceOpenClosed, RowRange.lessThan("a"), null),

          // [a,c] (a,c) -> (a,c)
          Arguments.of(fenceClosed, RowRange.open("a", "c"), RowRange.open("a", "c")),
          // [a,c] [a,c) -> [a,c)
          Arguments.of(fenceClosed, RowRange.closedOpen("a", "c"), RowRange.closedOpen("a", "c")),
          // [a,c] (a,c] -> (a,c]
          Arguments.of(fenceClosed, RowRange.openClosed("a", "c"), RowRange.openClosed("a", "c")),
          // [a,c] [a,c] -> [a,c]
          Arguments.of(fenceClosed, RowRange.closed("a", "c"), RowRange.closed("a", "c")),

          // (a,c) (-inf, +inf) -> (a,c)
          Arguments.of(fenceOpen, RowRange.all(), fenceOpen),
          // (a,c) [a, +inf) -> (a,c)
          Arguments.of(fenceOpen, RowRange.atLeast("a"), fenceOpen),
          // (a,c) (-inf, c] -> (a,c)
          Arguments.of(fenceOpen, RowRange.atMost("c"), fenceOpen),
          // (a,c) [a,c] -> (a,c)
          Arguments.of(fenceOpen, RowRange.closed("a", "c"), fenceOpen),

          // (a,c) (0,z) -> (a,c)
          Arguments.of(fenceOpen, RowRange.open("0", "z"), fenceOpen),
          // (a,c) [0,z) -> (a,c)
          Arguments.of(fenceOpen, RowRange.closedOpen("0", "z"), fenceOpen),
          // (a,c) (0,z] -> (a,c)
          Arguments.of(fenceOpen, RowRange.openClosed("0", "z"), fenceOpen),
          // (a,c) [0,z] -> (a,c)
          Arguments.of(fenceOpen, RowRange.closed("0", "z"), fenceOpen),

          // (a,c) (0,b) -> (a,b)
          Arguments.of(fenceOpen, RowRange.open("0", "b"), RowRange.open("a", "b")),
          // (a,c) [0,b) -> (a,b)
          Arguments.of(fenceOpen, RowRange.closedOpen("0", "b"), RowRange.open("a", "b")),
          // (a,c) (0,b] -> (a,b]
          Arguments.of(fenceOpen, RowRange.openClosed("0", "b"), RowRange.openClosed("a", "b")),
          // (a,c) [0,b] -> (a,b]
          Arguments.of(fenceOpen, RowRange.closed("0", "b"), RowRange.openClosed("a", "b")),

          // (a,c) (a1,z) -> (a1,c)
          Arguments.of(fenceOpen, RowRange.open("a1", "z"), RowRange.open("a1", "c")),
          // (a,c) [a1,z) -> [a1,c)
          Arguments.of(fenceOpen, RowRange.closedOpen("a1", "z"), RowRange.closedOpen("a1", "c")),
          // (a,c) (a1,z] -> (a1,c)
          Arguments.of(fenceOpen, RowRange.openClosed("a1", "z"), RowRange.open("a1", "c")),
          // (a,c) [a1,z] -> [a1,c)
          Arguments.of(fenceOpen, RowRange.closed("a1", "z"), RowRange.closedOpen("a1", "c")),

          // (a,c) (a1,b) -> (a1,b)
          Arguments.of(fenceOpen, RowRange.open("a1", "b"), RowRange.open("a1", "b")),
          // (a,c) [a1,b) -> [a1,b)
          Arguments.of(fenceOpen, RowRange.closedOpen("a1", "b"), RowRange.closedOpen("a1", "b")),
          // (a,c) (a1,b] -> (a1,b]
          Arguments.of(fenceOpen, RowRange.openClosed("a1", "b"), RowRange.openClosed("a1", "b")),
          // (a,c) [a1,b] -> [a1,b]
          Arguments.of(fenceOpen, RowRange.closed("a1", "b"), RowRange.closed("a1", "b")),
          // (a,c) (a,+inf) -> (a,c)
          Arguments.of(fenceOpen, RowRange.greaterThan("a"), RowRange.open("a", "c")),
          // (a,c) (1,+inf) -> (a,c)
          Arguments.of(fenceOpen, RowRange.greaterThan("1"), RowRange.open("a", "c")),

          // (c,n) (a,c) -> empty
          Arguments.of(fenceOpenCN, RowRange.open("a", "c"), null),
          // (c,n) (a,c] -> empty
          Arguments.of(fenceOpenCN, RowRange.closedOpen("a", "c"), null),
          // (c,n) (n,r) -> empty
          Arguments.of(fenceOpenCN, RowRange.open("n", "r"), null),
          // (c,n) [n,r) -> empty
          Arguments.of(fenceOpenCN, RowRange.closedOpen("n", "r"), null),
          // (c,n) (a,b) -> empty
          Arguments.of(fenceOpenCN, RowRange.open("a", "b"), null),
          // (c,n) (a,b] -> empty
          Arguments.of(fenceOpenCN, RowRange.closedOpen("a", "b"), null),

          // [c,n] (a,c) -> empty
          Arguments.of(fenceClosedCN, RowRange.open("a", "c"), null),
          // [c,n] (a,c] -> (c,c)
          Arguments.of(fenceClosedCN, RowRange.openClosed("a", "c"), RowRange.closed("c")),
          // [c,n] (n,r) -> (n,n)
          Arguments.of(fenceClosedCN, RowRange.open("n", "r"), null),
          // [c,n] [n,r) -> (n,n)
          Arguments.of(fenceClosedCN, RowRange.closedOpen("n", "r"), RowRange.closed("n")),
          // [c,n] (q,r) -> empty
          Arguments.of(fenceClosedCN, RowRange.open("q", "r"), null),
          // [c,n] [q,r) -> empty
          Arguments.of(fenceClosedCN, RowRange.closedOpen("q", "r"), null),

          // [b] (b,c) -> empty
          Arguments.of(fenceClosedB, RowRange.open("b", "c"), null),
          // [b] [b,c) -> [b]
          Arguments.of(fenceClosedB, RowRange.closedOpen("b", "c"), RowRange.closed("b")),
          // [b] (a,b) -> empty
          Arguments.of(fenceClosedB, RowRange.open("a", "b"), null),
          // [b] (a,b] -> [b]
          Arguments.of(fenceClosedB, RowRange.openClosed("a", "b"), RowRange.closed("b")));
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-028  ·  EnumSource

**项目** `Commons-RNG`  **文件** `commons-rng/commons-rng-simple/src/test/java/org/apache/commons/rng/simple/internal/RandomSourceInternalParametricTest.java`  **测试** `testCreateSeedBytes`

### Test method

```java
@ParameterizedTest
    @EnumSource
    void testCreateSeedBytes(RandomSourceInternal randomSourceInternal) {
        // This should be the full length seed
        final byte[] seed = randomSourceInternal.createSeedBytes(new SplitMix64(12345L));
        final int size = seed.length;

        final Integer expected = EXPECTED_SEED_BYTES.get(randomSourceInternal);
        Assertions.assertNotNull(expected, () -> "Missing expected seed byte size: " + randomSourceInternal);
        Assertions.assertEquals(expected.intValue(), size, randomSourceInternal::toString);
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

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-031  ·  MethodSource

**项目** `Druid`  **文件** `druid/multi-stage-query/src/test/java/org/apache/druid/msq/exec/MSQInsertTest.java`  **测试** `testRollUpOnExternalDataSource`

### Test method

```java
@MethodSource("data")
  @ParameterizedTest(name = "{index}:with context {0}")
  public void testRollUpOnExternalDataSource(String contextName, Map<String, Object> context) throws IOException
  {
    final File toRead = getResourceAsTemporaryFile("/wikipedia-sampled.json");
    final String toReadFileNameAsJson = queryFramework().queryJsonMapper().writeValueAsString(toRead.getAbsolutePath());

    RowSignature rowSignature = RowSignature.builder()
                                            .add("__time", ColumnType.LONG)
                                            .add("cnt", ColumnType.LONG)
                                            .build();

    testIngestQuery().setSql(" insert into foo1 SELECT\n"
                             + "  floor(TIME_PARSE(\"timestamp\") to day) AS __time,\n"
                             + "  count(*) as cnt\n"
                             + "FROM TABLE(\n"
                             + "  EXTERN(\n"
                             + "    '{ \"files\": [" + toReadFileNameAsJson + "],\"type\":\"local\"}',\n"
                             + "    '{\"type\": \"json\"}',\n"
                             + "    '[{\"name\": \"timestamp\", \"type\": \"string\"}, {\"name\": \"page\", \"type\": \"string\"}, {\"name\": \"user\", \"type\": \"string\"}]'\n"
                             + "  )\n"
                             + ") group by 1  PARTITIONED by day ")
                     .setQueryContext(new ImmutableMap.Builder<String, Object>().putAll(context).putAll(
                         ROLLUP_CONTEXT_PARAMS).build())
                     .setExpectedRollUp(true)
                     .setExpectedDataSource("foo1")
                     .setExpectedRowSignature(rowSignature)
                     .addExpectedAggregatorFactory(new LongSumAggregatorFactory("cnt", "cnt"))
                     .setExpectedSegments(ImmutableSet.of(SegmentId.of(
                         "foo1",
                         Intervals.of("2016-06-27/P1D"),
                         "test",
                         0
                     )))
                     .setExpectedResultRows(ImmutableList.of(new Object[]{1466985600000L, 20L}))
                     .setExpectedCountersForStageWorkerChannel(
                         CounterSnapshotMatcher
                             .with().rows(20).bytes(toRead.length()).files(1).totalFiles(1),
                         0, 0, "input0"
                     )
                     .setExpectedCountersForStageWorkerChannel(
                         CounterSnapshotMatcher
                             .with().rows(1).frames(1),
                         0, 0, "shuffle"
                     )
                     .setExpectedCountersForStageWorkerChannel(
                         CounterSnapshotMatcher
                             .with().rows(1).frames(1),
                         1, 0, "input0"
                     )
                     .setExpectedCountersForStageWorkerChannel(
                         CounterSnapshotMatcher
                             .with().rows(1).frames(1),
                         1, 0, "shuffle"
                     )
                     .setExpectedCountersForStageWorkerChannel(
                         CounterSnapshotMatcher
                             .with().rows(1).frames(1),
                         2, 0, "input0"
                     )
                     .setExpectedSegmentGenerationProgressCountersForStageWorker(
                         CounterSnapshotMatcher
                             .with().segmentRowsProcessed(1),
                         2, 0
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

## IRR-034  ·  CsvSource

**项目** `Hudi`  **文件** `hudi/hudi-client/hudi-client-common/src/test/java/org/apache/hudi/table/upgrade/TestSevenToEightUpgradeHandler.java`  **测试** `testUpgradeMergeMode`

### Test method

```java
@ParameterizedTest
  @CsvSource({
      // hard coding all merge strategy Ids since older version of hudi has different variable name to represent the merge strategy id.
      "com.example.CustomPayload, , CUSTOM, " + "00000000-0000-0000-0000-000000000000" + ", com.example.CustomPayload",
      "com.example.CustomPayload, preCombineFieldValue, CUSTOM, " + "00000000-0000-0000-0000-000000000000" + ", com.example.CustomPayload",
      "org.apache.hudi.metadata.HoodieMetadataPayload, , CUSTOM, " + "00000000-0000-0000-0000-000000000000" + ", org.apache.hudi.metadata.HoodieMetadataPayload",
      "org.apache.hudi.metadata.HoodieMetadataPayload, preCombineFieldValue, CUSTOM, " + "00000000-0000-0000-0000-000000000000" + ", org.apache.hudi.metadata.HoodieMetadataPayload",
      "org.apache.hudi.common.model.OverwriteWithLatestAvroPayload, , COMMIT_TIME_ORDERING, " + "ce9acb64-bde0-424c-9b91-f6ebba25356d"
          + ", org.apache.hudi.common.model.OverwriteWithLatestAvroPayload",
      "org.apache.hudi.common.model.DefaultHoodieRecordPayload, , EVENT_TIME_ORDERING, " + "eeb8d96f-b1e4-49fd-bbf8-28ac514178e5"
          + ", org.apache.hudi.common.model.DefaultHoodieRecordPayload",
      ", preCombineFieldValue, EVENT_TIME_ORDERING, " + "eeb8d96f-b1e4-49fd-bbf8-28ac514178e5" + ", org.apache.hudi.common.model.DefaultHoodieRecordPayload",
      "org.apache.hudi.common.model.OverwriteWithLatestAvroPayload, preCombineFieldValue, EVENT_TIME_ORDERING,"
          + "eeb8d96f-b1e4-49fd-bbf8-28ac514178e5" + ", org.apache.hudi.common.model.DefaultHoodieRecordPayload",
      ", preCombineFieldValue, EVENT_TIME_ORDERING, " + "eeb8d96f-b1e4-49fd-bbf8-28ac514178e5" + ", org.apache.hudi.common.model.DefaultHoodieRecordPayload",
      "org.apache.hudi.common.model.DefaultHoodieRecordPayload, preCombineFieldValue, EVENT_TIME_ORDERING,"
          + "eeb8d96f-b1e4-49fd-bbf8-28ac514178e5" + ", org.apache.hudi.common.model.DefaultHoodieRecordPayload",
      ", , COMMIT_TIME_ORDERING, " + "ce9acb64-bde0-424c-9b91-f6ebba25356d" + ", org.apache.hudi.common.model.OverwriteWithLatestAvroPayload"
  })
  void testUpgradeMergeMode(String payloadClass, String preCombineField, String expectedMergeMode, String expectedStrategy, String expectedPayloadClass) {
    HoodieTableConfig tableConfig = Mockito.mock(HoodieTableConfig.class);
    Map<ConfigProperty, String> tablePropsToAdd = new HashMap<>();

    when(tableConfig.getPayloadClass()).thenReturn(payloadClass);
    when(tableConfig.getOrderingFieldsStr()).thenReturn(Option.ofNullable(preCombineField));

    SevenToEightUpgradeHandler.upgradeMergeMode(tableConfig, tablePropsToAdd);

    assertEquals(expectedMergeMode, tablePropsToAdd.get(HoodieTableConfig.RECORD_MERGE_MODE));
    assertEquals(expectedStrategy, tablePropsToAdd.get(HoodieTableConfig.RECORD_MERGE_STRATEGY_ID));
    if (expectedPayloadClass != null) {
      assertEquals(expectedPayloadClass, tablePropsToAdd.get(HoodieTableConfig.PAYLOAD_CLASS_NAME));
    } else {
      assertTrue(!tablePropsToAdd.containsKey(HoodieTableConfig.PAYLOAD_CLASS_NAME));
    }
  }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-037  ·  MethodSource

**项目** `Hadoop`  **文件** `hadoop/hadoop-common-project/hadoop-common/src/test/java/org/apache/hadoop/fs/TestLocalDirAllocator.java`  **测试** `testCreateManyFilesRandom`

### Test method

```java
@Timeout(value = 30)
  @MethodSource("params")
  @ParameterizedTest
  public void testCreateManyFilesRandom(String paramRoot, String paramPrefix) throws Exception {
    assumeNotWindows();
    initTestLocalDirAllocator(paramRoot, paramPrefix);
    final int numDirs = 5;
    final int numTries = 100;
    String[] dirs = new String[numDirs];
    for (int d = 0; d < numDirs; ++d) {
      dirs[d] = buildBufferDir(root, d);
    }
    boolean next_dir_not_selected_at_least_once = false;
    try {
      conf.set(CONTEXT, dirs[0] + "," + dirs[1] + "," + dirs[2] + ","
          + dirs[3] + "," + dirs[4]);
      Path[] paths = new Path[5];
      for (int d = 0; d < numDirs; ++d) {
        paths[d] = new Path(dirs[d]);
        assertTrue(localFs.mkdirs(paths[d]));
      }

      int inDir=0;
      int prevDir = -1;
      int[] counts = new int[5];
      for(int i = 0; i < numTries; ++i) {
        File result = createTempFile(SMALL_FILE_SIZE);
        for (int d = 0; d < numDirs; ++d) {
          if (result.getPath().startsWith(paths[d].toUri().getPath())) {
            inDir = d;
            break;
          }
        }
        // Verify we always select a different dir
        assertNotEquals(prevDir, inDir);
        // Verify we are not always selecting the next dir - that was the old
        // algorithm.
        if ((prevDir != -1) && (inDir != ((prevDir + 1) % numDirs))) {
          next_dir_not_selected_at_least_once = true;
        }
        prevDir = inDir;
        counts[inDir]++;
        result.delete();
      }
    } finally {
      rmBufferDirs();
    }
    assertTrue(next_dir_not_selected_at_least_once);
  }
```

### Parameter provider — 同文件内的 `params`

```java
  public static Collection<Object[]> params() {
    Object [][] data = new Object[][] {
      { BUFFER_DIR_ROOT, RELATIVE },
      { ABSOLUTE_DIR_ROOT, ABSOLUTE },
      { QUALIFIED_DIR_ROOT, QUALIFIED }
    };

    return Arrays.asList(data);
  }
```

### Test-side helpers called by this test (4)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`initTestLocalDirAllocator`**

```java
  public void initTestLocalDirAllocator(String paramRoot, String paramPrefix) {
    this.root = paramRoot;
    this.prefix = paramPrefix;
  }
```

**`buildBufferDir`**

```java
  private String buildBufferDir(String dir, int i) {
    return dir + prefix + i;
  }
```

**`createTempFile`**

```java
  private static File createTempFile() throws IOException {
    return createTempFile(-1);
  }
```

**`rmBufferDirs`**

```java
  private static void rmBufferDirs() throws IOException {
    assertTrue(!localFs.exists(BUFFER_PATH_ROOT) ||
        localFs.delete(BUFFER_PATH_ROOT, true));
  }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-040  ·  ValueSource

**项目** `Calcite`  **文件** `calcite/testkit/src/main/java/org/apache/calcite/test/SqlOperatorTest.java`  **测试** `testTimestampDiff`

### Test method

```java
@ValueSource(booleans = {true, false})
  @ParameterizedTest(name = "CoercionEnabled: {0}")
  void testTimestampDiff(boolean coercionEnabled) {
    final SqlOperatorFixture f = fixture()
        .withValidatorConfig(c -> c.withTypeCoercionEnabled(coercionEnabled));
    f.setFor(SqlStdOperatorTable.TIMESTAMP_DIFF, VmName.EXPAND);
    HOUR_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "timestamp '2016-02-24 12:42:25', "
                + "timestamp '2016-02-24 15:42:25')",
            "3", "INTEGER NOT NULL"));
    MICROSECOND_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "timestamp '2016-02-24 12:42:25', "
                + "timestamp '2016-02-24 12:42:20')",
            "-5000000", "INTEGER NOT NULL"));
    NANOSECOND_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "timestamp '2016-02-24 12:42:25', "
                + "timestamp '2016-02-24 12:42:20')",
            "-5000000000", "BIGINT NOT NULL"));
    YEAR_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "timestamp '2014-02-24 12:42:25', "
                + "timestamp '2016-02-24 12:42:25')",
            "2", "INTEGER NOT NULL"));
    WEEK_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "timestamp '2014-02-24 12:42:25', "
                + "timestamp '2016-02-24 12:42:25')",
            "104", "INTEGER NOT NULL"));
    WEEK_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "timestamp '2014-02-19 12:42:25', "
                + "timestamp '2016-02-24 12:42:25')",
            "105", "INTEGER NOT NULL"));
    MONTH_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "timestamp '2014-02-24 12:42:25', "
                + "timestamp '2016-02-24 12:42:25')",
            "24", "INTEGER NOT NULL"));
    MONTH_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "timestamp '2019-09-01 00:00:00', "
                + "timestamp '2020-03-01 00:00:00')",
            "6", "INTEGER NOT NULL"));
    MONTH_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "timestamp '2019-09-01 00:00:00', "
                + "timestamp '2016-08-01 00:00:00')",
            "-37", "INTEGER NOT NULL"));
    QUARTER_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "timestamp '2014-02-24 12:42:25', "
                + "timestamp '2016-02-24 12:42:25')",
            "8", "INTEGER NOT NULL"));
    // Until 1.33, CENTURY was an invalid time frame for TIMESTAMPDIFF
    f.checkScalar("timestampdiff(CENTURY, "
            + "timestamp '2014-02-24 12:42:25', "
            + "timestamp '2614-02-24 12:42:25')",
        "6", "INTEGER NOT NULL");
    QUARTER_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "timestamp '2014-02-24 12:42:25', "
                + "cast(null as timestamp))",
            isNullValue(), "INTEGER"));
    QUARTER_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "cast(null as timestamp), "
                + "timestamp '2014-02-24 12:42:25')",
            isNullValue(), "INTEGER"));

    // timestampdiff with date
    MONTH_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "date '2016-03-15', date '2016-06-14')",
            "2", "INTEGER NOT NULL"));
    MONTH_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "date '2019-09-01', date '2020-03-01')",
            "6", "INTEGER NOT NULL"));
    MONTH_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "date '2019-09-01', date '2016-08-01')",
            "-37", "INTEGER NOT NULL"));
    MONTH_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "time '12:42:25', time '12:42:25')",
            "0", "INTEGER NOT NULL"));
    // 2 test cases for [CALCITE-7146] TIMESTAMPDIFF accepts arguments with mismatched types
    MONTH_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "time '12:42:25', date '2016-06-14')",
            "557", "INTEGER NOT NULL"));
    MONTH_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "date '2016-06-14', time '12:42:25')",
            "-557", "INTEGER NOT NULL"));
    DAY_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "date '2016-06-15', date '2016-06-14')",
            "-1", "INTEGER NOT NULL"));
    HOUR_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "date '2016-06-15', date '2016-06-14')",
            "-24", "INTEGER NOT NULL"));
    HOUR_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "date '2016-06-15',  date '2016-06-15')",
            "0", "INTEGER NOT NULL"));
    MINUTE_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "date '2016-06-15', date '2016-06-14')",
            "-1440", "INTEGER NOT NULL"));
    SECOND_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "cast(null as date), date '2016-06-15')",
            isNullValue(), "INTEGER"));
    DAY_VARIANTS.forEach(s ->
        f.checkScalar("timestampdiff(" + s + ", "
                + "date '2016-06-15', cast(null as date))",
            isNullValue(), "INTEGER"));
  }
```

### Test-side helpers called by this test (2)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`fixture`**

```java
  protected SqlOperatorFixture fixture() {
    return SqlOperatorFixtureImpl.DEFAULT;
  }
```

**`forEach`**

```java
    static void forEach(Consumer<Numeric> consumer) {
      consumer.accept(TINYINT);
      consumer.accept(SMALLINT);
      consumer.accept(INTEGER);
      consumer.accept(BIGINT);
      consumer.accept(DECIMAL5_2);
      consumer.accept(REAL);
      consumer.accept(FLOAT);
      consumer.accept(DOUBLE);
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-043  ·  ValueSource

**项目** `Camel`  **文件** `camel/components/camel-coap/src/test/java/org/apache/camel/coap/CoAPComponentTLSTestBase.java`  **测试** `testCall`

### Test method

```java
@ParameterizedTest
    @ValueSource(strings = { "direct:start", "direct:selfsigned", /*"direct:clientauth",*/ "direct:ciphersuites" })
    @DisplayName("Test calls with/without certificates")
    void testCall(String endpointUri) throws Exception {
        MockEndpoint mock = getMockEndpoint("mock:result");
        mock.expectedMinimumMessageCount(1);
        mock.expectedBodiesReceived("Hello Camel CoAP");
        mock.expectedHeaderReceived(CoAPConstants.CONTENT_TYPE,
                MediaTypeRegistry.toString(MediaTypeRegistry.APPLICATION_OCTET_STREAM));
        mock.expectedHeaderReceived(CoAPConstants.COAP_RESPONSE_CODE, CoAP.ResponseCode.CONTENT.toString());
        sendBodyAndHeader(endpointUri, "Camel CoAP", CoAPConstants.COAP_METHOD, "POST");
        MockEndpoint.assertIsSatisfied(context);
    }
```

### Test-side helpers called by this test (2)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`sendBodyAndHeader`**

```java
    protected void sendBodyAndHeader(String endpointUri, final Object body, String headerName, String headerValue) {
        template.send(endpointUri, new Processor() {
            public void process(Exchange exchange) {
                Message in = exchange.getIn();
                in.setBody(body);
                in.setHeader(headerName, headerValue);
            }
        });
    }
```

**`process`**

```java
            public void process(Exchange exchange) {
                Message in = exchange.getIn();
                in.setBody(body);
                in.setHeader(headerName, headerValue);
            }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-046  ·  CsvSource

**项目** `XMLBeans`  **文件** `xmlbeans/src/test/java/xmlobject/checkin/CDataTest.java`  **测试** `checkCData`

### Test method

```java
@ParameterizedTest
    @CsvSource(value = {
        "'<a><![CDATA[cdata text]]></a>'," +
        "'<a><![CDATA[cdata text]]></a>'," +
        "'<a><![CDATA[cdata text]]></a>'",
        // Bookmark doesn't seem to keep the length of the CDATA
        // "<a>NL<b><![CDATA[cdata text]]> regular text</b>NL</a>," +
        // "<a>\n<b>cdata text regular text</b>\n</a>," +
        // "<a>NL  <b>cdata text regular text</b>NL</a>"
        "'<a>\n<c>text <![CDATA[cdata text]]></c>\n</a>'," +
        "'<a>\n<c>text cdata text</c>\n</a>'," +
        "'<a>NL  <c>text cdata text</c>NL</a>'",
        // https://issues.apache.org/jira/browse/XMLBEANS-404
        "'<a>\n<c>text <![CDATA[cdata text]]]]></c>\n</a>'," +
        "'<a>\n<c>text cdata text]]</c>\n</a>'," +
        "'<a>NL  <c>text cdata text]]</c>NL</a>'"
    })
    void checkCData(String xmlText, String expected1, String expected2) throws XmlException {
        String NL = Stream.of(SystemProperties.getProperty("line.separator"),System.getProperty("line.separator"),"\n")
            .filter(Objects::nonNull).findFirst().get();

        XmlOptions opts = new XmlOptions();
        opts.setUseCDataBookmarks();

        XmlObject xo = XmlObject.Factory.parse(xmlText.replace("NL", NL), opts);

        String result1 = xo.xmlText(opts);
        assertEquals(expected1.replace("NL", NL), result1, "xmlText");

        opts.setSavePrettyPrint();
        String result2 = xo.xmlText(opts);
        assertEquals(expected2.replace("NL", NL), result2, "prettyPrint");
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-049  ·  ValueSource

**项目** `Commons-RNG`  **文件** `commons-rng/commons-rng-sampling/src/test/java/org/apache/commons/rng/sampling/DiscreteProbabilityCollectionSamplerTest.java`  **测试** `testPrecondition4`

### Test method

```java
@ParameterizedTest
    @ValueSource(doubles = {-1, Double.POSITIVE_INFINITY, Double.NaN})
    void testPrecondition4(double p) {
        final List<Double> collection = Arrays.asList(1d, 2d);
        final double[] probabilities = {0, p};
        Assertions.assertThrows(IllegalArgumentException.class,
            () -> new DiscreteProbabilityCollectionSampler<>(rng,
                collection,
                probabilities));
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-052  ·  EnumSource

**项目** `Jena`  **文件** `jena/jena-ontapi/src/test/java/org/apache/jena/ontapi/OntClassHierarchyRootTest.java`  **测试** `testIsHierarchyRoot6`

### Test method

```java
@ParameterizedTest
    @EnumSource(names = {
            "OWL2_DL_MEM_RDFS_BUILTIN_INF",
            "OWL2_MEM_RDFS_INF",
            "OWL1_MEM_RDFS_INF",
    })
    public void testIsHierarchyRoot6(TestSpec spec) {
        // D  THING    G
        // |    |    / .
        // C    F   K  .
        // |    |   |  .
        // B    E   H  .
        // |         \ .
        // A           G
        OntModel m = TestModelFactory.createClassesDGCFKBEHAG(OntModelFactory.createModel(spec.inst));
        OntClass Thing = OWL2.Thing.inModel(m).as(OntClass.class);
        OntClass Nothing = OWL2.Nothing.inModel(m).as(OntClass.class);
        m.getOntClass(TestModelFactory.NS + "F").addSuperClass(Thing);

        Assertions.assertFalse(m.getOntClass(TestModelFactory.NS + "A").isHierarchyRoot());
        Assertions.assertFalse(m.getOntClass(TestModelFactory.NS + "B").isHierarchyRoot());
        Assertions.assertFalse(m.getOntClass(TestModelFactory.NS + "C").isHierarchyRoot());
        Assertions.assertTrue(m.getOntClass(TestModelFactory.NS + "D").isHierarchyRoot());
        Assertions.assertFalse(m.getOntClass(TestModelFactory.NS + "E").isHierarchyRoot());
        Assertions.assertTrue(m.getOntClass(TestModelFactory.NS + "F").isHierarchyRoot());
        Assertions.assertTrue(m.getOntClass(TestModelFactory.NS + "G").isHierarchyRoot());
        Assertions.assertTrue(m.getOntClass(TestModelFactory.NS + "H").isHierarchyRoot());
        Assertions.assertTrue(m.getOntClass(TestModelFactory.NS + "K").isHierarchyRoot());
        Assertions.assertTrue(Thing.isHierarchyRoot());
        Assertions.assertFalse(Nothing.isHierarchyRoot());
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

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-055  ·  CsvSource

**项目** `NiFi`  **文件** `nifi/nifi-extension-bundles/nifi-aws-bundle/nifi-aws-processors/src/test/java/org/apache/nifi/processors/aws/cloudwatch/TestPutCloudWatchMetric.java`  **测试** `testValidRegionRoutesToSuccess`

### Test method

```java
@ParameterizedTest
    @CsvSource({"us-east-1", "us-west-1", "us-east-2"})
    public void testValidRegionRoutesToSuccess(String region) {
        runner.setProperty(PutCloudWatchMetric.VALUE, "6");
        runner.setProperty(PutCloudWatchMetric.REGION, region);
        runner.assertValid();

        runner.enqueue(new byte[] {});
        runner.run();

        assertEquals(1, mockPutCloudWatchMetric.putMetricDataCallCount);
        runner.assertAllFlowFilesTransferred(PutCloudWatchMetric.REL_SUCCESS, 1);
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-058  ·  EnumSource

**项目** `Commons-RNG`  **文件** `commons-rng/commons-rng-simple/src/test/java/org/apache/commons/rng/simple/internal/RandomSourceInternalParametricTest.java`  **测试** `testCreateSeedBytesSizeIsPositiveAndMultipleOf4Or8`

### Test method

```java
@ParameterizedTest
    @EnumSource
    void testCreateSeedBytesSizeIsPositiveAndMultipleOf4Or8(RandomSourceInternal randomSourceInternal) {
        // This should be the full length seed
        final byte[] seed = randomSourceInternal.createSeedBytes(new SplitMix64(12345L));

        final int size = seed.length;
        Assertions.assertNotEquals(0, size, "Seed is empty");

        if (randomSourceInternal.isNativeSeed(Integer.valueOf(0))) {
            Assertions.assertEquals(4, size, "Expect 4 bytes for Integer");
        } else if (randomSourceInternal.isNativeSeed(Long.valueOf(0))) {
            Assertions.assertEquals(8, size, "Expect 8 bytes for Long");
        } else if (randomSourceInternal.isNativeSeed(new int[0])) {
            Assertions.assertEquals(0, size % 4, "Expect 4n bytes for int[]");
        } else if (randomSourceInternal.isNativeSeed(new long[0])) {
            Assertions.assertEquals(0, size % 8, "Expect 8n bytes for long[]");
        } else {
            Assertions.fail("Unknown native seed type");
        }
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

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-061  ·  EnumSource

**项目** `NiFi`  **文件** `nifi/nifi-system-tests/nifi-system-test-suite/src/test/java/org/apache/nifi/tests/system/provenance/ReplayProvenanceIT.java`  **测试** `testReplayLastEvent`

### Test method

```java
@ParameterizedTest
    @EnumSource(ReplayEventNodes.class)
    public void testReplayLastEvent(final ReplayEventNodes nodes) throws NiFiClientException, IOException, InterruptedException {
        ProcessorEntity generate = getClientUtil().createProcessor("GenerateFlowFile");
        ProcessorEntity terminate = getClientUtil().createProcessor("TerminateFlowFile");
        ConnectionEntity connection = getClientUtil().createConnection(generate, terminate, "success");

        // Run Generate once
        getClientUtil().startProcessor(generate);
        waitForQueueCount(connection.getId(), getNumberOfNodes());
        getClientUtil().stopProcessor(generate);

        // Run terminate once
        getClientUtil().startProcessor(terminate);
        waitForQueueCount(connection.getId(), 0);
        getClientUtil().stopProcessor(terminate);

        // Replay last event for terminate and ensure that data is queued up.
        final ReplayLastEventResponseEntity replayResponse = getNifiClient().getProvenanceClient().replayLastEvent(terminate.getId(), nodes);
        assertNull(replayResponse.getAggregateSnapshot().getFailureExplanation());
        assertEquals(Boolean.TRUE, replayResponse.getAggregateSnapshot().getEventAvailable());
        final int expectedEventsPlayed = (nodes == ReplayEventNodes.PRIMARY) ? 1 : getNumberOfNodes();
        assertEquals(expectedEventsPlayed, replayResponse.getAggregateSnapshot().getEventsReplayed().size());

        waitForQueueCount(connection.getId(), expectedEventsPlayed);

        // Attempt to replay event for generate - it should provide an error because this is a source processor whose event cannot be replayed
        final ReplayLastEventResponseEntity generateReplayResponse = getNifiClient().getProvenanceClient().replayLastEvent(generate.getId(), nodes);
        final String failureExplanation = generateReplayResponse.getAggregateSnapshot().getFailureExplanation();
        assertNotNull(failureExplanation);

        // The failure text is not provided if multiple nodes failed, as it can get too unwieldy to understand.
        final String expectedFailureText = (nodes == ReplayEventNodes.ALL && getNumberOfNodes() > 1) ? "See logs for more details" : "Source FlowFile Queue";
        assertTrue(failureExplanation.contains(expectedFailureText), failureExplanation);
    }
```

### Enum declaration — `ReplayEventNodes` (nifi/nifi-toolkit/nifi-toolkit-client/src/main/java/org/apache/nifi/toolkit/client/ProvenanceClient.java)

```java
    enum ReplayEventNodes {
        PRIMARY,
        ALL;
    }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-064  ·  ValueSource

**项目** `Hive`  **文件** `hive/iceberg/iceberg-catalog/src/test/java/org/apache/iceberg/hive/TestHiveCatalog.java`  **测试** `testReplaceTxnBuilder`

### Test method

```java
@ParameterizedTest
  @ValueSource(ints = {1, 2})
  public void testReplaceTxnBuilder(int formatVersion) {
    Schema schema = getTestSchema();
    PartitionSpec spec = PartitionSpec.builderFor(schema).bucket("data", 16).build();
    TableIdentifier tableIdent = TableIdentifier.of(DB_NAME, "tbl");
    String location = temp.resolve("tbl").toString();

    try {
      Transaction createTxn = catalog.buildTable(tableIdent, schema)
          .withPartitionSpec(spec)
          .withLocation(location)
          .withProperty("key1", "value1")
          .withProperty(TableProperties.FORMAT_VERSION, String.valueOf(formatVersion))
          .createOrReplaceTransaction();
      createTxn.commitTransaction();

      Table table = catalog.loadTable(tableIdent);
      assertThat(table.spec().fields()).hasSize(1);

      String newLocation = temp.resolve("tbl-2").toString();

      Transaction replaceTxn = catalog.buildTable(tableIdent, schema)
          .withProperty("key2", "value2")
          .withLocation(newLocation)
          .replaceTransaction();
      replaceTxn.commitTransaction();

      table = catalog.loadTable(tableIdent);
      assertThat(table.location()).isEqualTo(newLocation);
      assertThat(table.currentSnapshot()).isNull();
      if (formatVersion == 1) {
        PartitionSpec v1Expected =
            PartitionSpec.builderFor(table.schema())
                .alwaysNull("data", "data_bucket")
                .withSpecId(1)
                .build();
        assertThat(table.spec())
            .as("Table should have a spec with one void field")
            .isEqualTo(v1Expected);
      } else {
        assertThat(table.spec().isUnpartitioned()).as("Table spec must be unpartitioned").isTrue();
      }

      assertThat(table.properties()).containsEntry("key1", "value1");
      assertThat(table.properties()).containsEntry("key2", "value2");
    } finally {
      catalog.dropTable(tableIdent);
    }
  }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`getTestSchema`**

```java
  private Schema getTestSchema() {
    return new Schema(
        required(1, "id", Types.IntegerType.get(), "unique ID"),
        required(2, "data", Types.StringType.get()));
  }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-067  ·  MethodSource

**项目** `ZooKeeper`  **文件** `zookeeper/zookeeper-server/src/test/java/org/apache/zookeeper/common/PEMFileLoaderTest.java`  **测试** `testLoadKeyStoreWithWrongFileType`

### Test method

```java
@ParameterizedTest
    @MethodSource("data")
    public void testLoadKeyStoreWithWrongFileType(
            X509KeyType caKeyType, X509KeyType certKeyType, String keyPassword, Integer paramIndex)
            throws Exception {
        init(caKeyType, certKeyType, keyPassword, paramIndex);
        assertThrows(KeyStoreException.class, () -> {
            // Trying to load a JKS file with PEM loader should fail
            String path = x509TestContext.getKeyStoreFile(KeyStoreFileType.JKS).getAbsolutePath();
            new PEMFileLoader.Builder()
                    .setKeyStorePath(path)
                    .setKeyStorePassword(x509TestContext.getKeyStorePassword())
                    .build()
                    .loadKeyStore();
        });
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

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-070  ·  EnumSource

**项目** `Hudi`  **文件** `hudi/hudi-io/src/test/java/org/apache/hudi/io/compress/TestHoodieCompressor.java`  **测试** `testDefaultDecompressors`

### Test method

```java
@ParameterizedTest
  @EnumSource(CompressionCodec.class)
  public void testDefaultDecompressors(CompressionCodec codec) throws IOException {
    switch (codec) {
      case NONE:
      case GZIP:
        HoodieCompressor decompressor = HoodieCompressorFactory.getCompressor(codec);
        byte[] actualOutput = new byte[INPUT_LENGTH + 100];
        try (InputStream stream = prepareInputStream(codec)) {
          for (int sizeToRead : READ_PART_SIZE_LIST) {
            stream.mark(INPUT_LENGTH);
            int actualSizeRead =
                decompressor.decompress(stream, actualOutput, 4, sizeToRead);
            assertEquals(actualSizeRead, Math.min(INPUT_LENGTH, sizeToRead));
            assertEquals(0, IOUtils.compareTo(
                actualOutput, 4, actualSizeRead, INPUT_BYTES, 0, actualSizeRead));
            stream.reset();
          }
        }
        break;
      default:
        assertThrows(
            IllegalArgumentException.class, () -> HoodieCompressorFactory.getCompressor(codec));
    }
  }
```

### Enum declaration — `CompressionCodec` (hudi/hudi-io/src/main/java/org/apache/hudi/io/compress/CompressionCodec.java)

```java
public enum CompressionCodec {
  NONE("none", 2),
  BZIP2("bz2", 5),
  GZIP("gz", 1),
  LZ4("lz4", 4),
  LZO("lzo", 0),
  SNAPPY("snappy", 3),
  ZSTD("zstd", 6);

  private static final Map<String, CompressionCodec>
      NAME_TO_COMPRESSION_CODEC_MAP = createNameToCompressionCodecMap();
  private static final Map<Integer, CompressionCodec>
      ID_TO_COMPRESSION_CODEC_MAP = createIdToCompressionCodecMap();

  private final String name;
  // CompressionCodec ID to be stored in HFile on storage
  // The ID of each codec cannot change or else that breaks all existing HFiles out there
  // even the ones that are not compressed! (They use the NONE algorithm)
  private final int id;

  CompressionCodec(final String name, int id) {
    this.name = name;
    this.id = id;
  }

  public String getName() {
    return name;
  }

  public int getId() {
    return id;
  }

  public static CompressionCodec findCodecByName(String name) {
    CompressionCodec codec =
        NAME_TO_COMPRESSION_CODEC_MAP.get(name.toLowerCase());
    ValidationUtils.checkArgument(
        codec != null, String.format("Cannot find compression codec: %s", name));
    return codec;
  }

  /**
   * Gets the compression codec based on the ID.  This ID is written to the HFile on storage.
   *
   * @param id ID indicating the compression codec
   * @return compression codec based on the ID
   */
  public static CompressionCodec decodeCompressionCodec(int id) {
    CompressionCodec codec = ID_TO_COMPRESSION_CODEC_MAP.get(id);
    ValidationUtils.checkArgument(
        codec != null, "Compression code not found for ID: " + id);
    return codec;
  }

  /**
   * @return the mapping of name to compression codec.
   */
  private static Map<String, CompressionCodec> createNameToCompressionCodecMap() {
    return Collections.unmodifiableMap(
        Arrays.stream(CompressionCodec.values())
            .collect(Collectors.toMap(CompressionCodec::getName, Function.identity()))
    );
  }

  /**
   * @return the mapping of ID to compression codec.
   */
  private static Map<Integer, CompressionCodec> createIdToCompressionCodecMap() {
    return Collections.unmodifiableMap(
        Arrays.stream(CompressionCodec.values())
            .collect(Collectors.toMap(CompressionCodec::getId, Function.identity()))
    );
  }
}
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`prepareInputStream`**

```java
  private static InputStream prepareInputStream(CompressionCodec codec) throws IOException {
    switch (codec) {
      case NONE:
        return new ByteArrayInputStream(
            new HoodieNoneCompressor().compress(INPUT_BYTES));
      case GZIP:
        return new ByteArrayInputStream(
            new HoodieAirliftGzipCompressor().compress(INPUT_BYTES));
      default:
        throw new IllegalArgumentException("Not supported in tests.");
    }
  }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-073  ·  MethodSource

**项目** `Commons-RDF`  **文件** `commons-rdf/commons-rdf-integration-tests/src/test/java/org/apache/commons/rdf/integrationtests/AllToAllTest.java`  **测试** `testAddTriplesFromOtherFactory`

### Test method

```java
@MethodSource("data")
    @ParameterizedTest(name = "{index}: {0} -> {1}")
    void testAddTriplesFromOtherFactory(final Class<? extends RDF> from, final Class<? extends RDF> to) throws Exception {
        RDF nodeFactory = from.getConstructor().newInstance();
        RDF graphFactory = to.newInstance();

        try (final Graph g = graphFactory.createGraph()) {
            final BlankNode s = nodeFactory.createBlankNode();
            final IRI p = nodeFactory.createIRI("http://example.com/p");
            final Literal o = nodeFactory.createLiteral("Hello");

            final Triple srcT1 = nodeFactory.createTriple(s, p, o);
            // This should work even with BlankNode as they are from the same
            // factory
            assertEquals(s, srcT1.getSubject());
            assertEquals(p, srcT1.getPredicate());
            assertEquals(o, srcT1.getObject());
            g.add(srcT1);

            // what about the blankNode within?
            assertTrue(g.contains(srcT1));
            final Triple t1 = g.stream().findAny().get();

            // Can't make assumptions about BlankNode equality - it might
            // have been mapped to a different BlankNode.uniqueReference()
            // assertEquals(srcT1, t1);
            // assertEquals(s, t1.getSubject());
            assertEquals(p, t1.getPredicate());
            assertEquals(o, t1.getObject());

            final IRI s2 = nodeFactory.createIRI("http://example.com/s2");
            final Triple srcT2 = nodeFactory.createTriple(s2, p, s);
            g.add(srcT2);
            assertTrue(g.contains(srcT2));

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

## IRR-076  ·  MethodSource

**项目** `Hudi`  **文件** `hudi/hudi-spark-datasource/hudi-spark/src/test/java/org/apache/hudi/functional/TestBufferedRecordMerger.java`  **测试** `testRegularMerging`

### Test method

```java
@ParameterizedTest
  @MethodSource("mergeModeAndStageProvider")
  void testRegularMerging(RecordMergeMode mergeMode, PartialUpdateMode updateMode, MergeStage stage) throws IOException {
    if (updateMode == PartialUpdateMode.FILL_UNAVAILABLE) {
      props.put(
          HoodieTableConfig.RECORD_MERGE_PROPERTY_PREFIX + PARTIAL_UPDATE_UNAVAILABLE_VALUE,
          IGNORE_MARKERS_VALUE);
    }

    if (stage == MergeStage.DELTA_MERGE) {
      runDeltaMerge(mergeMode, updateMode);
    } else if (stage == MergeStage.FINAL_MERGE) {
      runFinalMerge(mergeMode, updateMode);
    } else {
      runDeltaDeleteMerge(mergeMode, updateMode);
    }
  }
```

### Parameter provider — 同文件内的 `mergeModeAndStageProvider`

```java
  private static Stream<Arguments> mergeModeAndStageProvider() {
    List<MergeStage> stages = Arrays.asList(MergeStage.values());
    return Arrays.stream(RecordMergeMode.values())
        .filter(mode -> mode == RecordMergeMode.COMMIT_TIME_ORDERING || mode == RecordMergeMode.EVENT_TIME_ORDERING)
        .flatMap(mode ->
            Arrays.stream(PartialUpdateMode.values())
                .flatMap(updateMode ->
                    stages.stream()
                        .map(stage -> Arguments.of(mode, updateMode, stage))
                )
        )
        .filter(args -> {
          PartialUpdateMode updateMode = (PartialUpdateMode) args.get()[1];
          return updateMode != PartialUpdateMode.IGNORE_DEFAULTS;
        });
  }
```

### Test-side helpers called by this test (5)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`runDeltaMerge`**

```java
  private void runDeltaMerge(RecordMergeMode mergeMode, PartialUpdateMode updateMode) throws IOException {
    BufferedRecordMerger<InternalRow> merger = createMerger(readerContext, mergeMode, Option.of(updateMode));
    // Create records with all columns.
    InternalRow oldRecord = createFullRecord("old_id", "Old Name", 25, "Old City", 1000L);
    InternalRow newRecord = createFullRecord("new_id", "New Name", 0, IGNORE_MARKERS_VALUE, 0L);

    // CASE 1: New record has lower ordering value.
    BufferedRecord<InternalRow> oldBufferedRecord =
        new BufferedRecord<>(RECORD_KEY, ORDERING_VALUE, oldRecord, 1, null);
    BufferedRecord<InternalRow> newBufferedRecord =
        new BufferedRecord<>(RECORD_KEY, ORDERING_VALUE - 1, newRecord, 1, null);
    Option<BufferedRecord<InternalRow>> deltaResult = merger.deltaMerge(newBufferedRecord, oldBufferedRecord);
    if (mergeMode == COMMIT_TIME_ORDERING) {
      assertTrue(deltaResult.isPresent());
      if (updateMode == null) {
        assertEquals(newRecord, deltaResult.get().getRecord());
      } else if (updateMode == PartialUpdateMode.IGNORE_DEFAULTS) {
        assertEquals(25, deltaResult.get().getRecord().getInt(2));
        assertEquals(1000L, deltaResult.get().getRecord().getLong(4));
      } else if (updateMode == PartialUpdateMode.FILL_UNAVAILABLE) {
        assertEquals("Old City", deltaResult.get().getRecord().getString(3));
      }
    } else {
      if (updateMode == null) {
        assertTrue(deltaResult.isEmpty());
      } else if (updateMode == PartialUpdateMode.IGNORE_DEFAULTS) {
        assertTrue(deltaResult.isPresent());
        assertEquals(oldRecord, deltaResult.get().getRecord());
      }
    }

    // CASE 2: New record has higher ordering value.
    oldBufferedRecord = new BufferedRecord<>(RECORD_KEY, ORDERING_VALUE, oldRecord, 1, null);
    newBufferedRecord = new BufferedRecord<>(RECORD_KEY, ORDERING_VALUE + 1, newRecord, 1, null);
    deltaResult = merger.deltaMerge(newBufferedRecord, oldBufferedRecord);
    assertTrue(deltaResult.isPresent());
    if (updateMode == null) {
      assertEquals(newRecord, deltaResult.get().getRecord());
    } else if (updateMode == PartialUpdateMode.IGNORE_DEFAULTS) {
      assertEquals(25, deltaResult.get().getRecord().getInt(2));
      assertEquals(1000L, deltaResult.get().getRecord().getLong(4));
    } else if (updateMode == PartialUpdateMode.FILL_UNAVAILABLE) {
      assertEquals("Old City", deltaResult.get().getRecord().getString(3));
    }

    // CASE 3: New record and old record have the same ordering value.
    oldBufferedRecord = new BufferedRecord<>(RECORD_KEY, ORDERING_VALUE, oldRecord, 1, null);
    newBufferedRecord = new BufferedRecord<>(RECORD_KEY, ORDERING_VALUE, newRecord, 1, null);
    deltaResult = merger.deltaMerge(newBufferedRecord, oldBufferedRecord);
    assertTrue(deltaResult.isPresent());
    if (updateMode == null) {
      assertEquals(newRecord, deltaResult.get().getRecord());
    } else if (updateMode == PartialUpdateMode.IGNORE_DEFAULTS) {
      assertEquals(25, deltaResult.get().getRecord().getInt(2));
      assertEquals(1000L, deltaResult.get().getRecord().getLong(4));
    } else if (updateMode == PartialUpdateMode.FILL_UNAVAILABLE) {
      assertEquals("Old City", deltaResult.get().getRecord().getString(3));
    }
  }
```

**`runFinalMerge`**

```java
  private void runFinalMerge(RecordMergeMode mergeMode, PartialUpdateMode updateMode) throws IOException {
    BufferedRecordMerger<InternalRow> merger = createMerger(readerContext, mergeMode, Option.ofNullable(updateMode));
    InternalRow oldRecord = createFullRecord(
        "older_id", "Older Name", 20, "Older City", 500L);
    InternalRow newRecord = createFullRecord(
        "new_id", "New Name", 0, IGNORE_MARKERS_VALUE, 0L);

    // New record has lower ordering value.
    BufferedRecord<InternalRow> olderBufferedRecord =
        new BufferedRecord<>(RECORD_KEY, ORDERING_VALUE, oldRecord, 1, null);
    BufferedRecord<InternalRow> newerBufferedRecord =
        new BufferedRecord<>(RECORD_KEY, ORDERING_VALUE - 1, newRecord, 1, null);
    BufferedRecord<InternalRow> finalResult = merger.finalMerge(olderBufferedRecord, newerBufferedRecord);
    assertFalse(finalResult.isDelete());
    if (mergeMode == COMMIT_TIME_ORDERING) {
      if (updateMode == null) {
        assertEquals(newRecord, finalResult.getRecord());
      } else if (updateMode == PartialUpdateMode.IGNORE_DEFAULTS) {
        assertEquals(20, finalResult.getRecord().getInt(2));
        assertEquals(500L, finalResult.getRecord().getLong(4));
      } else if (updateMode == PartialUpdateMode.FILL_UNAVAILABLE) {
        assertEquals("Older City", finalResult.getRecord().getString(3));
      }
    } else {
      assertEquals(oldRecord, finalResult.getRecord());
    }

    // New record has higher ordering value.
    olderBufferedRecord = new BufferedRecord<>(RECORD_KEY, ORDERING_VALUE, oldRecord, 1, null);
    newerBufferedRecord = new BufferedRecord<>(RECORD_KEY, ORDERING_VALUE + 1, newRecord, 1, null);
    finalResult = merger.finalMerge(olderBufferedRecord, newerBufferedRecord);
    assertFalse(finalResult.isDelete());
    if (updateMode == null) {
      assertEquals(newRecord, finalResult.getRecord());
    } else if (updateMode == PartialUpdateMode.IGNORE_DEFAULTS) {
      assertEquals(20, finalResult.getRecord().getInt(2));
      assertEquals(500, finalResult.getRecord().getLong(4));
    } else if (updateMode == PartialUpdateMode.FILL_UNAVAILABLE) {
      assertEquals("Older City", finalResult.getRecord().getString(3));
    }

    // New record has equal ordering value.
    olderBufferedRecord = new BufferedRecord<>(RECORD_KEY, ORDERING_VALUE, oldRecord, 1, null);
    newerBufferedRecord = new BufferedRecord<>(RECORD_KEY, ORDERING_VALUE, newRecord, 1, null);
    finalResult = merger.finalMerge(olderBufferedRecord, newerBufferedRecord);
    assertFalse(finalResult.isDelete());
    if (updateMode == null) {
      assertEquals(newRecord, finalResult.getRecord());
    } else if (updateMode == PartialUpdateMode.IGNORE_DEFAULTS) {
      assertEquals(20, finalResult.getRecord().getInt(2));
      assertEquals(500, finalResult.getRecord().getLong(4));
    } else if (updateMode == PartialUpdateMode.FILL_UNAVAILABLE) {
      assertEquals("Older City", finalResult.getRecord().getString(3));
    }
  }
```

**`runDeltaDeleteMerge`**

```java
  private void runDeltaDeleteMerge(RecordMergeMode mergeMode, PartialUpdateMode updateMode) throws IOException {
    BufferedRecordMerger<InternalRow> merger = createMerger(readerContext, mergeMode, Option.ofNullable(updateMode));
    // Create records with all columns.
    InternalRow oldRecord = createFullRecord("old_id", "Old Name", 25, "Old City", 1000L);
    InternalRow newRecord = createFullRecord("new_id", "New Name", 0, IGNORE_MARKERS_VALUE, 0L);

    // CASE 1: New record has lower ordering value.
    BufferedRecord<InternalRow> oldBufferedRecord =
        new BufferedRecord<>(RECORD_KEY, ORDERING_VALUE, oldRecord, 1, null);
    DeleteRecord deleteRecord = DeleteRecord.create(RECORD_KEY, "anyPath", ORDERING_VALUE - 1);
    Option<DeleteRecord> deltaResult = merger.deltaMerge(deleteRecord, oldBufferedRecord);
    if (mergeMode == COMMIT_TIME_ORDERING) {
      assertTrue(deltaResult.isPresent());
      assertEquals(deleteRecord, deltaResult.get());
    } else {
      assertTrue(deltaResult.isEmpty());
    }

    // CASE 2: New record has higher ordering value.
    deleteRecord = DeleteRecord.create(RECORD_KEY, "anyPath", ORDERING_VALUE + 1);
    deltaResult = merger.deltaMerge(deleteRecord, oldBufferedRecord);
    assertTrue(deltaResult.isPresent());
    assertEquals(deleteRecord, deltaResult.get());

    // CASE 3: New record and old record have the same ordering value.
    deleteRecord = DeleteRecord.create(RECORD_KEY, "anyPath", ORDERING_VALUE);
    deltaResult = merger.deltaMerge(deleteRecord, oldBufferedRecord);
    assertTrue(deltaResult.isPresent());
    assertEquals(deleteRecord, deltaResult.get());
  }
```

**`createMerger`**

```java
  private BufferedRecordMerger<InternalRow> createMerger(HoodieReaderContext<InternalRow> readerContext,
                                                         RecordMergeMode mergeMode,
                                                         Option<PartialUpdateMode> partialUpdateModeOpt) {
    return BufferedRecordMergerFactory.create(
        readerContext,
        mergeMode,
        false,
        mergeMode == EVENT_TIME_ORDERING
            ? Option.of(new DefaultSparkRecordMerger())
            : Option.of(new OverwriteWithLatestSparkRecordMerger()),
        Option.empty(), // payloadClass
        READER_SCHEMA, // readerSchema
        props, // props
        partialUpdateModeOpt
    );
  }
```

**`createFullRecord`**

```java
  private static InternalRow createFullRecord(
      String id, String name, int age, String city, long timestamp) {
    return new GenericInternalRow(new Object[]{
        UTF8String.fromString(id),
        UTF8String.fromString(name),
        age,
        UTF8String.fromString(city),
        timestamp
    });
  }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-079  ·  MethodSource

**项目** `Commons-Net`  **文件** `commons-net/src/test/java/org/apache/commons/net/ftp/ListingFunctionalTest.java`  **测试** `testInitiateListParsingWithPathAndAutodetection`

### Test method

```java
@ParameterizedTest(name = "hostname={0}")
    @MethodSource("testCases")
    public void testInitiateListParsingWithPathAndAutodetection(final TestCase testCase) throws IOException {
        client = createFTPClient(testCase.hostName);
        final FTPListParseEngine engine = client.initiateListParsing(testCase.validPath);
        final List<FTPFile> files = Arrays.asList(engine.getNext(25));
        assertTrue(findByName(files, testCase.validFilename), files.toString());
    }
```

### Parameter provider — 同文件内的 `testCases`

```java
    private static Stream<TestCase> testCases() {
        final String[][] testData = { { "ftp.ibiblio.org", "unix", "vms", "HA!", "javaio.jar", "pub/languages/java/javafaq", "/pub/languages/java/javafaq", },
                { "apache.cs.utah.edu", "unix", "vms", "HA!", "HEADER.html", "apache.org", "/apache.org", },
//                { // not available
//                    "ftp.wacom.com", "windows", "VMS", "HA!",
//                    "wacom97.zip", "pub\\drivers"
//                },
                { "ftp.decuslib.com", "vms", "windows", // VMS OpenVMS V8.3
                        "[.HA!]", "FREEWARE_SUBMISSION_INSTRUCTIONS.TXT;1", "[.FREEWAREV80.FREEWARE]", "DECUSLIB:[DECUS.FREEWAREV80.FREEWARE]" },
//                {  // VMS TCPware V5.7-2 does not return (RWED) permissions
//                    "ftp.process.com", "vms", "windows",
//                    "[.HA!]", "MESSAGE.;1",
//                    "[.VMS-FREEWARE.FREE-VMS]" //
//                },
        };
        return Arrays.stream(testData).map(TestCase::new);
    }
```

### Test-side helpers called by this test (3)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`createFTPClient`**

```java
    private FTPClient createFTPClient(final String hostName) {
        try {
            final FTPClient ftpClient = new FTPClient();
            ftpClient.addProtocolCommandListener(new PrintCommandListener(System.out));
            ftpClient.connect(hostName);
            ftpClient.login("anonymous", "anonymous");
            ftpClient.enterLocalPassiveMode();
            ftpClient.setAutodetectUTF8(true);
            ftpClient.opts("UTF-8", "NLST");
            return ftpClient;
        } catch (final SocketException e) {
            return fail("Could not connect to FTP", e);
        } catch (final IOException e) {
            return fail(e);
        }
    }
```

**`findByName`**

```java
    private boolean findByName(final List<?> fileList, final String string) {
        boolean found = false;
        final Iterator<?> iter = fileList.iterator();
        while (iter.hasNext() && !found) {
            final Object element = iter.next();
            if (element instanceof FTPFile) {
                final FTPFile file = (FTPFile) element;
                found = file.getName().equals(string);
            } else {
                final String fileName = (String) element;
                found = fileName.endsWith(string);
            }
        }
        return found;
    }
```

**`toString`**

```java
@Override
        public String toString() {
            return validParserKey + " @ " + hostName;
        }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-082  ·  MethodSource

**项目** `Thrift`  **文件** `thrift/lib/java/src/test/java/org/apache/thrift/test/voidmethexceptions/TestVoidMethExceptions.java`  **测试** `testAsyncClientMustReturnResultReturnVoidNoThrowsTApplicationException`

### Test method

```java
@ParameterizedTest
  @MethodSource("provideParameters")
  public void testAsyncClientMustReturnResultReturnVoidNoThrowsTApplicationException(
      TestParameters p) throws Throwable {
    try (AutoCloseable ignored = p.start()) {
      p.checkAsyncClient(
          "returnVoidNoThrowsTApplicationException",
          "sent msg",
          false,
          null,
          null,
          null,
          TAppService01.AsyncClient::returnVoidNoThrowsTApplicationException);
    }
  }
```

### Parameter provider — 同文件内的 `provideParameters`

```java
  private static Stream<TestParameters> provideParameters() throws Exception {
    return Stream.<TestParameters>builder()
        .add(new TestParameters(ServerImplementationType.SYNC_SERVER))
        .add(new TestParameters(ServerImplementationType.ASYNC_SERVER))
        .build();
  }
```

### Test-side helpers called by this test (5)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`start`**

```java
    public AutoCloseable start() throws Exception {
      serverThread.start();
      futureServerStarted.get(TIMEOUT_MILLIS, TimeUnit.MILLISECONDS);
      return () -> {
        serverImplementationType.service.setCancelled(true);
        server.stop();
        serverThread.join(TIMEOUT_MILLIS);
      };
    }
```

**`checkAsyncClient`**

```java
    private <T> void checkAsyncClient(
        String desc,
        String msg,
        boolean throwException,
        T expectedResult,
        Class<? extends Exception> expectedExceptionClass,
        String expectedExceptionMsg,
        AsyncCall<TAppService01.AsyncClient, String, Boolean, AsyncMethodCallback<T>> call)
        throws Throwable {
      if (log.isInfoEnabled()) {
        log.info(
            "start test checkAsyncClient::"
                + desc
                + ", throwException: "
                + throwException
                + ", serverImplementationType: "
                + serverImplementationType);
      }
      assertNotEquals(serverPort, -1);
      try (TNonblockingSocket clientTransportAsync =
          new TNonblockingSocket("localhost", serverPort, TIMEOUT_MILLIS)) {
        TAsyncClientManager asyncClientManager = new TAsyncClientManager();
        try {
          TAppService01.AsyncClient asyncClient =
              new TAppService01.AsyncClient(
                  new TBinaryProtocol.Factory(), asyncClientManager, clientTransportAsync);
          asyncClient.setTimeout(TIMEOUT_MILLIS);

          CompletableFuture<T> futureResult = new CompletableFuture<>();

          call.apply(
              asyncClient,
              msg,
              throwException,
              new AsyncMethodCallback<T>() {

                @Override
                public void onError(Exception exception) {
                  futureResult.completeExceptionally(exception);
                }

                @Override
                public void onComplete(T response) {
                  futureResult.complete(response);
                }
              });
          if (throwException && expectedExceptionClass != null) {
            Exception ex =
                assertThrows(
                    expectedExceptionClass,
                    () -> {
                      try {
                        futureResult.get(TIMEOUT_MILLIS, TimeUnit.MILLISECONDS);
                      } catch (ExecutionException x) {
                        throw x.getCause();
                      }
                    });
            assertEquals(expectedExceptionClass, ex.getClass());
            if (expectedExceptionMsg != null) {
              assertEquals(expectedExceptionMsg, ex.getMessage());
            }
          } else {
            T result;
            try {
              result = futureResult.get(TIMEOUT_MILLIS, TimeUnit.MILLISECONDS);
            } catch (ExecutionException x) {
              throw x.getCause();
            }
            assertEquals(expectedResult, result);
          }
    // … 省略 5 行
```

**`apply`**

```java
    R apply(T t, U u, V v) throws Exception;
```

**`onError`**

```java
@Override
                public void onError(Exception exception) {
                  futureResult.completeExceptionally(exception);
                }
```

**`onComplete`**

```java
@Override
                public void onComplete(T response) {
                  futureResult.complete(response);
                }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-085  ·  MethodSource

**项目** `Thrift`  **文件** `thrift/lib/java/src/test/java/org/apache/thrift/test/voidmethexceptions/TestVoidMethExceptions.java`  **测试** `testAsyncClientMustReturnResultReturnVoidNoThrowsRuntimeException`

### Test method

```java
@ParameterizedTest
  @MethodSource("provideParameters")
  public void testAsyncClientMustReturnResultReturnVoidNoThrowsRuntimeException(TestParameters p)
      throws Throwable {
    try (AutoCloseable ignored = p.start()) {
      p.checkAsyncClient(
          "returnVoidNoThrowsRuntimeException",
          "sent msg",
          false,
          null,
          null,
          null,
          TAppService01.AsyncClient::returnVoidNoThrowsRuntimeException);
    }
  }
```

### Parameter provider — 同文件内的 `provideParameters`

```java
  private static Stream<TestParameters> provideParameters() throws Exception {
    return Stream.<TestParameters>builder()
        .add(new TestParameters(ServerImplementationType.SYNC_SERVER))
        .add(new TestParameters(ServerImplementationType.ASYNC_SERVER))
        .build();
  }
```

### Test-side helpers called by this test (5)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`start`**

```java
    public AutoCloseable start() throws Exception {
      serverThread.start();
      futureServerStarted.get(TIMEOUT_MILLIS, TimeUnit.MILLISECONDS);
      return () -> {
        serverImplementationType.service.setCancelled(true);
        server.stop();
        serverThread.join(TIMEOUT_MILLIS);
      };
    }
```

**`checkAsyncClient`**

```java
    private <T> void checkAsyncClient(
        String desc,
        String msg,
        boolean throwException,
        T expectedResult,
        Class<? extends Exception> expectedExceptionClass,
        String expectedExceptionMsg,
        AsyncCall<TAppService01.AsyncClient, String, Boolean, AsyncMethodCallback<T>> call)
        throws Throwable {
      if (log.isInfoEnabled()) {
        log.info(
            "start test checkAsyncClient::"
                + desc
                + ", throwException: "
                + throwException
                + ", serverImplementationType: "
                + serverImplementationType);
      }
      assertNotEquals(serverPort, -1);
      try (TNonblockingSocket clientTransportAsync =
          new TNonblockingSocket("localhost", serverPort, TIMEOUT_MILLIS)) {
        TAsyncClientManager asyncClientManager = new TAsyncClientManager();
        try {
          TAppService01.AsyncClient asyncClient =
              new TAppService01.AsyncClient(
                  new TBinaryProtocol.Factory(), asyncClientManager, clientTransportAsync);
          asyncClient.setTimeout(TIMEOUT_MILLIS);

          CompletableFuture<T> futureResult = new CompletableFuture<>();

          call.apply(
              asyncClient,
              msg,
              throwException,
              new AsyncMethodCallback<T>() {

                @Override
                public void onError(Exception exception) {
                  futureResult.completeExceptionally(exception);
                }

                @Override
                public void onComplete(T response) {
                  futureResult.complete(response);
                }
              });
          if (throwException && expectedExceptionClass != null) {
            Exception ex =
                assertThrows(
                    expectedExceptionClass,
                    () -> {
                      try {
                        futureResult.get(TIMEOUT_MILLIS, TimeUnit.MILLISECONDS);
                      } catch (ExecutionException x) {
                        throw x.getCause();
                      }
                    });
            assertEquals(expectedExceptionClass, ex.getClass());
            if (expectedExceptionMsg != null) {
              assertEquals(expectedExceptionMsg, ex.getMessage());
            }
          } else {
            T result;
            try {
              result = futureResult.get(TIMEOUT_MILLIS, TimeUnit.MILLISECONDS);
            } catch (ExecutionException x) {
              throw x.getCause();
            }
            assertEquals(expectedResult, result);
          }
    // … 省略 5 行
```

**`apply`**

```java
    R apply(T t, U u, V v) throws Exception;
```

**`onError`**

```java
@Override
                public void onError(Exception exception) {
                  futureResult.completeExceptionally(exception);
                }
```

**`onComplete`**

```java
@Override
                public void onComplete(T response) {
                  futureResult.complete(response);
                }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-088  ·  MethodSource

**项目** `ozone`  **文件** `ozone/hadoop-hdds/container-service/src/test/java/org/apache/hadoop/ozone/container/keyvalue/TestKeyValueBlockIterator.java`  **测试** `testKeyValueBlockIteratorWithHasNext`

### Test method

```java
@ParameterizedTest
  @MethodSource("provideTestData")
  public void testKeyValueBlockIteratorWithHasNext(
      ContainerTestVersionInfo versionInfo, String keySeparator)
      throws Exception {
    initTest(versionInfo, keySeparator);
    List<Long> blockIDs = createContainerWithBlocks(CONTAINER_ID, 2);
    try (BlockIterator<BlockData> blockIter = db.getStore().getBlockIterator(CONTAINER_ID)) {

      // Even calling multiple times hasNext() should not move entry forward.
      assertTrue(blockIter.hasNext());
      assertTrue(blockIter.hasNext());
      assertTrue(blockIter.hasNext());
      assertTrue(blockIter.hasNext());
      assertTrue(blockIter.hasNext());
      assertEquals((long) blockIDs.get(0), blockIter.nextBlock().getLocalID());

      assertTrue(blockIter.hasNext());
      assertTrue(blockIter.hasNext());
      assertTrue(blockIter.hasNext());
      assertTrue(blockIter.hasNext());
      assertTrue(blockIter.hasNext());
      assertEquals((long) blockIDs.get(1), blockIter.nextBlock().getLocalID());

      blockIter.seekToFirst();
      assertEquals((long) blockIDs.get(0), blockIter.nextBlock().getLocalID());
      assertEquals((long) blockIDs.get(1), blockIter.nextBlock().getLocalID());

      NoSuchElementException exception = assertThrows(NoSuchElementException.class, blockIter::nextBlock);
      assertThat(exception).hasMessage("Block Iterator reached end for ContainerID " + CONTAINER_ID);
    }
  }
```

### Parameter provider — 同文件内的 `provideTestData`

```java
  private static List<Arguments> provideTestData() {
    List<Arguments> listA =
        ContainerTestVersionInfo.getLayoutList().stream().map(
                each -> Arguments.of(each, ""))
            .collect(toList());
    List<Arguments> listB =
        ContainerTestVersionInfo.getLayoutList().stream().map(
                each -> Arguments.of(each, new DatanodeConfiguration()
                    .getContainerSchemaV3KeySeparator()))
            .collect(toList());

    listB.addAll(listA);
    return listB;
  }
```

### Test-side helpers called by this test (3)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`initTest`**

```java
  private void initTest(ContainerTestVersionInfo versionInfo,
      String keySeparator) throws Exception {
    this.layout = versionInfo.getLayout();
    String schemaVersion = versionInfo.getSchemaVersion();
    this.conf = new OzoneConfiguration();
    ContainerTestVersionInfo.setTestSchemaVersion(schemaVersion, conf);
    DatanodeConfiguration dc = conf.getObject(DatanodeConfiguration.class);
    dc.setContainerSchemaV3KeySeparator(keySeparator);
    conf.setFromObject(dc);
    setup();
  }
```

**`createContainerWithBlocks`**

```java
  private List<Long> createContainerWithBlocks(long containerId,
            int unprefixedBlocks) throws Exception {
    return createContainerWithBlocks(containerId, unprefixedBlocks, 0).get("");
  }
```

**`setup`**

```java
  public void setup() throws Exception {
    conf.set(HDDS_DATANODE_DIR_KEY, testRoot.getAbsolutePath());
    conf.set(OzoneConfigKeys.OZONE_METADATA_DIRS, testRoot.getAbsolutePath());
    volumeSet = new MutableVolumeSet(datanodeID, clusterID, conf, null,
        StorageVolume.VolumeType.DATA_VOLUME, null);
    createDbInstancesForTestIfNeeded(volumeSet, clusterID, clusterID, conf);

    containerData = new KeyValueContainerData(105L,
        layout,
        (long) StorageUnit.GB.toBytes(1), UUID.randomUUID().toString(),
        UUID.randomUUID().toString());
    // Init the container.
    KeyValueContainer container = new KeyValueContainer(containerData, conf);
    container.create(volumeSet, new RoundRobinVolumeChoosingPolicy(),
        clusterID);
    db = BlockUtils.getDB(containerData, conf);
  }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-091  ·  CsvSource

**项目** `Hudi`  **文件** `hudi/hudi-hadoop-common/src/test/java/org/apache/hudi/io/hadoop/TestHoodieHFileReaderWriter.java`  **测试** `testHoodieHFileCompatibility`

### Test method

```java
@ParameterizedTest
  @CsvSource(value = {
      "/hfile/hudi_0_9_hbase_1_2_3,true", "/hfile/hudi_0_9_hbase_1_2_3,false",
      "/hfile/hudi_0_10_hbase_1_2_3,true", "/hfile/hudi_0_10_hbase_1_2_3,false",
      "/hfile/hudi_0_11_hbase_2_4_9,true", "/hfile/hudi_0_11_hbase_2_4_9,false"})
  public void testHoodieHFileCompatibility(String hfilePrefix, boolean useBloomFilter) throws IOException {
    // This fixture is generated from TestHoodieReaderWriterBase#testWriteReadPrimitiveRecord()
    // using different Hudi releases
    String simpleHFile = hfilePrefix + SIMPLE_SCHEMA_HFILE_SUFFIX;
    // This fixture is generated from TestHoodieReaderWriterBase#testWriteReadComplexRecord()
    // using different Hudi releases
    String complexHFile = hfilePrefix + COMPLEX_SCHEMA_HFILE_SUFFIX;
    // This fixture is generated from TestBootstrapIndex#testBootstrapIndex()
    // using different Hudi releases.  The file is copied from .hoodie/.aux/.bootstrap/.partitions/
    String bootstrapIndexFile = hfilePrefix + BOOTSTRAP_INDEX_HFILE_SUFFIX;

    FileSystem fs = HadoopFSUtils.getFs(getFilePath().toString(), new Configuration());
    byte[] content = readHFileFromResources(simpleHFile);
    verifyHFileReader(
        content, hfilePrefix, true, useBloomFilter, NUM_RECORDS_FIXTURE);

    HoodieStorage storage = HoodieTestUtils.getStorage(getFilePath());
    try (HoodieAvroHFileReaderImplBase hfileReader = createHFileReader(storage, content, useBloomFilter)) {
      Schema avroSchema =
          getSchemaFromResource(TestHoodieReaderWriterBase.class, "/exampleSchema.avsc");
      assertEquals(NUM_RECORDS_FIXTURE, hfileReader.getTotalRecords());
      verifySimpleRecords(hfileReader.getRecordIterator(avroSchema));
    }

    content = readHFileFromResources(complexHFile);
    verifyHFileReader(
        content, hfilePrefix, true, useBloomFilter, NUM_RECORDS_FIXTURE);
    try (HoodieAvroHFileReaderImplBase hfileReader = createHFileReader(storage, content, useBloomFilter)) {
      Schema avroSchema =
          getSchemaFromResource(TestHoodieReaderWriterBase.class, "/exampleSchemaWithUDT.avsc");
      assertEquals(NUM_RECORDS_FIXTURE, hfileReader.getTotalRecords());
      verifySimpleRecords(hfileReader.getRecordIterator(avroSchema));
    }

    content = readHFileFromResources(bootstrapIndexFile);
    verifyHFileReader(
        content, hfilePrefix, false, useBloomFilter, 4);
  }
```

### Test-side helpers called by this test (3)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`getFilePath`**

```java
@Override
  protected StoragePath getFilePath() {
    return new StoragePath(tempDir.toString() + "/f1_1-0-1_000.hfile");
  }
```

**`verifyHFileReader`**

```java
  protected void verifyHFileReader(byte[] content,
                                   String hfileName,
                                   boolean mayUseDefaultComparator,
                                   boolean useBloomFilter,
                                   int count) throws IOException {
    try (HoodieAvroHFileReaderImplBase hfileReader =
             createHFileReader(HoodieTestUtils.getStorage(hfileName), content, useBloomFilter)) {
      assertEquals(count, hfileReader.getTotalRecords());
    }
  }
```

**`createHFileReader`**

```java
  protected HoodieAvroHFileReaderImplBase createHFileReader(HoodieStorage storage,
                                                            byte[] content,
                                                            boolean useBloomFilter) throws IOException {
    HFileReaderFactory readerFactory = HFileReaderFactory.builder()
        .withStorage(storage).withProps(DEFAULT_PROPS)
        .withContent(content).build();
    return HoodieNativeAvroHFileReader.builder()
        .readerFactory(readerFactory).path(getFilePath()).useBloomFilter(useBloomFilter).build();
  }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-094  ·  ValueSource

**项目** `Commons-Codec`  **文件** `commons-codec/src/test/java/org/apache/commons/codec/binary/Base64Test.java`  **测试** `testRfc4648Section10DecodeEncode`

### Test method

```java
@ParameterizedTest
    // @formatter:off
    @ValueSource(strings = {
            "",
            "Zg==",
            "Zm8=",
            "Zm9v",
            "Zm9vYg==",
            "Zm9vYmE=",
            "Zm9vYmFy"
    })
    // @formatter:on
    void testRfc4648Section10DecodeEncode(final String input) {
        testDecodeEncode(input);
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`testDecodeEncode`**

```java
    private void testDecodeEncode(final String encodedText) {
        final String decodedText = StringUtils.newStringUsAscii(Base64.decodeBase64(encodedText));
        final String encodedText2 = Base64.encodeBase64String(StringUtils.getBytesUtf8(decodedText));
        assertEquals(encodedText, encodedText2);
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-097  ·  MethodSource

**项目** `Commons-RNG`  **文件** `commons-rng/commons-rng-core/src/test/java/org/apache/commons/rng/core/JumpableProvidersParametricTest.java`  **测试** `testLongJumpReturnsACopy`

### Test method

```java
@ParameterizedTest
    @MethodSource("getJumpableProviders")
    void testLongJumpReturnsACopy(JumpableUniformRandomProvider generator) {
        assertJumpReturnsACopy(getLongJumpFunction(generator), generator);
    }
```

### Parameter provider — 同文件内的 `getJumpableProviders`

```java
    private static Iterable<JumpableUniformRandomProvider> getJumpableProviders() {
        return ProvidersList.listJumpable();
    }
```

### Test-side helpers called by this test (2)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`assertJumpReturnsACopy`**

```java
    private static void assertJumpReturnsACopy(TestJumpFunction jumpFunction,
                                               JumpableUniformRandomProvider generator) {
        final UniformRandomProvider copy = jumpFunction.jump();
        Assertions.assertNotSame(generator, copy, "The copy instance should be a different object");
        Assertions.assertEquals(generator.getClass(), copy.getClass(), "The copy instance should be the same class");
    }
```

**`getLongJumpFunction`**

```java
    private static TestJumpFunction getLongJumpFunction(JumpableUniformRandomProvider generator) {
        Assumptions.assumeTrue(generator instanceof LongJumpableUniformRandomProvider, "No long jump function");
        final LongJumpableUniformRandomProvider rng2 = (LongJumpableUniformRandomProvider) generator;
        return rng2::jump;
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-100  ·  EnumSource

**项目** `Commons-Imaging`  **文件** `commons-imaging/src/test/java/org/apache/commons/imaging/ImageFormatsTest.java`  **测试** `testDefaultExtension`

### Test method

```java
@ParameterizedTest
    @EnumSource(ImageFormats.class)
    void testDefaultExtension(final ImageFormats imageFormats) {
        assertNotNull(imageFormats.getDefaultExtension());
        assertFalse(imageFormats.getDefaultExtension().isEmpty());
    }
```

### Enum declaration — `ImageFormats` (commons-imaging/src/main/java/org/apache/commons/imaging/ImageFormats.java)

```java
public enum ImageFormats implements ImageFormat {

    // @formatter:off
    UNKNOWN("bin"),
    BMP("bmp", "dib"),
    DCX("dcx"),
    GIF("gif"),
    ICNS("icns"),
    ICO("ico"),
    JBIG2("jbig2"),
    JPEG("jpg", "jpeg"),
    PAM("pam"),
    PSD("psd"),
    PBM("pbm"),
    PGM("pgm"),
    PNM("pnm"),
    PPM("ppm"),
    PCX("pcx", "pcc"),
    PNG("png"),
    RGBE("hdr", "pic"),
    TGA("tga"),
    TIFF("tif", "tiff"),
    WBMP("wbmp"),
    WEBP("webp"),
    XBM("xbm"),
    XPM("xpm");
    // @formatter:on

    private final String[] extensions;

    ImageFormats(final String... extensions) {
        this.extensions = Objects.requireNonNull(extensions);
    }

    @Override
    public String getDefaultExtension() {
        return extensions[0];
    }

    @Override
    public String[] getExtensions() {
        return this.extensions.clone();
    }

    @Override
    public String getName() {
        return name();
    }
}
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-103  ·  CsvSource

**项目** `Qpid`  **文件** `qpid-broker-j/broker-plugins/access-control/src/test/java/org/apache/qpid/server/security/access/config/RuleTest.java`  **测试** `isOwner`

### Test method

```java
@ParameterizedTest
    @CsvSource(
    {
            "owner,true,true", "Owner,true,true", "OWNER,true,true",
            "any,false,false", "Any,false,false", "ANY,false,false"
    })
    void isOwner(final String identity, final boolean isForOwner, final boolean isForOwnerOrAll)
    {
        final Rule rule = new Rule.Builder().withIdentity(identity).build();
        assertEquals(isForOwner, rule.isForOwner());
        assertEquals(isForOwnerOrAll, rule.isForOwnerOrAll());
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-106  ·  ValueSource

**项目** `Hive`  **文件** `hive/iceberg/iceberg-catalog/src/test/java/org/apache/iceberg/hive/HiveCreateReplaceTableTest.java`  **测试** `testReplaceTableTxn`

### Test method

```java
@ParameterizedTest
  @ValueSource(ints = {1, 2})
  public void testReplaceTableTxn(int formatVersion) {
    catalog.createTable(
        TABLE_IDENTIFIER,
        SCHEMA,
        SPEC,
        tableLocation,
        ImmutableMap.of(TableProperties.FORMAT_VERSION, String.valueOf(formatVersion)));
    assertThat(catalog.tableExists(TABLE_IDENTIFIER)).as("Table should exist").isTrue();

    Transaction txn = catalog.newReplaceTableTransaction(TABLE_IDENTIFIER, SCHEMA, false);
    txn.commitTransaction();

    Table table = catalog.loadTable(TABLE_IDENTIFIER);
    if (formatVersion == 1) {
      PartitionSpec v1Expected =
          PartitionSpec.builderFor(table.schema()).alwaysNull("id", "id").withSpecId(1).build();
      assertThat(table.spec())
          .as("Table should have a spec with one void field")
          .isEqualTo(v1Expected);
    } else {
      assertThat(table.spec().isUnpartitioned()).as("Table spec must be unpartitioned").isTrue();
    }
  }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-109  ·  MethodSource

**项目** `Thrift`  **文件** `thrift/lib/java/src/test/java/org/apache/thrift/test/voidmethexceptions/TestVoidMethExceptions.java`  **测试** `testSyncClientMustReturnResultReturnString`

### Test method

```java
@ParameterizedTest
  @MethodSource("provideParameters")
  public void testSyncClientMustReturnResultReturnString(TestParameters p) throws Exception {
    try (AutoCloseable ignored = p.start()) {
      p.checkSyncClient(
          "returnString",
          "sent msg",
          false,
          "sent msg",
          null,
          null,
          TAppService01.Iface::returnString);
    }
  }
```

### Parameter provider — 同文件内的 `provideParameters`

```java
  private static Stream<TestParameters> provideParameters() throws Exception {
    return Stream.<TestParameters>builder()
        .add(new TestParameters(ServerImplementationType.SYNC_SERVER))
        .add(new TestParameters(ServerImplementationType.ASYNC_SERVER))
        .build();
  }
```

### Test-side helpers called by this test (3)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`start`**

```java
    public AutoCloseable start() throws Exception {
      serverThread.start();
      futureServerStarted.get(TIMEOUT_MILLIS, TimeUnit.MILLISECONDS);
      return () -> {
        serverImplementationType.service.setCancelled(true);
        server.stop();
        serverThread.join(TIMEOUT_MILLIS);
      };
    }
```

**`checkSyncClient`**

```java
    private void checkSyncClient(
        String desc,
        String msg,
        boolean throwException,
        String expectedResult,
        Class<? extends Exception> expectedExceptionClass,
        String expectedExceptionMsg,
        SyncCall<TAppService01.Iface, String, Boolean, String> call)
        throws Exception {
      if (log.isInfoEnabled()) {
        log.info(
            "start test checkSyncClient::"
                + desc
                + ", throwException: "
                + throwException
                + ", serverImplementationType: "
                + serverImplementationType);
      }
      assertNotEquals(-1, serverPort);
      try (TTransport clientTransport =
          new TFramedTransport(
              new TSocket(new TConfiguration(), "localhost", serverPort, TIMEOUT_MILLIS))) {
        clientTransport.open();
        TAppService01.Iface client = new TAppService01.Client(new TBinaryProtocol(clientTransport));
        if (throwException && expectedExceptionClass != null) {
          Exception ex =
              assertThrows(
                  expectedExceptionClass,
                  () -> {
                    call.apply(client, msg, throwException);
                  });
          assertEquals(expectedExceptionClass, ex.getClass());
          if (expectedExceptionMsg != null) {
            assertEquals(expectedExceptionMsg, ex.getMessage());
          }
        } else {
          // expected
          String result = call.apply(client, msg, throwException);
          assertEquals(expectedResult, result);
        }
      }
    }
```

**`apply`**

```java
    R apply(T t, U u, V v) throws Exception;
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-112  ·  ValueSource

**项目** `NiFi`  **文件** `nifi/nifi-commons/nifi-record-path/src/test/java/org/apache/nifi/record/path/TestRecordFieldRemover.java`  **测试** `testNotIsPathRemovalRequiresSchemaModification`

### Test method

```java
@ParameterizedTest
    @ValueSource(strings = {"[1]", "[-1]", "/street[ 1, 2 ]", "//[ -1,-2,3]", //
            "['one']", "[ 'one', 'two' ]", "/street[ 'one, two' ]", "//['one' , 'two']"})
    void testNotIsPathRemovalRequiresSchemaModification(final String input) {
        assertFalse(new RecordFieldRemover.RecordPathRemovalProperties("/addresses" + input)
                .isRemovingFieldsNotJustElementsFromWithinCollection());
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-115  ·  MethodSource

**项目** `Commons-CLI`  **文件** `commons-cli/src/test/java/org/apache/commons/cli/ValueTest.java`  **测试** `testLongOptionalNArgValuesWithOption`

### Test method

```java
@ParameterizedTest
    @MethodSource("parsers")
    void testLongOptionalNArgValuesWithOption(final CommandLineParser parser) throws Exception {
        final CommandLine cmd = parser.parse(opts, new String[] { "--hide", "house", "hair", "head" });
        assertNull(cmd.getOptionValues(NULL_OPTION));
        assertNull(cmd.getOptionValues(NULL_STRING));
        assertTrue(cmd.hasOption(opts.getOption("hide")));
        assertEquals("house", cmd.getOptionValue(opts.getOption("hide")));
        assertEquals("house", cmd.getOptionValues(opts.getOption("hide"))[0]);
        assertEquals("hair", cmd.getOptionValues(opts.getOption("hide"))[1]);
        assertEquals(cmd.getArgs().length, 1);
        assertEquals("head", cmd.getArgs()[0]);
    }
```

### Parameter provider — 同文件内的 `parsers`

```java
    protected static Stream<CommandLineParser> parsers() {
        return Stream.of(new DefaultParser(), new PosixParser());
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-118  ·  ValueSource

**项目** `XMLBeans`  **文件** `xmlbeans/src/test/java/xmlcursor/xquery/detailed/StoreTestsXqrl.java`  **测试** `doSaveTest`

### Test method

```java
@ParameterizedTest
    @ValueSource(strings = {
        "<foo xmlns=\"foo.com\"><bar>1</bar></foo>",
        "<foo><!--comment--><?target foo?></foo>",
        "<foo>a<bar>b</bar>c<bar>d</bar>e</foo>",
        "<foo xmlns:x=\"y\"><bar xmlns:x=\"z\"/></foo>",
        "<foo x=\"y\" p=\"r\"/>",
        "<bar>xxxxsssssssssssssss</bar>"
    })
    void doSaveTest(String xml) throws Exception {
        if (xml.startsWith("<bar>")) xml = xml.replace("s", "<foo>aaa</foo>bbb");

        try (XmlCursor c = XmlObject.Factory.parse(xml).newCursor();
             XmlCursor cq = c.execQuery(".")) {
            String s = cq.xmlText();
            assertEquals(s, xml);
        }
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-121  ·  EnumSource

**项目** `Commons-Numbers`  **文件** `commons-numbers/commons-numbers-gamma/src/test/java/org/apache/commons/numbers/gamma/BoostBetaTest.java`  **测试** `testIBeta`

### Test method

```java
@ParameterizedTest
    @EnumSource(value = TriTestCase.class, mode = Mode.MATCH_ANY,
                names = {"IBETA_[SML].*", "IBETAC_[SML].*", "RBETA.*"})
    void testIBeta(TriTestCase tc) {
        assertFunction(tc);
    }
```

### Enum declaration — `TriTestCase` (commons-numbers/commons-numbers-gamma/src/test/java/org/apache/commons/numbers/gamma/BoostBetaTest.java)

```java
    private enum TriTestCase implements TestError {
        /** ibeta derivative Boost small integer data. */
        IBETA_DERIV_SMALL_INT(BoostBeta::ibetaDerivative, "ibeta_derivative_small_int_data.csv", 60, 13),
        /** ibeta derivative Boost small data. */
        IBETA_DERIV_SMALL(BoostBeta::ibetaDerivative, "ibeta_derivative_small_data.csv", 22, 4),
        /** ibeta derivative Boost medium data. */
        IBETA_DERIV_MED(BoostBeta::ibetaDerivative, "ibeta_derivative_med_data.csv", 150, 33),
        /** ibeta derivative Boost large and diverse data. */
        IBETA_DERIV_LARGE(BoostBeta::ibetaDerivative, "ibeta_derivative_large_data.csv", 3900, 260),
        // LogGamma based implementation is worse
        /** ibeta derivative Boost small integer data. */
        IBETA_DERIV1_SMALL_INT(BoostBetaTest::ibetaDerivative1, "ibeta_derivative_small_int_data.csv", 220, 55),
        /** ibeta derivative Boost small data. */
        IBETA_DERIV1_SMALL(BoostBetaTest::ibetaDerivative1, "ibeta_derivative_small_data.csv", 75, 10.5),
        /** ibeta derivative Boost medium data. */
        IBETA_DERIV1_MED(BoostBetaTest::ibetaDerivative1, "ibeta_derivative_med_data.csv", 1500, 300),
        /** ibeta derivative Boost large and diverse data. */
        IBETA_DERIV1_LARGE(BoostBetaTest::ibetaDerivative1, "ibeta_derivative_large_data.csv", 9e7, 250000),
        // LogBeta based implementation is worse
        /** ibeta derivative Boost small integer data. */
        IBETA_DERIV2_SMALL_INT(BoostBetaTest::ibetaDerivative2, "ibeta_derivative_small_int_data.csv", 180, 31),
        /** ibeta derivative Boost small data. */
        IBETA_DERIV2_SMALL(BoostBetaTest::ibetaDerivative2, "ibeta_derivative_small_data.csv", 75, 8.5),
        /** ibeta derivative Boost medium data. */
        IBETA_DERIV2_MED(BoostBetaTest::ibetaDerivative2, "ibeta_derivative_med_data.csv", 500, 85),
        /** ibeta derivative Boost large and diverse data. */
        IBETA_DERIV2_LARGE(BoostBetaTest::ibetaDerivative2, "ibeta_derivative_large_data.csv", 28000, 1200),

        /** ibeta Boost small integer data. */
        IBETA_SMALL_INT(BoostBeta::beta, "ibeta_small_int_data.csv", 48, 11),
        /** ibeta Boost small data. */
        IBETA_SMALL(BoostBeta::beta, "ibeta_small_data.csv", 17, 3.3),
        /** ibeta Boost medium data. */
        IBETA_MED(BoostBeta::beta, "ibeta_med_data.csv", 190, 20),
        /** ibeta Boost large and diverse data. */
        IBETA_LARGE(BoostBeta::beta, "ibeta_large_data.csv", 1300, 50),
        /** ibetac Boost small integer data. */
        IBETAC_SMALL_INT(BoostBeta::betac, "ibeta_small_int_data.csv", 4, 57, 11),
        /** ibetac Boost small data. */
        IBETAC_SMALL(BoostBeta::betac, "ibeta_small_data.csv", 4, 14, 3.2),
        /** ibetac Boost medium data. */
        IBETAC_MED(BoostBeta::betac, "ibeta_med_data.csv", 4, 130, 24),
        /** ibetac Boost large and diverse data. */
        IBETAC_LARGE(BoostBeta::betac, "ibeta_large_data.csv", 4, 7000, 220),
        /** regularised ibeta Boost small integer data. */
        RBETA_SMALL_INT(BoostBeta::ibeta, "ibeta_small_int_data.csv", 5, 7.5, 1.2),
        /** regularised ibeta Boost small data. */
        RBETA_SMALL(BoostBeta::ibeta, "ibeta_small_data.csv", 5, 14, 3.3),
        /** regularised ibeta Boost medium data. */
        RBETA_MED(BoostBeta::ibeta, "ibeta_med_data.csv", 5, 200, 28),
        /** regularised ibeta Boost large and diverse data. */
        RBETA_LARGE(BoostBeta::ibeta, "ibeta_large_data.csv", 5, 2400, 100),
        /** regularised ibetac Boost small integer data. */
        RBETAC_SMALL_INT(BoostBeta::ibetac, "ibeta_small_int_data.csv", 6, 8, 1.6),
        /** regularised ibetac Boost small data. */
        RBETAC_SMALL(BoostBeta::ibetac, "ibeta_small_data.csv", 6, 11, 2.75),
        /** regularised ibetac Boost medium data. */
        RBETAC_MED(BoostBeta::ibetac, "ibeta_med_data.csv", 6, 105, 23),
        /** regularised ibetac Boost large and diverse data. */
        RBETAC_LARGE(BoostBeta::ibetac, "ibeta_large_data.csv", 6, 4000, 180),

        // Classic continued fraction representation is:
        // - worse on small data
        // - comparable (or better) on medium data
        // - much worse on large data
        /** regularised ibeta Boost small data using the classic continued fraction evaluation. */
        RBETA1_SMALL(BoostBetaTest::ibeta, "ibeta_small_data.csv", 5, 45, 5),
        /** regularised ibeta Boost small data using the classic continued fraction evaluation. */
        RBETA1_MED(BoostBetaTest::ibeta, "ibeta_med_data.csv", 5, 200, 26),
        /** regularised ibeta Boost large and diverse data. */
        RBETA1_LARGE(BoostBetaTest::ibeta, "ibeta_large_data.csv", 5, 150000, 7500),
        /** regularised ibeta Boost small data using the classic continued fraction evaluation. */
        RBETAC1_SMALL(BoostBetaTest::ibetac, "ibeta_small_data.csv", 6, 35, 4.5),
        /** regularised ibeta Boost small data using the classic continued fraction evaluation. */
        RBETAC1_MED(BoostBetaTest::ibetac, "ibeta_med_data.csv", 6, 100, 22),
        /** regularised ibetac Boost large and diverse data. */
        RBETAC1_LARGE(BoostBetaTest::ibetac, "ibeta_large_data.csv", 6, 370000, 11000);

        /** The function. */
        private final DoubleTernaryOperator fun;

        /** The filename containing the test data. */
        private final String filename;

        /** The field containing the expected value. */
        private final int expected;

        /** The maximum allowed ulp. */
        private final double maxUlp;

        /** The maximum allowed RMS ulp. */
        private final double rmsUlp;

        /**
         * Instantiates a new test case.
         *
         * @param fun function to test
         * @param filename Filename of the test data
         * @param maxUlp maximum allowed ulp
         * @param rmsUlp maximum allowed RMS ulp
         */
        TriTestCase(DoubleTernaryOperator fun, String filename, double maxUlp, double rmsUlp) {
            this(fun, filename, 3, maxUlp, rmsUlp);
        }

        /**
         * Instantiates a new test case.
         *
         * @param fun function to test
         * @param filename Filename of the test data
         * @param expected Expected result field index
         * @param maxUlp maximum allowed ulp
         * @param rmsUlp maximum allowed RMS ulp
         */
        TriTestCase(DoubleTernaryOperator fun, String filename, int expected, double maxUlp, double rmsUlp) {
            this.fun = fun;
            this.filename = filename;
            this.expected = expected;
            this.maxUlp = maxUlp;
            this.rmsUlp = rmsUlp;
        }

        /**
         * @return function to test
         */
        DoubleTernaryOperator getFunction() {
            return fun;
        }

        /**
         * @return Filename of the test data
         */
        String getFilename() {
            return filename;
        }

        /**
         * @return Expected result field index
         */
        int getExpectedField() {
            return expected;
        }

        @Override
        public double getTolerance() {
            return maxUlp;
        }

        @Override
        public double getRmsTolerance() {
            return rmsUlp;
        }
    }
```

### Test-side helpers called by this test (6)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`assertFunction`**

```java
    private static void assertFunction(BiTestCase tc) {
        final TestUtils.ErrorStatistics stats = new TestUtils.ErrorStatistics();
        try (DataReader in = new DataReader(tc.getFilename())) {
            while (in.next()) {
                try {
                    final double x = in.getDouble(0);
                    final double y = in.getDouble(1);
                    final BigDecimal expected = in.getBigDecimal(tc.getExpectedField());
                    final double actual = tc.getFunction().applyAsDouble(x, y);
                    TestUtils.assertEquals(expected, actual, tc.getTolerance(), stats::add,
                        () -> tc + " x=" + x + ", y=" + y);
                } catch (final NumberFormatException ex) {
                    Assertions.fail("Failed to load data: " + Arrays.toString(in.getFields()), ex);
                }
            }
        } catch (final IOException ex) {
            Assertions.fail("Failed to load data: " + tc.getFilename(), ex);
        }

        assertRms(tc, stats);
    }
```

**`getFilename`**

```java
        String getFilename() {
            return filename;
        }
```

**`getExpectedField`**

```java
        int getExpectedField() {
            return expected;
        }
```

**`getFunction`**

```java
        DoubleBinaryOperator getFunction() {
            return fun;
        }
```

**`getTolerance`**

```java
@Override
        public double getTolerance() {
            return maxUlp;
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

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-124  ·  EnumSource

**项目** `NiFi`  **文件** `nifi/nifi-extension-bundles/nifi-kafka-bundle/nifi-kafka-3-integration/src/test/java/org/apache/nifi/kafka/processors/ConsumeKafkaRecordIT.java`  **测试** `testInvalidRecordInMiddle`

### Test method

```java
@ParameterizedTest
    @EnumSource(value = OutputStrategy.class)
    void testInvalidRecordInMiddle(final OutputStrategy outputStrategy) throws ExecutionException, InterruptedException {
        testSingleInvalidRecord("testInvalidRecordInMiddle", outputStrategy, VALID_RECORD_1_TEXT, INVALID_RECORD_TEXT, VALID_RECORD_2_TEXT);
    }
```

### Enum declaration — `OutputStrategy` (nifi/nifi-extension-bundles/nifi-aws-bundle/nifi-aws-processors/src/main/java/org/apache/nifi/processors/aws/kinesis/property/OutputStrategy.java)

```java
public enum OutputStrategy implements DescribedValue {
    USE_VALUE("Use Content as Value", "Write only the Kinesis Record value to the FlowFile record."),
    USE_WRAPPER("Use Wrapper", "Write the Kinesis Record value and metadata into the FlowFile record.");

    private final String displayName;
    private final String description;

    OutputStrategy(final String displayName, final String description) {
        this.displayName = displayName;
        this.description = description;
    }

    @Override
    public String getValue() {
        return name();
    }

    @Override
    public String getDisplayName() {
        return displayName;
    }

    @Override
    public String getDescription() {
        return description;
    }
}
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`testSingleInvalidRecord`**

```java
    private void testSingleInvalidRecord(final String topicPrefix, final OutputStrategy outputStrategy, final String... recordTexts) throws ExecutionException, InterruptedException {
        final String topicName = topicPrefix + outputStrategy.getValue();
        runner.setProperty(ConsumeKafka.TOPICS, topicName);
        runner.setProperty(ConsumeKafka.GROUP_ID, topicName);
        runner.setProperty(ConsumeKafka.PROCESSING_STRATEGY, ProcessingStrategy.RECORD.getValue());
        runner.setProperty(ConsumeKafka.OUTPUT_STRATEGY, outputStrategy.getValue());
        runner.setProperty(ConsumeKafka.AUTO_OFFSET_RESET, AutoOffsetReset.EARLIEST.getValue());

        for (final String text : recordTexts) {
            produceOne(topicName, 0, null, text, List.of());
        }

        runner.run(1, false, true);

        while (runner.getFlowFilesForRelationship(ConsumeKafka.SUCCESS).isEmpty()) {
            Thread.sleep(10L);
            runner.run(1, false, false);
        }

        runner.assertTransferCount(ConsumeKafka.SUCCESS, 1);
        runner.assertTransferCount(ConsumeKafka.PARSE_FAILURE, 1);

        assertEquals(String.valueOf(recordTexts.length - 1), runner.getFlowFilesForRelationship(ConsumeKafka.SUCCESS).getFirst().getAttribute("record.count"));
        runner.getFlowFilesForRelationship(ConsumeKafka.PARSE_FAILURE).getFirst().assertContentEquals(INVALID_RECORD_TEXT);
    }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-127  ·  MethodSource

**项目** `Commons-IO`  **文件** `commons-io/src/test/java/org/apache/commons/io/input/QueueInputStreamTest.java`  **测试** `testUnbufferedReadWrite`

### Test method

```java
@ParameterizedTest(name = "inputData={0}")
    @MethodSource("inputData")
    void testUnbufferedReadWrite(final String inputData) throws IOException {
        try (QueueInputStream inputStream = new QueueInputStream();
                QueueOutputStream outputStream = inputStream.newQueueOutputStream()) {
            writeUnbuffered(outputStream, inputData);
            final String actualData = readUnbuffered(inputStream);
            assertEquals(inputData, actualData);
        }
    }
```

### Parameter provider — 同文件内的 `inputData`

```java
    public static Stream<Arguments> inputData() {
        // @formatter:off
        return Stream.of(Arguments.of(""),
                Arguments.of("1"),
                Arguments.of("12"),
                Arguments.of("1234"),
                Arguments.of("12345678"),
                Arguments.of(StringUtils.repeat("A", 4095)),
                Arguments.of(StringUtils.repeat("A", 4096)),
                Arguments.of(StringUtils.repeat("A", 4097)),
                Arguments.of(StringUtils.repeat("A", 8191)),
                Arguments.of(StringUtils.repeat("A", 8192)),
                Arguments.of(StringUtils.repeat("A", 8193)),
                Arguments.of(StringUtils.repeat("A", 8192 * 4)));
        // @formatter:on
    }
```

### Test-side helpers called by this test (2)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`writeUnbuffered`**

```java
    private void writeUnbuffered(final QueueOutputStream outputStream, final String inputData) throws IOException {
        final byte[] bytes = inputData.getBytes(StandardCharsets.UTF_8);
        outputStream.write(bytes, 0, bytes.length);
    }
```

**`readUnbuffered`**

```java
    private String readUnbuffered(final InputStream inputStream) throws IOException {
        return readUnbuffered(inputStream, Integer.MAX_VALUE);
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-130  ·  EnumSource

**项目** `Commons-Numbers`  **文件** `commons-numbers/commons-numbers-gamma/src/test/java/org/apache/commons/numbers/gamma/BoostGammaTest.java`  **测试** `testLogGammaPDerivative`

### Test method

```java
@ParameterizedTest
    @EnumSource(value = BiTestCase.class, mode = Mode.MATCH_ANY, names = {"LOG_GAMMA_P_DERIV.*"})
    void testLogGammaPDerivative(BiTestCase tc) {
        assertFunction(tc);
    }
```

### Enum declaration — `BiTestCase` (commons-numbers/commons-numbers-gamma/src/test/java/org/apache/commons/numbers/gamma/BoostBetaTest.java)

```java
    private enum BiTestCase implements TestError {
        // beta(a, b)
        // Note that the worst errors occur when a or b are large, and that
        // when this is the case the result is very close to zero, so absolute
        // errors will be very small.
        /** beta Boost small data. */
        BETA_SMALL(BoostBeta::beta, "beta_small_data.csv", 4, 1.7),
        /** beta Boost medium data. */
        BETA_MED(BoostBeta::beta, "beta_med_data.csv", 200, 35),
        /** beta Boost divergent data. */
        BETA_EXP(BoostBeta::beta, "beta_exp_data.csv", 17, 3.6),
        // LogBeta based implementation is worse
        /** beta Boost small data. */
        BETA1_SMALL(BoostBetaTest::beta, "beta_small_data.csv", 110, 28),
        /** beta Boost medium data. */
        BETA1_MED(BoostBetaTest::beta, "beta_med_data.csv", 280, 46),
        /** beta Boost divergent data. */
        BETA1_EXP(BoostBetaTest::beta, "beta_exp_data.csv", 28, 4.5),
        /** binomial coefficient Boost small argument data. */
        BINOMIAL_SMALL(BoostBetaTest::binomialCoefficient, "binomial_small_data.csv", -2, 0.5),
        /** binomial coefficient Boost large argument data. */
        BINOMIAL_LARGE(BoostBetaTest::binomialCoefficient, "binomial_large_data.csv", 5, 1.1),
        /** binomial coefficient extra large argument data. */
        BINOMIAL_XLARGE(BoostBetaTest::binomialCoefficient, "binomial_extra_large_data.csv", 9, 2),
        /** binomial coefficient huge argument data. */
        BINOMIAL_HUGE(BoostBetaTest::binomialCoefficient, "binomial_huge_data.csv", 9, 2),
        // Using the beta function is worse
        /** binomial coefficient Boost large argument data computed using the beta function. */
        BINOMIAL1_LARGE(BoostBetaTest::binomialCoefficient1, "binomial_large_data.csv", 31, 9),
        /** binomial coefficient huge argument data computed using the beta function. */
        BINOMIAL1_HUGE(BoostBetaTest::binomialCoefficient1, "binomial_huge_data.csv", 70, 19);

        /** The function. */
        private final DoubleBinaryOperator fun;

        /** The filename containing the test data. */
        private final String filename;

        /** The field containing the expected value. */
        private final int expected;

        /** The maximum allowed ulp. */
        private final double maxUlp;

        /** The maximum allowed RMS ulp. */
        private final double rmsUlp;

        /**
         * Instantiates a new test case.
         *
         * @param fun function to test
         * @param filename Filename of the test data
         * @param maxUlp maximum allowed ulp
         * @param rmsUlp maximum allowed RMS ulp
         */
        BiTestCase(DoubleBinaryOperator fun, String filename, double maxUlp, double rmsUlp) {
            this(fun, filename, 2, maxUlp, rmsUlp);
        }

        /**
         * Instantiates a new test case.
         *
         * @param fun function to test
         * @param filename Filename of the test data
         * @param expected Expected result field index
         * @param maxUlp maximum allowed ulp
         * @param rmsUlp maximum allowed RMS ulp
         */
        BiTestCase(DoubleBinaryOperator fun, String filename, int expected, double maxUlp, double rmsUlp) {
            this.fun = fun;
            this.filename = filename;
            this.expected = expected;
            this.maxUlp = maxUlp;
            this.rmsUlp = rmsUlp;
        }

        /**
         * @return function to test
         */
        DoubleBinaryOperator getFunction() {
            return fun;
        }

        /**
         * @return Filename of the test data
         */
        String getFilename() {
            return filename;
        }

        /**
         * @return Expected result field index
         */
        int getExpectedField() {
            return expected;
        }

        @Override
        public double getTolerance() {
            return maxUlp;
        }

        @Override
        public double getRmsTolerance() {
            return rmsUlp;
        }
    }
```

### Test-side helpers called by this test (6)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`assertFunction`**

```java
    private static void assertFunction(TestCase tc) {
        final TestUtils.ErrorStatistics stats = new TestUtils.ErrorStatistics();
        try (DataReader in = new DataReader(tc.getFilename())) {
            while (in.next()) {
                try {
                    final double x = in.getDouble(0);
                    final BigDecimal expected = in.getBigDecimal(tc.getExpectedField());
                    final double actual = tc.getFunction().applyAsDouble(x);
                    TestUtils.assertEquals(expected, actual, tc.getTolerance(), stats::add,
                        () -> tc + " x=" + x);
                } catch (final NumberFormatException ex) {
                    Assertions.fail("Failed to load data: " + Arrays.toString(in.getFields()), ex);
                }
            }
        } catch (final IOException ex) {
            Assertions.fail("Failed to load data: " + tc.getFilename(), ex);
        }

        assertRms(tc, stats);
    }
```

**`getFilename`**

```java
        String getFilename() {
            return filename;
        }
```

**`getExpectedField`**

```java
        int getExpectedField() {
            return expected;
        }
```

**`getFunction`**

```java
        DoubleUnaryOperator getFunction() {
            return fun;
        }
```

**`assertEquals`**

```java
    private static void assertEquals(DoubleBinaryOperator fun, double x, double y, double expected) {
        final double actual = fun.applyAsDouble(x, y);
        Assertions.assertEquals(expected, actual, () -> x + ", " + y);
    }
```

**`getTolerance`**

```java
@Override
                public double getTolerance() {
                    return tolerance;
                }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-133  ·  ValueSource

**项目** `Commons-BCEL`  **文件** `commons-bcel/src/test/java/org/apache/bcel/classfile/ConstantPoolModuleToStringTest.java`  **测试** `testClass`

### Test method

```java
@ParameterizedTest
    @ValueSource(strings = {
    // @formatter:off
        "java.lang.CharSequence$1CharIterator",                 // contains attribute EnclosingMethod
        "org.apache.commons.lang3.function.TriFunction",        // contains attributes BootstrapMethods, InnerClasses, LineNumberTable, LocalVariableTable,
                                                                // LocalVariableTypeTable, RuntimeVisibleAnnotations, Signature, SourceFile
        "org.apache.commons.lang3.math.NumberUtils",            // contains attribute ConstantFloat, ConstantDouble
        "org.apache.bcel.Const",                                // contains attributes MethodParameters
        "java.io.StringBufferInputStream",                      // contains attributes Deprecated, StackMap
        "java.nio.file.Files",                                  // contains attributes ConstantValue, ExceptionTable, NestMembers
        "org.junit.jupiter.api.AssertionsKt",                   // contains attribute ParameterAnnotation
        "javax.annotation.ManagedBean",                         // contains attribute AnnotationDefault
        "javax.management.remote.rmi.RMIConnectionImpl_Stub"})  // contains attribute Synthetic
    // @formatter:on
    void testClass(final String className) throws Exception {
        testJavaClass(SyntheticRepository.getInstance().loadClass(className));
    }
```

### Test-side helpers called by this test (2)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`testJavaClass`**

```java
    private static void testJavaClass(final JavaClass javaClass) {
        final ConstantPool constantPool = javaClass.getConstantPool();
        final ToStringVisitor visitor = new ToStringVisitor(constantPool);
        final DescendingVisitor descendingVisitor = new DescendingVisitor(javaClass, visitor);
        try {
            javaClass.accept(descendingVisitor);
            assertNotNull(visitor.toString());
        } catch (Exception | Error e) {
            fail(visitor.toString(), e);
        }
    }
```

**`toString`**

```java
@Override
        public String toString() {
            return "ToStringVisitor [count=" + count + ", stringBuilder=" + stringBuilder + ", pool=" + pool + "]";
        }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-136  ·  CsvSource

**项目** `POI`  **文件** `poi/poi-ooxml/src/test/java/org/apache/poi/poifs/crypt/dsig/TestSignatureInfo.java`  **测试** `getSigner`

### Test method

```java
@ParameterizedTest
    @CsvSource(value = {
        "hyperlink-example-signed.docx, true",
        "hello-world-signed.docx, true",
        "hello-world-signed.pptx, false",
        "hello-world-signed.xlsx, true",
        "hello-world-office-2010-technical-preview.docx, true",
        "ms-office-2010-signed.docx, true",
        "ms-office-2010-signed.pptx, false",
        "ms-office-2010-signed.xlsx, true",
        "Office2010-SP1-XAdES-X-L.docx, true",
        "signed.docx, true"
    })
    void getSigner(String testFile, boolean secureValidation) throws Exception {
        try (OPCPackage pkg = OPCPackage.open(testdata.getFile(testFile), PackageAccess.READ)) {
            SignatureConfig sic = new SignatureConfig();
            sic.setSecureValidation(secureValidation);
            SignatureInfo si = new SignatureInfo();
            si.setOpcPackage(pkg);
            si.setSignatureConfig(sic);
            List<X509Certificate> result = new ArrayList<>();
            for (SignaturePart sp : si.getSignatureParts()) {
                if (sp.validate()) {
                    result.add(sp.getSigner());
                }
            }

            assertNotNull(result);
            assertEquals(1, result.size(), "test-file: " + testFile);
            X509Certificate signer = result.get(0);
            LOG.atDebug().log("signer: {}", signer.getSubjectX500Principal());

            boolean b = si.verifySignature();
            assertTrue(b, "test-file: " + testFile);
            pkg.revert();
        }
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-139  ·  CsvSource

**项目** `JMeter`  **文件** `jmeter/src/core/src/test/java/org/apache/jmeter/util/XPathUtilTest.java`  **测试** `testComputeAssertionResultUsingSaxon`

### Test method

```java
@ParameterizedTest
    @CsvSource(value = {
            "/book,false,false,false",
            "/book,true,false,true",
            "/b,false,false,true",
            "/b,true,false,false",
            "count(//page)=2,false,false,false",
            "count(//page)=2,true,false,true",
            "count(//page)=3,false,false,true",
            "count(//page)=3,true,false,false"
    })
    public void testComputeAssertionResultUsingSaxon(String xpathquery, boolean isNegated, boolean isError, boolean isFailure)
            throws SaxonApiException, FactoryConfigurationError {
        //test xpath2 assertion
        AssertionResult res = new AssertionResult("test");
        String responseData = "<book><page>one</page><page>two</page><empty></empty><a><b></b></a></book>";
        XPathUtil.computeAssertionResultUsingSaxon(res, responseData, xpathquery, "", isNegated);
        assertEquals(isError, res.isError());
        assertEquals(isFailure, res.isFailure());
    }
```

### To classify

`equivalence_class` / `semantic_role`

---

## IRR-142  ·  EnumSource

**项目** `Iceberg`  **文件** `iceberg/flink/v2.1/flink/src/test/java/org/apache/iceberg/flink/sink/shuffle/TestDataStatisticsCoordinator.java`  **测试** `testDataStatisticsEventHandlingWithNullValue`

### Test method

```java
@ParameterizedTest
  @EnumSource(StatisticsType.class)
  public void testDataStatisticsEventHandlingWithNullValue(StatisticsType type) throws Exception {
    try (DataStatisticsCoordinator dataStatisticsCoordinator = createCoordinator(type)) {
      dataStatisticsCoordinator.start();
      tasksReady(dataStatisticsCoordinator);

      SortKey nullSortKey = Fixtures.SORT_KEY.copy();
      nullSortKey.set(0, null);

      StatisticsEvent checkpoint1Subtask0DataStatisticEvent =
          Fixtures.createStatisticsEvent(
              type,
              Fixtures.TASK_STATISTICS_SERIALIZER,
              1L,
              nullSortKey,
              CHAR_KEYS.get("b"),
              CHAR_KEYS.get("b"),
              CHAR_KEYS.get("c"),
              CHAR_KEYS.get("c"),
              CHAR_KEYS.get("c"));
      StatisticsEvent checkpoint1Subtask1DataStatisticEvent =
          Fixtures.createStatisticsEvent(
              type,
              Fixtures.TASK_STATISTICS_SERIALIZER,
              1L,
              nullSortKey,
              CHAR_KEYS.get("b"),
              CHAR_KEYS.get("c"),
              CHAR_KEYS.get("c"));
      // Handle events from operators for checkpoint 1
      dataStatisticsCoordinator.handleEventFromOperator(
          0, 0, checkpoint1Subtask0DataStatisticEvent);
      dataStatisticsCoordinator.handleEventFromOperator(
          1, 0, checkpoint1Subtask1DataStatisticEvent);

      waitForCoordinatorToProcessActions(dataStatisticsCoordinator);

      Map<SortKey, Long> keyFrequency =
          ImmutableMap.of(nullSortKey, 2L, CHAR_KEYS.get("b"), 3L, CHAR_KEYS.get("c"), 5L);
      MapAssignment mapAssignment =
          MapAssignment.fromKeyFrequency(NUM_SUBTASKS, keyFrequency, 0.0d, SORT_ORDER_COMPARTOR);

      CompletedStatistics completedStatistics = dataStatisticsCoordinator.completedStatistics();
      assertThat(completedStatistics.checkpointId()).isEqualTo(1L);
      assertThat(completedStatistics.type()).isEqualTo(StatisticsUtil.collectType(type));
      if (StatisticsUtil.collectType(type) == StatisticsType.Map) {
        assertThat(completedStatistics.keyFrequency()).isEqualTo(keyFrequency);
      } else {
        assertThat(completedStatistics.keySamples())
            .containsExactly(
                nullSortKey,
                nullSortKey,
                CHAR_KEYS.get("b"),
                CHAR_KEYS.get("b"),
                CHAR_KEYS.get("b"),
                CHAR_KEYS.get("c"),
                CHAR_KEYS.get("c"),
                CHAR_KEYS.get("c"),
                CHAR_KEYS.get("c"),
                CHAR_KEYS.get("c"));
      }

      GlobalStatistics globalStatistics = dataStatisticsCoordinator.globalStatistics();
      assertThat(globalStatistics.checkpointId()).isEqualTo(1L);
      assertThat(globalStatistics.type()).isEqualTo(StatisticsUtil.collectType(type));
      if (StatisticsUtil.collectType(type) == StatisticsType.Map) {
        assertThat(globalStatistics.mapAssignment()).isEqualTo(mapAssignment);
      } else {
        assertThat(globalStatistics.rangeBounds()).containsExactly(CHAR_KEYS.get("b"));
      }
    }
  }
```

### Enum declaration — `StatisticsType` (iceberg/flink/v1.20/flink/src/main/java/org/apache/iceberg/flink/sink/shuffle/StatisticsType.java)

```java
public enum StatisticsType {
  /**
   * Tracks the data statistics as {@code Map<SortKey, Long>} frequency. It works better for
   * low-cardinality scenarios (like country, event_type, etc.) where the cardinalities are in
   * hundreds or thousands.
   *
   * <ul>
   *   <li>Pro: accurate measurement on the statistics/weight of every key.
   *   <li>Con: memory footprint can be large if the key cardinality is high.
   * </ul>
   */
  Map,

  /**
   * Sample the sort keys via reservoir sampling. Then split the range partitions via range bounds
   * from sampled values. It works better for high-cardinality scenarios (like device_id, user_id,
   * uuid etc.) where the cardinalities can be in millions or billions.
   *
   * <ul>
   *   <li>Pro: relatively low memory footprint for high-cardinality sort keys.
   *   <li>Con: non-precise approximation with potentially lower accuracy.
   * </ul>
   */
  Sketch,

  /**
   * Initially use Map for statistics tracking. If key cardinality turns out to be high,
   * automatically switch to sketch sampling.
   */
  Auto
}
```

### Test-side helpers called by this test (4)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`createCoordinator`**

```java
  private static DataStatisticsCoordinator createCoordinator(StatisticsType type) {
    return new DataStatisticsCoordinator(
        OPERATOR_NAME,
        new MockOperatorCoordinatorContext(TEST_OPERATOR_ID, NUM_SUBTASKS),
        Fixtures.SCHEMA,
        Fixtures.SORT_ORDER,
        NUM_SUBTASKS,
        type,
        0.0d);
  }
```

**`tasksReady`**

```java
  private void tasksReady(DataStatisticsCoordinator coordinator) {
    setAllTasksReady(NUM_SUBTASKS, coordinator, receivingTasks);
  }
```

**`waitForCoordinatorToProcessActions`**

```java
  static void waitForCoordinatorToProcessActions(DataStatisticsCoordinator coordinator) {
    CompletableFuture<Void> future = new CompletableFuture<>();
    coordinator.callInCoordinatorThread(
        () -> {
          future.complete(null);
          return null;
        },
        "Coordinator fails to process action");

    try {
      future.get();
    } catch (InterruptedException e) {
      throw new AssertionError("test interrupted");
    } catch (ExecutionException e) {
      ExceptionUtils.rethrow(ExceptionUtils.stripExecutionException(e));
    }
  }
```

**`setAllTasksReady`**

```java
  static void setAllTasksReady(
      int subtasks,
      DataStatisticsCoordinator dataStatisticsCoordinator,
      EventReceivingTasks receivingTasks) {
    for (int i = 0; i < subtasks; i++) {
      dataStatisticsCoordinator.executionAttemptReady(
          i, 0, receivingTasks.createGatewayForSubtask(i, 0));
    }
  }
```

### To classify

`equivalence_class` / `enum_structure` / `enum_usage_intent` / `behavior_carrying`

---

## IRR-145  ·  MethodSource

**项目** `Commons-RNG`  **文件** `commons-rng/commons-rng-simple/src/test/java/org/apache/commons/rng/simple/ProvidersCommonParametricTest.java`  **测试** `testFactoryCreateMethod`

### Test method

```java
@ParameterizedTest
    @MethodSource("getProvidersTestData")
    void testFactoryCreateMethod(ProvidersList.Data data) {
        final RandomSource originalSource = data.getSource();
        final Object originalSeed = data.getSeed();
        final Object[] originalArgs = data.getArgs();
        // Cannot test providers that require arguments
        Assumptions.assumeTrue(originalArgs == null);
        @SuppressWarnings("deprecation")
        final UniformRandomProvider rng = RandomSource.create(data.getSource());
        final UniformRandomProvider generator = originalSource.create(originalSeed, originalArgs);
        Assertions.assertEquals(generator.getClass(), rng.getClass());
    }
```

### Parameter provider — 同文件内的 `getProvidersTestData`

```java
    private static Iterable<ProvidersList.Data> getProvidersTestData() {
        return ProvidersList.list();
    }
```

### To classify

`equivalence_class` / `semantic_role` / `methodsource_intent` / `type_complexity` / `value_complexity` / `behavior_carrying`

---

## IRR-148  ·  ValueSource

**项目** `Flink`  **文件** `flink/flink-formats/flink-avro/src/test/java/org/apache/flink/formats/avro/typeutils/AvroTypeExtractionTest.java`  **测试** `testSerializeWithAvro`

### Test method

```java
@ParameterizedTest
    @ValueSource(booleans = {true, false})
    void testSerializeWithAvro(boolean useMiniCluster, @InjectMiniCluster MiniCluster miniCluster)
            throws Exception {
        final StreamExecutionEnvironment env = getExecutionEnvironment(useMiniCluster, miniCluster);
        ((SerializerConfigImpl) env.getConfig().getSerializerConfig()).setForceKryoAvro(true);
        Path in = new Path(inFile.getAbsoluteFile().toURI());

        AvroInputFormat<User> users = new AvroInputFormat<>(in, User.class);
        DataStream<User> usersDS =
                env.createInput(users)
                        .map(
                                (MapFunction<User, User>)
                                        value -> {
                                            Map<CharSequence, Long> ab = new HashMap<>(1);
                                            ab.put("hehe", 12L);
                                            value.setTypeMap(ab);
                                            return value;
                                        });

        usersDS.sinkTo(
                FileSink.forRowFormat(new Path(resultPath), new SimpleStringEncoder<User>())
                        .build());

        env.execute("Simple Avro read job");

        expected =
                "{\"name\": \"Alyssa\", \"favorite_number\": 256, \"favorite_color\": null,"
                        + " \"type_long_test\": null, \"type_double_test\": 123.45, \"type_null_test\": null,"
                        + " \"type_bool_test\": true, \"type_array_string\": [\"ELEMENT 1\", \"ELEMENT 2\"],"
                        + " \"type_array_boolean\": [true, false], \"type_nullable_array\": null, \"type_enum\": \"GREEN\","
                        + " \"type_map\": {\"hehe\": 12}, \"type_fixed\": null, \"type_union\": null,"
                        + " \"type_nested\": {\"num\": 239, \"street\": \"Baker Street\", \"city\": \"London\","
                        + " \"state\": \"London\", \"zip\": \"NW1 6XE\"},"
                        + " \"type_bytes\": \"\\u0000\\u0000\\u0000\\u0000\\u0000\\u0000\\u0000\\u0000\\u0000\\u0000\", "
                        + "\"type_date\": \"2014-03-01\", \"type_time_millis\": \"12:12:12\", \"type_time_micros\": \"00:00:00.123456\", "
                        + "\"type_timestamp_millis\": \"2014-03-01T12:12:12.321Z\", "
                        + "\"type_timestamp_micros\": \"1970-01-01T00:00:00.123456Z\", "
                        + "\"type_decimal_bytes\": \"\\u0007Ð\", \"type_decimal_fixed\": [7, -48]}\n"
                        + "{\"name\": \"Charlie\", \"favorite_number\": null, "
                        + "\"favorite_color\": \"blue\", \"type_long_test\": 1337, \"type_double_test\": 1.337, "
                        + "\"type_null_test\": null, \"type_bool_test\": false, \"type_array_string\": [], "
                        + "\"type_array_boolean\": [], \"type_nullable_array\": null, \"type_enum\": \"RED\", "
                        + "\"type_map\": {\"hehe\": 12}, \"type_fixed\": null, \"type_union\": null, "
                        + "\"type_nested\": {\"num\": 239, \"street\": \"Baker Street\", \"city\": \"London\", \"state\": \"London\", "
                        + "\"zip\": \"NW1 6XE\"}, "
                        + "\"type_bytes\": \"\\u0000\\u0000\\u0000\\u0000\\u0000\\u0000\\u0000\\u0000\\u0000\\u0000\", "
                        + "\"type_date\": \"2014-03-01\", \"type_time_millis\": \"12:12:12\", \"type_time_micros\": \"00:00:00.123456\", "
                        + "\"type_timestamp_millis\": \"2014-03-01T12:12:12.321Z\", "
                        + "\"type_timestamp_micros\": \"1970-01-01T00:00:00.123456Z\", "
                        + "\"type_decimal_bytes\": \"\\u0007Ð\", \"type_decimal_fixed\": [7, -48]}\n";
    }
```

### Test-side helpers called by this test (1)

> Parameter-dependent branching may live here rather than in the test body — check these before deciding.

**`getExecutionEnvironment`**

```java
    private static StreamExecutionEnvironment getExecutionEnvironment(
            boolean useMiniCluster, MiniCluster miniCluster) {
        return useMiniCluster
                ? new TestStreamEnvironment(miniCluster, PARALLELISM)
                : StreamExecutionEnvironment.getExecutionEnvironment();
    }
```

### To classify

`equivalence_class` / `semantic_role`

---
