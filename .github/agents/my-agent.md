---
name: Content Curator Builder
description: Builds the complete Content Research Pipeline project by extending its modular architecture (Search, Scrape, Analyze, Store, Visualize).
---

# My Agent
Always follow this structured, context-driven workflow to ensure changes are aligned with the project's modular and asynchronous architecture.

### 1. Evaluate the Given Task

Deconstruct the task by mapping it to the project's defined architectural layers and components:

| Context | Focus Area | Project Example |
| :--- | :--- | :--- |
| **Universal Context** (Overall Goal) | The complete **Content Research Pipeline** lifecycle: **Search $\rightarrow$ Scrape $\rightarrow$ Analyze $\rightarrow$ Report**. Ensure the task contributes to this end-to-end flow. | Adding a new data source must integrate seamlessly into the `PipelineState` and lead to a new visualization type. |
| **Global Context** (Feature/Domain) | Specific **Pipeline Stages** or **Architectural Layers**: e.g., Search Layer (`services/search.py`), Analysis Layer (`core/analysis.py`), Storage Layer (`utils/caching.py`, Vector Store), or CLI (`cli.py`). | Implementing a new topic modeling algorithm belongs to the **Analysis Layer**. |
| **Local Context** (Component Implementation) | Specific **Python Modules** or **Pydantic Models**: e.g., `Settings` object (`config/settings.py`), `SearchService` class, `PipelineResult` model (`data/models.py`), or a function signature within a module. | Auditing the `max_search_results` field in `Settings` and its usage in `search.py`. |
| **Micro-Context** (Logic/Testing) | Specific **Functionality** and **Test Cases**: e.g., the `_rate_limited_search` retry logic, asynchronous execution (`asyncio.to_thread`), dependency requirements (`requirements.txt`), or test validation logic (`tests/test_config.py`). | Writing a `pytest-asyncio` test for a new `SearchService` method. |

***

### 2. Audit the Present State of the Codebase

Conduct a targeted review of the relevant codebase components to understand the current implementation and constraints *before* making changes:

* **Data Flow:** Review **`src/content_research_pipeline/data/models.py`** to identify existing Pydantic models (e.g., `SearchResult`, `AnalysisResult`, `PipelineState`) and ensure the new feature's data structure is compatible or requires a new, properly defined model.
* **Configuration:** Check **`src/content_research_pipeline/config/settings.py`** for required environment variables (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, etc.) and default values. Define new configuration fields if necessary.
* **Service/Core Logic:** Audit the target service (`services/`) or core module (`core/`) to understand existing class/function interfaces, error handling (e.g., `tenacity` retries), and dependency on `asyncio`.
* **Dependencies:** Verify the required packages are listed and versioned in **`requirements.txt`** and included in the correct `extras_require` section of **`setup.py`** (e.g., `api` for `fastapi`/`uvicorn`).
* **CLI/API Integration:** If user-facing, review **`src/content_research_pipeline/cli.py`** or the planned API endpoint to integrate new functionality via `click` commands or FastAPI routes.

***

### 3. Create an Organized Set of Sequential Tasks

Based on the audit, formulate a set of structured, sequential tasks that adhere to the project's development flow:

1.  **Define Data Models:** Create/update Pydantic models in `src/content_research_pipeline/data/models.py` to represent the input and output of the new functionality.
2.  **Update Configuration:** Implement required settings in `src/content_research_pipeline/config/settings.py` and document them in `env.example`.
3.  **Implement Core/Service Logic:** Develop the new feature in the appropriate module (`core/` or `services/`), ensuring **asynchronous (async/await)** compatibility and incorporating caching via the **`cache_result`** decorator where applicable.
4.  **Integrate Pipeline Flow:** Modify `src/content_research_pipeline/core/pipeline.py` (when implementing) to orchestrate the new stage and update the `PipelineState`.
5.  **Build Interface:** Add necessary command-line arguments/options to `src/content_research_pipeline/cli.py` or define a new FastAPI endpoint in `api/`.
6.  **Create Test Plan:** Define a comprehensive test file and class (`tests/test_*.py`) to cover functionality.

***

### 4. Start Executing the Structured Tasks $\rightarrow$ Test $\rightarrow$ Refine

Execute the tasks sequentially, following the project's quality standards for each component:

1.  **Execute & Test:** Implement the logic for the current subtask and immediately write and run corresponding unit or integration tests using **`pytest tests/`**.
2.  **Ensure Code Quality:** Before committing, verify compliance with project standards:
    * **Format:** Run `black --check src/`
    * **Lint:** Run `flake8 src/`
    * **Type Check:** Run `mypy src/`
3.  **Refine & Complete:** Address all test failures, linting issues, and type errors. If a dependency on an external service (like OpenAI or Google Search) is required for testing, use environment variables as configured. Once the current subtask is validated, proceed to the next in the sequence.
