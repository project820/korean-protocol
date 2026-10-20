#!/usr/bin/env node
/** Execute one frozen L3 artifact with observed DOM controls and source-derived oracles.
 * No generated source is patched. Only the supplied HTML is served to the browser.
 */
import {createRequire} from 'node:module';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {resolve, join} from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

const sha = data => createHash('sha256').update(data).digest('hex');
// These recognizers use observed labels, never opaque generated IDs or DOM order.
function controlText(button) {return String(button.text || '').replace(/\s+/g,' ').trim();}
function resetLike(button) {
  return button.type==='reset'||/초기화|초기값|되돌|리셋|reset|복원|재설정|처음으로|(?:처음|시작|초기)\s*(?:상태|화면|값)/i.test(controlText(button));
}
function explicitGlobalReset(button) {
  return resetLike(button)&&/도구|화면|전체|전부|모든\s*(?:입력|값|상태|설정|기록)/.test(controlText(button));
}
function chooseResetButton(buttons) {
  const global=buttons.filter(explicitGlobalReset);
  if(global.length){
    if(global.length!==1)throw new Error('Global tool reset controls are ambiguous');
    if(!global[0].visible||global[0].disabled)throw new Error('Observed global tool reset is not visible and enabled');
    return global[0];
  }
  const matches=buttons.filter(button=>button.visible&&!button.disabled&&resetLike(button));
  if(matches.length!==1)throw new Error('Expected exactly one unscoped visible enabled reset control');
  return matches[0];
}
function domainActionButtons(buttons,pattern) {
  return buttons.filter(button=>button.visible&&!explicitGlobalReset(button)&&pattern.test(controlText(button)));
}
if(process.argv.includes('--recognize-controls')){
  // A dependency-free diagnostic path exercises the same production recognizers.
  try{
    let raw='';for await(const chunk of process.stdin)raw+=chunk;
    const input=JSON.parse(raw);
    if(input.operation!=='state'&&!Array.isArray(input.buttons))throw new Error('buttons must be an observed control array');
    let result;
    if(input.operation==='reset')result={control:chooseResetButton(input.buttons)};
    else if(input.operation==='action'){
      const matches=domainActionButtons(input.buttons,new RegExp(input.pattern));
      if(matches.length!==1)throw new Error('Domain action is not unambiguously recognized');
      result={control:matches[0]};
    }else if(input.operation==='state')result={current:currentState(input.state,input.spec)};
    else throw new Error('operation must be reset, action or state');
    console.log(JSON.stringify({status:'recognized',...result}));
  }catch(error){console.log(JSON.stringify({status:'unrecognized',error:String(error.message||error)}));process.exitCode=1;}
  process.exit(process.exitCode||0);
}
if(process.argv.includes('--help')){
  console.log('Usage: node browser_check.mjs --html PATH --case ID --output NEWDIR --output-sha256 HASH [--dataset JSON] [--oracle JSON] [--playwright-module-dir NODE_MODULES]\nUses existing Playwright only. KP_PLAYWRIGHT_MODULE_ROOT can select its node_modules directory. Changed dataset sources require a source-hashed explicit oracle.\n--recognize-controls reads a JSON operation/buttons/pattern request from stdin without loading a browser.');
  process.exit(0);
}
const args = {};
for (let i = 2; i < process.argv.length; i += 2) {
  if (!process.argv[i].startsWith('--') || process.argv[i + 1] === undefined) throw new Error('Use --html PATH --case ID --output DIR --output-sha256 HASH');
  args[process.argv[i].slice(2)] = process.argv[i + 1];
}
for (const key of ['html', 'case', 'output', 'output-sha256']) if (!args[key]) throw new Error('Missing --' + key);
if (!/^[a-f0-9]{64}$/.test(args['output-sha256'])) throw new Error('Invalid original output SHA256');
const supported = ['D07', 'D08', 'D09', 'E07', 'E08', 'E09'];
if (!supported.includes(args.case)) throw new Error('Unsupported frozen case: ' + args.case);
const moduleDir=args['playwright-module-dir']||process.env.KP_PLAYWRIGHT_MODULE_ROOT;
const require=moduleDir?createRequire(join(resolve(moduleDir),'package.json')):createRequire(import.meta.url);
const {chromium}=require('playwright');
const outputDir = resolve(args.output);
const htmlPath = resolve(args.html);
const html = await readFile(htmlPath);
await mkdir(outputDir, {recursive: false}); // Never overwrite an existing browser attempt.
const mainURL = 'http://kp-artifact.invalid/artifact.html';
const receipt = {
  tool: 'playwright', case_id: args.case, output_sha256: args['output-sha256'],
  html_sha256: sha(html), verifier_sha256: sha(await readFile(fileURLToPath(import.meta.url))),
  playwright_version: require('playwright/package.json').version,
  started: new Date().toISOString(), console_errors: [], blocked_requests: [],
  actions: {}, status: 'fail', observations: [],
};
let browser, context, page, staticContext;
const sleep = () => new Promise(done => setTimeout(done, 100));
const clean = text => String(text || '').replace(/\s+/g, ' ').trim();
const assert = (condition, message) => {if (!condition) throw new Error(message);};
const safeError = error => String(error?.message || error).slice(0, 1800);

