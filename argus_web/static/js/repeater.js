(function() {
  'use strict';

  var STATE = {
    tabs: [],
    active: 0,
    nextId: 1,
    browserUA: navigator.userAgent || '',
  };

  var tabsContainer = document.getElementById('repeater-tabs');
  var workspace = document.querySelector('.repeater-workspace');
  var historyBody = document.querySelector('#history-table tbody');
  var uaBadge = document.getElementById('ua-badge');

  // Mostra UA detectado
  if (uaBadge) {
    uaBadge.textContent = 'UA: ' + STATE.browserUA.substring(0, 40) + '...';
  }

  function makeTab() {
    return {
      id: STATE.nextId++,
      method: 'GET',
      url: '',
      headers: 'User-Agent: ' + STATE.browserUA + '\n',
      body: '',
      useUA: true,
      timeout: 15,
      response: null,
    };
  }

  function getActive() {
    return STATE.tabs[STATE.active];
  }

  function renderTabs() {
    if (!tabsContainer) return;
    tabsContainer.innerHTML = '';
    STATE.tabs.forEach(function(t, i) {
      var el = document.createElement('div');
      el.className = 'repeater-tab' + (i === STATE.active ? ' active' : '');
      el.textContent = '#' + t.id;
      if (STATE.tabs.length > 1) {
        var close = document.createElement('span');
        close.className = 'close';
        close.textContent = '×';
        close.onclick = function(e) {
          e.stopPropagation();
          STATE.tabs.splice(i, 1);
          if (STATE.active >= STATE.tabs.length) STATE.active = STATE.tabs.length - 1;
          renderTabs();
          renderActiveTab();
        };
        el.appendChild(close);
      }
      el.onclick = function() {
        STATE.active = i;
        renderTabs();
        renderActiveTab();
      };
      tabsContainer.appendChild(el);
    });
  }

  function fillForm(t) {
    workspace.querySelector('[data-field="method"]').value = t.method;
    workspace.querySelector('[data-field="url"]').value = t.url;
    workspace.querySelector('[data-field="headers"]').value = t.headers;
    workspace.querySelector('[data-field="body"]').value = t.body;
    workspace.querySelector('[data-field="use_ua"]').checked = t.useUA;
    workspace.querySelector('[data-field="timeout"]').value = t.timeout;
  }

  function readForm() {
    var t = getActive();
    t.method = workspace.querySelector('[data-field="method"]').value;
    t.url = workspace.querySelector('[data-field="url"]').value.trim();
    t.headers = workspace.querySelector('[data-field="headers"]').value;
    t.body = workspace.querySelector('[data-field="body"]').value;
    t.useUA = workspace.querySelector('[data-field="use_ua"]').checked;
    t.timeout = parseInt(workspace.querySelector('[data-field="timeout"]').value) || 15;
  }

  function parseHeaders(text) {
    var headers = {};
    (text || '').split('\n').forEach(function(line) {
      var idx = line.indexOf(':');
      if (idx < 1) return;
      var k = line.substring(0, idx).trim();
      var v = line.substring(idx + 1).trim();
      if (k && v) headers[k] = v;
    });
    return headers;
  }

  function renderActiveTab() {
    var t = getActive();
    if (!t) return;
    fillForm(t);
    if (t.response) {
      renderResponse(t.response);
    } else {
      document.getElementById('resp-body').textContent = 'Aguardando envio...';
      document.getElementById('resp-meta').textContent = '';
    }
  }

  function renderResponse(resp) {
    var body = document.getElementById('resp-body');
    var headers = document.getElementById('resp-headers');
    var raw = document.getElementById('resp-raw');
    var meta = document.getElementById('resp-meta');

    // Meta
    var cls = 'badge ';
    if (resp.status >= 500) cls += 'status-5xx';
    else if (resp.status >= 400) cls += 'status-4xx';
    else if (resp.status >= 300) cls += 'status-3xx';
    else cls += 'status-2xx';
    meta.innerHTML = '<span class="' + cls + '">' + resp.status + '</span> ' +
                     resp.time_ms + 'ms · ' + resp.size + 'B';

    // Body (format JSON se possivel)
    var bodyText = resp.body || '';
    try {
      var parsed = JSON.parse(bodyText);
      bodyText = JSON.stringify(parsed, null, 2);
    } catch (e) {}
    body.textContent = bodyText;

    // Headers
    var h = '';
    Object.keys(resp.headers || {}).forEach(function(k) {
      h += k + ': ' + resp.headers[k] + '\n';
    });
    headers.textContent = h;

    // Raw
    raw.textContent = 'HTTP/1.1 ' + resp.status + '\n' + h + '\n\n' + bodyText;
  }

  function send() {
    readForm();
    var t = getActive();
    if (!t.url) {
      alert('Informe a URL');
      return;
    }

    var headers = parseHeaders(t.headers);
    if (t.useUA) {
      headers['User-Agent'] = STATE.browserUA;
    }

    var payload = {
      method: t.method,
      url: t.url,
      headers: headers,
      body: t.body,
      timeout: t.timeout,
    };

    var btn = workspace.querySelector('[data-action="send"]');
    btn.disabled = true;
    btn.textContent = 'Enviando...';
    document.getElementById('resp-body').textContent = 'Aguardando...';

    var csrf = getCookie('csrftoken');

    fetch('/repeater/api/send/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf,
      },
      body: JSON.stringify(payload),
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      btn.disabled = false;
      btn.textContent = 'Send';
      if (data.error) {
        document.getElementById('resp-body').textContent = 'ERRO: ' + data.error;
        document.getElementById('resp-meta').textContent = '';
        return;
      }
      t.response = data;
      renderResponse(data);
      loadHistory();
    })
    .catch(function(err) {
      btn.disabled = false;
      btn.textContent = 'Send';
      document.getElementById('resp-body').textContent = 'Falha: ' + err;
    });
  }

  function reset() {
    var t = getActive();
    t.method = 'GET';
    t.url = '';
    t.headers = 'User-Agent: ' + STATE.browserUA + '\n';
    t.body = '';
    t.useUA = true;
    t.timeout = 15;
    t.response = null;
    fillForm(t);
    renderResponse({status: 0, time_ms: 0, size: 0, body: 'Aguardando envio...', headers: {}});
  }

  function getCookie(name) {
    var v = null;
    document.cookie.split(';').forEach(function(c) {
      var parts = c.trim().split('=');
      if (parts[0] === name) v = decodeURIComponent(parts[1]);
    });
    return v || '';
  }

  function loadHistory() {
    fetch('/repeater/api/history/')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        historyBody.innerHTML = '';
        (data.results || []).forEach(function(row) {
          var tr = document.createElement('tr');
          tr.innerHTML =
            '<td>' + row.id + '</td>' +
            '<td><code>' + row.method + '</code></td>' +
            '<td><code class="small">' + (row.url || '').substring(0, 60) + '</code></td>' +
            '<td>' + (row.response_status || '—') + '</td>' +
            '<td>' + (row.response_time_ms || '—') + 'ms</td>' +
            '<td><button class="btn btn-sm btn-outline-secondary">Abrir</button></td>';
          historyBody.appendChild(tr);
        });
      });
  }

  // Wire up
  workspace.querySelector('[data-action="send"]').addEventListener('click', send);
  workspace.querySelector('[data-action="reset"]').addEventListener('click', reset);
  document.getElementById('btn-new-tab').addEventListener('click', function() {
    STATE.tabs.push(makeTab());
    STATE.active = STATE.tabs.length - 1;
    renderTabs();
    renderActiveTab();
  });

  // Response tabs
  document.querySelectorAll('#resp-tabs button').forEach(function(b) {
    b.addEventListener('click', function() {
      document.querySelectorAll('#resp-tabs button').forEach(function(x) {
        x.classList.remove('active');
      });
      b.classList.add('active');
      var target = b.getAttribute('data-resp-tab');
      ['body', 'headers', 'raw'].forEach(function(k) {
        document.getElementById('resp-' + k).classList.toggle('d-none', k !== target);
      });
    });
  });

  // Init
  STATE.tabs.push(makeTab());
  renderTabs();
  renderActiveTab();
  loadHistory();
})();
