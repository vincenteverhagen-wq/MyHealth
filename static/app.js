const KEYS=['energie','vet','verzadigd_vet','koolhydraten','suikers','vezels','eiwit','zout'];
const LABELS={energie:'Energie',vet:'Vet',verzadigd_vet:'Verzadigd vet',koolhydraten:'Koolhydraten',suikers:'Suikers',vezels:'Vezels',eiwit:'Eiwit',zout:'Zout'};
const MACROS=['vet','verzadigd_vet','koolhydraten','suikers','vezels','eiwit','zout'];
let products=[], rows=[];
const $=s=>document.querySelector(s);
const fmt=(n,d=1)=>Number(n).toLocaleString('nl-NL',{maximumFractionDigits:d,minimumFractionDigits:0});
const api=async(url,options={})=>{const r=await fetch(url,{headers:{'Content-Type':'application/json'},...options});if(!r.ok){let e=await r.json().catch(()=>({error:'Er ging iets mis.'}));throw Error(e.error)}return r.status===204?null:r.json()};
function toast(message){const el=$('#toast');el.textContent=message;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),2600)}
function navigate(view){document.querySelectorAll('.view,.nav').forEach(e=>e.classList.remove('active'));$('#'+view).classList.add('active');document.querySelector(`.nav[data-view="${view}"]`).classList.add('active');if(view==='meals')loadMeals();if(view==='health')loadHealthDays()}
document.querySelectorAll('.nav').forEach(b=>b.onclick=()=>navigate(b.dataset.view));
async function loadProducts(){products=await api('/api/products');renderProductTable();renderRows()}
function addRow(){rows.push({key:crypto.randomUUID(),product_id:products[0]?.id||'',grams:100});renderRows()}
function renderRows(){const wrap=$('#meal-rows');wrap.innerHTML='';$('#empty-builder').style.display=rows.length?'none':'block';rows.forEach(row=>{const div=document.createElement('div');div.className='meal-row';div.innerHTML=`<select aria-label="Product">${products.map(p=>`<option value="${p.id}" ${p.id==row.product_id?'selected':''}>${p.name}</option>`).join('')}</select><input type="number" min="0.1" step="0.1" value="${row.grams}" aria-label="Gram"><button title="Verwijderen">×</button>`;const [select,input,button]=div.children;select.onchange=()=>{row.product_id=Number(select.value);calculate()};input.oninput=()=>{row.grams=Math.max(0,Number(input.value)||0);calculate()};button.onclick=()=>{rows=rows.filter(r=>r.key!==row.key);renderRows()};wrap.append(div)});calculate()}
function calculate(){const totals=Object.fromEntries(KEYS.map(k=>[k,0]));rows.forEach(r=>{const p=products.find(p=>p.id==r.product_id);if(p)KEYS.forEach(k=>totals[k]+=p[k]*r.grams/100)});$('#item-count').textContent=`${rows.length} ${rows.length===1?'product':'producten'} toegevoegd`;$('#total-energie').textContent=fmt(totals.energie,0);$('#macro-list').innerHTML=MACROS.map(k=>`<div class="macro"><label>${LABELS[k]}</label><span>${fmt(totals[k],k==='zout'?3:1)} g</span><div class="bar"><i style="width:${Math.min(100,totals[k]*2)}%"></i></div></div>`).join('')}
$('#add-row').onclick=addRow;
$('#save-meal').onclick=async()=>{try{await api('/api/meals',{method:'POST',body:JSON.stringify({name:$('#meal-name').value,items:rows})});toast('Maaltijd opgeslagen');$('#meal-name').value='';rows=[];renderRows()}catch(e){toast(e.message)}};
async function loadMeals(){const meals=await api('/api/meals');const list=$('#meal-list');if(!meals.length){list.innerHTML='<div class="panel empty"><h3>Nog geen maaltijden</h3><p>Maak en bewaar je eerste maaltijd.</p></div>';return}list.innerHTML=meals.map(m=>`<article class="panel meal-card"><div class="card-top"><div><h3>${escapeHtml(m.name)}</h3><small>${m.items.length} ingrediënten</small></div><button class="delete" onclick="deleteMeal(${m.id})">×</button></div><ul>${m.items.map(i=>`<li><span>${escapeHtml(i.name)}</span><strong>${fmt(i.grams)} g</strong></li>`).join('')}</ul><div class="totals"><div><strong>${fmt(m.totals.energie,0)}</strong><small>kcal</small></div><div><strong>${fmt(m.totals.eiwit)} g</strong><small>eiwit</small></div><div><strong>${fmt(m.totals.koolhydraten)} g</strong><small>koolhydraten</small></div><div><strong>${fmt(m.totals.vet)} g</strong><small>vet</small></div></div></article>`).join('')}
window.deleteMeal=async id=>{await api(`/api/meals/${id}`,{method:'DELETE'});toast('Maaltijd verwijderd');loadMeals()};
function renderProductTable(){$('#product-table').innerHTML=products.map(p=>`<tr><td><strong>${escapeHtml(p.name)}</strong></td><td>${fmt(p.energie)}</td><td>${fmt(p.eiwit)} g</td><td>${fmt(p.koolhydraten)} g</td><td>${fmt(p.vet)} g</td><td><button class="delete" onclick="deleteProduct(${p.id})">×</button></td></tr>`).join('')}
$('#nutrient-fields').innerHTML=KEYS.map(k=>`<label>${LABELS[k]}${k==='energie'?' (kcal)':' (g)'}<input name="${k}" type="number" min="0" step="0.001" value="0" required></label>`).join('');
$('#product-form').onsubmit=async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.target));try{await api('/api/products',{method:'POST',body:JSON.stringify(data)});e.target.reset();e.target.querySelectorAll('input[type=number]').forEach(i=>i.value=0);toast('Product toegevoegd');loadProducts()}catch(e){toast(e.message)}};
window.deleteProduct=async id=>{try{await api(`/api/products/${id}`,{method:'DELETE'});toast('Product verwijderd');loadProducts()}catch(e){toast(e.message)}};
function escapeHtml(s){return String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
// Een product toevoegen zonder de maaltijdmaker te verlaten.
const nutrientInputs=KEYS.map(k=>`<label>${LABELS[k]}${k==='energie'?' (kcal)':' (g)'}<input name="${k}" type="number" min="0" step="0.001" value="0" required></label>`).join('');
$('#quick-nutrient-fields').innerHTML=nutrientInputs;
const productDialog=$('#product-dialog');
$('#quick-product').onclick=()=>productDialog.showModal();
$('#close-product-dialog').onclick=$('#cancel-product-dialog').onclick=()=>productDialog.close();
$('#new-meal-from-products').onclick=()=>navigate('builder');
$('#quick-product-form').onsubmit=async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.target));try{const product=await api('/api/products',{method:'POST',body:JSON.stringify(data)});products.push(product);products.sort((a,b)=>a.name.localeCompare(b.name,'nl'));rows.push({key:crypto.randomUUID(),product_id:product.id,grams:100});e.target.reset();e.target.querySelectorAll('input[type=number]').forEach(i=>i.value=0);productDialog.close();renderProductTable();renderRows();toast(`${product.name} toegevoegd aan de maaltijd`)}catch(error){toast(error.message)}};

