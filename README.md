# ParameterizedTest-Empirical-Study

Simple instructions

1. Add projects to `projects.txt` — one project per line with a name and git URL separated by whitespace. Example:

```
camel https://github.com/apache/camel.git
wicket https://github.com/apache/wicket.git
```

2. Run the pipeline:

```
./run_project.sh
```

3. If you want to keep cloned repositories after the run (default is to remove them), use:

```
./run_project.sh --keep
```

Outputs

- `releases/` — per-project tag lists (e.g. `releases/camel.txt`)
- `selected_releases/` — chosen releases per project
- `parser_result/` — parser outputs organized by project and tag
- `trend_result` - summary of parameterized test number and trend

That's it — add your projects and run the script.

### Parser Attribution

This project uses a modified version of the parameterized test parser originally developed by [gengwu](https://github.com/gzhao9/test-parser). The core logic remains mostly unchanged, but has been adapted to integrate with this automated pipeline.

Note: The current parser implementation uses absolute paths to locate `.jar` files and output directories. Please make sure to update these paths according to your local environment when replicating or adapting the workflow.
