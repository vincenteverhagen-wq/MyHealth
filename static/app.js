const KEYS=['energie','vet','verzadigd_vet','koolhydraten','suikers','vezels','eiwit','zout'];
const LABELS={energie:'Energie',vet:'Vet',verzadigd_vet:'Verzadigd vet',koolhydraten:'Koolhydraten',suikers:'Suikers',vezels:'Vezels',eiwit:'Eiwit',zout:'Zout'};
const MACROS=['vet','verzadigd_vet','koolhydraten','suikers','vezels','eiwit','zout'];
let products=[], rows=[];
const $=s=>document.querySelector(s);
const fmt=(n,d=1)=>Number(n).toLocaleString('nl-NL',{maximumFractionDigits:d,minimumFractionDigits:0});
const api=async(url,options={})=>{const r=await fetch(url,{headers:{'Content-Type':'application/json'},...options});if(r.status===401){window.location.href='/login';throw Error('Log opnieuw in.')}if(!r.ok){let e=await r.json().catch(()=>({error:'Er ging iets mis.'}));throw Error(e.error)}return r.status===204?null:r.json()};
function toast(message){const el=$('#toast');el.textContent=message;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),2600)}
function navigate(view){document.querySelectorAll('.view,.nav').forEach(e=>e.classList.remove('active'));$('#'+view).classList.add('active');document.querySelector(`.nav[data-view="${view}"]`).classList.add('active');const moreMenu=$('.more-menu');moreMenu.classList.remove('open');moreMenu.classList.toggle('has-active',['meals','products','exercises','friends'].includes(view));if(view==='overview')loadOverview();if(view==='meals')loadMeals();if(view==='health')loadHealthDays();if(view==='fitness'){ensureFitnessDate();loadFitnessDay()}if(view==='exercises')loadExercises();if(view==='friends')loadFriends()}
document.querySelectorAll('.nav').forEach(b=>b.onclick=()=>navigate(b.dataset.view));
$('#more-menu-toggle').onclick=event=>{event.stopPropagation();$('.more-menu').classList.toggle('open')};
document.addEventListener('click',event=>{if(!event.target.closest('.more-menu'))$('.more-menu').classList.remove('open')});
async function loadProducts(){products=await api('/api/products');renderProductTable();renderRows();updateCategoryOptions()}
function addRow(){openProductPicker({type:'meal'})}
function renderRows(){const wrap=$('#meal-rows');wrap.innerHTML='';$('#empty-builder').style.display=rows.length?'none':'block';rows.forEach(row=>{const product=products.find(item=>item.id==row.product_id);const div=document.createElement('div');div.className='meal-row';div.innerHTML=`<button class="product-choice" type="button"><span>${escapeHtml(product?.name||'Kies een product')}</span><small>${escapeHtml(product?.category||'Product wijzigen')}</small></button><input type="number" min="0.1" step="0.1" value="${row.grams}" aria-label="Gram"><button title="Verwijderen">×</button>`;const [choice,input,remove]=div.children;choice.onclick=()=>openProductPicker({type:'meal',rowKey:row.key});input.oninput=()=>{row.grams=Math.max(0,Number(input.value)||0);calculate()};remove.onclick=()=>{rows=rows.filter(item=>item.key!==row.key);renderRows()};wrap.append(div)});calculate()}
function calculate(){const totals=Object.fromEntries(KEYS.map(k=>[k,0]));rows.forEach(r=>{const p=products.find(p=>p.id==r.product_id);if(p)KEYS.forEach(k=>totals[k]+=p[k]*r.grams/100)});$('#item-count').textContent=`${rows.length} ${rows.length===1?'product':'producten'} toegevoegd`;$('#total-energie').textContent=fmt(totals.energie,0);$('#macro-list').innerHTML=MACROS.map(k=>`<div class="macro"><label>${LABELS[k]}</label><span>${fmt(totals[k],k==='zout'?3:1)} g</span><div class="bar"><i style="width:${Math.min(100,totals[k]*2)}%"></i></div></div>`).join('')}
$('#add-row').onclick=addRow;
$('#save-meal').onclick=async()=>{try{await api('/api/meals',{method:'POST',body:JSON.stringify({name:$('#meal-name').value,items:rows})});toast('Maaltijd opgeslagen');$('#meal-name').value='';rows=[];renderRows()}catch(e){toast(e.message)}};
async function loadMeals(){const meals=await api('/api/meals');const list=$('#meal-list');if(!meals.length){list.innerHTML='<div class="panel empty"><h3>Nog geen maaltijden</h3><p>Maak en bewaar je eerste maaltijd.</p></div>';return}list.innerHTML=meals.map(m=>`<article class="panel meal-card"><div class="card-top"><div><h3>${escapeHtml(m.name)}</h3><small>${m.items.length} ingrediënten</small></div><button class="delete" onclick="deleteMeal(${m.id})">×</button></div><ul>${m.items.map(i=>`<li><span>${escapeHtml(i.name)}</span><strong>${fmt(i.grams)} g</strong></li>`).join('')}</ul><div class="totals"><div><strong>${fmt(m.totals.energie,0)}</strong><small>kcal</small></div><div><strong>${fmt(m.totals.eiwit)} g</strong><small>eiwit</small></div><div><strong>${fmt(m.totals.koolhydraten)} g</strong><small>koolhydraten</small></div><div><strong>${fmt(m.totals.vet)} g</strong><small>vet</small></div></div></article>`).join('')}
window.deleteMeal=async id=>{await api(`/api/meals/${id}`,{method:'DELETE'});toast('Maaltijd verwijderd');loadMeals()};
function renderProductTable(){$('#product-table').innerHTML=products.map(p=>`<tr><td><strong>${escapeHtml(p.name)}</strong></td><td><span class="category-badge">${escapeHtml(p.category||'Overig')}</span></td><td>${fmt(p.energie)}</td><td>${fmt(p.eiwit)} g</td><td>${fmt(p.koolhydraten)} g</td><td>${fmt(p.vet)} g</td><td><button class="delete" onclick="deleteProduct(${p.id})">×</button></td></tr>`).join('')}
$('#nutrient-fields').innerHTML=KEYS.map(k=>`<label>${LABELS[k]}${k==='energie'?' (kcal)':' (g)'}<input name="${k}" type="number" min="0" step="0.001" value="0" required></label>`).join('');
$('#product-form').onsubmit=async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.target));try{await api('/api/products',{method:'POST',body:JSON.stringify(data)});e.target.reset();e.target.querySelectorAll('input[type=number]').forEach(i=>i.value=0);toast('Product toegevoegd');loadProducts()}catch(e){toast(e.message)}};
window.deleteProduct=async id=>{try{await api(`/api/products/${id}`,{method:'DELETE'});toast('Product verwijderd');loadProducts()}catch(e){toast(e.message)}};
function escapeHtml(s){return String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
// Een product toevoegen zonder de maaltijdmaker te verlaten.
const nutrientInputs=KEYS.map(k=>`<label>${LABELS[k]}${k==='energie'?' (kcal)':' (g)'}<input name="${k}" type="number" min="0" step="0.001" value="0" required></label>`).join('');
$('#quick-nutrient-fields').innerHTML=nutrientInputs;
const productDialog=$('#product-dialog');
let productPickerTarget={type:'meal'};
let activeCatalogCategory='Alle';
const catalogDialog=$('#catalog-dialog');
$('#quick-product').onclick=()=>{productPickerTarget={type:'meal'};productDialog.showModal()};
$('#close-product-dialog').onclick=$('#cancel-product-dialog').onclick=()=>productDialog.close();
$('#new-meal-from-products').onclick=()=>navigate('builder');
$('#quick-product-form').onsubmit=async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.target));try{const product=await api('/api/products',{method:'POST',body:JSON.stringify(data)});products.push(product);products.sort((a,b)=>a.name.localeCompare(b.name,'nl'));e.target.reset();e.target.querySelectorAll('input[type=number]').forEach(i=>i.value=0);productDialog.close();renderProductTable();updateCategoryOptions();selectCatalogProduct(product);toast(`${product.name} toegevoegd`)}catch(error){toast(error.message)}};

