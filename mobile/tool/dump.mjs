// prints semantics nodes for debugging
export async function dump(p){ console.log(await p.evaluate(() => [...document.querySelectorAll('flt-semantics [role], flt-semantics')].map(e => `${e.getAttribute('role')||''}|${e.getAttribute('aria-label')||''}|${(e.innerText||'').slice(0,40).replace(/\n/g,'/')}`).filter((v,i,a)=>a.indexOf(v)===i).slice(0,40).join('\n'))); }
