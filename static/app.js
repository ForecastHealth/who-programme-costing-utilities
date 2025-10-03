const form = document.getElementById('config-form');
const countrySelect = document.getElementById('country');
const currencySelect = document.getElementById('desired_currency');
const statusEl = document.getElementById('status');
const runButton = document.getElementById('run-button');
const resultsSection = document.getElementById('results');
const summaryEl = document.getElementById('summary');
const tableHead = document.querySelector('#results-table thead');
const tableBody = document.querySelector('#results-table tbody');
const downloadBtn = document.getElementById('download-btn');
const paginationEl = document.getElementById('pagination');
const prevPageBtn = document.getElementById('prev-page');
const nextPageBtn = document.getElementById('next-page');
const pageInfo = document.getElementById('page-info');
const pageSizeSelect = document.getElementById('page-size');

let lastCsv = '';
let tableHeaders = [];
let tableRows = [];
let currentPage = 1;
let rowsPerPage = pageSizeSelect ? Number(pageSizeSelect.value) : 50;

const setStatus = (message) => {
  statusEl.textContent = message;
};

const populateSelect = (select, options, selectedValue) => {
  select.innerHTML = '';
  options.forEach((value) => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    if (value === selectedValue) {
      option.selected = true;
    }
    select.appendChild(option);
  });
};

const applyDefaults = (defaults) => {
  const { country, start_year, end_year, discount_rate, desired_currency, desired_year } = defaults;
  form.start_year.value = start_year;
  form.end_year.value = end_year;
  form.discount_rate.value = discount_rate;
  form.desired_year.value = desired_year;
  if (countrySelect.querySelector(`[value="${country}"]`)) {
    countrySelect.value = country;
  }
  if (currencySelect.querySelector(`[value="${desired_currency}"]`)) {
    currencySelect.value = desired_currency;
  }
};

const escapeHtml = (value) =>
  String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

const parseCsv = (text) => {
  const rows = [];
  let currentField = '';
  let currentRow = [];
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];

    if (char === '"') {
      if (inQuotes && text[i + 1] === '"') {
        currentField += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      currentRow.push(currentField);
      currentField = '';
    } else if ((char === '\n' || char === '\r') && !inQuotes) {
      if (char === '\r' && text[i + 1] === '\n') i += 1;
      currentRow.push(currentField);
      rows.push(currentRow);
      currentRow = [];
      currentField = '';
    } else {
      currentField += char;
    }
  }

  if (currentField.length > 0 || currentRow.length > 0) {
    currentRow.push(currentField);
    rows.push(currentRow);
  }

  return rows.filter((row) => row.some((cell) => cell !== ''));
};

const renderTable = () => {
  if (!tableHeaders.length) {
    tableHead.innerHTML = '';
    tableBody.innerHTML = '';
    summaryEl.textContent = 'No records to display.';
    if (paginationEl) paginationEl.hidden = true;
    return;
  }

  tableHead.innerHTML = `<tr>${tableHeaders.map((h) => `<th>${escapeHtml(h)}</th>`).join('')}</tr>`;

  const totalPages = Math.max(1, Math.ceil(tableRows.length / rowsPerPage));
  if (currentPage > totalPages) currentPage = totalPages;
  const startIndex = (currentPage - 1) * rowsPerPage;
  const pageRows = tableRows.slice(startIndex, startIndex + rowsPerPage);

  tableBody.innerHTML = pageRows
    .map(
      (row) =>
        `<tr>${row
          .map((cell) => `<td>${escapeHtml(cell)}</td>`)
          .join('')}</tr>`
    )
    .join('');

  summaryEl.textContent = `Returned ${tableRows.length.toLocaleString()} records. Showing ${pageRows.length.toLocaleString()} records (page ${currentPage} of ${totalPages}).`;

  if (paginationEl) {
    paginationEl.hidden = totalPages <= 1;
    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    prevPageBtn.disabled = currentPage === 1;
    nextPageBtn.disabled = currentPage === totalPages;
  }
};

const downloadCsv = () => {
  if (!lastCsv) return;
  const blob = new Blob([lastCsv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'programme_costing_output.csv';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

downloadBtn.addEventListener('click', downloadCsv);

const loadMetadata = async () => {
  try {
    const response = await fetch('/meta/options');
    if (!response.ok) {
      throw new Error(`Failed to load metadata (${response.status})`);
    }
    const meta = await response.json();
    populateSelect(countrySelect, meta.countries, meta.defaults.country);
    populateSelect(currencySelect, meta.currencies, meta.defaults.desired_currency);
    applyDefaults(meta.defaults);
    setStatus('Ready to run. Defaults loaded.');
  } catch (error) {
    console.error(error);
    setStatus(`Error loading configuration: ${error.message}`);
  }
};

form.addEventListener('submit', async (event) => {
  event.preventDefault();

  const payload = {
    country: form.country.value,
    start_year: Number(form.start_year.value),
    end_year: Number(form.end_year.value),
    discount_rate: Number(form.discount_rate.value),
    desired_currency: form.desired_currency.value,
    desired_year: Number(form.desired_year.value)
  };

  runButton.disabled = true;
  setStatus('Running costing request…');
  resultsSection.hidden = true;

  try {
    const response = await fetch('/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`Costing failed (${response.status})`);
    }

    const csvText = await response.text();
    lastCsv = csvText;
    const parsed = parseCsv(csvText);
    if (parsed.length === 0) {
      tableHeaders = [];
      tableRows = [];
      summaryEl.textContent = 'No records returned.';
    } else {
      [tableHeaders, ...tableRows] = parsed;
    }
    currentPage = 1;
    renderTable();
    resultsSection.hidden = tableRows.length === 0;
    setStatus('Success. Results ready.');
  } catch (error) {
    console.error(error);
    setStatus(`Error: ${error.message}`);
  } finally {
    runButton.disabled = false;
  }
});

if (prevPageBtn && nextPageBtn) {
  prevPageBtn.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage -= 1;
      renderTable();
    }
  });

  nextPageBtn.addEventListener('click', () => {
    const totalPages = Math.max(1, Math.ceil(tableRows.length / rowsPerPage));
    if (currentPage < totalPages) {
      currentPage += 1;
      renderTable();
    }
  });
}

if (pageSizeSelect) {
  pageSizeSelect.addEventListener('change', () => {
    rowsPerPage = Number(pageSizeSelect.value);
    currentPage = 1;
    renderTable();
  });
}

loadMetadata();