function productCategories(){return [...new Set(['Overig',...products.map(product=>product.category||'Overig')])].sort((a,b)=>a.localeCompare(b,'nl'))}
function updateCategoryOptions(){$('#category-options').innerHTML=productCategories().map(category=>`<option value="${escapeHtml(category)}"></option>`).join('')}
function openProductPicker(target){productPickerTarget=target;activeCatalogCategory='Alle';$('#catalog-search').value='';renderCatalog();catalogDialog.showModal();setTimeout(()=>$('#catalog-search').focus(),50)}
function renderCatalog(){const search=$('#catalog-search').value.trim().toLocaleLowerCase('nl');const categories=productCategories();$('#catalog-categories').innerHTML=['Alle',...categories].map(category=>`<button type="button" class="catalog-category ${category===activeCatalogCategory?'active':''}" data-catalog-category="${escapeHtml(category)}">${escapeHtml(category)}</button>`).join('');document.querySelectorAll('[data-catalog-category]').forEach(button=>button.onclick=()=>{activeCatalogCategory=button.dataset.catalogCategory;renderCatalog()});const filtered=products.filter(product=>(activeCatalogCategory==='Alle'||(product.category||'Overig')===activeCatalogCategory)&&(!search||product.name.toLocaleLowerCase('nl').includes(search)));$('#catalog-products').innerHTML=filtered.length?filtered.map(product=>`<button type="button" class="catalog-product" data-catalog-product="${product.id}"><small>${escapeHtml(product.category||'Overig')}</small><strong>${escapeHtml(product.name)}</strong><span>${fmt(product.energie)} kcal · ${fmt(product.eiwit)} g eiwit per 100 g</span></button>`).join(''):'<div class="catalog-empty">Geen producten gevonden in deze selectie.</div>';document.querySelectorAll('[data-catalog-product]').forEach(button=>button.onclick=()=>selectCatalogProduct(products.find(product=>product.id===Number(button.dataset.catalogProduct))))}
function selectCatalogProduct(product){if(!product)return;if(productPickerTarget.type==='meal'){const existing=rows.find(row=>row.key===productPickerTarget.rowKey);if(existing)existing.product_id=product.id;else rows.push({key:crypto.randomUUID(),product_id:product.id,grams:100});renderRows()}else if(productPickerTarget.type==='health'){const list=healthRows[productPickerTarget.category];const existing=list.find(row=>row.key===productPickerTarget.rowKey);if(existing)existing.product_id=product.id;else list.push({key:crypto.randomUUID(),product_id:product.id,grams:100});renderHealthEditor()}catalogDialog.close()}
$('#catalog-search').oninput=renderCatalog;
$('#close-catalog-dialog').onclick=()=>catalogDialog.close();
$('#catalog-new-product').onclick=()=>{catalogDialog.close();productDialog.showModal()};

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
  $('#health-categories').innerHTML=HEALTH_CATEGORIES.map(category=>`<article class="panel health-category"><div class="health-category-head"><h3>${HEALTH_LABELS[category]}</h3><div class="health-category-actions"><button class="secondary" data-health-meal="${category}">+ Maaltijd</button><button class="add" data-health-product="${category}">+ Product</button></div></div><div class="health-items">${healthRows[category].length?healthRows[category].map(row=>{const product=products.find(item=>item.id==row.product_id);return`<div class="health-item" data-health-key="${row.key}"><button class="product-choice" type="button"><span>${escapeHtml(product?.name||'Kies een product')}</span><small>${escapeHtml(product?.category||'Product wijzigen')}</small></button><input type="number" min="0.1" step="0.1" value="${row.grams}" aria-label="Gram"><button title="Verwijderen">×</button></div>`}).join(''):'<div class="health-empty">Nog niets toegevoegd.</div>'}</div></article>`).join('');
  document.querySelectorAll('[data-health-product]').forEach(button=>button.onclick=()=>openProductPicker({type:'health',category:button.dataset.healthProduct}));
  document.querySelectorAll('[data-health-meal]').forEach(button=>button.onclick=()=>openHealthMealPicker(button.dataset.healthMeal));
  document.querySelectorAll('.health-item').forEach(element=>{const row=HEALTH_CATEGORIES.flatMap(category=>healthRows[category].map(item=>({category,item}))).find(value=>value.item.key===element.dataset.healthKey);if(!row)return;const [choice,input,remove]=element.children;choice.onclick=()=>openProductPicker({type:'health',category:row.category,rowKey:row.item.key});input.oninput=()=>{row.item.grams=Math.max(0,Number(input.value)||0);calculateHealth()};remove.onclick=()=>{healthRows[row.category]=healthRows[row.category].filter(item=>item.key!==row.item.key);renderHealthEditor()}});
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

