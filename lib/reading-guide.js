function initReadingGuide({store, selection, jump, saveNote, askAI, sectionNote}) {
  const plans = {
    article: [
      ['Survey', '5 to 10 min', 'Read the abstract, introduction, conclusion, and headings.', ['Research question', 'Central argument', 'Main concepts']],
      ['Map the argument', '10 min', 'Trace the explanation from its assumptions through the mechanism to the outcome.', ['What is being explained?', 'What is the explanation?', 'How does it work?', 'What assumptions does it depend on?']],
      ['Read closely', '30 to 60 min', 'Focus on theory, definitions, mechanisms, and the evidence needed to judge the argument. Skim familiar material and slow down at difficult passages.'],
      ['Recall', '10 min']
    ],
    chapter: [
      ['Survey', '5 min', 'Read the title, opening pages, conclusion, and headings. Check the book introduction if you have it.', ['Where does the chapter fit in the book?', 'What is the central argument?', 'What are the main concepts?']],
      ['Find the argument', '5 to 10 min', 'State the chapter’s purpose before tracing the reasoning.', ['What is the author trying to establish?', 'Why does the book need this chapter?']],
      ['Read in order', '30 to 60 min', 'Follow the chapter’s order. After each section, write one or two sentences on what it argues and how it advances the chapter. Record definitions and distinctions you need later.'],
      ['Recall and evaluate', '10 min']
    ]
  };
  const goals = {
    understand: [
      ['What question does the article address?', 'What is its main answer?', 'Which terms do I need to understand?'],
      ['What does the main claim mean in plain language?', 'Which example makes it clearest?'],
      ['What is the point of this passage?', 'How does the author define or illustrate the key idea here?'],
      ['How would I explain the main claim and its key concept to someone new to the topic?']
    ],
    trace: [
      ['What is the starting problem?', 'What conclusion does the author reach?', 'Which sections connect the two?'],
      ['Which premises lead to the conclusion?', 'What mechanism or intermediate step connects them?', 'What does that link assume?'],
      ['What earlier claim does this passage build on?', 'What new step does it add, and what supports that step?'],
      ['Can I reconstruct the chain from premises to conclusion?', 'Which link do I need to reread?']
    ],
    respond: [
      ['Which claim could I respond to?', 'Where does the author state it most clearly?'],
      ['Which assumption does the claim depend on?', 'What counterexample or alternative explanation would challenge it?'],
      ['What evidence or example supports this claim here?', 'What would I need to show to challenge the author’s interpretation?'],
      ['Can I state the author’s strongest case fairly?', 'What is my objection, and which passage should my response address?']
    ]
  };
  const chapterSurvey = {
    understand: plans.chapter[0][3],
    trace: ['What problem does the chapter open with?', 'What conclusion does the chapter reach?', 'Which headings mark the turns in the reasoning?'],
    respond: ['Which claim or distinction could I respond to?', 'Which section develops it most fully?']
  };
  const questions = step => {
    if (data.kind === 'chapter' && step === 0) return chapterSurvey[data.goal];
    return goals[data.goal][step];
  };
  const panel = document.querySelector('#reading-guide');
  const aiLabels = ['Ask AI to survey', 'Ask AI to map the argument', 'Ask AI about this page', 'Ask AI to check my recall'];
  const toggle = document.querySelector('#guide-toggle');
  const recall = document.querySelector('#guide-recall');
  const get = name => panel.querySelector('[data-guide="' + name + '"]');
  const recallBody = recall.querySelector('textarea');
  const critique = recall.querySelector('[data-critique]');
  let reading, data;
  let outlineRequest = 0;
  const draftKey = (kind, goal) => 'cv:guide:' + reading.id + ':' + kind + (goal === 'original' ? '' : ':' + goal);
  const persist = () => store.set(draftKey(data.kind, data.goal), JSON.stringify(data));
  function loadPlan(kind, goal) {
    kind = kind === 'chapter' ? 'chapter' : 'article';
    goal = Object.hasOwn(goals, goal) ? goal : 'original';
    let saved;
    try { saved = JSON.parse(store.get(draftKey(kind, goal))); } catch {}
    if (goal === 'original' && !saved) return loadPlan(kind, 'understand');
    data = {step: 0, started: 0, answers: {}, sections: [], recall: '', critique: '', ...saved, kind, goal};
    if (!plans[kind][data.step]) data.step = 0;
    get('kind').value = kind;
    get('goal').value = goal;
    get('goal').querySelector('[value="original"]').hidden = !store.get(draftKey(kind, 'original'));
    get('range').value = data.range || '';
    render();
  }
  const goalQuestions = step => data.goal === 'original' ? plans[data.kind][step][3] : questions(step);
  const element = (tag, text) => {
    const node = document.createElement(tag);
    node.textContent = text;
    return node;
  };
  const button = (text, action) => {
    const node = element('button', text);
    node.type = 'button';
    node.onclick = action;
    return node;
  };
  const field = (label, value, onInput) => {
    const node = element('label', label);
    const input = element('textarea', '');
    input.rows = 2;
    input.value = value || '';
    input.oninput = () => { onInput(input.value); persist(); };
    node.append(input);
    return node;
  };
  function showTime() {
    if (panel.hidden || !data) return;
    const elapsed = data.started ? Math.max(0, Math.floor((Date.now() - data.started) / 1000)) : 0;
    const time = Math.floor(elapsed / 60) + ':' + String(elapsed % 60).padStart(2, '0');
    get('time').textContent = data.started ? time + ' elapsed' : '';
    get('timer').hidden = Boolean(data.started);
    recall.querySelector('output').textContent = time + ' elapsed · 10 min suggested';
  }
  async function loadOutline() {
    const {doc} = reading;
    const request = ++outlineRequest;
    const menu = get('outline');
    const status = get('bookmark-status');
    menu.hidden = true;
    status.textContent = 'Loading PDF bookmarks…';
    menu.disabled = true;
    try {
      const entries = [];
      const visit = items => {
        for (const item of items) {
          if (item.dest) entries.push(item);
          visit(item.items || []);
        }
      };
      visit(await doc.getOutline() || []);
      if (request !== outlineRequest) return;
      status.textContent = entries.length ? '' : 'This PDF has no bookmarks. Use the page box to jump.';
      menu.replaceChildren(new Option('Jump to a PDF bookmark', ''));
      entries.forEach((item, i) => menu.add(new Option(item.title, String(i + 1))));
      menu.disabled = !entries.length;
      menu.hidden = !entries.length;
      menu.onchange = async () => {
        const item = entries[Number(menu.value) - 1];
        menu.value = '';
        if (!item) return;
        try {
          const dest = typeof item.dest === 'string' ? await doc.getDestination(item.dest) : item.dest;
          const index = Number.isInteger(dest?.[0]) ? dest[0] : await doc.getPageIndex(dest?.[0]);
          if (request === outlineRequest) jump(reading.id, index + 1);
        } catch {
          if (request === outlineRequest) get('status').textContent = 'Could not open that bookmark. Use the page box.';
        }
      };
    } catch {
      if (request === outlineRequest) status.textContent = 'Could not load PDF bookmarks. Use the page box to jump.';
    }
  }
  function exportNote() {
    const plan = plans[data.kind];
    const parts = plan.slice(0, 2).flatMap(([title], step) =>
      goalQuestions(step).map((label, i) => [title, label, data.answers[step + '-' + i]?.trim()])
        .filter(([, , answer]) => answer).map(([stage, label, answer]) => stage + ' / ' + label + '\n' + answer));
    for (const section of data.sections) {
      if (section.text.trim()) parts.push((section.gap ? 'Recall gap / PDF page ' : 'PDF page ') + section.page + '\n' + section.text.trim());
    }
    if (data.recall.trim()) parts.push('Reconstruction\n' + data.recall.trim());
    if (data.critique.trim()) parts.push('Evaluation\n' + data.critique.trim());
    if (!parts.length) {
      get('status').textContent = 'Write something in the guide before copying it to Notes.';
      return;
    }
    const goalLabel = get('goal').selectedOptions[0]?.textContent;
    saveNote(reading.id, data.goal === 'original' || !goalLabel ? 'Reading guide' : 'Reading guide / ' + goalLabel, parts.join('\n\n'));
    get('status').textContent = 'Copied to a new note.';
  }
  function render() {
    const plan = plans[data.kind];
    const [, duration, prompt] = plan[data.step];
    const labels = goalQuestions(data.step);
    get('steps').replaceChildren(...plan.map(([name], step) => {
      const control = button(name, () => {
        if (data.step !== step) {
          data.step = step;
          data.started = 0;
          persist();
          render();
          get('steps').children[step].focus();
        }
      });
      if (data.step === step) control.setAttribute('aria-current', 'step');
      return control;
    }));
    get('status').textContent = '';
    get('prompt').textContent = prompt || 'Write the argument from memory. Then return to the pages you need to check.';
    get('questions').replaceChildren(...(data.step >= 2 ? (labels || []) : []).map(label => element('li', label)));
    get('duration').textContent = duration + ' suggested';
    get('fields').replaceChildren();
    get('sections').replaceChildren();
    get('add').hidden = data.step !== 2 && data.step !== 3;
    get('add').textContent = data.step === 3 ? 'Note a gap at this page' : 'New note';
    get('recall').hidden = data.step !== 3;
    get('ai').textContent = aiLabels[data.step];
    get('range-label').hidden = data.kind !== 'chapter' || data.step === 2;
    if (labels && data.step < 2) {
      labels.forEach((label, i) => {
        const key = data.step + '-' + i;
        get('fields').append(field(label, data.answers[key], value => { data.answers[key] = value; }));
      });
    }
    if (data.step === 2 || data.step === 3) {
      data.sections.forEach((section, i) => {
        if (!section.gap || data.step !== 3) return;
        const row = element('li', '');
        const page = button('Go to PDF page ' + section.page, () => jump(reading.id, section.page));
        const label = (section.gap ? 'Recall gap' : 'Section note') + ' ' + (i + 1);
        row.append(page, field(label, section.text, value => { section.text = value; }));
        get('sections').append(row);
      });
    }
    showTime();
  }
  function close() {
    if (recall.open) recall.close();
    if (!panel.hidden) {
      panel.hidden = true;
      toggle.setAttribute('aria-expanded', 'false');
      outlineRequest++;
    }
  }
  function place() {
    if (panel.hidden) return;
    const toolbar = toggle.parentElement.getBoundingClientRect();
    const width = panel.getBoundingClientRect().width;
    const beside = toolbar.left >= width + 16;
    panel.style.left = Math.max(8, beside ? toolbar.left - width - 8 : toolbar.right - width - 8) + 'px';
    const top = Math.min(toolbar.bottom + 8, window.innerHeight * .4);
    panel.style.top = top + 'px';
    panel.style.maxHeight = (window.innerHeight - top - 8) + 'px';
  }
  window.addEventListener('resize', place);
  get('close').onclick = () => { close(); toggle.focus(); };
  panel.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      event.stopPropagation();
      close();
      toggle.focus();
    }
  });
  toggle.onclick = () => {
    if (!panel.hidden) return close();
    reading = selection();
    if (!reading) return;
    const kind = store.get('cv:guide-mode:' + reading.id);
    const planKind = kind === 'article' || kind === 'chapter' ? kind : reading.kind;
    loadPlan(planKind, store.get('cv:guide-goal:' + reading.id + ':' + planKind));
    panel.hidden = false;
    toggle.setAttribute('aria-expanded', 'true');
    place();
    get('close').focus();
    loadOutline();
  };
  get('kind').onchange = () => {
    const kind = get('kind').value;
    store.set('cv:guide-mode:' + reading.id, kind);
    loadPlan(kind, store.get('cv:guide-goal:' + reading.id + ':' + kind));
  };
  get('goal').onchange = () => {
    store.set('cv:guide-goal:' + reading.id + ':' + data.kind, get('goal').value);
    loadPlan(data.kind, get('goal').value);
  };
  get('range').oninput = () => {
    data.range = get('range').value;
    persist();
  };
  get('timer').onclick = () => {
    data.started = Date.now();
    persist();
    showTime();
    get('time').focus();
  };
  get('add').onclick = () => {
    const current = selection();
    if (!current || current.id !== reading.id) return;
    if (data.step === 2) {
      sectionNote?.({src: current.id, page: current.page});
      return;
    }
    data.sections.push({page: current.page, text: '', gap: data.step === 3});
    persist();
    render();
    get('sections').lastElementChild.querySelector('textarea').focus();
  };
  get('recall').onclick = () => {
    recallBody.value = data.recall;
    recall.querySelector('[data-recall-questions]').replaceChildren(...(goalQuestions(3) || []).map(label => element('li', label)));
    critique.querySelector('textarea').value = data.critique;
    critique.hidden = data.kind !== 'chapter';
    if (!data.started) data.started = Date.now();
    persist();
    showTime();
    recall.showModal();
  };
  recallBody.oninput = () => { data.recall = recallBody.value; persist(); };
  critique.querySelector('textarea').oninput = e => { data.critique = e.target.value; persist(); };
  get('ai').onclick = () => {
    const current = selection();
    if (!current || current.id !== reading.id) return;
    const chapter = data.kind === 'chapter';
    const recallDraft = data.recall.trim();
    if (data.step === 3 && !recallDraft) {
      get('status').textContent = 'Write your reconstruction in Recall first.';
      return;
    }
    let scope = data.step === 2 ? 'Use PDF page ' + current.page + '.\n\n' : '';
    if (chapter && data.step !== 2) {
      const range = (data.range || '').trim().match(/^(\d+)(?:\s*[-–—]\s*(\d+))?$/);
      const first = Number(range?.[1]), last = Number(range?.[2] || range?.[1]);
      if (!(first >= 1 && last >= first && last <= current.doc.numPages)) {
        get('status').textContent = 'Enter the chapter’s PDF page range, for example 1-23.';
        get('range').focus();
        return;
      }
      scope = 'Use only PDF pages ' + first + '-' + last + '.\n\n';
    }
    const labels = goalQuestions(data.step);
    const evidence = '\n\nCite the relevant passages. Check substantive claims against the main text. If the supplied pages do not answer a question, say what is missing under that question.';
    let prompt;
    if (labels && data.step < 3) {
      prompt = 'Answer each Reading guide question in the order below. Use each question as its heading and answer it directly. Skip a chapter inventory or boundary discussion.\n\n' +
        labels.join('\n') + evidence;
    } else if (data.step === 2) {
      prompt = 'Help me read this page closely. What does this passage argue? How does it advance the argument? Explain any key definitions, distinctions, mechanisms, and evidence on the page. Flag points that need surrounding context.' + evidence;
    } else {
      prompt = 'Check my reconstruction against the reading. Identify what I got right, what I missed or misstated, and which passages I should reread.' +
        (labels ? '\n\nUse these recall questions to guide your feedback:\n' + labels.join('\n') : '') + evidence +
        '\n\nMy reconstruction:\n' + recallDraft +
        (chapter && data.critique.trim() ? '\n\nCheck whether the text supports this proposed critique:\n' + data.critique.trim() : '');
    }
    askAI(scope + prompt);
  };
  get('save').onclick = exportNote;
  setInterval(showTime, 1000);
  return close;
}
