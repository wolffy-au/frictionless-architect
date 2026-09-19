(() => {
  const warningBanner = document.getElementById("warning-banner");
  const diagramBtn = document.getElementById("diagram-btn");
  const tableBtn = document.getElementById("table-btn");
  const refreshBtn = document.getElementById("refresh-btn");
  const refreshStatus = document.getElementById("refresh-status");
  const neo4jStatus = document.getElementById("neo4j-status");
  const sampleStatus = document.getElementById("sample-status");
  const cacheAge = document.getElementById("cache-age");
  const lastWarning = document.getElementById("last-warning");
  const errorMessage = document.getElementById("error-message");
  const diagramView = document.getElementById("diagram-view");
  const tableView = document.getElementById("table-view");
  const elementsTable = document.getElementById("elements-table");
  const relationshipsTable = document.getElementById("relationships-table");
  const summaryList = document.getElementById("summary-list");
  const TABLE_URL = "/schema-payload";
  let cyInstance = null;

  function showWarning(message) {
    if (!message) {
      warningBanner.classList.remove("visible");
      warningBanner.textContent = "";
      return;
    }
    warningBanner.textContent = message;
    warningBanner.classList.add("visible");
  }

  function showDiagramView() {
    diagramBtn.classList.add("active");
    tableBtn.classList.remove("active");
    diagramView.classList.remove("hidden");
    tableView.classList.add("hidden");
  }

  function showTableView() {
    diagramBtn.classList.remove("active");
    tableBtn.classList.add("active");
    diagramView.classList.add("hidden");
    tableView.classList.remove("hidden");
  }

  function badge(className, text) {
    const span = document.createElement("span");
    span.className = `badge ${className}`;
    span.textContent = text;
    return span;
  }

  // Builds real DOM nodes rather than an HTML string: payload data (element
  // names, ids, ...) is server/model-sourced and must never be interpolated
  // into innerHTML, even escaped -- textContent/createElement sidestep the
  // question entirely by never parsing the value as markup.
  function buildTable(container, rows, columns) {
    container.replaceChildren();
    if (!rows.length) {
      const empty = document.createElement("p");
      empty.textContent = "No records";
      container.appendChild(empty);
      return;
    }
    const table = document.createElement("table");
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    for (const col of columns) {
      const th = document.createElement("th");
      th.textContent = col.label;
      headRow.appendChild(th);
    }
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    for (const row of rows) {
      const tr = document.createElement("tr");
      for (const col of columns) {
        const td = document.createElement("td");
        if (col.render) {
          td.appendChild(col.render(row[col.field]));
        } else {
          td.textContent = row[col.field] ?? "—";
        }
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    container.appendChild(table);
  }

  function renderTables(payload) {
    const elemColumns = [
      { label: "Identifier", field: "identifier" },
      { label: "Name", field: "name" },
      { label: "Type", field: "type" },
      {
        label: "Coverage",
        field: "coverage",
        render: (value) => badge(value ? "ok" : "warn", value ? "covered" : "missing"),
      },
      { label: "Source", field: "source_file" },
    ];
    buildTable(elementsTable, payload.elements, elemColumns);
    const relColumns = [
      { label: "Identifier", field: "identifier" },
      { label: "Type", field: "type" },
      { label: "Source", field: "source" },
      { label: "Target", field: "target" },
      { label: "Source File", field: "source_file" },
    ];
    buildTable(relationshipsTable, payload.relationships, relColumns);
  }

  function renderSummary(payload) {
    summaryList.replaceChildren();
    for (const element of payload.elements) {
      const row = document.createElement("div");
      const name = document.createElement("strong");
      name.textContent = element.name || element.identifier;
      row.appendChild(name);
      row.appendChild(document.createTextNode(" · "));
      row.appendChild(badge(element.coverage ? "ok" : "warn", element.coverage ? "covered" : "gap"));
      summaryList.appendChild(row);
    }
  }

  function buildDiagram(payload) {
    if (!payload.views.length || typeof cytoscape !== "function") {
      diagramView.innerHTML = "<p>No diagram available</p>";
      return;
    }
    const view = payload.views[0];
    const nodes = (view.nodes || []).map((node) => {
      return {
        data: {
          id: node.identifier || node.elementRef,
          label: node.label || node.elementRef,
        },
        position: {
          x: node.bounds?.x ?? 0,
          y: node.bounds?.y ?? 0,
        },
      };
    });
    const edges = (view.connections || []).map((connection) => ({
      data: {
        id: connection.identifier || connection.relationshipRef,
        source: connection.source,
        target: connection.target,
      },
    }));
    if (cyInstance) {
      cyInstance.destroy();
    }
    cyInstance = cytoscape({
      container: diagramView,
      elements: [...nodes, ...edges],
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            background: "#1b396a",
            color: "#fff",
            width: 140,
            height: 60,
          },
        },
        {
          selector: "edge",
          style: {
            width: 2,
            lineColor: "#1b396a",
            curveStyle: "bezier",
            targetArrowShape: "triangle",
            targetArrowColor: "#1b396a",
          },
        },
      ],
      layout: { name: "preset" },
    });
  }

  async function loadPayload(forceReload = false) {
    try {
      refreshStatus.textContent = "";
      const params = forceReload ? "?force_reload=true" : "";
      const response = await fetch(`${TABLE_URL}${params}`);
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const payload = await response.json();
      renderTables(payload);
      renderSummary(payload);
      buildDiagram(payload);
      const warning = payload.warnings?.length ? payload.warnings[0] : "";
      showWarning(warning);
      errorMessage.style.display = "none";
    } catch (err) {
      showWarning("");
      errorMessage.style.display = "block";
      errorMessage.textContent = err.message || "Unable to load schema payload.";
    }
  }

  async function loadStatus() {
    try {
      const response = await fetch("/schema-payload/status");
      if (!response.ok) {
        return;
      }
      const status = await response.json();
      neo4jStatus.textContent = status.neo4j_status || "unknown";
      sampleStatus.textContent = status.sample_file_status || "unknown";
      const cacheAgeSeconds = status.cache_age_seconds;
      if (typeof cacheAgeSeconds === "number") {
        cacheAge.textContent = `${cacheAgeSeconds}s`;
      } else {
        cacheAge.textContent = "—";
      }
      lastWarning.textContent = status.last_warning || "";
      if (status.last_warning) {
        showWarning(status.last_warning);
      }
    } catch {
      // ignore
    }
  }

  refreshBtn.addEventListener("click", async () => {
    refreshBtn.disabled = true;
    refreshStatus.textContent = "Triggering refresh...";
    try {
      const response = await fetch("/schema-payload/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: "manual" }),
      });
      if (response.status === 409) {
        refreshStatus.textContent = "Refresh already running.";
        return;
      }
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const body = await response.json();
      refreshStatus.textContent = `Refresh started (${body.estimated_completion_ms}ms)`;
      await loadPayload(false);
    } catch (err) {
      refreshStatus.textContent = err.message || "Refresh failed";
    } finally {
      refreshBtn.disabled = false;
    }
  });

  diagramBtn.addEventListener("click", showDiagramView);
  tableBtn.addEventListener("click", showTableView);

  document.addEventListener("DOMContentLoaded", () => {
    loadPayload();
    loadStatus();
    setInterval(loadStatus, 15000);
  });
})();
