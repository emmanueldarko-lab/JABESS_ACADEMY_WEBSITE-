// Progressive enhancement for the mobile navigation and small UI interactions.
document.addEventListener('DOMContentLoaded',()=>{document.querySelectorAll('.flash').forEach(el=>{setTimeout(()=>{el.style.opacity='0';el.style.transition='opacity .5s';},6000);});});
