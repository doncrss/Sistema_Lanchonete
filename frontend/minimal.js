const $ = (s) => document.querySelector(s);
const money = new Intl.NumberFormat("pt-BR", {style:"currency",currency:"BRL"});
const state = {products:[], cart:new Map(), category:"Todos", search:"", token:""};
const esc = (v) => String(v).replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
async function api(path, options={}, admin=false){
  const h={"Content-Type":"application/json",...(options.headers||{})}; if(admin&&state.token) h["X-Admin-Token"]=state.token;
  const r=await fetch(path,{...options,headers:h});
  if(!r.ok){let d="Erro na operação"; try{d=(await r.json()).detail||d}catch{} throw new Error(d)}
  return r.status===204?null:r.json();
}
function toast(t){const e=$("#toast");e.textContent=t;e.classList.add("visible");clearTimeout(toast.timer);toast.timer=setTimeout(()=>e.classList.remove("visible"),3000)}
function price(p, ids=[]){return p.preco+(p.variacoes||[]).filter(o=>ids.includes(o.id)).reduce((n,o)=>n+o.adicional,0)}
function visible(){return state.products.filter(p=>(state.category==="Todos"||p.tipo===state.category)&&`${p.nome} ${p.tipo}`.toLowerCase().includes(state.search.toLowerCase()))}
function render(){
  const cats=["Todos",...new Set(state.products.map(p=>p.tipo))]; if(!cats.includes(state.category))state.category="Todos";
  $("#categories").innerHTML=cats.map(c=>`<button class="category-button${c===state.category?" active":""}" data-category="${esc(c)}">${esc(c)}</button>`).join("");
  const ps=visible(); $("#message").hidden=ps.length>0; $("#message").textContent="Nenhum produto encontrado.";
  $("#products").innerHTML=ps.map(p=>{const groups=[...new Set((p.variacoes||[]).map(o=>o.nome))]; return `<article class="product-card"><div class="product-visual"><span class="product-chip">${esc(p.tipo)}</span><img class="product-icon" src="/assets/${p.tipo.toLowerCase()==="bebida"?"drink.svg":"burger.svg"}"></div><div class="product-info"><h3>${esc(p.nome)}</h3>${p.descricao?`<p class="product-description">${esc(p.descricao)}</p>`:""}${groups.map(g=>`<label class="variation-label">${esc(g)}<select class="variation-select" data-product="${p.id}" data-group="${esc(g)}">${p.variacoes.filter(o=>o.nome===g).map(o=>`<option value="${o.id}">${esc(o.valor)} ${o.adicional?"+ "+money.format(o.adicional):""}</option>`).join("")}</select></label>`).join("")}<div class="product-buy"><span class="product-price" data-price="${p.id}">${money.format(p.preco)}</span><button class="add-button" data-add="${p.id}">+</button></div></div></article>`}).join(""); renderCart();
}
function cart(){let count=0,total=0;for(const l of state.cart.values()){const p=state.products.find(p=>p.id===l.productId);if(p){count+=l.quantity;total+=price(p,l.variations)*l.quantity}}return{count,total}}
function renderCart(){const c=cart();$("#cart-count").textContent=c.count;$("#cart-empty").hidden=c.count>0;$("#cart-bottom").hidden=c.count===0;$("#cart-total").textContent=$("#checkout-total").textContent=money.format(c.total);
 $("#cart-items").innerHTML=[...state.cart].map(([k,l])=>{const p=state.products.find(p=>p.id===l.productId);return `<div class="cart-line"><div><div class="cart-line-name">${esc(p.nome)}</div><div class="cart-line-price">${money.format(price(p,l.variations)*l.quantity)}</div></div><div class="quantity-control"><button data-key="${k}" data-d="-1">−</button><span>${l.quantity}</span><button data-key="${k}" data-d="1">+</button></div></div>`}).join("");}
async function load(){try{state.products=await api("/api/produtos");render()}catch(e){$("#message").textContent=e.message}}

$("#categories").onclick=e=>{const b=e.target.closest("[data-category]");if(b){state.category=b.dataset.category;render()}};
$("#search").oninput=e=>{state.search=e.target.value;render()};
$("#products").onclick=e=>{const b=e.target.closest("[data-add]");if(!b)return;const p=state.products.find(p=>p.id===Number(b.dataset.add));const card=b.closest(".product-card");const ids=[...card.querySelectorAll(".variation-select")].map(s=>Number(s.value));const key=`${p.id}-${ids.join(".")}`;const line=state.cart.get(key);if(line)line.quantity++;else state.cart.set(key,{productId:p.id,comboId:p.combo_id,variations:ids,quantity:1});renderCart();toast("Adicionado à sacola!")};
$("#products").onchange=e=>{const s=e.target.closest(".variation-select");if(!s)return;const p=state.products.find(p=>p.id===Number(s.dataset.product));const card=s.closest(".product-card");const ids=[...card.querySelectorAll(".variation-select")].map(x=>Number(x.value));card.querySelector(".product-price").textContent=money.format(price(p,ids))};
$("#cart-items").onclick=e=>{const b=e.target.closest("[data-key]");if(!b)return;const l=state.cart.get(b.dataset.key);l.quantity+=Number(b.dataset.d);if(l.quantity<=0)state.cart.delete(b.dataset.key);renderCart()};