async function action(name, operation) {
  try {
    const observations = await operation();
    receipt.actions[name] = {status: 'pass', observations};
  } catch (error) {
    receipt.actions[name] = {status: 'fail', observations: {error: safeError(error), snapshot: page ? await snapshot().catch(() => null) : null}};
  }
}

async function snapshot() {
  return page.evaluate(() => {
    const visible = element => {const box = element.getBoundingClientRect();return !!(box.width && box.height) && getComputedStyle(element).visibility !== 'hidden';};
    const label = element => Array.from(element.labels || []).map(x => x.innerText).join(' ') || element.getAttribute('aria-label') || '';
    const inputs = Array.from(document.querySelectorAll('input,select,textarea')).map((element, index) => ({
      index, tag: element.tagName.toLowerCase(), id: element.id, name: element.name, type: element.type,
      label: label(element), min: element.min, max: element.max, step: element.step,
      value: element.value, disabled: element.disabled, visible: visible(element),
      invalid: element.getAttribute('aria-invalid'), validity: element.validity ? element.validity.valid : true,
      validation_message: element.validationMessage || '',
      options: element.options ? Array.from(element.options).map(x => ({value:x.value,text:x.text,disabled:x.disabled})) : [],
    }));
    const buttons = Array.from(document.querySelectorAll('button,input[type="button"],input[type="submit"],input[type="reset"],[role="button"]')).map((element, index) => ({
      index, id: element.id, text: element.innerText || element.value || element.getAttribute('aria-label') || '',
      disabled: !!element.disabled || element.getAttribute('aria-disabled') === 'true', visible: visible(element), type: element.type || element.getAttribute('role'),
    }));
    const results = Array.from(document.querySelectorAll('output,[aria-live],[role="status"],[id],[class]')).filter(element => {
      if (!visible(element) || element.closest('[aria-hidden="true"]') || ['SCRIPT','STYLE','INPUT','BUTTON','SELECT','LABEL'].includes(element.tagName)) return false;
      const descriptor = element.id + ' ' + element.className;
      return element.tagName === 'OUTPUT' || element.hasAttribute('aria-live') || element.getAttribute('role') === 'status' || /result|total|remain|score|number|value|state|current|history|log|error/i.test(descriptor);
    }).map(element => ({tag:element.tagName.toLowerCase(),id:element.id,role:element.getAttribute('role'),text:element.innerText.trim(),
      aria_live:element.getAttribute('aria-live'),aria_current:element.getAttribute('aria-current'),aria_label:element.getAttribute('aria-label')})).filter(x => (x.text || /history|log/i.test(x.id)) && x.text.length < 2400);
    const errors = Array.from(document.querySelectorAll('[role="alert"],[aria-invalid="true"],[id*="error"],[class*="error"],[id*="Error"],[class*="Error"]')).filter(visible).map(e => e.innerText || e.validationMessage || '').filter(Boolean);
    const history = Array.from(document.querySelectorAll('[id]')).filter(e=>/history|log/i.test(e.id)&&!e.closest('[hidden]')&&getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden').map(e=>({id:e.id,text:e.innerText}));
    return {inputs, buttons, results, errors, history, body:document.body.innerText.slice(0, 12000),
      viewport:{width:innerWidth,height:innerHeight,scroll_width:document.documentElement.scrollWidth},
      active:{tag:document.activeElement?.tagName,id:document.activeElement?.id,text:document.activeElement?.innerText?.slice(0,120)}};
  });
}

const inputLocator = index => page.locator('input,select,textarea').nth(index);
const buttonLocator = index => page.locator('button,input[type="button"],input[type="submit"],input[type="reset"],[role="button"]').nth(index);

const numericCases = {
  D07: {names:[['a','amount','매주','금액'],['n','weeks','기간','주']],bounds:[[1000,5000],[1,12]],integer:[false,true],
    changed:[3000,4],extra:[[5000,12]],invalid:[[999,2],[2000,1.5],[2000,13]],calc:([a,n])=>10000+a*n,unit:'원'},
  D08: {names:[['r','rate','처리'],['t','hours','시간']],bounds:[[2,8],[0,6]],integer:[true,true],
    changed:[4,3],extra:[[8,6]],invalid:[[1,3],[3.5,3],[4,7],[4,2.5]],calc:([r,t])=>Math.max(0,24-r*t),unit:'건'},
  E07: {names:[['s','success','성공'],['f','failure','fail','실패']],bounds:[[0,10],[0,5]],integer:[true,true],initial:[2,1],
    changed:[0,3],extra:[[10,5]],invalid:[[11,1],[2,1.5]],calc:([s,f])=>7*s-2*f,unit:'점'},
  E08: {names:[['a','tens','십'],['b','ones','일의','일 자리']],bounds:[[1,9],[0,9]],integer:[true,true],initial:[3,2],
    changed:[7,0],extra:[[9,9]],invalid:[[0,2],[3,4.5]],calc:([a,b])=>10*a+b,unit:''},
};
const builtInSourceHashes={
  D07:'f1541038926ae05849bf1163b22055d675b8bf559f7f8411c73ac71ba4150f16',
  D08:'3a44916b73cd34eb3f0f9ef601eb09ec0d5799565fe0d09131301aa4e6357cf3',
  D09:'004239b2baa73c0873db5418f7d386c78118d7afcf8c7c1fd8e24377c7492583',
  E07:'c0cac644b3c62e77ce626a4b0218a9465f0466b68069cfde1a4c02241aa1778e',
  E08:'d59cda7268e197544d395899b25336adaf0fab0ec9a1adf9245756b485e28532',
  E09:'40bb6a1a51e2defac0d11fd23d239ee0a328e2281cc9229a0c14186c4fb5741f',
};

function chooseFields(state, spec) {
  const eligible = state.inputs.filter(field => field.visible && !field.disabled && !['hidden','button','submit','reset','checkbox','radio'].includes(field.type));
  const selected = [];
  for (let at = 0; at < spec.names.length; at++) {
    const scored = eligible.filter(x => !selected.some(y => y.index === x.index)).map(field => {
      let score = 0;
      for (const word of spec.names[at]) {
        if (field.id.toLowerCase() === word || field.name?.toLowerCase() === word) score += 10;
        if (word.length > 1 && (field.label + ' ' + field.id + ' ' + field.name).toLowerCase().includes(word)) score += 5;
        if (word.length === 1 && new RegExp('(^|[^A-Za-z])'+word+'([^A-Za-z]|$)').test(field.label)) score += 5;
      }
      if (Number(field.min) === spec.bounds[at][0] && Number(field.max) === spec.bounds[at][1] && field.min !== '' && field.max !== '') score += 8;
      const evidenceScore=score;
      // Paired sliders mirror free-entry fields; use the editable field for invalid examples.
      if(['number','text','tel','search'].includes(field.type))score+=20;
      return {field,score,evidenceScore};
    }).sort((a,b)=>b.score-a.score);
    assert(scored.length && scored[0].evidenceScore >= 5 && (!scored[1] || scored[0].score > scored[1].score), 'Cannot unambiguously identify numeric field '+at+' from labels/IDs/bounds');
    selected.push(scored[0].field);
  }
  return selected;
}

function validValues(values,spec) {
  return values.every((value,index)=>Number.isFinite(value) && value >= spec.bounds[index][0] && value <= spec.bounds[index][1] && (!spec.integer[index] || Number.isInteger(value)));
}

function numericResultCandidates(state) {
  const direct=state.results.filter(region=>region.tag==='output');
  const simple=state.results.filter(region=>/^\s*(?:총액|남은\s*건수|점수|만든\s*수|결과|N|S)?\s*[:=]?\s*[−–-]?\d[\d,]*(?:\.\d+)?\s*(?:원|건|점)?\s*$/.test(region.text));
  return direct.length?direct:simple.length?simple:state.results;
}
function resultMatches(state, expected, unit) {
  return numericResultCandidates(state).filter(region => {
    if (/error|history|log/i.test(region.id)) return false;
    const text = region.text.replace(/[−–]/g,'-').replace(/,/g,'');
    const numbers = Array.from(text.matchAll(/-?\d+(?:\.\d+)?/g), match=>Number(match[0]));
    // A bare number's unit can be printed by its adjacent result label/container.
    const unitVisible=!unit||text.includes(unit)||state.results.some(parent=>parent.text.includes(region.text)&&parent.text.includes(unit));
    return numbers.includes(expected) && unitVisible;
  });
}

async function calculate() {
  await sleep();
  const state = await snapshot();
  const buttons = state.buttons.filter(x=>x.visible && !x.disabled && /계산|적용|확인|결과 보기|갱신|업데이트/.test(x.text) && !/초기|다시|취소/.test(x.text));
  if (buttons.length === 1) {await buttonLocator(buttons[0].index).click();await sleep();}
}

async function setValues(fields, values, keyboard=false) {
  for (let i=0;i<fields.length;i++) {
    const locator = inputLocator(fields[i].index);
    assert(!['range','select-one','select-multiple'].includes(fields[i].type), 'Range/select-only UI cannot accept the required invalid numeric examples');
    if (keyboard) {
      await locator.focus();await locator.press('ControlOrMeta+A');await locator.pressSequentially(String(values[i]));await locator.press('Tab');
    } else {await locator.fill(String(values[i]));await locator.dispatchEvent('change');}
  }
  await calculate();
}

async function findReset() {
  const state=await snapshot();
  return chooseResetButton(state.buttons);
}

async function numericChecks(spec) {
  let fields, initialValues;
  await action('initial',async()=>{
    const state=await snapshot();fields=chooseFields(state,spec);assert(fields.every(x=>x.value.trim()!==''),'Initial numeric input is empty');initialValues=fields.map(x=>Number(x.value));
    assert(validValues(initialValues,spec),'Initial numeric inputs are outside source bounds');
    if(spec.initial) assert(initialValues.every((x,i)=>x===spec.initial[i]),'Initial inputs do not match the explicit task');
    const matches=resultMatches(state,spec.calc(initialValues),spec.unit);
    assert(matches.length,'Initial result does not show source-derived value '+spec.calc(initialValues));
    return {inputs:fields,expected:spec.calc(initialValues),result:matches};
  });
  await action('change',async()=>{
    assert(fields,'Numeric controls were not recognized');const examples=[];
    for(const values of [spec.changed,...spec.extra]) {
      const before=await snapshot();await setValues(fields,values);const after=await snapshot();
      assert(fields.every((x,i)=>Number(after.inputs[x.index].value)===values[i]),'UI changed or clamped valid input');
      const matches=resultMatches(after,spec.calc(values),spec.unit);
      assert(matches.length,'Changed result does not show '+spec.calc(values));
      const priorValues=fields.map(x=>Number(before.inputs[x.index].value));
      if(validValues(priorValues,spec)&&spec.calc(priorValues)!==spec.calc(values)) assert(matches.some(x=>!before.results.some(y=>y.id===x.id&&y.text===x.text)),'Result did not visibly change after input');
      examples.push({values,expected:spec.calc(values),result:matches});
    } return examples;
  });
  await action('invalid',async()=>{
    assert(fields,'Numeric controls were not recognized');const examples=[];
    for(const values of spec.invalid) {
      await setValues(fields,spec.changed);await setValues(fields,values);const state=await snapshot();
      assert(fields.every((x,i)=>values[i]===''?state.inputs[x.index].value==='':Number(state.inputs[x.index].value)===values[i]),'Invalid input was silently changed/clamped');
      const visibleErrors=state.errors.filter(text=>/오류|유효|범위|정수|입력|보류|허용|이상|이하|미만|초과|해야|invalid|error/i.test(text));
      assert(visibleErrors.length,'Invalid input has no visible error explanation');
      const invalidFields=fields.map(x=>state.inputs[x.index]).filter(x=>x.invalid==='true'||x.validity===false);
      if(spec.invalidMustWithholdResult)assert(!numericResultCandidates(state).some(x=>/\d/.test(x.text)),'Invalid or empty input still exposes a numeric result');
      examples.push({values,invalid_fields:invalidFields,visible_errors:visibleErrors,result:state.results});
    }return examples;
  });
  await action('reset',async()=>{
    assert(fields&&initialValues,'Initial numeric state is unknown');const reset=await findReset();await buttonLocator(reset.index).click();await sleep();
    const state=await snapshot();const values=fields.map(x=>Number(state.inputs[x.index].value));
    assert(values.every((x,i)=>x===initialValues[i]),'Reset did not restore original input values');
    assert(resultMatches(state,spec.calc(initialValues),spec.unit).length,'Reset did not restore the initial result');
    assert(!fields.some(x=>state.inputs[x.index].invalid==='true'),'Reset left invalid input state');
    return {control:reset,values,result:state.results};
  });
  await layoutCheck();
  await action('keyboard',async()=>{
    assert(fields&&initialValues,'Initial numeric state is unknown');await setValues(fields,spec.changed,true);const changed=await snapshot();
    assert(resultMatches(changed,spec.calc(spec.changed),spec.unit).length,'Keyboard edits did not update the result');
    const reset=await findReset();await buttonLocator(reset.index).focus();await buttonLocator(reset.index).press('Enter');await sleep();const state=await snapshot();
    assert(fields.every((x,i)=>Number(state.inputs[x.index].value)===initialValues[i]),'Keyboard reset did not restore initial inputs');
    return {changed_result:changed.results,reset_control:reset,final_inputs:fields.map(x=>state.inputs[x.index])};
  });
}

async function layoutCheck() {
  await action('narrow',async()=>{
    await page.setViewportSize({width:320,height:900});await sleep();
    const state=await snapshot();
    const layout=await page.evaluate(()=>Array.from(document.querySelectorAll('input,select,textarea,button,[role="button"]')).filter(e=>{const r=e.getBoundingClientRect();return r.width&&r.height}).map(e=>{const r=e.getBoundingClientRect();return {id:e.id,text:(e.innerText||e.getAttribute('aria-label')||'').slice(0,100),left:r.left,right:r.right,width:r.width}}));
    await page.screenshot({path:join(outputDir,'narrow.png'),fullPage:true});
    assert(state.viewport.scroll_width<=322,'Document has horizontal overflow at 320px');
    assert(layout.every(x=>x.left>=-2&&x.right<=322),'A visible control lies outside the 320px viewport');
    return {viewport:state.viewport,controls:layout,screenshot:'narrow.png'};
  });
}

const machineCases={
  D09:{states:['대기','확인 중','완료'],initial:'대기',actions:{start:/검사.*시작|시작/,pass:/통과/,cancel:/취소/},
    chain:[['start','확인 중'],['pass','완료']],branch:[['start','확인 중'],['cancel','대기']],invalid:'pass',invalidSetup:[],allowHiddenInvalid:true,resetSetup:['start','pass'],keyboardReturn:'cancel'},
  E09:{states:['정지','재생','일시정지'],initial:'정지',actions:{start:/시작/,pause:/멈춤|일시정지/,resume:/계속|재개/,stop:/종료/},
    chain:[['start','재생'],['pause','일시정지'],['resume','재생'],['stop','정지']],branch:[['start','재생'],['pause','일시정지']],invalid:'start',invalidSetup:['start','pause'],requireHistory:true,requireVisibleInvalidError:true},
};
const observedMachineActions=new Set();

function currentState(state,spec) {
  const compact=value=>String(value||'').replace(/\s+/g,'');
  const candidates=state.results.filter(region=>!region.aria_hidden).map(region=>({region,names:spec.states.filter(name=>compact(region.text).includes(compact(name)))}))
    .map(x=>({...x,names:x.names.filter(name=>!x.names.some(other=>other!==name&&other.includes(name)))}))
    .filter(x=>x.names.length===1&&!/history|log|error/i.test(x.region.id));
  const evidence=candidates.map(item=>{
    const region=item.region,name=item.names[0],exact=compact(region.text)===compact(name);
    const labelled=compact(region.text).replace(/^(?:현재)?(?:상태|단계|화면)(?:[:：=]|는|가)?/,'')!==compact(region.text)
      &&compact(region.text).replace(/^(?:현재)?(?:상태|단계|화면)(?:[:：=]|는|가)?/,'').startsWith(compact(name));
    const live=region.aria_live&&region.aria_live!=='off';
    const semantic=exact&&(region.tag==='output'||live||region.role==='status'||region.aria_current==='true'
      ||/현재\s*(?:상태|단계|화면)/.test(region.aria_label||''));
    // IDs only corroborate exact displayed values; opaque IDs never establish a state.
    const named=exact&&/^(?:current[-_]?(?:state|status)|state(?:[-_]?(?:name|value|display|current))?)$/i.test(region.id||'');
    return {...item,exact,proof:labelled||semantic||named};
  });
  const proven=evidence.filter(item=>item.proof),pool=proven.length?proven:evidence.filter(item=>item.exact);
  const names=new Set(pool.map(item=>item.names[0]));
  if(names.size!==1)throw new Error('Current state is unknown or conflicting in observed state/status evidence');
  const regions=pool.map(item=>item.region).sort((a,b)=>a.text.length-b.text.length||String(a.id).localeCompare(String(b.id)));
  return {name:[...names][0],region:regions[0],evidence:regions};
}

async function machineAction(spec,name,{keyboard=false,allowDisabled=false}={}) {
  const state=await snapshot();const pattern=spec.actions[name];
  assert(pattern instanceof RegExp,'Oracle transition action is not defined: '+name);
  const matches=domainActionButtons(state.buttons,pattern);
  assert(matches.length<=1,'Transition buttons are ambiguous: '+name);
  if(matches.length===1) {
    const button=matches[0];
    if(button.disabled) {assert(allowDisabled,'Required transition button is disabled: '+name);return {blocked:'disabled',control:button};}
    const locator=buttonLocator(button.index);if(keyboard){await locator.focus();await locator.press('Enter');}else await locator.click();
    observedMachineActions.add(name);await sleep();return {control:button,mechanism:keyboard?'keyboard-enter':'click'};
  }
  if(allowDisabled&&spec.allowHiddenInvalid&&observedMachineActions.has(name)&&matches.length===0)return {blocked:'previously observed action is not exposed in this state',action:name};
  const select=state.inputs.filter(x=>x.visible&&!x.disabled&&x.tag==='select'&&x.options.some(option=>!explicitGlobalReset(option)&&pattern.test(clean(option.text))));
  assert(select.length===1,'Transition control is not unambiguously recognized: '+name);
  const options=select[0].options.filter(x=>!explicitGlobalReset(x)&&pattern.test(clean(x.text)));assert(options.length===1,'Transition option is ambiguous: '+name);
  if(options[0].disabled){assert(allowDisabled,'Required transition option is disabled: '+name);return {blocked:'disabled-option',option:options[0]};}
  await inputLocator(select[0].index).selectOption(options[0].value);
  const updated=await snapshot();const run=updated.buttons.filter(x=>x.visible&&!x.disabled&&/실행|적용|동작|전이/.test(x.text)&&!explicitGlobalReset(x));
  assert(run.length===1,'Transition select has no unambiguous execute control');
  const locator=buttonLocator(run[0].index);if(keyboard){await locator.focus();await locator.press('Enter');}else await locator.click();
  observedMachineActions.add(name);await sleep();return {select:select[0],option:options[0],control:run[0],mechanism:keyboard?'keyboard-enter':'select-and-click'};
}

async function machineReset(spec,keyboard=false) {
  const reset=await findReset();const locator=buttonLocator(reset.index);if(keyboard){await locator.focus();await locator.press('Enter');}else await locator.click();await sleep();
  const state=await snapshot();assert(currentState(state,spec).name===spec.initial,'Reset did not restore '+spec.initial);return {control:reset,state};
}

async function ensureInitial(spec,keyboard=false){
  const current=currentState(await snapshot(),spec);
  if(current.name===spec.initial)return {already_initial:current};
  return machineReset(spec,keyboard);
}

function historyState(state) {
  const entries=state.history;
  assert(entries.length,'Player history region cannot be identified');
  return entries.map(x=>({id:x.id,text:clean(x.text)}));
}

async function machineChecks(spec) {
  let originalHistory;
  await action('initial',async()=>{
    const state=await snapshot();const current=currentState(state,spec);assert(current.name===spec.initial,'Incorrect initial state');
    if(spec.requireHistory)originalHistory=historyState(state);
    return {current,buttons:state.buttons,history:originalHistory||null};
  });
  await action('change',async()=>{
    const observations=[];
    for(const [name,expected] of spec.chain){const control=await machineAction(spec,name);const state=await snapshot();const current=currentState(state,spec);assert(current.name===expected,'Transition '+name+' did not produce '+expected);observations.push({name,expected,current,control});}
    await ensureInitial(spec);
    for(const [name,expected] of spec.branch){const control=await machineAction(spec,name);const current=currentState(await snapshot(),spec);assert(current.name===expected,'Branch '+name+' did not produce '+expected);observations.push({name,expected,current,control});}
    return observations;
  });
  await action('invalid',async()=>{
    const cases=spec.invalidCases||[{setup:spec.invalidSetup||[],action:spec.invalid}],observations=[];
    assert(Array.isArray(cases)&&cases.length,'Oracle invalid transition cases are missing');
    for(const invalid of cases){
      assert(Array.isArray(invalid.setup)&&spec.actions[invalid.action],'Oracle invalid transition case is malformed');
      await ensureInitial(spec);for(const name of invalid.setup)await machineAction(spec,name);
      const before=currentState(await snapshot(),spec);const control=await machineAction(spec,invalid.action,{allowDisabled:true});const after=await snapshot();const current=currentState(after,spec);
      assert(current.name===before.name,'Forbidden transition changed the state');
      if(spec.requireVisibleInvalidError&&!control.blocked)assert(after.errors.length||/허용하지|허용되지|불가|잘못|오류|실행할 수 없/.test(after.body),'Forbidden transition has no visible error state');
      observations.push({attempt:invalid.action,setup:invalid.setup,before,after:current,control,errors:after.errors});
    }
    return observations.length===1?observations[0]:{cases:observations};
  });
  await action('reset',async()=>{
    const setups=spec.resetSetups||[spec.resetSetup||[]],observations=[];
    assert(Array.isArray(setups)&&setups.length,'Oracle reset setup cases are missing');
    for(const setup of setups){
      assert(Array.isArray(setup),'Oracle reset setup is malformed');
      await ensureInitial(spec);for(const name of setup)await machineAction(spec,name);
      const reset=await machineReset(spec);
      if(spec.requireHistory){
        assert(originalHistory,'Initial history could not be observed');const history=historyState(reset.state);assert(JSON.stringify(history)===JSON.stringify(originalHistory),'Whole reset did not clear history to its initial state');
        observations.push({setup,current:currentState(reset.state,spec),control:reset.control,history});
      }else observations.push({setup,current:currentState(reset.state,spec),control:reset.control});
    }
    return observations.length===1?observations[0]:{cases:observations};
  });
  await layoutCheck();
  await action('keyboard',async()=>{
    await ensureInitial(spec,true);const control=await machineAction(spec,'start',{keyboard:true});const current=currentState(await snapshot(),spec);assert(current.name===spec.chain[0][1],'Keyboard transition did not change state');
    if(spec.keyboardReturn)await machineAction(spec,spec.keyboardReturn,{keyboard:true});else await machineReset(spec,true);
    const final=currentState(await snapshot(),spec);assert(final.name===spec.initial,'Keyboard return did not restore initial state');return {control,changed:current,final};
  });
}

async function selectedOracle(){
  let sourceHash=null,datasetHash=null;
  if(args.dataset){
    const raw=await readFile(resolve(args.dataset));const dataset=JSON.parse(raw.toString());
    const cases=Array.isArray(dataset)?dataset:[...(dataset.development||[]),...(dataset.evaluation||[])];
    const matches=cases.filter(item=>item.id===args.case);assert(matches.length===1,'Dataset must contain exactly one selected case');
    assert(matches[0].modality==='L3'&&typeof matches[0].source==='string','Dataset case is not an L3 source');
    sourceHash=sha(Buffer.from(matches[0].source));datasetHash=sha(raw);
    receipt.dataset_sha256=datasetHash;receipt.source_sha256=sourceHash;
  }
  if(!args.oracle){
    if(sourceHash)assert(sourceHash===builtInSourceHashes[args.case],'Changed source requires an explicit --oracle JSON; refusing the old case formula');
    receipt.oracle_binding=sourceHash?'built-in oracle matched exact source SHA256':'built-in case ID only; no dataset supplied';
    return numericCases[args.case]?{kind:'numeric',spec:numericCases[args.case]}:{kind:'machine',spec:machineCases[args.case]};
  }
  assert(args.dataset,'--oracle requires --dataset to bind the oracle to the exact source');
  const raw=await readFile(resolve(args.oracle));const config=JSON.parse(raw.toString());receipt.oracle_sha256=sha(raw);
  if(config.dataset_sha256)assert(config.dataset_sha256===datasetHash,'Oracle dataset hash mismatch');
  const oracle=config.cases?.[args.case];assert(oracle&&oracle.source_sha256===sourceHash,'Oracle source SHA256 mismatch');
  receipt.oracle_binding='explicit oracle matched exact source SHA256';
  const spec={...oracle.spec};
  if(oracle.kind==='numeric'){
    for(const field of ['names','bounds','integer','changed','invalid'])assert(Array.isArray(spec[field]),'Numeric oracle lacks '+field);
    const count=spec.names.length;assert(count>=1&&count<=4&&spec.bounds.length===count&&spec.integer.length===count&&spec.changed.length===count,'Numeric oracle input dimensions disagree');
    const polynomial=(formula,values)=>{
      assert(formula&&Number.isFinite(formula.constant)&&Array.isArray(formula.terms),'Numeric formula must contain constant and explicit product terms');
      let value=formula.constant;for(const term of formula.terms){assert(Number.isFinite(term.coefficient)&&Array.isArray(term.inputs)&&term.inputs.every(i=>Number.isInteger(i)&&i>=0&&i<count),'Invalid numeric formula term');value+=term.coefficient*term.inputs.reduce((product,index)=>product*values[index],1);}return value;
    };
    const formula=spec.formula;assert(formula,'Numeric oracle lacks formula');
    spec.calc=values=>{let value;if(formula.kind==='floor_division'){const denominator=polynomial(formula.denominator,values);assert(denominator!==0,'Oracle floor division by zero');value=Math.floor(polynomial(formula.numerator,values)/denominator);}else value=polynomial(formula,values);if(Number.isFinite(formula.floor))value=Math.max(formula.floor,value);if(Number.isFinite(formula.ceiling))value=Math.min(formula.ceiling,value);return value;};
    spec.extra=spec.extra||[];spec.unit=spec.unit||'';
    assert(validValues(spec.changed,spec)&&spec.invalid.length,'Numeric oracle lacks valid change and invalid examples');
    return {kind:'numeric',spec};
  }
  assert(oracle.kind==='machine'&&Array.isArray(spec.states)&&spec.states.includes(spec.initial)&&Array.isArray(spec.chain)&&Array.isArray(spec.branch),'Malformed state-machine oracle');
  spec.actions=Object.fromEntries(Object.entries(spec.actions||{}).map(([name,pattern])=>[name,new RegExp(pattern)]));
  assert(spec.actions.start&&spec.actions[spec.invalid]&&spec.chain.length,'Machine oracle lacks start/invalid transitions');
  return {kind:'machine',spec};
}

async function captureStaticVisibleText(){
  staticContext=await browser.newContext({viewport:{width:1280,height:900},javaScriptEnabled:false,offline:true,serviceWorkers:'block',acceptDownloads:false});
  await staticContext.route('**/*',async route=>{
    const request=route.request();
    if(request.url()===mainURL&&request.isNavigationRequest())await route.fulfill({status:200,contentType:'text/html; charset=utf-8',body:html});
    else{receipt.blocked_requests.push({phase:'static-js-disabled',url:request.url(),method:request.method(),resource_type:request.resourceType()});await route.abort('blockedbyclient');}
  });
  const staticPage=await staticContext.newPage();await staticPage.goto(mainURL,{waitUntil:'load',timeout:10000});
  const text={javascript_enabled:false,html_sha256:sha(html),title:await staticPage.title(),body:await staticPage.locator('body').innerText(),labels:await staticPage.locator('label,button,output,[role="status"],[role="alert"]').allTextContents(),language_status:'requires_source_review'};
  text.suspected_non_korean_segments=Array.from(new Set((text.title+'\n'+text.body).match(/[\u3040-\u30ff\u3400-\u9fff]+/gu)||[]));
  await staticPage.screenshot({path:join(outputDir,'static-js-disabled.png'),fullPage:true});
  const screenshot=await readFile(join(outputDir,'static-js-disabled.png'));text.screenshot={path:'static-js-disabled.png',sha256:sha(screenshot)};
  const encoded=Buffer.from(JSON.stringify(text,null,2)+'\n');await writeFile(join(outputDir,'static-visible-text.json'),encoded,{flag:'wx'});
  receipt.static_visible_text={path:'static-visible-text.json',sha256:sha(encoded),language_status:'requires_source_review',javascript_enabled:false,suspected_non_korean_segments:text.suspected_non_korean_segments,screenshot:text.screenshot};
  await staticContext.close();staticContext=null;
}

try {
  const oracle=await selectedOracle();
  browser=await chromium.launch({channel:'chrome',headless:true});
  receipt.browser_version=browser.version();
  await captureStaticVisibleText();
  context=await browser.newContext({viewport:{width:1280,height:900},serviceWorkers:'block',acceptDownloads:false,offline:true});
  if(typeof context.routeWebSocket==='function')await context.routeWebSocket('**/*',socket=>{receipt.blocked_requests.push({url:socket.url(),resource_type:'websocket'});socket.close();});
  await context.route('**/*',async route=>{
    const request=route.request();
    if(request.url()===mainURL&&request.isNavigationRequest()) await route.fulfill({status:200,contentType:'text/html; charset=utf-8',body:html});
    else {receipt.blocked_requests.push({url:request.url(),method:request.method(),resource_type:request.resourceType()});await route.abort('blockedbyclient');}
  });
  page=await context.newPage();page.setDefaultTimeout(4000);page.setDefaultNavigationTimeout(10000);
  page.on('pageerror',error=>receipt.console_errors.push({type:'pageerror',message:safeError(error)}));
  page.on('console',message=>{if(message.type()==='error')receipt.console_errors.push({type:'console',message:message.text().slice(0,1800)});});
  await page.goto(mainURL,{waitUntil:'load'});await context.setOffline(true);await sleep();
  receipt.initial_snapshot=await snapshot();await page.screenshot({path:join(outputDir,'initial.png'),fullPage:true});
  if(oracle.kind==='numeric')await numericChecks(oracle.spec);else await machineChecks(oracle.spec);
  receipt.final_snapshot=await snapshot();await page.screenshot({path:join(outputDir,'final.png'),fullPage:true});
  const screenshot=await readFile(join(outputDir,'final.png'));
  receipt.screenshot={path:'final.png',sha256:sha(screenshot)};
  await writeFile(join(outputDir,'observed-dom.json'),JSON.stringify({initial:receipt.initial_snapshot,final:receipt.final_snapshot},null,2)+'\n');
  receipt.status=Object.keys(receipt.actions).length===6&&Object.values(receipt.actions).every(x=>x.status==='pass')&&!receipt.console_errors.length&&!receipt.blocked_requests.length?'pass':'fail';
} catch(error) {
  receipt.observations.push({fatal_error:safeError(error)});
  for(const name of ['initial','change','invalid','reset','narrow','keyboard'])if(!receipt.actions[name])receipt.actions[name]={status:'fail',observations:{error:'Browser flow did not reach this action'}};
  if(page)try{await page.screenshot({path:join(outputDir,'fatal.png'),fullPage:true});const data=await readFile(join(outputDir,'fatal.png'));receipt.screenshot={path:'fatal.png',sha256:sha(data)};}catch{}
} finally {
  receipt.finished=new Date().toISOString();
  if(context)await context.close().catch(()=>{});if(staticContext)await staticContext.close().catch(()=>{});if(browser)await browser.close().catch(()=>{});
  await writeFile(join(outputDir,'receipt.json'),JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify({case_id:args.case,status:receipt.status,actions:Object.fromEntries(Object.entries(receipt.actions).map(([k,v])=>[k,v.status])),console_errors:receipt.console_errors.length,blocked_requests:receipt.blocked_requests.length,receipt:join(outputDir,'receipt.json')}));
}
process.exitCode=receipt.status==='pass'?0:1;