// Gecombineerd dagoverzicht en profielen van andere gebruikers.
let overviewUserId=null;
function ensureOverviewDates(){const today=localToday();if(!$('#overview-from').value)$('#overview-from').value=today;if(!$('#overview-to').value)$('#overview-to').value=today}
async function loadOverview(){ensureOverviewDates();const from=$('#overview-from').value,to=$('#overview-to').value;if(from>to){toast('De begindatum moet voor de einddatum liggen');return}const base=overviewUserId?`/api/users/${overviewUserId}/overview`:'/api/overview';try{const data=await api(`${base}?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`);renderOverview(data)}catch(error){toast(error.message)}}
function renderOverview(data){
  const isSelf=data.user.is_self,isDay=data.start_date===data.end_date;
  $('#overview-heading').textContent=isSelf?'Mijn overzicht':`Overzicht van ${data.user.username}`;
  $('#overview-subtitle').textContent=isSelf?'Voeding, fitness en energiebalans op één plek.':`Overzicht van ${data.user.username}.`;
  $('#overview-range').textContent=isDay?displayDate(data.start_date):`${displayDate(data.start_date)} t/m ${displayDate(data.end_date)}`;
  $('#overview-back').hidden=isSelf;
  $('#export-overview').hidden=!isSelf;
  $('#overview-eaten').textContent=fmt(data.food.totals.energie,0);
  $('#overview-burned').textContent=fmt(data.burned_kcal,0);
  $('#overview-burn-total').textContent=`${fmt(data.burned_kcal,0)} kcal`;
  $('#overview-balance').textContent=fmt(data.balance,0);
  $('#overview-food-total').textContent=`${fmt(data.food.totals.energie,0)} kcal`;
  const foodItems=data.food.days.flatMap(day=>HEALTH_CATEGORIES.flatMap(category=>day.categories[category].map(item=>({date:day.date,category,item}))));
  $('#overview-food').innerHTML=foodItems.length?foodItems.map(({date,category,item})=>`<div class="overview-detail"><strong>${escapeHtml(item.name)}</strong><span>${isDay?'':`${displayDate(date)} · `}${HEALTH_LABELS[category]} · ${fmt(item.grams)} g · ${fmt(item.nutrients.energie,0)} kcal</span></div>`).join(''):'<div class="overview-empty">Geen voeding geregistreerd.</div>';
  const fitnessItems=data.fitness.days.flatMap(day=>day.exercises.map(exercise=>({date:day.date,exercise})));
  const fitnessVolume=fitnessItems.flatMap(item=>item.exercise.sets).reduce((sum,set)=>sum+set.reps*set.weight,0);
  $('#overview-fitness-total').textContent=fitnessItems.length?`${fitnessItems.length} oefeningen · ${fmt(fitnessVolume,0)} kg volume`:'';
  $('#overview-fitness').innerHTML=fitnessItems.length?fitnessItems.map(({date,exercise})=>`<div class="overview-detail"><strong>${escapeHtml(exercise.name)}</strong><span>${isDay?'':`${displayDate(date)} · `}${exercise.sets.map(set=>`${set.reps}×${fmt(set.weight)} kg`).join(' · ')}</span></div>`).join(''):'<div class="overview-empty">Geen fitness geregistreerd.</div>';
  $('#overview-burn-days').innerHTML=data.burn.days.map(day=>`<div class="burn-day"><label><span>${displayDate(day.date)}</span><div><input data-burn-input="${day.date}" type="number" min="0" step="1" value="${Math.round(day.burned_kcal)}" ${isSelf?'':'disabled'}><small>kcal</small></div></label>${isSelf?`<button type="button" onclick="saveOverviewBurn('${day.date}')">Opslaan</button>`:''}</div>`).join('');
}
$('#overview-from').onchange=loadOverview;
$('#overview-to').onchange=loadOverview;
window.saveOverviewBurn=async dateValue=>{const input=document.querySelector(`[data-burn-input="${dateValue}"]`);try{await api(`/api/overview/${dateValue}/burn`,{method:'POST',body:JSON.stringify({burned_kcal:Number(input.value)})});toast(`Verbranding van ${displayDate(dateValue)} opgeslagen`);loadOverview()}catch(error){toast(error.message)}};
$('#overview-back').onclick=()=>{overviewUserId=null;loadOverview()};
document.querySelector('.nav[data-view="overview"]').onclick=()=>{overviewUserId=null;navigate('overview')};