$("#checkout-open").onclick=()=>$("#checkout-modal").showModal();
$("#order-local").onchange=e=>{$("#address-field").hidden=e.target.value!=="entrega";$("#address-field input").required=e.target.value==="entrega"};
$("#checkout-form").onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target);try{await api("/api/pedidos",{method:"POST",body:JSON.stringify({local:f.get("local"),cliente:{nome:f.get("nome"),contato:f.get("contato"),endereco:f.get("endereco")||""},itens:[...state.cart.values()].map(l=>({produto_id:l.productId,quantidade:l.quantity,combo_id:l.comboId,variacao_ids:l.variations}))})});state.cart.clear();renderCart();e.target.reset();$("#checkout-modal").close();toast("Pedido enviado à cozinha!")}catch(err){$("#checkout-error").textContent=err.message}};

document.querySelectorAll("[data-close]").forEach(b=>b.onclick=()=>$("#"+b.dataset.close).close());
$("#admin-open").onclick=()=>{$("#admin-modal").showModal();const token=sessionStorage.getItem("lanchotech-admin-token");if(token)enterAdmin(token)};
async function enterAdmin(token){state.token=token;sessionStorage.setItem("lanchotech-admin-token",token);try{await loadOrders();$("#admin-login").hidden=true;$("#admin-content").hidden=false}catch(e){$("#admin-error").textContent=e.message;state.token="";sessionStorage.removeItem("lanchotech-admin-token")}}
$("#admin-login").onsubmit=e=>{e.preventDefault();enterAdmin(new FormData(e.target).get("token").trim())};
$("#admin-logout").onclick=()=>{state.token="";sessionStorage.removeItem("lanchotech-admin-token");$("#admin-content").hidden=true;$("#admin-login").hidden=false};
async function loadOrders(){const orders=await api("/api/pedidos",{},true);$("#admin-orders").innerHTML=orders.map(o=>`<article class="admin-order"><div class="admin-order-head"><span>#${o.id} · ${esc(o.cliente_nome)}</span><strong>${money.format(o.total)}</strong></div><div class="admin-order-meta">${esc(o.status)} · ${esc(o.local)}</div><select data-status="${o.id}"><option value="recebido">Recebido</option><option value="em_preparo">Em preparo</option><option value="pronto">Pronto</option><option value="saiu_para_entrega">Saiu para entrega</option><option value="concluido">Concluído</option><option value="cancelado">Cancelado</option></select></article>`).join("");}
$("#refresh-orders").onclick=loadOrders;
$("#admin-orders").onchange=async e=>{if(!e.target.dataset.status)return;try{await api(`/api/pedidos/${e.target.dataset.status}/status`,{method:"PATCH",body:JSON.stringify({status:e.target.value})},true);toast("Status atualizado!");loadOrders()}catch(err){toast(err.message)}};
async function loadAdminProducts(){const ps=await api("/api/produtos");$("#admin-products").innerHTML=ps.map(p=>`<article class="admin-product"><strong>${esc(p.nome)}</strong><span>${esc(p.tipo)} · ${money.format(p.preco)}</span>${p.combo_id?`<button class="delete-product" data-delete-combo="${p.combo_id}">Excluir combo</button>`:`<button class="delete-product" data-delete-product="${p.id}">Excluir</button>`}</article>`).join("")+`<form id="product-form" class="product-form"><h3>Novo produto</h3><div class="product-form-fields"><label class="field-label">Nome<input name="nome" required></label><label class="field-label">Categoria<input name="tipo" required></label><label class="field-label">Preço<input name="preco" type="number" step="0.01" required></label></div><button class="button button-primary">Adicionar</button></form>`;}
$("#products-tab").onclick=async()=>{$("#orders-pane").hidden=true;$("#products-pane").hidden=false;$("#orders-tab").classList.remove("active");$("#products-tab").classList.add("active");await loadAdminProducts()};
$("#orders-tab").onclick=()=>{$("#orders-pane").hidden=false;$("#products-pane").hidden=true;$("#orders-tab").classList.add("active");$("#products-tab").classList.remove("active")};
$("#admin-products").onsubmit=async e=>{if(e.target.id!=="product-form")return;e.preventDefault();const f=new FormData(e.target);try{await api("/api/produtos",{method:"POST",body:JSON.stringify({nome:f.get("nome"),tipo:f.get("tipo"),preco:Number(f.get("preco"))})},true);toast("Produto adicionado!");load();loadAdminProducts()}catch(err){toast(err.message)}};
$("#admin-products").onclick=async e=>{const b=e.target.closest("[data-delete-product]");if(!b||!confirm("Excluir produto?"))return;try{await api(`/api/produtos/${b.dataset.deleteProduct}`,{method:"DELETE"},true);toast("Produto excluído!");load();loadAdminProducts()}catch(err){toast(err.message)}};

load();
