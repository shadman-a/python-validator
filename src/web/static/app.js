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

  function updateConfidenceCell(cell, value) {
    if (!cell) return;
    const numeric = Number(value);
    if (Number.isFinite(numeric)) {
      cell.textContent = `${numeric}%`;
      cell.dataset.confidence = String(numeric);
      cell.dataset.level = numeric >= 80 ? 'high' : numeric >= 55 ? 'med' : 'low';
    } else {
      cell.textContent = '';
      cell.dataset.confidence = '';
      cell.dataset.level = '';
    }
  }

  function updateRowNumbers() {
    const rows = Array.from(tbody.querySelectorAll('tr'));
    rows.forEach((row, index) => {
      const cell = row.querySelector('.row-index');
      if (cell) {
        cell.textContent = String(index + 1);
      }
      const skipInput = row.querySelector('input[name="skip"]');
      if (skipInput) {
        skipInput.value = String(index);
      }
    });
    if (rowCountLabel) {
      rowCountLabel.textContent = rows.length ? `${rows.length} fields` : 'No fields yet';
    }
  }

  document.querySelectorAll('[data-action="add-row"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const row = document.createElement('tr');
      const mode = table?.dataset?.mappingMode || 'full';
      if (mode === 'columns') {
        row.innerHTML = `
          <td class="row-index"></td>
          <td><input type="text" name="field_name" /></td>
          <td><input type="text" name="left_column" /></td>
          <td><input type="text" name="right_column" /></td>
          <td><input type="checkbox" name="skip" /></td>
          <td class="confidence"></td>
          <td class="reason"></td>
          <td>
            <button type="button" data-action="remove-row">Remove</button>
            <input type="hidden" name="normalize" value="" />
            <input type="hidden" name="value_map" value="" />
          </td>
        `;
      } else {
        row.innerHTML = `
          <td class="row-index"></td>
          <td><input type="text" name="field_name" /></td>
          <td><input type="text" name="left_column" /></td>
          <td><input type="text" name="right_column" /></td>
          <td><input type="checkbox" name="skip" /></td>
          <td><input type="text" name="normalize" placeholder="trim, upper" /></td>
          <td><textarea name="value_map"></textarea></td>
          <td class="confidence"></td>
          <td class="reason"></td>
          <td><button type="button" data-action="remove-row">Remove</button></td>
        `;
      }
      tbody.appendChild(row);
      attachRemove(row);
      updateConfidenceCell(row.querySelector('.confidence'), '');
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
  tbody.querySelectorAll('.confidence').forEach(cell => {
    if (!cell.dataset.confidence && cell.textContent.trim()) {
      updateConfidenceCell(cell, cell.textContent.replace('%', '').trim());
    }
  });
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
        updateConfidenceCell(row.querySelector('.confidence'), item.confidence);
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
  const mappingPreview = form.querySelector('[data-mapping-preview]');
  const recList = form.querySelector('[data-rec-list]');
  const recEmpty = form.querySelector('[data-rec-empty]');
  const recStatus = form.querySelector('[data-rec-status]');
  const useTopRec = form.querySelector('[data-action="use-top-rec"]');
  const submitLabel = form.querySelector('[data-submit-label]');
  const stepEls = Array.from(form.querySelectorAll('[data-step]'));
  const stepLabels = Array.from(document.querySelectorAll('[data-step-label]'));
  const progressBar = document.querySelector('[data-progress-bar]');
  const leftPathInput = form.querySelector('input[name="left_path"]');
  const rightPathInput = form.querySelector('input[name="right_path"]');
  const leftUploadInput = form.querySelector('input[name="left_upload"]');
  const rightUploadInput = form.querySelector('input[name="right_upload"]');
  const summaryMode = form.querySelector('[data-summary-mode]');
  const summaryRule = form.querySelector('[data-summary-rule]');
  const summaryLeft = form.querySelector('[data-summary-left]');
  const summaryRight = form.querySelector('[data-summary-right]');
  const summaryRightWrap = form.querySelector('[data-summary-right-wrapper]');
  const summaryMapping = form.querySelector('[data-summary-mapping]');
  const summaryMappingWrap = form.querySelector('[data-summary-mapping-wrapper]');
  const ruleSelect = form.querySelector('select[name="rule_file"]');
  let currentStepIndex = 0;
  let recToken = 0;
  const mappingSummaries = (() => {
    const raw = document.getElementById('mapping-summaries')?.textContent || '[]';
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
      return [];
    }
  })();

  function getCheckedValue(inputs) {
    return (inputs.find(input => input.checked) || {}).value;
  }

  function getMode() {
    const checked = getCheckedValue(modeInputs);
    if (checked) return checked;
    const hidden = modeInputs.find(input => input.type === 'hidden' && input.value);
    if (hidden) return hidden.value;
    return modeInputs.length ? (modeInputs[0].value || 'single') : 'compare';
  }

  function normalizeHeader(value) {
    return (value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  }

  function parseCsvHeader(text) {
    const line = (text || '').split(/\r?\n/)[0] || '';
    const fields = [];
    let current = '';
    let inQuotes = false;
    for (let i = 0; i < line.length; i += 1) {
      const ch = line[i];
      if (ch === '"') {
        if (inQuotes && line[i + 1] === '"') {
          current += '"';
          i += 1;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (ch === ',' && !inQuotes) {
        fields.push(current.trim());
        current = '';
      } else {
        current += ch;
      }
    }
    if (current.length || line.endsWith(',')) {
      fields.push(current.trim());
    }
    return fields.filter(Boolean);
  }

  function readColumnsFromFile(file) {
    if (!file) return Promise.resolve([]);
    const reader = new FileReader();
    const blob = file.slice(0, 65536);
    return new Promise(resolve => {
      reader.onload = () => {
        resolve(parseCsvHeader(reader.result || ''));
      };
      reader.onerror = () => resolve([]);
      reader.readAsText(blob);
    });
  }

  async function fetchColumnsFromPath(leftPath, rightPath) {
    const params = new URLSearchParams();
    if (leftPath) params.append('left_path', leftPath);
    if (rightPath) params.append('right_path', rightPath);
    if (!params.toString()) return { leftColumns: [], rightColumns: [] };
    const response = await fetch(`/files/columns?${params.toString()}`);
    if (!response.ok) return { leftColumns: [], rightColumns: [] };
    const payload = await response.json();
    return {
      leftColumns: Array.isArray(payload.left_columns) ? payload.left_columns : [],
      rightColumns: Array.isArray(payload.right_columns) ? payload.right_columns : [],
    };
  }

  function scoreMapping(mapping, leftColumns, rightColumns) {
    const leftSet = new Set(leftColumns.map(normalizeHeader));
    const rightSet = new Set(rightColumns.map(normalizeHeader));
    const leftTargets = Array.from(new Set((mapping.left_columns || []).filter(Boolean)));
    const rightTargets = Array.from(new Set((mapping.right_columns || []).filter(Boolean)));
    const leftKey = mapping.left_key || '';
    const rightKey = mapping.right_key || '';
    if (leftKey) leftTargets.push(leftKey);
    if (rightKey) rightTargets.push(rightKey);

    const countMatches = (targets, pool) => {
      let matches = 0;
      targets.forEach(target => {
        if (pool.has(normalizeHeader(target))) {
          matches += 1;
        }
      });
      return { matches, total: targets.length };
    };

    const leftScore = countMatches(leftTargets, leftSet);
    const rightScore = countMatches(rightTargets, rightSet);
    const total = leftScore.total + rightScore.total;
    const matches = leftScore.matches + rightScore.matches;
    const score = total ? Math.round((matches / total) * 100) : 0;
    const reasons = [];
    if (leftScore.total) reasons.push(`Left ${leftScore.matches}/${leftScore.total}`);
    if (rightScore.total) reasons.push(`Right ${rightScore.matches}/${rightScore.total}`);
    if (leftKey || rightKey) {
      const keyMatches = (leftKey && leftSet.has(normalizeHeader(leftKey)) ? 1 : 0) +
        (rightKey && rightSet.has(normalizeHeader(rightKey)) ? 1 : 0);
      const keyTotal = (leftKey ? 1 : 0) + (rightKey ? 1 : 0);
      reasons.push(`Keys ${keyMatches}/${keyTotal}`);
    }
    return {
      score,
      reasons,
      leftScore,
      rightScore,
    };
  }

  function buildRecommendations(leftColumns, rightColumns) {
    return mappingSummaries
      .map(summary => {
        const scored = scoreMapping(summary, leftColumns, rightColumns);
        return {
          name: summary.name,
          fieldCount: summary.field_count || 0,
          score: scored.score,
          reasons: scored.reasons,
          leftScore: scored.leftScore,
          rightScore: scored.rightScore,
        };
      })
      .filter(item => item.score > 0)
      .sort((a, b) => b.score - a.score);
  }

  function updateSubmitLabel() {
    if (!submitLabel) return;
    const mode = getMode();
    if (mode === 'compare') {
      const choice = getCheckedValue(mappingInputs);
      if (choice === 'create') {
        submitLabel.textContent = 'Continue to mapping builder';
      } else {
        submitLabel.textContent = 'Start run';
      }
    } else {
      submitLabel.textContent = 'Start run';
    }
  }

  function updateSummary() {
    const mode = getMode();
    if (summaryMode) {
      summaryMode.textContent = mode === 'compare' ? 'Compare CSVs' : 'Single CSV';
    }
    if (summaryRule) {
      summaryRule.textContent = form.querySelector('select[name="rule_file"]')?.value || '--';
    }
    const leftFileName = leftUploadInput?.files?.[0]?.name;
    const rightFileName = rightUploadInput?.files?.[0]?.name;
    if (summaryLeft) {
      summaryLeft.textContent = leftFileName || leftPathInput?.value || '--';
    }
    if (summaryRight) {
      summaryRight.textContent = rightFileName || rightPathInput?.value || '--';
    }
    if (summaryRightWrap) {
      summaryRightWrap.style.display = mode === 'compare' ? '' : 'none';
    }
    if (summaryMappingWrap) {
      summaryMappingWrap.style.display = mode === 'compare' ? '' : 'none';
    }
    if (summaryMapping) {
      if (mode !== 'compare') {
        summaryMapping.textContent = 'Not needed';
      } else {
        const choice = getCheckedValue(mappingInputs) || 'create';
        if (choice === 'create') {
          summaryMapping.textContent = 'Create new mapping';
        } else {
          summaryMapping.textContent = mappingSelect?.value || 'Select a mapping';
        }
      }
    }
  }

  function updateMappingPreview() {
    if (!mappingPreview) return;
    const selected = mappingSelect?.value;
    if (!selected) {
      mappingPreview.innerHTML = '<p class="muted">Pick a mapping to preview keys and coverage.</p>';
      return;
    }
    const summary = mappingSummaries.find(item => item.name === selected);
    if (!summary) {
      mappingPreview.innerHTML = '<p class="muted">Mapping details unavailable.</p>';
      return;
    }
    mappingPreview.innerHTML = `
      <div class="preview-row"><strong>Fields:</strong> ${summary.field_count || 0}</div>
      <div class="preview-row"><strong>Left key:</strong> ${summary.left_key || '-'}</div>
      <div class="preview-row"><strong>Right key:</strong> ${summary.right_key || '-'}</div>
    `;
  }

  function renderRecommendations(recs) {
    if (!recList || !recEmpty || !recStatus) return;
    recList.innerHTML = '';
    if (!mappingSummaries.length) {
      recStatus.textContent = 'No saved mappings';
      recEmpty.textContent = 'Create a mapping to see recommendations.';
      recEmpty.style.display = '';
      if (useTopRec) useTopRec.disabled = true;
      return;
    }
    if (!recs.length) {
      recStatus.textContent = 'No matches yet';
      recEmpty.style.display = '';
      if (useTopRec) useTopRec.disabled = true;
      return;
    }
    recEmpty.style.display = 'none';
    recStatus.textContent = `${recs.length} match${recs.length === 1 ? '' : 'es'} found`;
    if (useTopRec) useTopRec.disabled = false;
    recs.slice(0, 3).forEach(rec => {
      const card = document.createElement('div');
      card.className = 'rec-card';
      card.innerHTML = `
        <div class="rec-title">
          <strong>${rec.name}</strong>
          <span class="chip">${rec.score}% match</span>
        </div>
        <div class="rec-bar"><span style="width: ${rec.score}%"></span></div>
        <p class="muted">${rec.reasons.join(' | ')}</p>
        <button class="link-button" type="button" data-rec-select>Use this mapping</button>
      `;
      card.querySelector('[data-rec-select]')?.addEventListener('click', () => {
        if (!mappingSelect) return;
        const existingChoice = mappingInputs.find(input => input.value === 'existing');
        if (existingChoice) existingChoice.checked = true;
        mappingSelect.value = rec.name;
        toggleMappingSelect();
        updateMappingPreview();
        updateSummary();
      });
      recList.appendChild(card);
    });
  }

  async function refreshRecommendations() {
    if (getMode() !== 'compare') {
      return;
    }
    const token = recToken + 1;
    recToken = token;
    let leftColumns = [];
    let rightColumns = [];
    if (leftUploadInput?.files?.length) {
      leftColumns = await readColumnsFromFile(leftUploadInput.files[0]);
    }
    if (rightUploadInput?.files?.length) {
      rightColumns = await readColumnsFromFile(rightUploadInput.files[0]);
    }
    const leftPath = leftPathInput?.value?.trim();
    const rightPath = rightPathInput?.value?.trim();
    if ((leftPath && !leftColumns.length) || (rightPath && !rightColumns.length)) {
      const fetched = await fetchColumnsFromPath(leftPath, rightPath);
      if (!leftColumns.length) leftColumns = fetched.leftColumns || [];
      if (!rightColumns.length) rightColumns = fetched.rightColumns || [];
    }
    if (token !== recToken) return;
    if (!leftColumns.length || !rightColumns.length) {
      if (recList) recList.innerHTML = '';
      if (recStatus) recStatus.textContent = 'Waiting for files';
      if (recEmpty) {
        recEmpty.textContent = 'Upload or provide both CSVs to see recommendations.';
        recEmpty.style.display = '';
      }
      if (useTopRec) useTopRec.disabled = true;
      return;
    }
    const recs = buildRecommendations(leftColumns, rightColumns);
    renderRecommendations(recs);
    if (mappingSelect && getCheckedValue(mappingInputs) === 'existing' && !mappingSelect.value && recs[0]?.score >= 60) {
      mappingSelect.value = recs[0].name;
      updateMappingPreview();
      updateSummary();
    }
  }

  function toggleCompareMode() {
    const mode = getMode();
    const showCompare = mode === 'compare';
    compareOnlyEls.forEach(el => {
      el.style.display = showCompare ? '' : 'none';
    });
    if (!showCompare && mappingSelect) {
      mappingSelect.value = '';
    }
    updateSubmitLabel();
    updateSummary();
    syncSteps();
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
    updateSubmitLabel();
    updateSummary();
  }

  function getVisibleSteps() {
    const mode = getMode();
    return stepEls.filter(step => {
      if (step.dataset.compareOnly !== undefined) {
        return mode === 'compare';
      }
      return true;
    });
  }

  function syncSteps() {
    const visibleSteps = getVisibleSteps();
    if (!visibleSteps.length) return;
    if (currentStepIndex >= visibleSteps.length) {
      currentStepIndex = visibleSteps.length - 1;
    }
    stepEls.forEach(step => {
      step.classList.remove('is-active');
      step.style.display = 'none';
      step.setAttribute('aria-hidden', 'true');
    });
    const activeStep = visibleSteps[currentStepIndex];
    activeStep.classList.add('is-active');
    activeStep.style.display = '';
    activeStep.setAttribute('aria-hidden', 'false');
    const visibleIds = visibleSteps.map(step => step.dataset.step);
    stepLabels.forEach(label => {
      const stepId = label.getAttribute('data-step-id');
      const isVisible = visibleIds.includes(stepId);
      label.style.display = isVisible ? '' : 'none';
      if (!isVisible) return;
      const idx = visibleIds.indexOf(stepId);
      label.classList.toggle('is-active', idx === currentStepIndex);
      label.classList.toggle('is-complete', idx < currentStepIndex);
    });
    if (progressBar) {
      const percent = visibleSteps.length <= 1 ? 100 : Math.round((currentStepIndex / (visibleSteps.length - 1)) * 100);
      progressBar.style.width = `${percent}%`;
    }
  }

  function goToStep(offset) {
    const visibleSteps = getVisibleSteps();
    const nextIndex = Math.max(0, Math.min(currentStepIndex + offset, visibleSteps.length - 1));
    currentStepIndex = nextIndex;
    syncSteps();
    updateSummary();
  }

  modeInputs.forEach(input => input.addEventListener('change', () => {
    toggleCompareMode();
    refreshRecommendations();
  }));
  mappingInputs.forEach(input => input.addEventListener('change', () => {
    toggleMappingSelect();
    updateMappingPreview();
  }));
  if (mappingSelect) {
    mappingSelect.addEventListener('change', () => {
      updateMappingPreview();
      updateSummary();
    });
  }
  if (useTopRec) {
    useTopRec.addEventListener('click', () => {
      const cards = recList?.querySelectorAll('.rec-card');
      if (!cards || !cards.length || !mappingSelect) return;
      const top = cards[0];
      const name = top.querySelector('strong')?.textContent;
      if (!name) return;
      const existingChoice = mappingInputs.find(input => input.value === 'existing');
      if (existingChoice) existingChoice.checked = true;
      mappingSelect.value = name;
      toggleMappingSelect();
      updateMappingPreview();
      updateSummary();
    });
  }

  form.querySelectorAll('[data-step-next]').forEach(button => {
    button.addEventListener('click', () => goToStep(1));
  });
  form.querySelectorAll('[data-step-prev]').forEach(button => {
    button.addEventListener('click', () => goToStep(-1));
  });

  function setupDropzone(dropzone) {
    const input = dropzone.querySelector('input[type="file"]');
    const nameLabel = dropzone.querySelector('[data-file-name]');
    const button = dropzone.querySelector('[data-dropzone-button]');

    function updateNameLabel() {
      if (!nameLabel || !input) return;
      const files = input.files;
      nameLabel.textContent = files && files.length ? files[0].name : 'No file selected';
      updateSummary();
      refreshRecommendations();
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
  }

  form.querySelectorAll('[data-dropzone]').forEach(setupDropzone);

  const debouncedRefresh = (() => {
    let timeout = null;
    return () => {
      if (timeout) window.clearTimeout(timeout);
      timeout = window.setTimeout(() => {
        refreshRecommendations();
      }, 350);
    };
  })();

  if (leftPathInput) leftPathInput.addEventListener('input', () => {
    debouncedRefresh();
    updateSummary();
  });
  if (rightPathInput) rightPathInput.addEventListener('input', () => {
    debouncedRefresh();
    updateSummary();
  });
  if (ruleSelect) ruleSelect.addEventListener('change', updateSummary);

  toggleCompareMode();
  toggleMappingSelect();
  updateMappingPreview();
  updateSubmitLabel();
  updateSummary();
  refreshRecommendations();
}

document.addEventListener('DOMContentLoaded', () => {
  setupIssueFilters();
  setupMappingTable();
  setupCopyYaml();
  setupNewRunForm();
});
