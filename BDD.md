# Behavior-Driven Development (BDD) Study Notes: GCO Project

This document explains how the BDD tests are structured and executed in the GCO project using the `behave` framework.

## 1. Directory Structure

The BDD tests are organized within the `features/` directory:

```text
gco/
├── behave.ini            # Configuration for behave
├── data.py               # The code being tested (Data Layer)
└── features/             # BDD Root
    ├── 01_data_loading.feature        # Gherkin feature files
    ├── 02_data_export_import.feature
    ├── ...
    └── steps/            # Step Definitions
        └── data_layer_steps.py        # Python implementation of steps
```

## 2. The BDD Flow

The execution follows a specific sequence from high-level requirements to low-level code verification:

### Step 1: Invocation
When you run `behave` from the project root:
- It looks for `behave.ini` for configuration (paths, formats, tags).
- It scans the `features/` directory for `.feature` files.

### Step 2: Feature & Scenario Discovery
Each `.feature` file (e.g., `01_data_loading.feature`) contains **Features** and **Scenarios** written in **Gherkin** (Given/When/Then).

Example from `01_data_loading.feature`:
```gherkin
Scenario: Load scores data
  Given the data directory exists
  When I load the scores data
  Then I should get a pandas DataFrame
```

### Step 3: Step Mapping (The "Magic" Discovery)
`behave` automatically looks for a directory named **`steps/`** inside the features folder. It imports **every** Python file in that directory. 

- **How it knows**: It doesn't need to be told to look at `data_layer_steps.py` specifically; it simply loads all `.py` files in `features/steps/` and matches the Gherkin text to the decorated functions in its registry.
- **Global Step Pool**: If you have multiple files under `steps/`, Behave treats them all as one large library of steps. The execution order is driven by the `.feature` file, which pulls the matching Python code from whichever file contains it.

In `data_layer_steps.py`:
```python
@when('I load the scores data')
def step_load_scores(context):
    """Load scores data"""
    test_state['scores'] = load_scores()
    context.scores = test_state['scores']
```

### Step 4: Execution & State Management
- **The `context` Object**: This is the most critical part of the flow. It's a shared object passed between steps in a single scenario. It allows one step (e.g., "When I load...") to pass data (e.g., `context.scores`) to a subsequent step (e.g., "Then I should get...").
- **Importing Logic**: `data_layer_steps.py` imports functions directly from `data.py` to test them in isolation.
- **Assertions**: The `@then` steps use standard Python `assert` statements. If an assertion fails, the test fails.

## 3. Key Components in `data_layer_steps.py`

| Component | Responsibility |
| :--- | :--- |
| **Imports** | Pulls functions like `load_scores()`, `export_app_state()` from `data.py`. |
| **Decorators** | `@given`, `@when`, `@then` map natural language to code. |
| **Context** | Stores temporary test data (e.g., `context.scores`, `context.diff`). |
| **Logic** | Executes the actual data layer functions and validates their output. |

## 4. Lifecycle Hooks (`environment.py`)
While step files define specific actions, `features/environment.py` manages the **test lifecycle**. It contains "hooks" that run at specific times:

| Hook | Timing | Our Use Case |
| :--- | :--- | :--- |
| `before_all` | Runs once before any tests start | Initializing the `created_backups` list. |
| `after_all` | Runs once after all tests finish | Deleting all files in the `created_backups` list. |
| `before_scenario` | Runs before every individual scenario | Resetting state for a fresh start. |

## 5. Why This Works
This structure separates **what** the system should do (the `.feature` files) from **how** it does it (the `data.py` logic), with the `steps/` acting as the bridge. It ensures that the Data Layer remains robust and that changes to data handling don't break the application's core functionality.

## 5. Reporting and Output
When running tests, `behave` generates output based on the configuration in `behave.ini`.

- **`pretty.output`**: This file is a saved snapshot of a successful test execution. It uses the `pretty` format to show a colorized (in terminal) or text-based (in file) log of every scenario and step.
- **Generating Reports**: You can generate your own report file by running:
  ```bash
  uv run behave --outfile your_report_name.txt
  ```