const overviewExportDialog=$('#overview-export-dialog');
$('#export-overview').onclick=()=>{ensureOverviewDates();$('#overview-export-form').elements.from.value=$('#overview-from').value;$('#overview-export-form').elements.to.value=$('#overview-to').value;overviewExportDialog.showModal()};
$('#close-overview-export').onclick=$('#cancel-overview-export').onclick=()=>overviewExportDialog.close();
$('#overview-export-form').onsubmit=event=>{event.preventDefault();const data=new FormData(event.target);const from=data.get('from'),to=data.get('to');if(from>to){toast('De begindatum moet voor de einddatum liggen');return}window.location.href=`/api/overview-export.pdf?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`;overviewExportDialog.close()};

async function loadFriends(){try{const friends=await api('/api/friends');$('#friends-list').innerHTML=friends.length?friends.map(friend=>`<article class="panel friend-card"><div class="friend-profile"><span class="friend-avatar">${escapeHtml(friend.username.charAt(0).toUpperCase())}</span><div><strong>${escapeHtml(friend.username)}</strong><small>Bekijk dagoverzicht</small></div></div><button onclick="openFriendOverview(${friend.id})">Profiel bekijken</button></article>`).join(''):'<div class="panel overview-empty">Er zijn nog geen andere gebruikers.</div>'}catch(error){toast(error.message)}}
window.openFriendOverview=id=>{overviewUserId=id;ensureOverviewDates();navigate('overview')};

