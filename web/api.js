class ApiError extends Error {}

// Кодує назву для адреси (щоб українські літери і спецсимволи не ламали URL)
const part = (name) => encodeURIComponent(name);

class ApiClient {
  constructor(baseUrl = "") {
    this.baseUrl = baseUrl; // порожньо – запити йдуть на той самий сервер, що віддав сторінку
  }

  async request(method, path, body) {
    const options = { method, headers: {} };
    if (body !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }

    let response;
    try {
      response = await fetch(this.baseUrl + path, options);
    } catch {
      throw new ApiError("Не вдалося підключитися до сервера");
    }

    let data = null;
    try {
      data = await response.json();
    } catch {
      // відповідь не у форматі JSON
    }

    if (!response.ok) {
      const detail = data && typeof data.detail === "string" ? data.detail : "Некоректний запит";
      throw new ApiError(detail);
    }
    return data;
  }

  // ---------- типи ----------
  getTypes() { return this.request("GET", "/types"); }

  // ---------- бази ----------
  listDatabases() { return this.request("GET", "/databases"); }
  createDatabase(name) { return this.request("POST", "/databases", { name }); }
  saveDatabase(db) { return this.request("POST", `/databases/${part(db)}/save`); }
  loadDatabase(db) { return this.request("POST", `/databases/${part(db)}/load`); }

  // ---------- таблиці ----------
  listTables(db) { return this.request("GET", `/databases/${part(db)}/tables`); }
  createTable(db, name, columns) {
    return this.request("POST", `/databases/${part(db)}/tables`, { name, columns });
  }
  getTable(db, table) { return this.request("GET", `/databases/${part(db)}/tables/${part(table)}`); }
  dropTable(db, table) { return this.request("DELETE", `/databases/${part(db)}/tables/${part(table)}`); }

  // ---------- рядки ----------
  addRow(db, table, values) {
    return this.request("POST", `/databases/${part(db)}/tables/${part(table)}/rows`, { values });
  }
  editRow(db, table, index, values) {
    return this.request("PUT", `/databases/${part(db)}/tables/${part(table)}/rows/${index}`, { values });
  }
  deleteRow(db, table, index) {
    return this.request("DELETE", `/databases/${part(db)}/tables/${part(table)}/rows/${index}`);
  }

  // ---------- join ----------
  join(db, table1, table2, field, saveAs = null) {
    return this.request("POST", `/databases/${part(db)}/join`, {
      table1, table2, field, save_as: saveAs,
    });
  }
}

const api = new ApiClient();