/* Password-derived keys and decrypted photos live only in this page's memory. */
export function createVault(config){
  let key=null,epoch=0,controller=new AbortController();
  const objectUrls=new Set(),pending=new Map();
  const encoder=new TextEncoder();
  const validFile=file=>typeof file==='string'&&/^assets\/gallery\/locked\/[a-f0-9]{32}\.bin$/.test(file);
  function lock(){
    epoch++;key=null;controller.abort();controller=new AbortController();
    objectUrls.forEach(url=>URL.revokeObjectURL(url));objectUrls.clear();pending.clear();
  }
  async function decrypt(file,decryptionKey,signal){
    if(!validFile(file))throw new Error('Invalid encrypted asset');
    const response=await fetch('/'+file,{signal,cache:'no-store',credentials:'omit'});
    if(!response.ok)throw new Error('Encrypted asset unavailable');
    const bytes=new Uint8Array(await response.arrayBuffer());
    if(bytes.length<=32||String.fromCharCode(...bytes.subarray(0,4))!=='GMP1')throw new Error('Invalid encrypted asset');
    return crypto.subtle.decrypt({name:'AES-GCM',iv:bytes.subarray(4,16),additionalData:encoder.encode('gaomu-private-v1:'+file),tagLength:128},decryptionKey,bytes.subarray(16));
  }
  async function unlock(password){
    lock();const current=epoch,signal=controller.signal;
    if(!window.isSecureContext||!crypto.subtle)throw new Error('Secure browser required');
    const material=await crypto.subtle.importKey('raw',encoder.encode(password),'PBKDF2',false,['deriveKey']);
    const candidate=await crypto.subtle.deriveKey({name:'PBKDF2',hash:'SHA-256',salt:Uint8Array.from(atob(config.salt),c=>c.charCodeAt(0)),iterations:config.iterations},material,{name:'AES-GCM',length:256},false,['decrypt']);
    const plain=await decrypt(config.manifest.file,candidate,signal);
    if(current!==epoch)throw new DOMException('Locked','AbortError');
    const manifest=JSON.parse(new TextDecoder().decode(plain));
    if(manifest.schema_version!==1||!Array.isArray(manifest.photos))throw new Error('Invalid encrypted album');
    for(const photo of manifest.photos){
      if(typeof photo.id!=='string'||typeof photo.alt!=='string'||!['file','thumbnail','thumbnail_large'].every(field=>validFile(photo[field]))||!Number.isInteger(photo.width)||!Number.isInteger(photo.height)||photo.width<1||photo.height<1||Math.max(photo.width,photo.height)>1600)throw new Error('Invalid encrypted photo');
    }
    key=candidate;
    return manifest.photos.map(photo=>({...photo,private:true,placeName:'个照合照'}));
  }
  async function image(photo,field){
    if(!key)throw new DOMException('Locked','AbortError');
    const file=photo[field],current=epoch;
    if(pending.has(file))return pending.get(file);
    const job=decrypt(file,key,controller.signal).then(plain=>{
      if(current!==epoch)throw new DOMException('Locked','AbortError');
      const url=URL.createObjectURL(new Blob([plain],{type:'image/webp'}));objectUrls.add(url);return url;
    }).catch(error=>{if(current===epoch)pending.delete(file);throw error;});
    pending.set(file,job);return job;
  }
  return {unlock,image,lock,get unlocked(){return key!==null;}};
}
