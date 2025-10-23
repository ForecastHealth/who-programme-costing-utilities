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
const tabsContainer = document.getElementById('category-tabs');
const metricTotalCostEl = document.getElementById('metric-total-cost');
const metricRecordCountEl = document.getElementById('metric-record-count');
const metricYearRangeEl = document.getElementById('metric-year-range');
const metricTopComponentEl = document.getElementById('metric-top-component');
const chartCanvas = document.getElementById('component-chart');

let lastCsv = '';
let tableHeaders = [];
let structuredRows = [];
let filteredRows = [];
let componentTotals = {};
let totalCost = 0;
let yearRange = { min: null, max: null };
let currentPage = 1;
let rowsPerPage = pageSizeSelect ? Number(pageSizeSelect.value) : 50;
let currentComponent = 'All';
let currentFilterTotalCost = 0;
let componentChart = null;
let tabButtons = [];
let lastRunConfig = null;

const setStatus = (message) => {
  if (statusEl) statusEl.textContent = message;
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
  if (countrySelect.querySelector(`[value="${country}"]`)) countrySelect.value = country;
  if (currencySelect.querySelector(`[value="${desired_currency}"]`)) currencySelect.value = desired_currency;
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

const normalizeRows = (parsed) => {
  tableHeaders = parsed[0].map((header) => header.trim());
  const rawRows = parsed.slice(1);

  structuredRows = rawRows
    .map((row) => {
      const entry = {};
      tableHeaders.forEach((header, idx) => {
        entry[header] = row[idx] ?? '';
      });

      const costCandidate = entry.cost ?? entry.Cost ?? entry.COST ?? '0';
      const numericCost = Number(String(costCandidate).replace(/,/g, ''));
      entry.__cost = Number.isFinite(numericCost) ? numericCost : 0;

      const componentCandidate = entry.component ?? entry.Component ?? entry.COMPONENT ?? 'Uncategorised';
      entry.__component = componentCandidate || 'Uncategorised';

      const yearCandidate = entry.year ?? entry.Year ?? entry.YEAR;
      const parsedYear = parseInt(yearCandidate, 10);
      entry.__year = Number.isNaN(parsedYear) ? null : parsedYear;

      return entry;
    })
    .filter((row) => tableHeaders.some((header) => row[header] !== ''));

  filteredRows = [...structuredRows];
};

const resetResults = () => {
  tableHeaders = [];
  structuredRows = [];
  filteredRows = [];
  componentTotals = {};
  totalCost = 0;
  yearRange = { min: null, max: null };
  currentPage = 1;
  currentComponent = 'All';
  currentFilterTotalCost = 0;
  if (componentChart) {
    componentChart.destroy();
    componentChart = null;
  }
  if (tabsContainer) {
    tabsContainer.innerHTML = '';
    tabsContainer.style.display = 'none';
  }
  tabButtons = [];
  summaryEl.textContent = 'No records returned.';
  tableHead.innerHTML = '';
  tableBody.innerHTML = '';
  if (paginationEl) paginationEl.hidden = true;
  resultsSection.hidden = true;
  updateMetrics();
};

const formatNumber = (value, maximumFractionDigits = 2) =>
  new Intl.NumberFormat('en-US', { maximumFractionDigits }).format(value);

const getCurrencyCode = () => (lastRunConfig?.desired_currency || form.desired_currency.value || 'USD');

const formatCurrency = (code, value) => `${code} ${formatNumber(value, 2)}`;

const computeAggregations = () => {
  totalCost = 0;
  componentTotals = {};
  yearRange = { min: Number.POSITIVE_INFINITY, max: Number.NEGATIVE_INFINITY };

  structuredRows.forEach((row) => {
    totalCost += row.__cost;
    const component = row.__component;
    componentTotals[component] = (componentTotals[component] || 0) + row.__cost;

    if (row.__year !== null) {
      yearRange.min = Math.min(yearRange.min, row.__year);
      yearRange.max = Math.max(yearRange.max, row.__year);
    }
  });

  if (!Number.isFinite(yearRange.min) || !Number.isFinite(yearRange.max)) {
    yearRange = { min: null, max: null };
  }
};

const updateMetrics = () => {
  if (!metricTotalCostEl) return;
  const currency = getCurrencyCode();

  if (structuredRows.length === 0) {
    metricTotalCostEl.textContent = '--';
    metricRecordCountEl.textContent = '--';
    metricYearRangeEl.textContent = '--';
    metricTopComponentEl.textContent = '--';
    return;
  }

  metricTotalCostEl.textContent = formatCurrency(currency, totalCost);
  metricRecordCountEl.textContent = formatNumber(structuredRows.length, 0);
  metricYearRangeEl.textContent = yearRange.min === null ? '--' : `${yearRange.min} – ${yearRange.max}`;

  const sortedComponents = Object.entries(componentTotals).sort((a, b) => b[1] - a[1]);
  if (sortedComponents.length) {
    const [component, value] = sortedComponents[0];
    const share = totalCost > 0 ? (value / totalCost) * 100 : 0;
    metricTopComponentEl.textContent = `${component} • ${formatCurrency(currency, value)} (${formatNumber(share, 1)}%)`;
  } else {
    metricTopComponentEl.textContent = '--';
  }
};

const buildChart = () => {
  if (!chartCanvas) return;
  if (componentChart) {
    componentChart.destroy();
    componentChart = null;
  }

  const entries = Object.entries(componentTotals).sort((a, b) => b[1] - a[1]);
  if (!entries.length || totalCost === 0) {
    chartCanvas.style.opacity = 0.3;
    const ctx = chartCanvas.getContext('2d');
    ctx.clearRect(0, 0, chartCanvas.width, chartCanvas.height);
    return;
  }
  chartCanvas.style.opacity = 1;
  chartCanvas.height = 260;

  const MAX_SLICES = 6;
  const labels = [];
  const values = [];
  let otherTotal = 0;

  entries.forEach(([label, value], index) => {
    if (index < MAX_SLICES) {
      labels.push(label);
      values.push(value);
    } else {
      otherTotal += value;
    }
  });
  if (otherTotal > 0) {
    labels.push('Other');
    values.push(otherTotal);
  }

  const palette = ['#2563eb', '#f97316', '#0ea5e9', '#22c55e', '#8b5cf6', '#ec4899', '#facc15'];
  const datasetColors = labels.map((_, idx) => palette[idx % palette.length]);
  const currency = getCurrencyCode();

  componentChart = new Chart(chartCanvas, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: datasetColors,
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom' },
        tooltip: {
          callbacks: {
            label: (context) => {
              const label = context.label || 'Unknown';
              const value = context.parsed || 0;
              const share = totalCost > 0 ? (value / totalCost) * 100 : 0;
              return `${label}: ${formatCurrency(currency, value)} (${formatNumber(share, 1)}%)`;
            },
          },
        },
      },
    },
  });
};

