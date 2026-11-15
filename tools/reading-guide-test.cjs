const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

class Control {
  constructor() { this.children = []; this.attributes = {}; this.style = {}; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  add(node) { this.append(node); }
  get lastElementChild() { return this.children.at(-1); }
  querySelector(tag) {
    return this.children.find(child => child.tag === tag || child.children?.some(node => node.tag === tag))
      ?.find(tag);
  }
  find(tag) { return this.tag === tag ? this : this.querySelector(tag); }
  setAttribute(key, value) { this.attributes[key] = value; }
  focus() {}
  addEventListener() {}
  getBoundingClientRect() { return {left: 700, right: 1200, bottom: 100, width: 340}; }
  showModal() { this.open = true; }
  close() { this.open = false; }
}
function make(tag) {
  const node = new Control();
  node.tag = tag;
  return node;
}

async function run() {
  const panel = new Control(), toggle = new Control(), recall = new Control(), controls = new Map();
  const body = make('textarea'), critique = new Control(), critiqueText = make('textarea');
  const oldDraft = new Control();
  panel.hidden = true;
  toggle.parentElement = new Control();
  critique.append(critiqueText);
  const get = name => {
    if (!controls.has(name)) controls.set(name, new Control());
    return controls.get(name);
  };
  panel.querySelector = selector => get(selector.split('"')[1]);
  get('goal').querySelector = () => oldDraft;
  get('goal').selectedOptions = [];
  recall.querySelector = selector => ({textarea: body, '[data-critique]': critique, '[data-recall-questions]': get('recall-questions'), output: get('clock')})[selector];
  const env = {
    document: {createElement: make, querySelector: id => ({'#reading-guide': panel, '#guide-toggle': toggle, '#guide-recall': recall})[id]},
    Option: class { constructor(text, value) { Object.assign(this, {text, value}); } },
    setInterval() {},
    window: {innerHeight: 800, addEventListener() {}}
  };
  vm.createContext(env);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../lib/reading-guide.js'), 'utf8'), env);
  const storage = new Map(), notes = [], jumps = [], prompts = [];
  const doc = {numPages: 34, getOutline: async () => [{title: 'Introduction', dest: [1]}]};
  let reading = {id: 'paper', kind: 'article', page: 3, doc};
  const close = env.initReadingGuide({
    store: storage, selection: () => reading, jump: (...args) => jumps.push(args),
    saveNote: (...args) => notes.push(args), askAI: prompt => prompts.push(prompt)
  });
  toggle.onclick();
  await new Promise(setImmediate);
  assert.equal(get('fields').children[0].textContent, 'What question does the article address?');
  get('ai').onclick();
  assert.match(prompts.pop(), /Check substantive claims against the main text/);
  get('outline').value = '1';
  await get('outline').onchange();
  assert.deepEqual(jumps.pop(), ['paper', 2]);
  const question = get('fields').children[0].lastElementChild;
  question.value = 'Why did turnout change?';
  question.oninput();
  get('goal').value = 'trace';
  get('goal').onchange();
  assert.equal(get('fields').children[0].textContent, 'What is the starting problem?');
  get('steps').children[1].onclick();
  get('ai').onclick();
  assert.match(prompts.pop(), /Which premises lead to the conclusion/);
  get('goal').value = 'respond';
  get('goal').onchange();
  assert.equal(get('fields').children[0].textContent, 'Which claim could I respond to?');
  get('goal').value = 'understand';
  get('goal').onchange();
  assert.equal(get('fields').children[0].lastElementChild.value, 'Why did turnout change?');
  get('kind').value = 'chapter';
  get('kind').onchange();
  assert.equal(get('fields').children[0].textContent, 'Where does the chapter fit in the book?');
  get('ai').onclick();
  assert.equal(prompts.length, 0);
  get('range').value = '1-23';
  get('range').oninput();
  get('ai').onclick();
  const survey = prompts.pop();
  assert.match(survey, /^Use only PDF pages 1-23/);
  for (const field of get('fields').children) assert.ok(survey.includes(field.textContent));
  for (const [goal, firstQuestion] of [
    ['trace', 'What problem does the chapter open with?'],
    ['respond', 'Which claim or distinction could I respond to?']
  ]) {
    get('goal').value = goal;
    get('goal').onchange();
    assert.equal(get('fields').children[0].textContent, firstQuestion);
    get('range').value = '1-23';
    get('range').oninput();
    get('ai').onclick();
    const scoped = prompts.pop();
    for (const field of get('fields').children) assert.ok(scoped.includes(field.textContent));
  }
  get('goal').value = 'understand';
  get('goal').onchange();
  get('steps').children[1].onclick();
  get('ai').onclick();
  const argument = prompts.pop();
  for (const field of get('fields').children) assert.ok(argument.includes(field.textContent));
  get('steps').children[2].onclick();
  get('ai').onclick();
  assert.match(prompts.pop(), /^Use PDF page 3/);
  get('steps').children[3].onclick();
  get('add').onclick();
  const section = get('sections').children[0].querySelector('textarea');
  section.value = 'Defines the concept used in the next section.';
  section.oninput();
  get('sections').children[0].children[0].onclick();
  assert.deepEqual(jumps.pop(), ['paper', 3]);
  get('steps').children[3].onclick();
  get('ai').onclick();
  assert.equal(prompts.length, 0);
  assert.match(get('status').textContent, /Write your reconstruction/);
  get('recall').onclick();
  assert.equal(recall.open, true);
  assert.equal(critique.hidden, false);
  body.value = 'My reconstruction';
  body.oninput();
  critiqueText.oninput({target: {value: 'A competing explanation'}});
  close();
  assert.equal(recall.open, false);
  toggle.onclick();
  get('ai').onclick();
  assert.match(prompts.pop(), /^Use only PDF pages 1-23[\s\S]*My reconstruction[\s\S]*A competing explanation/);
  get('save').onclick();
  assert.match(notes[0][2], /PDF page 3[\s\S]*My reconstruction[\s\S]*A competing explanation/);
  get('kind').value = 'article';
  get('kind').onchange();
  assert.equal(get('fields').children[0].lastElementChild.value, 'Why did turnout change?');
  close();
  reading = {id: 'other', kind: 'article', page: 1, doc: {getOutline: async () => null}};
  toggle.onclick();
  await new Promise(setImmediate);
  assert.equal(get('fields').children[0].lastElementChild.value, '');
  assert.equal(get('outline').hidden, true);
  assert.match(get('bookmark-status').textContent, /has no bookmarks/);
  assert.equal(panel.style.left, '352px');
  close();
  const sectionNotes = [];
  env.initReadingGuide({
    store: storage, selection: () => reading, jump() {}, saveNote() {}, askAI() {},
    sectionNote: seed => sectionNotes.push(seed)
  });
  toggle.onclick();
  get('steps').children[2].onclick();
  get('add').onclick();
  assert.equal(sectionNotes[0].src, 'other');
  assert.equal(sectionNotes[0].page, 1);
  assert.equal(sectionNotes[0].question, undefined);
  assert.equal(get('sections').children.length, 0);
  console.log('PASS: separate article and chapter drafts, bookmark navigation, section notes, recall, export and reading isolation');
}
run().catch(error => { console.error(error); process.exitCode = 1; });