// MyFitness: oefeningen, sets en trainingen per dag.
let exercises=[];
let selectedFitnessExercise=null;
let fitnessSets=[];
let activeExerciseCategory='Alle';
const EXERCISE_BASE_CATEGORIES=['Benen','Borst','Rug','Triceps','Biceps','Schouders'];
const fitnessPicker=$('#exercise-picker-dialog');

function ensureFitnessDate(){if(!$('#fitness-date').value)$('#fitness-date').value=localToday()}
async function loadExercises(){try{exercises=await api('/api/exercises');updateExerciseCategoryOptions();renderExerciseList();renderExercisePicker()}catch(error){toast(error.message)}}
function exerciseCategories(){const custom=[...new Set(exercises.map(exercise=>exercise.category||'Overig'))].filter(category=>!EXERCISE_BASE_CATEGORIES.includes(category)).sort((a,b)=>a.localeCompare(b,'nl'));return[...EXERCISE_BASE_CATEGORIES,...custom]}
function updateExerciseCategoryOptions(){$('#exercise-category-options').innerHTML=exerciseCategories().map(category=>`<option value="${escapeHtml(category)}"></option>`).join('')}
function renderExerciseList(){if(!$('#exercise-list'))return;$('#exercise-count').textContent=`${exercises.length} oefeningen`;$('#exercise-list').innerHTML=exercises.map(exercise=>`<div class="exercise-list-item"><div class="exercise-name-group"><strong>${escapeHtml(exercise.name)}</strong><small>${escapeHtml(exercise.category||'Overig')}</small></div><button title="Verwijderen" onclick="deleteExercise(${exercise.id})">×</button></div>`).join('')}
$('#exercise-form').onsubmit=async event=>{event.preventDefault();const data=Object.fromEntries(new FormData(event.target));try{await api('/api/exercises',{method:'POST',body:JSON.stringify(data)});event.target.reset();toast('Oefening toegevoegd');await loadExercises()}catch(error){toast(error.message)}};
window.deleteExercise=async id=>{try{await api(`/api/exercises/${id}`,{method:'DELETE'});toast('Oefening verwijderd');loadExercises()}catch(error){toast(error.message)}};