// Een eerder opgeslagen maaltijd als ingrediëntenblok toevoegen.
const mealDialog=$('#meal-dialog');
let savedMeals=[];
$('#add-saved-meal').onclick=async()=>{mealDialog.showModal();const picker=$('#saved-meal-picker');picker.innerHTML='<div class="picker-empty">Maaltijden laden…</div>';try{savedMeals=await api('/api/meals');if(!savedMeals.length){picker.innerHTML='<div class="picker-empty"><strong>Nog geen maaltijden opgeslagen</strong>Maak en bewaar eerst een maaltijd.</div>';return}picker.innerHTML=savedMeals.map(meal=>`<button class="saved-meal-option" data-meal-id="${meal.id}"><strong>${escapeHtml(meal.name)}</strong><span>${meal.items.length} ingrediënten · ${fmt(meal.totals.energie,0)} kcal</span><b>Toevoegen →</b></button>`).join('');picker.querySelectorAll('[data-meal-id]').forEach(button=>button.onclick=()=>addWholeMeal(Number(button.dataset.mealId)))}catch(error){picker.innerHTML=`<div class="picker-empty">${escapeHtml(error.message)}</div>`}};
$('#close-meal-dialog').onclick=()=>mealDialog.close();
function addWholeMeal(mealId){const meal=savedMeals.find(item=>item.id===mealId);if(!meal)return;meal.items.forEach(item=>rows.push({key:crypto.randomUUID(),product_id:item.product_id,grams:item.grams}));mealDialog.close();renderRows();toast(`${meal.name} toegevoegd: ${meal.items.length} ingrediënten`)}

