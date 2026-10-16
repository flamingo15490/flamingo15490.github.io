import {createVault} from '/private-viewer.js';
/* Province selections show city-named albums; the map never loads city geometry. */
'use strict';
(() => {
  const root=document.querySelector('[data-travel-gallery]');
  if(!root)return;
  const {places,regions,city_names,private_config,other_photos=[]}=JSON.parse(document.getElementById('travel-gallery-data').textContent);
  const allPhotos=places.flatMap(place=>place.photos.map(photo=>({...photo,placeId:place.id,placeName:place.name,provinceId:place.province_id})));
  const options=document.getElementById('place-options');
  const albums=document.getElementById('gallery-albums');
  const reset=document.getElementById('gallery-reset');
  const dialog=document.getElementById('gallery-lightbox');
  const fullImage=document.getElementById('lightbox-image');
  const svg=document.getElementById('travel-atlas');
  const viewport=document.getElementById('atlas-viewport');
  const provincePaths=[...svg.querySelectorAll('[data-region]')];
  const hover=document.getElementById('atlas-hover');
  const visitedRegions=regions.filter(r=>places.some(p=>p.province_id===r.id&&p.photos.length));
  const vault=createVault(private_config);
  let privatePhotos=[],unlockAttempt=0,lightboxRequest=0;
  let privateObserver;
  let selected='';
  let activeView='travel';
  const viewTabs=[...root.querySelectorAll('[data-gallery-view]')];
  let visiblePhotos=[];
  let lightboxIndex=0;
  let opener;
  let transform={x:0,y:0,k:1};
  const pointers=new Map();
  let gesture;
  let dragged=false;
  root.dataset.mapState='ready';
  const text=(tag,value,className)=>{const el=document.createElement(tag);el.textContent=value;if(className)el.className=className;return el;};
  function shortName(name){return name.replace(/维吾尔自治区$|壮族自治区$|回族自治区$|自治区$|特别行政区$|省$|市$/,'');}
  document.getElementById('place-total').textContent=visitedRegions.length;
  document.getElementById('photo-total').textContent=allPhotos.length;
  options.querySelector('span').textContent=allPhotos.length;
  visitedRegions.forEach(region=>{
    const button=text('button',shortName(region.name),'place-option');button.type='button';button.dataset.province=region.id;
    button.setAttribute('aria-pressed','false');
    button.append(text('span',String(allPhotos.filter(p=>p.provinceId===region.id).length)));options.append(button);
  });
  function thumbnail(photo){
    const image=document.createElement('img');
    if(photo.private){
      image.alt=photo.alt;image.width=photo.width;image.height=photo.height;image.loading='lazy';image.decoding='async';
      const load=async()=>{
        try{
          const field=image.clientWidth*(window.devicePixelRatio||1)>photo.thumbnail_width?'thumbnail_large':'thumbnail';
          const url=await vault.image(photo,field);if(vault.unlocked&&image.isConnected)image.src=url;
        }catch(error){if(error.name!=='AbortError')image.alt='照片暂时未能加载';}
      };
      if('IntersectionObserver' in window){
        privateObserver??=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){privateObserver.unobserve(entry.target);entry.target.loadPrivatePhoto();}}),{rootMargin:'200px'});
        image.loadPrivatePhoto=load;privateObserver.observe(image);
      }else{queueMicrotask(load);}
      return image;
    }
    image.src='/'+photo.thumbnail;
    const variants=[{file:photo.thumbnail,width:photo.thumbnail_width},{file:photo.thumbnail_large,width:photo.thumbnail_large_width}].filter(v=>v.file&&v.width);
    image.srcset=variants.map(v=>`/${v.file} ${v.width}w`).join(', ');
    image.sizes='(max-width:700px) calc((100vw - 52px) / 2), (max-width:1120px) calc((100vw - 100px) / 3), 355px';
    image.alt=photo.alt;image.width=photo.width;image.height=photo.height;
    image.loading='lazy';image.decoding='async';image.dataset.photoId=photo.id;
    return image;
  }
  async function showLightbox(index){
    if(!visiblePhotos.length)return;
    lightboxIndex=(index+visiblePhotos.length)%visiblePhotos.length;
    const photo=visiblePhotos[lightboxIndex];
    const request=++lightboxRequest;
    fullImage.removeAttribute('src');fullImage.alt=photo.alt;fullImage.width=photo.width;fullImage.height=photo.height;
    document.getElementById('lightbox-position').textContent=`${lightboxIndex+1} / ${visiblePhotos.length}`;
    document.getElementById('lightbox-caption').textContent=`${photo.placeName}${photo.date?' · '+photo.date:''}${photo.caption?' · '+photo.caption:''}`;
    document.getElementById('lightbox-prev').disabled=visiblePhotos.length<2;
    document.getElementById('lightbox-next').disabled=visiblePhotos.length<2;
    if(!photo.private){fullImage.src='/'+photo.file;return;}
    const stage=root.querySelector('.lightbox-stage');stage.setAttribute('aria-busy','true');
    try{const url=await vault.image(photo,'file');if(request===lightboxRequest&&vault.unlocked&&dialog.open)fullImage.src=url;}
    catch(error){if(request===lightboxRequest&&error.name!=='AbortError')document.getElementById('lightbox-caption').textContent='照片暂时未能加载，请重试。';}
    finally{if(request===lightboxRequest)stage.removeAttribute('aria-busy');}

  }
  function openPhoto(index,button){opener=button;showLightbox(index);dialog.showModal();document.body.classList.add('gallery-modal-open');}
  function photoFigure(photo,index){
    const figure=document.createElement('figure');figure.className='gallery-photo';
    const button=document.createElement('button');button.type='button';button.className='photo-open';button.setAttribute('aria-label',`放大照片：${photo.alt}`);
    button.append(thumbnail(photo));button.addEventListener('click',()=>openPhoto(index,button));figure.append(button);
    if(photo.caption||photo.date){const caption=document.createElement('figcaption');if(photo.caption)caption.append(text('span',photo.caption));if(photo.date)caption.append(text('small',photo.date));figure.append(caption);}
    return figure;
  }
  function render(){
    const region=regions.find(r=>r.id===selected);
    const selectedAlbums=selected?places.filter(p=>p.province_id===selected):[];
    visiblePhotos=selectedAlbums.flatMap(place=>place.photos.map(photo=>({...photo,placeId:place.id,placeName:place.name,provinceId:place.province_id})));
    document.getElementById('gallery-selection').textContent=region?region.name:'旅行相册';
    document.getElementById('gallery-result-count').textContent=region?`${selectedAlbums.length} 个相册 · ${visiblePhotos.length} 张照片`:`${visitedRegions.length} 个地区 · ${places.length} 个相册`;
    reset.hidden=!selected;
    options.querySelectorAll('[data-province]').forEach(button=>{const active=button.dataset.province===selected;button.classList.toggle('is-selected',active);button.setAttribute('aria-pressed',String(active));});
    svg.querySelectorAll('[data-label-region]').forEach(label=>{label.classList.toggle('has-travel',visitedRegions.some(r=>r.id===label.dataset.labelRegion));label.classList.toggle('is-selected',label.dataset.labelRegion===selected);});
    provincePaths.forEach(path=>{const active=path.dataset.region===selected;path.classList.toggle('is-selected',active);path.setAttribute('aria-pressed',String(active));});
    albums.replaceChildren();
    if(!selected){
      const grid=document.createElement('div');grid.className='photo-grid province-albums';
      visitedRegions.forEach(r=>{
        const photos=allPhotos.filter(p=>p.provinceId===r.id);
        const card=document.createElement('article');card.className='province-album';
        const button=document.createElement('button');button.type='button';button.className='province-album-open';button.setAttribute('aria-label',`查看${r.name}相册`);
        button.append(thumbnail(photos[0]),text('span',shortName(r.name),'province-album-name'),text('small',`${photos.length} 张照片`));
        button.addEventListener('click',()=>selectRegion(r.id));card.append(button);grid.append(card);
      });
      albums.append(grid);
    }else{
      let offset=0;
      selectedAlbums.forEach(place=>{
        const section=document.createElement('section');section.className='city-album';
        const heading=document.createElement('div');heading.className='city-album-heading';heading.append(text('h3',place.name),text('span',`${place.photos.length} 张照片`));
        const grid=document.createElement('div');grid.className='photo-grid';
        place.photos.forEach(photo=>{const index=offset++;grid.append(photoFigure({...photo,placeName:place.name},index));});
        section.append(heading,grid);albums.append(section);
      });
    }
    const pending=selected?(city_names[selected]||[]).filter(city=>!selectedAlbums.some(place=>place.city_id===city.id||place.city_parent_id===city.id)):[];
    if(selected&&!selectedAlbums.length&&!pending.length)pending.push({name:shortName(region.name)});
    document.getElementById('pending-cities').hidden=!pending.length;
    document.getElementById('pending-city-names').textContent=pending.map(city=>city.name).join(' · ');
    document.getElementById('gallery-empty').hidden=selected?selectedAlbums.length>0||pending.length>0:visitedRegions.length>0;
    document.getElementById('gallery-empty-title').textContent='照片还在整理中';
  }
  function setView(view){
    if(activeView==='private'&&view!=='private')lockPrivate(false);
    activeView=view;
    viewTabs.forEach(tab=>{const active=tab.dataset.galleryView===view;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;});
    document.getElementById('gallery-travel-panel').hidden=view!=='travel';
    document.getElementById('gallery-other-panel').hidden=view!=='other';
    document.getElementById('gallery-private-panel').hidden=view!=='private';
    if(view==='travel'){render();sizeAtlas();}
    else if(view==='other'){
      visiblePhotos=other_photos.map(photo=>({...photo,placeName:'其他图片'}));
      const grid=document.getElementById('other-photo-grid');grid.replaceChildren();
      visiblePhotos.forEach((photo,index)=>grid.append(photoFigure(photo,index)));
      document.getElementById('other-empty').hidden=visiblePhotos.length>0;
      document.getElementById('other-photo-count').textContent=visiblePhotos.length+' 张照片';
    }
  }
  function lockPrivate(focus=true){
    unlockAttempt++;privateObserver?.disconnect();privateObserver=undefined;
    if(activeView==='private'&&dialog.open)dialog.close();
    vault.lock();privatePhotos=[];
    if(activeView==='private')visiblePhotos=[];
    document.getElementById('private-photo-grid').replaceChildren();
    document.getElementById('private-content').hidden=true;document.getElementById('private-gate').hidden=false;
    document.getElementById('private-password').value='';document.getElementById('private-status').textContent='';
    document.getElementById('private-photo-count').textContent='';document.getElementById('private-unlock').disabled=false;
    fullImage.removeAttribute('src');fullImage.alt='';document.getElementById('lightbox-caption').textContent='';document.getElementById('lightbox-position').textContent='';
    if(focus)document.getElementById('private-password').focus();
  }
  document.getElementById('private-unlock-form').addEventListener('submit',async event=>{
    event.preventDefault();const input=document.getElementById('private-password');const password=input.value;input.value='';
    const attempt=++unlockAttempt,button=document.getElementById('private-unlock'),status=document.getElementById('private-status');
    button.disabled=true;status.textContent='正在解锁…';
    try{
      const photos=await vault.unlock(password);if(attempt!==unlockAttempt)return;
      privatePhotos=photos;visiblePhotos=photos;
      const grid=document.getElementById('private-photo-grid');grid.replaceChildren();
      privatePhotos.forEach((photo,index)=>grid.append(photoFigure(photo,index)));
      document.getElementById('private-photo-count').textContent=photos.length+' 张照片';
      document.getElementById('private-gate').hidden=true;document.getElementById('private-content').hidden=false;status.textContent='';
      document.getElementById('private-lock').focus();
    }catch(error){
      if(attempt===unlockAttempt){vault.lock();status.textContent=error.name==='OperationError'?'密码不正确，请重试。':(!window.isSecureContext||!crypto.subtle?'请使用支持安全连接的新版浏览器。':'暂时无法解锁，请检查网络后重试。');input.focus();}
    }finally{if(attempt===unlockAttempt)button.disabled=false;}
  });
  document.getElementById('private-lock').addEventListener('click',()=>lockPrivate());
  window.addEventListener('pagehide',()=>lockPrivate(false));
  window.addEventListener('pageshow',()=>lockPrivate(false));
  document.getElementById('private-password').value='';
  viewTabs.forEach((tab,index)=>{
    tab.addEventListener('click',()=>setView(tab.dataset.galleryView));
    tab.addEventListener('keydown',event=>{
      let next;
      if(event.key==='ArrowRight')next=(index+1)%viewTabs.length;
      if(event.key==='ArrowLeft')next=(index+viewTabs.length-1)%viewTabs.length;
      if(event.key==='Home')next=0;
      if(event.key==='End')next=viewTabs.length-1;
      if(next!==undefined){event.preventDefault();viewTabs[next].focus();setView(viewTabs[next].dataset.galleryView);}
    });
  });
  function selectRegion(id){selected=selected===id?'':id;render();if(!selected)overview();}
  root.addEventListener('click',event=>{const button=event.target.closest('[data-province]');if(button)selectRegion(button.dataset.province);});
  reset.addEventListener('click',()=>{selected='';render();overview();options.querySelector('[data-province=""]').focus();});
  document.getElementById('lightbox-close').addEventListener('click',()=>dialog.close());
  document.getElementById('lightbox-prev').addEventListener('click',()=>showLightbox(lightboxIndex-1));
  document.getElementById('lightbox-next').addEventListener('click',()=>showLightbox(lightboxIndex+1));
  dialog.addEventListener('keydown',event=>{if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();showLightbox(lightboxIndex+(event.key==='ArrowRight'?1:-1));}});
  dialog.addEventListener('click',event=>{if(event.target===dialog)dialog.close();});
  dialog.addEventListener('close',()=>{lightboxRequest++;root.querySelector('.lightbox-stage').removeAttribute('aria-busy');document.body.classList.remove('gallery-modal-open');fullImage.removeAttribute('src');if(opener?.isConnected)opener.focus();});
  function updateTransform(){
    viewport.setAttribute('transform',`translate(${transform.x} ${transform.y}) scale(${transform.k})`);
    svg.dataset.zoom=transform.k.toFixed(2);svg.classList.toggle('is-detailed',transform.k>2);
    svg.querySelectorAll('[data-label-x]').forEach(label=>label.setAttribute('transform',`translate(${label.dataset.labelX} ${label.dataset.labelY}) scale(${1/transform.k})`));
    document.getElementById('map-zoom-out').disabled=transform.k<=1;document.getElementById('map-zoom-in').disabled=transform.k>=12;
  }
  function zoom(factor,anchor={x:500,y:400}){const k=Math.max(1,Math.min(12,transform.k*factor));if(k===1){overview();return;}const ratio=k/transform.k;transform={x:anchor.x-(anchor.x-transform.x)*ratio,y:anchor.y-(anchor.y-transform.y)*ratio,k};updateTransform();}
  function overview(){transform={x:0,y:0,k:1};updateTransform();}
  provincePaths.forEach(path=>{
    path.classList.toggle('has-travel',visitedRegions.some(r=>r.id===path.dataset.region));
    path.addEventListener('click',()=>{if(!dragged)selectRegion(path.dataset.region);});
    path.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();event.stopPropagation();selectRegion(path.dataset.region);}});
    path.addEventListener('pointerenter',()=>{hover.textContent=regions.find(r=>r.id===path.dataset.region).name;hover.hidden=false;});
    path.addEventListener('pointerleave',()=>{hover.hidden=true;});
  });
  function svgPoint(event) {
    const point=new DOMPoint(event.clientX,event.clientY).matrixTransform(svg.getScreenCTM().inverse());
    return {x:point.x,y:point.y};
  }
  function rebaseGesture() {
    const points=[...pointers.values()];
    if(!points.length){gesture=null;return;}
    if(points.length===1)gesture={point:points[0],start:{...transform}};
    else {const [a,b]=points;gesture={point:{x:(a.x+b.x)/2,y:(a.y+b.y)/2},distance:Math.hypot(a.x-b.x,a.y-b.y),start:{...transform}};}
  }
  const compactMap=()=>window.matchMedia('(max-width:700px), (pointer:coarse)').matches;
  svg.addEventListener('pointerdown',event=>{
    if(event.button>0)return;
    // Touch gestures belong to page scrolling, never to the map.
    if(event.pointerType==='touch'||compactMap()){dragged=false;return;}
    pointers.set(event.pointerId,svgPoint(event));
    if(pointers.size===1)dragged=false;
    rebaseGesture();
    // Keep click targets intact; pointer capture is only needed for gestures.
  });
  svg.addEventListener('pointermove',event=>{
    if(event.pointerType==='touch'||compactMap()||!pointers.has(event.pointerId)||!gesture)return;
    const point=svgPoint(event);pointers.set(event.pointerId,point);
    if(pointers.size===1){
      const dx=point.x-gesture.point.x,dy=point.y-gesture.point.y;
      if(Math.hypot(dx,dy)>4)dragged=true;
      if(dragged){svg.setPointerCapture(event.pointerId);transform={...gesture.start,x:gesture.start.x+dx,y:gesture.start.y+dy};}
    } else {
      dragged=true;
      const [a,b]=[...pointers.values()];const middle={x:(a.x+b.x)/2,y:(a.y+b.y)/2};
      const distance=Math.hypot(a.x-b.x,a.y-b.y);
      const k=Math.max(1,Math.min(12,gesture.start.k*distance/Math.max(gesture.distance,1)));
      const ratio=k/gesture.start.k;
      transform={k,x:middle.x-(gesture.point.x-gesture.start.x)*ratio,y:middle.y-(gesture.point.y-gesture.start.y)*ratio};
    }
    if(dragged){hover.hidden=true;svg.classList.add('is-dragging');updateTransform();}
  });
  function endPointer(event) {pointers.delete(event.pointerId);rebaseGesture();if(!pointers.size)svg.classList.remove('is-dragging');}
  svg.addEventListener('pointerup',endPointer);svg.addEventListener('pointercancel',endPointer);
  svg.addEventListener('pointerleave',event=>{if(!svg.hasPointerCapture(event.pointerId))endPointer(event);});
  svg.addEventListener('wheel',event=>{if(!event.ctrlKey||compactMap())return;event.preventDefault();zoom(Math.exp(-event.deltaY*.003),svgPoint(event));},{passive:false});
  svg.addEventListener('keydown',event=>{
    if(event.target!==svg)return;
    if(['+','=','-','Home','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key))event.preventDefault();
    if(event.key==='+'||event.key==='=')zoom(1.5);
    if(event.key==='-')zoom(1/1.5);
    if(event.key==='Home')overview();
    const d={ArrowLeft:[50,0],ArrowRight:[-50,0],ArrowUp:[0,50],ArrowDown:[0,-50]}[event.key];
    if(d){transform.x+=d[0];transform.y+=d[1];updateTransform();}
  });

  document.getElementById('map-overview').addEventListener('click',overview);
  document.getElementById('map-zoom-in').addEventListener('click',()=>zoom(1.5));
  document.getElementById('map-zoom-out').addEventListener('click',()=>zoom(1/1.5));
  const shell=root.querySelector('.interactive-map-shell');
  document.getElementById('map-expand').addEventListener('click',async()=>{
    try{if(document.fullscreenElement)await document.exitFullscreen();else await shell.requestFullscreen();}
    catch{const status=document.getElementById('map-status');status.textContent='当前浏览器暂不支持展开地图。';status.hidden=false;}
  });
  document.addEventListener('fullscreenchange',()=>document.getElementById('map-expand').setAttribute('aria-label',document.fullscreenElement?'收起地图':'展开地图'));
  function sizeAtlas(){
    svg.setAttribute('viewBox',shell.clientWidth<560?'175 0 650 800':'0 0 1000 800');
    svg.setAttribute('aria-label',compactMap()?'中国旅行地图，34个省级行政区；点击省份查看相册，使用按钮缩放地图':'中国旅行地图，34个省级行政区；支持拖动、缩放和地点选择');
    if(compactMap()){pointers.clear();gesture=null;dragged=false;svg.classList.remove('is-dragging');}
  }
  window.addEventListener('resize',sizeAtlas);sizeAtlas();render();overview();
})();
