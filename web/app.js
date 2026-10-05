const $ = (id) => document.getElementById(id);

// Поточний стан сторінки
const state = {
  types: [],        // типи з сервера: [{name, hint}]
  hints: {},        // тип → підказка формату
  db: null,         // обрана база
  tableName: null,  // обрана таблиця
  table: null,      // дані обраної таблиці з сервера
  selectedRow: -1,  // номер виділеного рядка
};
let joinTables = {};  // таблиці для вікна сполучення

// ---------- допоміжне ----------

function setStatus(text, isError = false) {
  $("status").textContent = text;
  $("status").classList.toggle("error", isError);
}

// Виконує запит; помилку від сервера показує в рядку статусу і повертає undefined
async function run(action) {
  try {
    return await action();
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    setStatus(error.message, true);
    return undefined;
  }
}

function showDialogError(dialog, error) {
  dialog.querySelector("p.error").textContent = error ? error.message : "";
}

// Виконує запит у вікні; при помилці показує її у вікні і повертає false
async function tryInDialog(dialog, action) {
  try {
    await action();
    return true;
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    showDialogError(dialog, error);
    return false;
  }
}

function openDialog(dialog) {
  showDialogError(dialog, null);
  dialog.showModal();
}

// Показує таблицю, отриману від сервера, в елементі <table>
function fillTable(tableElement, table) {
  tableElement.innerHTML = "";
  const header = tableElement.createTHead().insertRow();
  header.appendChild(document.createElement("th")).textContent = "#";
  for (const column of table.columns) {
    const th = document.createElement("th");
    th.textContent = column.name;
    const type = document.createElement("span");
    type.className = "type";
    type.textContent = column.type;
    th.appendChild(type);
    header.appendChild(th);
  }
  const body = tableElement.createTBody();
  table.rows.forEach((row, index) => {
    const tr = body.insertRow();
    tr.insertCell().textContent = index + 1;
    for (const value of row) tr.insertCell().textContent = String(value);
  });
}

function updateButtons() {
  const hasDb = state.db !== null;
  const hasTable = state.table !== null;
  for (const id of ["save-btn", "load-btn", "create-table-btn"]) $(id).disabled = !hasDb;
  for (const id of ["drop-table-btn", "add-row-btn"]) $(id).disabled = !hasTable;
  $("delete-row-btn").disabled = !hasTable || state.selectedRow < 0;
  $("join-btn").disabled = !hasDb || $("tables-list").children.length < 2;
}

// ---------- оновлення даних з сервера ----------

async function refreshDatabases(select = state.db) {
  const names = await run(() => api.listDatabases());
  if (!names) return false;  // сервер недоступний – нічого не очищаємо
  const dbSelect = $("db-select");
  dbSelect.innerHTML = "";
  for (const name of names) dbSelect.add(new Option(name, name));
  state.db = names.includes(select) ? select : (names[0] ?? null);
  if (state.db) dbSelect.value = state.db;
  await refreshTables(state.tableName);
  return true;
}

async function refreshTables(select = null) {
  let names = [];
  if (state.db) names = (await run(() => api.listTables(state.db))) ?? [];
  state.tableName = names.includes(select) ? select : (names[0] ?? null);

  const list = $("tables-list");
  list.innerHTML = "";
  for (const name of names) {
    const li = document.createElement("li");
    li.textContent = name;
    li.classList.toggle("selected", name === state.tableName);
    li.addEventListener("click", () => selectTable(name));
    list.appendChild(li);
  }
  await loadTable();
}

function selectTable(name) {
  state.tableName = name;
  for (const li of $("tables-list").children) li.classList.toggle("selected", li.textContent === name);
  loadTable();
}

async function loadTable() {
  state.table = null;
  state.selectedRow = -1;
  if (state.db && state.tableName) {
    state.table = (await run(() => api.getTable(state.db, state.tableName))) ?? null;
  }
  if (state.table) {
    fillTable($("data-table"), state.table);
    $("table-title").textContent = `Таблиця: ${state.table.name}`;
  } else {
    $("data-table").innerHTML = "";
    $("table-title").textContent = "Таблицю не обрано";
  }
  updateButtons();
}

// ---------- бази ----------

$("db-select").addEventListener("change", () => {
  state.db = $("db-select").value;
  refreshTables();
});

