const catalogs = new Map();
async function catalog(module) {
  if (!catalogs.has(module)) {
    const response = await fetch(`assets/${module}/catalog.json`);
    if (!response.ok) throw Error(`Cannot load ${module}`);
    catalogs.set(module, await response.json());
  }
  return catalogs.get(module);
}
function tile(name) {
  const card = document.createElement('article'); card.className = 'tile';
  const label = document.createElement('small'); label.textContent = name; card.append(label);
  return card;
}
async function shapes() {
  const section = document.querySelector('#shapes'); const grid = section.querySelector('.grid');
  const query = section.querySelector('input').value.toLowerCase(); grid.replaceChildren();
  for (const shape of (await catalog('shapes')).filter(s => s.name.toLowerCase().includes(query))) {
    const card = tile(shape.name); const image = new Image(); image.src = shape.svg; image.alt = shape.name;
    card.prepend(image); const link = document.createElement('a'); link.href = shape.svg; link.textContent = 'SVG'; card.append(link); grid.append(card);
  }
}
async function fonts() {
  const section = document.querySelector('#fonts'); const grid = section.querySelector('.grid'); grid.replaceChildren();
  const text = section.querySelector('input').value; const weight = section.querySelector('#fontWeight').value;
  for (const font of await catalog('fonts')) {
    const family = `motion-preview-${font.id}`;
    if (!window[family]) {
      const face = new FontFace(family, `url("${font.file}")`, {weight:'100 1000'});
      window[family] = face; await face.load(); document.fonts.add(face);
    }
    const card = tile(font.name); card.classList.add('font-tile');
    const preview = document.createElement('div'); preview.className = 'font-preview'; preview.textContent = text;
    preview.style.fontFamily = family; preview.style.fontWeight = weight; card.prepend(preview);
    const axes = document.createElement('small'); axes.textContent = font.axes.map(a => `${a.tag} ${a.min}–${a.max}`).join(' · '); card.append(axes); grid.append(card);
  }
}
let symbolLimit = 160;
async function symbols() {
  const section = document.querySelector('#symbols'); const grid = section.querySelector('.grid');
  const query = section.querySelector('input').value.toLowerCase().replaceAll(' ', '_');
  const style = section.querySelector('select').value; const filled = section.querySelector('input[type=checkbox]').checked;
  const data = await catalog('symbols'); const names = Object.keys(data.styles[style]).filter(name => name.includes(query));
  grid.replaceChildren();
  for (const name of names.slice(0, symbolLimit)) {
    const card = tile(name); const icon = document.createElement('span'); icon.className = 'symbol'; icon.textContent = String.fromCodePoint(data.styles[style][name]);
    icon.style.fontFamily = `Symbols${style[0].toUpperCase()+style.slice(1)}`; icon.style.fontVariationSettings = `'FILL' ${filled?1:0}, 'wght' 400, 'GRAD' 0, 'opsz' 24`;
    card.prepend(icon); grid.append(card);
  }
  section.querySelector('.note').textContent = `${names.length.toLocaleString()} symbols · Google revision ${data.revision.slice(0,12)}`;
  document.querySelector('#more').hidden = symbolLimit >= names.length;
}
const render = {shapes, fonts, symbols};
async function show(module) {
  try {
    document.querySelector('#error').hidden = true;
    document.querySelectorAll('main>section').forEach(section => section.hidden = section.id !== module);
    document.querySelectorAll('nav button').forEach(button => button.setAttribute('aria-selected', String(button.dataset.module === module)));
    if (render[module]) await render[module]();
  } catch (error) { const banner=document.querySelector('#error'); banner.textContent=error.message; banner.hidden=false; }
}
document.querySelectorAll('nav button').forEach(button => button.addEventListener('click', () => show(button.dataset.module)));
document.querySelector('#shapes input').addEventListener('input', shapes);
document.querySelectorAll('#fonts input').forEach(input => input.addEventListener('input', fonts));
document.querySelectorAll('#symbols input,#symbols select').forEach(input => input.addEventListener('input', () => { symbolLimit=160; symbols(); }));
document.querySelector('#more').addEventListener('click', () => {symbolLimit+=160;symbols();});
fetch('manifest.json', {cache:'no-store'}).then(response=>response.json()).then(data=>document.querySelector('#version').textContent=`v${data.version}`);