// Compacte rekenmachine. Alleen door de knoppen ingevoerde tekens worden verwerkt.
let calcInput='',calcResult=0;
function updateCalc(){const pretty=calcInput.replaceAll('*','×').replaceAll('/','÷');$('#calc-expression').textContent=pretty||' ';$('#calc-display').textContent=fmt(calcResult,3)}
function solveCalc(){if(!calcInput)return;try{if(!/^[0-9+\-*/. ]+$/.test(calcInput))throw Error();const value=Function(`"use strict";return (${calcInput})`)();if(!Number.isFinite(value))throw Error();calcResult=Math.round(value*1000)/1000;calcInput=String(calcResult);updateCalc()}catch{$('#calc-expression').textContent='Ongeldige berekening';calcInput='';calcResult=0}}
document.querySelectorAll('[data-calc]').forEach(button=>button.onclick=()=>{const value=button.dataset.calc;if(/[+\-*/]$/.test(calcInput)&&/[+\-*/]/.test(value))calcInput=calcInput.slice(0,-1);calcInput+=value;const tail=calcInput.match(/(?:^|[+\-*/])(-?\d*\.?\d*)$/)?.[1];calcResult=Number(tail)||0;updateCalc()});
$('#calc-equals').onclick=solveCalc;
$('#calc-clear').onclick=()=>{calcInput='';calcResult=0;updateCalc()};
$('#use-as-grams').onclick=()=>{solveCalc();if(calcResult<=0){toast('Bereken eerst een uitkomst groter dan 0');return}if(!rows.length){toast('Voeg eerst een ingrediënt toe');return}rows.at(-1).grams=calcResult;renderRows();toast(`${fmt(calcResult,3)} gram ingevuld`)};

const calculator=$('#calculator');
calculator.addEventListener('pointerdown',()=>{calculator.classList.add('keyboard-active');calculator.focus({preventScroll:true})});
calculator.addEventListener('focusin',()=>calculator.classList.add('keyboard-active'));
calculator.addEventListener('focusout',event=>{if(!calculator.contains(event.relatedTarget))calculator.classList.remove('keyboard-active')});
calculator.addEventListener('keydown',event=>{
  if(event.ctrlKey||event.metaKey||event.altKey)return;
  const keyMap={',':'.','x':'*','X':'*',':':'/'};
  const key=keyMap[event.key]||event.key;
  if(/^[0-9.+\-*/]$/.test(key)){
    event.preventDefault();
    if(/[+\-*/]$/.test(calcInput)&&/[+\-*/]/.test(key))calcInput=calcInput.slice(0,-1);
    calcInput+=key;
    const tail=calcInput.match(/(?:^|[+\-*/])(-?\d*\.?\d*)$/)?.[1];
    calcResult=Number(tail)||0;
    updateCalc();
  }else if(event.key==='Enter'||event.key==='='){
    event.preventDefault();solveCalc();
  }else if(event.key==='Backspace'){
    event.preventDefault();calcInput=calcInput.slice(0,-1);calcResult=Number(calcInput.match(/(?:^|[+\-*/])(-?\d*\.?\d*)$/)?.[1])||0;updateCalc();
  }else if(event.key==='Escape'||event.key==='Delete'||event.key==='c'||event.key==='C'){
    event.preventDefault();calcInput='';calcResult=0;updateCalc();
  }
});