function openExercisePicker(){activeExerciseCategory='Alle';$('#exercise-search').value='';renderExercisePicker();fitnessPicker.showModal();setTimeout(()=>$('#exercise-search').focus(),40)}
function renderExercisePicker(){if(!$('#exercise-picker-list'))return;const search=$('#exercise-search').value.trim().toLocaleLowerCase('nl');const categories=['Alle',...exerciseCategories()];$('#exercise-picker-categories').innerHTML=categories.map(category=>`<button type="button" class="exercise-category-filter ${category===activeExerciseCategory?'active':''}" data-exercise-category="${escapeHtml(category)}">${escapeHtml(category)}</button>`).join('');document.querySelectorAll('[data-exercise-category]').forEach(button=>button.onclick=()=>{activeExerciseCategory=button.dataset.exerciseCategory;renderExercisePicker()});const filtered=exercises.filter(exercise=>(activeExerciseCategory==='Alle'||exercise.category===activeExerciseCategory)&&exercise.name.toLocaleLowerCase('nl').includes(search));$('#exercise-picker-list').innerHTML=filtered.length?filtered.map(exercise=>`<button type="button" class="exercise-picker-option" data-exercise-id="${exercise.id}"><span class="exercise-muscle-badge">${escapeHtml(exercise.category||'Overig')}</span>${escapeHtml(exercise.name)}</button>`).join(''):'<div class="fitness-empty">Geen oefeningen gevonden.</div>';document.querySelectorAll('[data-exercise-id]').forEach(button=>button.onclick=()=>selectFitnessExercise(exercises.find(exercise=>exercise.id===Number(button.dataset.exerciseId))))}
function selectFitnessExercise(exercise){selectedFitnessExercise=exercise;fitnessSets=[newFitnessSet('warmingup'),newFitnessSet('warmingup'),newFitnessSet('work'),newFitnessSet('work')];fitnessPicker.close();renderFitnessEditor();$('#fitness-editor').hidden=false;$('#fitness-editor').scrollIntoView({behavior:'smooth',block:'center'})}
function newFitnessSet(setType){return{key:crypto.randomUUID(),set_type:setType,reps:'',weight:''}}
function renderFitnessEditor(){if(!selectedFitnessExercise)return;$('#fitness-editor-name').textContent=selectedFitnessExercise.name;const counts={warmingup:0,work:0};$('#fitness-set-list').innerHTML=fitnessSets.map(set=>{counts[set.set_type]++;const number=counts[set.set_type];return`<div class="fitness-set-row" data-fitness-set="${set.key}"><div class="fitness-set-type">${set.set_type==='warmingup'?'Warming-up':'Werkset'}<small>set ${number}</small></div><input type="number" min="1" step="1" placeholder="Bijv. 6" value="${set.reps}" aria-label="Herhalingen"><input type="number" min="0" step="0.25" placeholder="Bijv. 50" value="${set.weight}" aria-label="Gewicht in kilogram"><button title="Set verwijderen">×</button></div>`}).join('');document.querySelectorAll('[data-fitness-set]').forEach(element=>{const set=fitnessSets.find(item=>item.key===element.dataset.fitnessSet);const [,reps,weight,remove]=element.children;reps.oninput=()=>set.reps=reps.value;weight.oninput=()=>set.weight=weight.value;remove.onclick=()=>{fitnessSets=fitnessSets.filter(item=>item.key!==set.key);renderFitnessEditor()}})}
$('#pick-exercise').onclick=async()=>{ensureFitnessDate();if(!exercises.length)await loadExercises();openExercisePicker()};
$('#close-exercise-picker').onclick=()=>fitnessPicker.close();
$('#exercise-search').oninput=renderExercisePicker;
$('#new-exercise-from-picker').onclick=()=>{fitnessPicker.close();navigate('exercises');setTimeout(()=>$('#exercise-form input[name="name"]').focus(),50)};
$('#add-warmup-set').onclick=()=>{const lastWarmupIndex=fitnessSets.reduce((last,set,index)=>set.set_type==='warmingup'?index:last,-1);fitnessSets.splice(lastWarmupIndex+1,0,newFitnessSet('warmingup'));renderFitnessEditor()};
$('#add-work-set').onclick=()=>{fitnessSets.push(newFitnessSet('work'));renderFitnessEditor()};
$('#cancel-fitness-editor').onclick=()=>{$('#fitness-editor').hidden=true;selectedFitnessExercise=null;fitnessSets=[]};
$('#save-fitness-exercise').onclick=async()=>{if(!selectedFitnessExercise)return;if(fitnessSets.some(set=>set.reps===''||set.weight==='')){toast('Vul bij iedere set herhalingen en een gewicht in');return}const sets=fitnessSets.map(set=>({set_type:set.set_type,reps:Number(set.reps),weight:Number(set.weight)}));if(sets.some(set=>!Number.isInteger(set.reps)||set.reps<=0||!Number.isFinite(set.weight)||set.weight<0)){toast('Vul bij iedere set geldige herhalingen en een gewicht in');return}try{await api(`/api/fitness-days/${$('#fitness-date').value}/exercises`,{method:'POST',body:JSON.stringify({exercise_id:selectedFitnessExercise.id,sets})});toast(`${selectedFitnessExercise.name} opgeslagen`);$('#fitness-editor').hidden=true;selectedFitnessExercise=null;fitnessSets=[];loadFitnessDay()}catch(error){toast(error.message)}};