$("new-db-btn").addEventListener("click", () => {
  $("new-db-name").value = "";
  openDialog($("new-db-dialog"));
});

$("new-db-ok").addEventListener("click", async () => {
  const dialog = $("new-db-dialog");
  const name = $("new-db-name").value;
  if (await tryInDialog(dialog, () => api.createDatabase(name))) {
    dialog.close();
    await refreshDatabases(name.trim());
  }
});

$("refresh-btn").addEventListener("click", async () => {
  if (await refreshDatabases()) setStatus("Дані оновлено");
});

$("save-btn").addEventListener("click", async () => {
  const answer = await run(() => api.saveDatabase(state.db));
  if (answer) setStatus(answer.detail);
});

$("load-btn").addEventListener("click", async () => {
  if (!confirm("Незбережені зміни буде втрачено. Продовжити?")) return;
  const answer = await run(() => api.loadDatabase(state.db));
  if (answer) {
    await refreshTables(state.tableName);
    setStatus(answer.detail);
  }
});

// ---------- таблиці ----------

function addColumnRow() {
  const body = $("columns-editor").tBodies[0];
  const tr = body.insertRow();
  const nameInput = document.createElement("input");
  const typeSelect = document.createElement("select");
  for (const type of state.types) typeSelect.add(new Option(type.name, type.name));
  const updateHint = () => { typeSelect.title = state.hints[typeSelect.value]; };
  typeSelect.addEventListener("change", updateHint);
  updateHint();
  tr.insertCell().appendChild(nameInput);
  tr.insertCell().appendChild(typeSelect);
  tr.addEventListener("click", () => {
    for (const row of body.rows) row.classList.toggle("selected", row === tr);
  });
}

$("create-table-btn").addEventListener("click", () => {
  $("new-table-name").value = "";
  $("columns-editor").tBodies[0].innerHTML = "";
  addColumnRow();
  openDialog($("create-table-dialog"));
});

$("add-column-btn").addEventListener("click", addColumnRow);

$("remove-column-btn").addEventListener("click", () => {
  const body = $("columns-editor").tBodies[0];
  const row = body.querySelector("tr.selected") ?? body.rows[body.rows.length - 1];
  if (row) row.remove();
});

$("create-table-ok").addEventListener("click", async () => {
  const dialog = $("create-table-dialog");
  const name = $("new-table-name").value;
  const columns = [...$("columns-editor").tBodies[0].rows].map((tr) => ({
    name: tr.querySelector("input").value,
    type: tr.querySelector("select").value,
  }));
  if (await tryInDialog(dialog, () => api.createTable(state.db, name, columns))) {
    dialog.close();
    await refreshTables(name.trim());
  }
});

$("drop-table-btn").addEventListener("click", async () => {
  if (!confirm(`Видалити таблицю '${state.tableName}'?`)) return;
  const answer = await run(() => api.dropTable(state.db, state.tableName));
  if (answer) setStatus(answer.detail);
  await refreshTables();
});

// ---------- рядки ----------

$("data-table").addEventListener("click", (event) => {
  const tr = event.target.closest("tbody tr");
  if (!tr) return;
  state.selectedRow = tr.sectionRowIndex;
  for (const row of tr.parentElement.rows) row.classList.toggle("selected", row === tr);
  updateButtons();
});

$("add-row-btn").addEventListener("click", () => {
  const fields = $("add-row-fields");
  fields.innerHTML = "";
  for (const column of state.table.columns) {
    const label = document.createElement("label");
    const caption = document.createElement("span");
    caption.textContent = `${column.name} (${column.type}):`;
    const input = document.createElement("input");
    input.placeholder = state.hints[column.type] ?? "";
    label.append(caption, input);
    fields.appendChild(label);
  }
  openDialog($("add-row-dialog"));
});

$("add-row-ok").addEventListener("click", async () => {
  const dialog = $("add-row-dialog");
  const values = [...$("add-row-fields").querySelectorAll("input")].map((input) => input.value);
  if (await tryInDialog(dialog, () => api.addRow(state.db, state.table.name, values))) {
    dialog.close();
    setStatus("Рядок додано (на диск ще не збережено)");
    await loadTable();
  }
});