// MyHealth voedingsdagboek.
const HEALTH_CATEGORIES=['ontbijt','lunch','avondeten','tussendoortje'];
const HEALTH_LABELS={ontbijt:'Ontbijt',lunch:'Lunch',avondeten:'Avondeten',tussendoortje:'Tussendoortje'};
let healthRows=Object.fromEntries(HEALTH_CATEGORIES.map(category=>[category,[]]));
let healthDays=[];
let healthMealCategory='ontbijt';
const localToday=()=>new Date().toLocaleDateString('sv-SE');
const displayDate=value=>{if(!value)return'';const [y,m,d]=value.split('-');return`${d}-${m}-${y}`};

function emptyHealthRows(){healthRows=Object.fromEntries(HEALTH_CATEGORIES.map(category=>[category,[]]))}
function renderHealthEditor(){
  $('#health-categories').innerHTML=HEALTH_CATEGORIES.map(category=>`<article class="panel health-category"><div class="health-category-head"><h3>${HEALTH_LABELS[category]}</h3><div class="health-category-actions"><button class="secondary" data-health-meal="${category}">+ Maaltijd</button><button class="add" data-health-product="${category}">+ Product</button></div></div><div class="health-items">${healthRows[category].length?healthRows[category].map(row=>`<div class="health-item" data-health-key="${row.key}"><select aria-label="Product">${products.map(product=>`<option value="${product.id}" ${product.id==row.product_id?'selected':''}>${escapeHtml(product.name)}</option>`).join('')}</select><input type="number" min="0.1" step="0.1" value="${row.grams}" aria-label="Gram"><button title="Verwijderen">×</button></div>`).join(''):'<div class="health-empty">Nog niets toegevoegd.</div>'}</div></article>`).join('');
  document.querySelectorAll('[data-health-product]').forEach(button=>button.onclick=()=>{const category=button.dataset.healthProduct;if(!products.length)return;healthRows[category].push({key:crypto.randomUUID(),product_id:products[0].id,grams:100});renderHealthEditor()});
  document.querySelectorAll('[data-health-meal]').forEach(button=>button.onclick=()=>openHealthMealPicker(button.dataset.healthMeal));
  document.querySelectorAll('.health-item').forEach(element=>{const row=HEALTH_CATEGORIES.flatMap(category=>healthRows[category].map(item=>({category,item}))).find(value=>value.item.key===element.dataset.healthKey);if(!row)return;const [select,input,remove]=element.children;select.onchange=()=>{row.item.product_id=Number(select.value);calculateHealth()};input.oninput=()=>{row.item.grams=Math.max(0,Number(input.value)||0);calculateHealth()};remove.onclick=()=>{healthRows[row.category]=healthRows[row.category].filter(item=>item.key!==row.item.key);renderHealthEditor()}});
  calculateHealth();
}
function calculateHealth(){const totals=Object.fromEntries(KEYS.map(key=>[key,0]));HEALTH_CATEGORIES.forEach(category=>healthRows[category].forEach(row=>{const product=products.find(item=>item.id==row.product_id);if(product)KEYS.forEach(key=>totals[key]+=product[key]*row.grams/100)}));$('#health-total-energie').textContent=fmt(totals.energie,0);$('#health-macro-list').innerHTML=MACROS.map(key=>`<div class="macro"><label>${LABELS[key]}</label><span>${fmt(totals[key],key==='zout'?3:1)} g</span><div class="bar"><i style="width:${Math.min(100,totals[key]*2)}%"></i></div></div>`).join('');$('#health-summary-date').textContent=displayDate($('#health-date').value)||'vandaag'}
async function openHealthMealPicker(category){healthMealCategory=category;const dialog=$('#health-meal-dialog');const picker=$('#health-meal-picker');dialog.showModal();picker.innerHTML='<div class="picker-empty">Maaltijden laden…</div>';try{const meals=await api('/api/meals');if(!meals.length){picker.innerHTML='<div class="picker-empty"><strong>Nog geen maaltijden opgeslagen</strong>Maak en bewaar eerst een maaltijd.</div>';return}picker.innerHTML=meals.map(meal=>`<button class="saved-meal-option" data-health-meal-id="${meal.id}"><strong>${escapeHtml(meal.name)}</strong><span>${meal.items.length} ingrediënten · ${fmt(meal.totals.energie,0)} kcal</span><b>Toevoegen →</b></button>`).join('');picker.querySelectorAll('[data-health-meal-id]').forEach((button,index)=>button.onclick=()=>{meals[index].items.forEach(item=>healthRows[healthMealCategory].push({key:crypto.randomUUID(),product_id:item.product_id,grams:item.grams}));dialog.close();renderHealthEditor();toast(`${meals[index].name} toegevoegd aan ${HEALTH_LABELS[healthMealCategory].toLowerCase()}`)})}catch(error){picker.innerHTML=`<div class="picker-empty">${escapeHtml(error.message)}</div>`}}
$('#close-health-meal-dialog').onclick=()=>$('#health-meal-dialog').close();
$('#add-health-day').onclick=()=>{const dateValue=localToday();$('#health-editor').hidden=false;$('#health-date').value=dateValue;const existing=healthDays.find(day=>day.date===dateValue);existing?editHealthDay(existing.id):emptyHealthRows();renderHealthEditor();$('#health-editor').scrollIntoView({behavior:'smooth',block:'start'})};
$('#health-date').onchange=()=>{const existing=healthDays.find(day=>day.date===$('#health-date').value);if(existing){loadHealthDayIntoEditor(existing)}else{emptyHealthRows();renderHealthEditor()}};
$('#save-health-day').onclick=async()=>{const entries=HEALTH_CATEGORIES.flatMap(category=>healthRows[category].map(row=>({category,product_id:row.product_id,grams:row.grams})));try{await api('/api/health-days',{method:'POST',body:JSON.stringify({date:$('#health-date').value,entries})});toast('Dag opgeslagen');await loadHealthDays()}catch(error){toast(error.message)}};
async function loadHealthDays(){try{healthDays=await api('/api/health-days');renderHealthDays()}catch(error){toast(error.message)}}
function renderHealthDays(){const list=$('#health-day-list');if(!healthDays.length){list.innerHTML='<div class="panel picker-empty"><strong>Nog geen dagen opgeslagen</strong>Klik op Dag toevoegen om vandaag te registreren.</div>';return}list.innerHTML=healthDays.map(day=>`<article class="panel health-day-card"><div class="health-day-card-head"><h3>${displayDate(day.date)}</h3><div class="health-day-card-head-actions"><strong>${fmt(day.totals.energie,0)} kcal</strong><button class="secondary" onclick="editHealthDay(${day.id})">Bewerken</button><button class="delete" onclick="deleteHealthDay(${day.id})">×</button></div></div><div class="day-categories">${HEALTH_CATEGORIES.map(category=>`<div class="day-moment"><strong>${HEALTH_LABELS[category]}</strong>${day.categories[category].length?day.categories[category].map(item=>`<span>${escapeHtml(item.name)} · ${fmt(item.grams)} g</span>`).join(''):'<span>—</span>'}</div>`).join('')}</div></article>`).join('')}
function loadHealthDayIntoEditor(day){$('#health-editor').hidden=false;$('#health-date').value=day.date;emptyHealthRows();HEALTH_CATEGORIES.forEach(category=>day.categories[category].forEach(item=>healthRows[category].push({key:crypto.randomUUID(),product_id:item.product_id,grams:item.grams})));renderHealthEditor()}
window.editHealthDay=id=>{const day=healthDays.find(item=>item.id===id);if(day){loadHealthDayIntoEditor(day);$('#health-editor').scrollIntoView({behavior:'smooth',block:'start'})}};
window.deleteHealthDay=async id=>{try{await api(`/api/health-days/${id}`,{method:'DELETE'});toast('Dag verwijderd');loadHealthDays()}catch(error){toast(error.message)}};

const exportDialog=$('#export-dialog');
$('#export-health').onclick=()=>{const today=localToday();$('#export-form').elements.from.value=today;$('#export-form').elements.to.value=today;exportDialog.showModal()};
$('#close-export-dialog').onclick=$('#cancel-export').onclick=()=>exportDialog.close();
$('#export-form').onsubmit=event=>{event.preventDefault();const data=new FormData(event.target);const from=data.get('from'),to=data.get('to');if(from>to){toast('De begindatum moet voor de einddatum liggen');return}window.location.href=`/api/health-export.pdf?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`;exportDialog.close()};

loadProducts();