async function loadFitnessDay(){ensureFitnessDate();try{const day=await api(`/api/fitness-days/${$('#fitness-date').value}`);renderFitnessDay(day)}catch(error){toast(error.message)}}
function renderFitnessDay(day){$('#fitness-day-title').textContent=`Training van ${displayDate(day.date)}`;const volume=day.exercises.flatMap(exercise=>exercise.sets).reduce((sum,set)=>sum+set.reps*set.weight,0);$('#fitness-day-volume').textContent=volume?`${fmt(volume,0)} kg volume`:'';$('#fitness-day-exercises').innerHTML=day.exercises.length?day.exercises.map(exercise=>`<article class="fitness-log-card"><div class="fitness-log-head"><h3>${escapeHtml(exercise.name)}</h3><button title="Verwijderen" onclick="deleteWorkoutExercise(${exercise.id})">×</button></div><div class="fitness-log-sets">${exercise.sets.map(set=>`<div class="fitness-log-set"><small>${set.set_type==='warmingup'?'Warming-up':'Werkset'} ${set.set_order}</small><strong>${set.reps} × ${fmt(set.weight)} kg</strong></div>`).join('')}</div></article>`).join(''):'<div class="fitness-empty">Nog geen oefeningen opgeslagen voor deze dag.</div>'}
window.deleteWorkoutExercise=async id=>{try{await api(`/api/workout-exercises/${id}`,{method:'DELETE'});toast('Oefening uit training verwijderd');loadFitnessDay()}catch(error){toast(error.message)}};
$('#fitness-date').onchange=()=>{$('#fitness-editor').hidden=true;selectedFitnessExercise=null;fitnessSets=[];loadFitnessDay()};

const fitnessExportDialog=$('#fitness-export-dialog');
$('#export-fitness').onclick=()=>{const today=localToday();$('#fitness-export-form').elements.from.value=today;$('#fitness-export-form').elements.to.value=today;fitnessExportDialog.showModal()};
$('#close-fitness-export').onclick=$('#cancel-fitness-export').onclick=()=>fitnessExportDialog.close();
$('#fitness-export-form').onsubmit=event=>{event.preventDefault();const data=new FormData(event.target);const from=data.get('from'),to=data.get('to');if(from>to){toast('De begindatum moet voor de einddatum liggen');return}window.location.href=`/api/fitness-export.pdf?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`;fitnessExportDialog.close()};

api('/api/auth/me').then(user=>{$('#current-user').textContent=user.username;$('#current-user-avatar').textContent=user.username.charAt(0).toUpperCase()}).catch(()=>{});
loadProducts();
loadExercises();
ensureOverviewDates();
loadOverview();