const setActiveTab = (component) => {
  tabButtons.forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.component === component);
  });
};

const buildTabs = () => {
  if (!tabsContainer) return;
  tabsContainer.innerHTML = '';
  tabButtons = [];

  const entries = Object.entries(componentTotals).sort((a, b) => b[1] - a[1]);
  if (!entries.length) {
    tabsContainer.style.display = 'none';
    return;
  }
  tabsContainer.style.display = 'flex';

  const createTabButton = (label, component) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = label;
    button.className = 'tab-button';
    button.dataset.component = component;
    button.addEventListener('click', () => applyFilter(component));
    tabsContainer.appendChild(button);
    tabButtons.push(button);
  };

  createTabButton('All', 'All');
  entries.forEach(([component]) => createTabButton(component, component));
};

const applyFilter = (component) => {
  currentComponent = component;
  if (component === 'All') {
    filteredRows = [...structuredRows];
    currentFilterTotalCost = totalCost;
  } else {
    filteredRows = structuredRows.filter((row) => row.__component === component);
    currentFilterTotalCost = componentTotals[component] || 0;
  }
  currentPage = 1;
  setActiveTab(component);
  renderTable();
};

const renderTable = () => {
  if (!tableHeaders.length) {
    summaryEl.textContent = 'No records to display.';
    tableHead.innerHTML = '';
    tableBody.innerHTML = '';
    if (paginationEl) paginationEl.hidden = true;
    return;
  }

  tableHead.innerHTML = `<tr>${tableHeaders.map((header) => `<th>${escapeHtml(header)}</th>`).join('')}</tr>`;

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / rowsPerPage));
  if (currentPage > totalPages) currentPage = totalPages;
  const startIndex = (currentPage - 1) * rowsPerPage;
  const pageRows = filteredRows.slice(startIndex, startIndex + rowsPerPage);

  tableBody.innerHTML = pageRows
    .map(
      (row) =>
        `<tr>${tableHeaders
          .map((header) => `<td>${escapeHtml(row[header] ?? '')}</td>`)
          .join('')}</tr>`
    )
    .join('');

  const currency = getCurrencyCode();
  const componentLabel = currentComponent === 'All' ? 'All components' : currentComponent;
  summaryEl.textContent = `${componentLabel} • ${filteredRows.length.toLocaleString()} records • Total cost ${formatCurrency(
    currency,
    currentFilterTotalCost,
  )}. Showing ${pageRows.length.toLocaleString()} records (page ${currentPage} of ${totalPages}).`;

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
    if (!response.ok) throw new Error(`Failed to load metadata (${response.status})`);
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
    desired_year: Number(form.desired_year.value),
  };

  runButton.disabled = true;
  setStatus('Running costing request…');
  resultsSection.hidden = true;

  try {
    const response = await fetch('/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) throw new Error(`Costing failed (${response.status})`);

    const csvText = await response.text();
    lastCsv = csvText;
    const parsed = parseCsv(csvText);
    if (parsed.length === 0) {
      resetResults();
      setStatus('No records returned.');
      return;
    }

    lastRunConfig = payload;
    normalizeRows(parsed);
    computeAggregations();
    updateMetrics();
    buildChart();
    buildTabs();
    applyFilter('All');
    resultsSection.hidden = false;
    setStatus('Success. Results ready.');
  } catch (error) {
    console.error(error);
    resetResults();
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
    const totalPages = Math.max(1, Math.ceil(filteredRows.length / rowsPerPage));
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