$("delete-row-btn").addEventListener("click", async () => {
  const answer = await run(() => api.deleteRow(state.db, state.table.name, state.selectedRow));
  if (answer) setStatus("Рядок видалено (на диск ще не збережено)");
  await loadTable();
});

// Редагування прямо в клітинці (подвійний клік)
$("data-table").addEventListener("dblclick", (event) => {
  const td = event.target.closest("tbody td");
  if (!td || td.cellIndex === 0 || td.querySelector("input")) return;  // колонку # не редагуємо

  const rowIndex = td.parentElement.sectionRowIndex;
  const columnIndex = td.cellIndex - 1;
  const oldValue = td.textContent;
  const input = document.createElement("input");
  input.className = "cell-edit";
  input.value = oldValue;
  td.textContent = "";
  td.appendChild(input);
  input.focus();
  input.select();

  let finished = false;
  const finish = async (save) => {
    if (finished) return;
    finished = true;
    if (!save || input.value === oldValue) {
      td.textContent = oldValue;
      return;
    }
    const values = state.table.rows[rowIndex].map(String);
    values[columnIndex] = input.value;
    const answer = await run(() => api.editRow(state.db, state.table.name, rowIndex, values));
    if (answer) setStatus("Рядок змінено (на диск ще не збережено)");
    await loadTable();  // при помилці повертається попереднє значення
  };
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") finish(true);
    if (e.key === "Escape") finish(false);
  });
  input.addEventListener("blur", () => finish(true));
});

// ---------- сполучення таблиць (JoinDialogUI) ----------

function selectCommonField() {
  const t1 = joinTables[$("join-table1").value];
  const t2 = joinTables[$("join-table2").value];
  const fieldSelect = $("join-field");
  fieldSelect.innerHTML = "";
  if (t1 && t2) {
    const names2 = new Set(t2.columns.map((c) => c.name));
    for (const column of t1.columns) {
      if (names2.has(column.name)) fieldSelect.add(new Option(column.name, column.name));
    }
  }
  $("join-run").disabled = fieldSelect.options.length === 0;
}

$("join-btn").addEventListener("click", async () => {
  const names = await run(() => api.listTables(state.db));
  if (!names) return;
  const tables = await run(() => Promise.all(names.map((n) => api.getTable(state.db, n))));
  if (!tables) return;
  joinTables = Object.fromEntries(tables.map((t) => [t.name, t]));

  for (const id of ["join-table1", "join-table2"]) {
    $(id).innerHTML = "";
    for (const name of names) $(id).add(new Option(name, name));
  }
  if (names.length > 1) $("join-table2").selectedIndex = 1;
  selectCommonField();
  $("join-result").innerHTML = "";
  $("join-save-name").value = "";
  openDialog($("join-dialog"));
});

$("join-table1").addEventListener("change", selectCommonField);
$("join-table2").addEventListener("change", selectCommonField);

$("join-run").addEventListener("click", async () => {
  const dialog = $("join-dialog");
  showDialogError(dialog, null);
  let result;
  const ok = await tryInDialog(dialog, async () => {
    result = await api.join(state.db, $("join-table1").value, $("join-table2").value, $("join-field").value);
  });
  if (ok) fillTable($("join-result"), result);
});

$("join-save").addEventListener("click", async () => {
  const dialog = $("join-dialog");
  const name = $("join-save-name").value;
  const ok = await tryInDialog(dialog, () =>
    api.join(state.db, $("join-table1").value, $("join-table2").value, $("join-field").value, name)
  );
  if (ok) {
    dialog.close();
    await refreshTables(name.trim());
    setStatus(`Результат збережено як таблицю '${name.trim()}' (на диск ще не збережено)`);
  }
});

// ---------- спільне для всіх вікон ----------

for (const button of document.querySelectorAll("dialog .cancel")) {
  button.addEventListener("click", () => button.closest("dialog").close());
}

// ---------- запуск ----------

async function init() {
  $("server-info").textContent = `сервер ${location.origin}`;
  try {
    state.types = await api.getTypes();
  } catch (error) {
    setStatus(`${error.message}. Переконайтесь, що сервер запущено (docker compose up).`, true);
    updateButtons();
    return;
  }
  state.hints = Object.fromEntries(state.types.map((t) => [t.name, t.hint]));
  await refreshDatabases();
}

init();