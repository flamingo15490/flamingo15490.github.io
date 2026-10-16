import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {webcrypto} from 'node:crypto';
const source=await readFile(new URL('../private-viewer.js',import.meta.url),'utf8');
const {createVault}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const crypto=webcrypto,encoder=new TextEncoder(),originalFetch=globalThis.fetch;
const password='synthetic-test-password-123456789';
const salt=crypto.getRandomValues(new Uint8Array(16)),iterations=600000;
const material=await crypto.subtle.importKey('raw',encoder.encode(password),'PBKDF2',false,['deriveKey']);
const key=await crypto.subtle.deriveKey({name:'PBKDF2',hash:'SHA-256',salt,iterations},material,{name:'AES-GCM',length:256},false,['encrypt']);
const paths={manifest:'assets/gallery/locked/'+ '1'.repeat(32)+'.bin',small:'assets/gallery/locked/'+'2'.repeat(32)+'.bin',large:'assets/gallery/locked/'+'3'.repeat(32)+'.bin',display:'assets/gallery/locked/'+'4'.repeat(32)+'.bin'};
const assets=new Map(),plain=new Uint8Array([1,5,9,33]);
async function encrypted(path,data){
  const iv=crypto.getRandomValues(new Uint8Array(12));
  const body=await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:encoder.encode('gaomu-private-v1:'+path)},key,data);
  const bytes=new Uint8Array(16+body.byteLength);bytes.set(encoder.encode('GMP1'));bytes.set(iv,4);bytes.set(new Uint8Array(body),16);assets.set('/'+path,bytes);return bytes;
}
for(const path of [paths.small,paths.large,paths.display])await encrypted(path,plain);
await encrypted(paths.manifest,encoder.encode(JSON.stringify({schema_version:1,photos:[{id:'fixture',alt:'Fixture photo',file:paths.display,thumbnail:paths.small,thumbnail_large:paths.large,width:1600,height:1200}]})));
const config={salt:Buffer.from(salt).toString('base64'),iterations,manifest:{file:paths.manifest}};

test('private gallery authentication, integrity and memory cleanup',async t=>{
  globalThis.window={isSecureContext:true};
  globalThis.fetch=async(url,options={})=>{
    if(String(url).startsWith('blob:'))return originalFetch(url,options);
    if(options.signal?.aborted)throw new DOMException('Aborted','AbortError');
    assert.equal(options.credentials,'omit');assert.equal(options.cache,'no-store');
    const bytes=assets.get(url);return new Response(bytes?.slice()??null,{status:bytes?200:404});
  };
  try{
    await t.test('wrong password cannot open the manifest',async()=>{
      const vault=createVault(config);await assert.rejects(vault.unlock('definitely-wrong-password'),{name:'OperationError'});assert.equal(vault.unlocked,false);
    });
    await t.test('correct password opens photos; locking revokes URLs and access',async()=>{
      const vault=createVault(config),photos=await vault.unlock(password);assert.equal(photos.length,1);assert.equal(vault.unlocked,true);
      const url=await vault.image(photos[0],'file');assert.deepEqual(new Uint8Array(await(await originalFetch(url)).arrayBuffer()),plain);
      vault.lock();assert.equal(vault.unlocked,false);await assert.rejects(originalFetch(url));await assert.rejects(vault.image(photos[0],'file'),{name:'AbortError'});
    });
    await t.test('modified image ciphertext is rejected',async()=>{
      const vault=createVault(config),photos=await vault.unlock(password),original=assets.get('/'+paths.display),changed=original.slice();changed[changed.length-1]^=1;assets.set('/'+paths.display,changed);
      try{await assert.rejects(vault.image(photos[0],'file'),{name:'OperationError'});}finally{assets.set('/'+paths.display,original);vault.lock();}
    });
    await t.test('moving ciphertext to a different valid path is rejected',async()=>{
      const vault=createVault(config),photos=await vault.unlock(password),target='assets/gallery/locked/'+'5'.repeat(32)+'.bin';assets.set('/'+target,assets.get('/'+paths.display));
      try{await assert.rejects(vault.image({...photos[0],file:target},'file'),{name:'OperationError'});}finally{assets.delete('/'+target);vault.lock();}
    });
    await t.test('locking during unlock cannot restore an old session',async()=>{
      const vault=createVault(config),opening=vault.unlock(password);vault.lock();await assert.rejects(opening,{name:'AbortError'});assert.equal(vault.unlocked,false);
    });
  }finally{globalThis.fetch=originalFetch;delete globalThis.window;}
});
