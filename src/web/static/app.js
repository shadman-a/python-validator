function setupIssueFilters() {
  const table = document.getElementById('issues-table');
  if (!table) return;
  const searchInput = document.getElementById('issue-search');
  const severitySelect = document.getElementById('issue-severity');
  const typeSelect = document.getElementById('issue-type');
  const rows = Array.from(table.querySelectorAll('tbody tr'));
  const types = new Set();
  rows.forEach(row => {
    const type = row.children[2]?.innerText || '';
    if (type) types.add(type);
  });
  types.forEach(type => {
    const opt = document.createElement('option');
    opt.value = type;
    opt.textContent = type;
    typeSelect.appendChild(opt);
  });

  function applyFilters() {
    const search = (searchInput.value || '').toLowerCase();
    const severity = severitySelect.value;
    const type = typeSelect.value;
    rows.forEach(row => {
      const text = row.innerText.toLowerCase();
      const rowSeverity = row.children[1]?.innerText || '';
      const rowType = row.children[2]?.innerText || '';
      const matches = (!search || text.includes(search)) &&
        (!severity || rowSeverity === severity) &&
        (!type || rowType === type);
      row.style.display = matches ? '' : 'none';
    });
  }

  searchInput.addEventListener('input', applyFilters);
  severitySelect.addEventListener('change', applyFilters);
  typeSelect.addEventListener('change', applyFilters);
}

function setupMappingTable() {
  const table = document.querySelector('.mapping-table');
  if (!table) return;
  const tbody = table.querySelector('tbody');
  const tableWrapper = table.closest('.form-section');
  const rowCountLabel = tableWrapper?.querySelector('[data-row-count]');

  function updateRowNumbers() {
    const rows = Array.from(tbody.querySelectorAll('tr'));
    rows.forEach((row, index) => {
      const cell = row.querySelector('.row-index');
      if (cell) {
        cell.textContent = String(index + 1);
      }
    });
    if (rowCountLabel) {
      rowCountLabel.textContent = rows.length ? `${rows.length} fields` : 'No fields yet';
    }
  }

  document.querySelectorAll('[data-action="add-row"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td class="row-index"></td>
        <td><input type="text" name="field_name" /></td>
        <td><input type="text" name="left_column" /></td>
        <td><input type="text" name="right_column" /></td>
        <td><input type="checkbox" name="skip" value="custom" /></td>
        <td><input type="text" name="normalize" placeholder="trim, upper" /></td>
        <td><textarea name="value_map"></textarea></td>
        <td class="confidence"></td>
        <td class="reason"></td>
        <td><button type="button" data-action="remove-row">Remove</button></td>
      `;
      tbody.appendChild(row);
      attachRemove(row);
      updateRowNumbers();
    });
  });

  function attachRemove(row) {
    const btn = row.querySelector('[data-action="remove-row"]');
    if (btn) {
      btn.addEventListener('click', () => {
        row.remove();
        updateRowNumbers();
      });
    }
  }

  tbody.querySelectorAll('tr').forEach(attachRemove);
  updateRowNumbers();

  const autoBtn = document.querySelector('[data-action="auto-guess"]');
  if (autoBtn) {
    autoBtn.addEventListener('click', async () => {
      const leftPath = autoBtn.getAttribute('data-left');
      const rightPath = autoBtn.getAttribute('data-right');
      const response = await fetch(`/mapping/guess?left_path=${encodeURIComponent(leftPath)}&right_path=${encodeURIComponent(rightPath)}`);
      if (!response.ok) return;
      const data = await response.json();
      data.forEach(item => {
        const row = tbody.querySelector(`tr[data-left="${item.left_column}"]`);
        if (!row) return;
        const rightSelect = row.querySelector('select[name="right_column"]');
        if (rightSelect) {
          rightSelect.value = item.best_right;
        }
        row.querySelector('.confidence').textContent = item.confidence;
        row.querySelector('.reason').textContent = item.reasons.join(', ');
      });
    });
  }
}

function setupCopyYaml() {
  const btn = document.querySelector('[data-action="copy-yaml"]');
  if (!btn) return;
  btn.addEventListener('click', () => {
    const textarea = document.querySelector('.yaml-view');
    if (!textarea) return;
    navigator.clipboard.writeText(textarea.value);
  });
}

function setupNewRunForm() {
  const form = document.querySelector('[data-new-run]');
  if (!form) return;

  const modeInputs = Array.from(form.querySelectorAll('input[name="mode"]'));
  const mappingInputs = Array.from(form.querySelectorAll('input[name="mapping_choice"]'));
  const compareOnlyEls = Array.from(form.querySelectorAll('[data-compare-only]'));
  const mappingSelectWrapper = form.querySelector('[data-mapping-select]');
  const mappingSelect = form.querySelector('select[name="mapping_file"]');

  function getCheckedValue(inputs) {
    return (inputs.find(input => input.checked) || {}).value;
  }

  function toggleCompareMode() {
    const mode = getCheckedValue(modeInputs);
    const showCompare = mode === 'compare';
    compareOnlyEls.forEach(el => {
      el.style.display = showCompare ? '' : 'none';
    });
    if (!showCompare && mappingSelect) {
      mappingSelect.value = '';
    }
  }

  function toggleMappingSelect() {
    const choice = getCheckedValue(mappingInputs);
    const showSelect = choice === 'existing';
    if (mappingSelectWrapper) {
      mappingSelectWrapper.style.display = showSelect ? '' : 'none';
    }
    if (!showSelect && mappingSelect) {
      mappingSelect.value = '';
    }
  }

  modeInputs.forEach(input => input.addEventListener('change', () => {
    toggleCompareMode();
    toggleMappingSelect();
  }));
  mappingInputs.forEach(input => input.addEventListener('change', toggleMappingSelect));

  toggleCompareMode();
  toggleMappingSelect();

  form.querySelectorAll('[data-dropzone]').forEach(dropzone => {
    const input = dropzone.querySelector('input[type="file"]');
    const nameLabel = dropzone.querySelector('[data-file-name]');
    const button = dropzone.querySelector('[data-dropzone-button]');

    function updateNameLabel() {
      if (!nameLabel) return;
      const files = input.files;
      nameLabel.textContent = files && files.length ? files[0].name : 'No file selected';
    }

    function openPicker() {
      if (input) input.click();
    }

    dropzone.addEventListener('click', event => {
      if (event.target.closest('[data-dropzone-button]')) return;
      openPicker();
    });

    if (button) {
      button.addEventListener('click', openPicker);
    }

    dropzone.addEventListener('dragover', event => {
      event.preventDefault();
      dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
      dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', event => {
      event.preventDefault();
      dropzone.classList.remove('dragover');
      const files = event.dataTransfer.files;
      if (!files || !files.length || !input) return;
      input.files = files;
      updateNameLabel();
    });

    if (input) {
      input.addEventListener('change', updateNameLabel);
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  setupIssueFilters();
  setupMappingTable();
  setupCopyYaml();
  setupNewRunForm();
});
