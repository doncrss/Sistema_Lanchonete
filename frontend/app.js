const API_BASE = (window.LANCHOTECH_API_URL || window.location.origin).replace(/\/$/, "");
const state = { products: [], cart: new Map(), category: "Todos", search: "", adminToken: "" };
const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const statusNames = {
  recebido: "Recebido",
  em_preparo: "Em preparo",
  pronto: "Pronto",
  saiu_para_entrega: "Saiu para entrega",
  concluido: "Concluído",
  cancelado: "Cancelado",
};
const productIcons = {
  hambúrguer: "burger.svg",
  acompanhamento: "fries.svg",
  bebida: "drink.svg",
  sobremesa: "drink.svg",
  combo: "burger.svg",
};

const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (character) => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
})[character]);

async function api(path, options = {}, admin = false) {
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (admin && state.adminToken) headers["X-Admin-Token"] = state.adminToken;
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    let message = `Não foi possível concluir a operação (${response.status}).`;
    try {
      const body = await response.json();
      message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      message = response.statusText || message;
    }
    if (admin && response.status === 401) {
      state.adminToken = "";
      sessionStorage.removeItem("lanchotech-admin-token");
    }
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return response.json();
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(showToast.timeout);
  showToast.timeout = setTimeout(() => toast.classList.remove("visible"), 3200);
}

function iconFor(type) {
  return productIcons[String(type).toLocaleLowerCase("pt-BR")] || "burger.svg";
}

function visibleProducts() {
  return state.products.filter((product) => {
    const matchesCategory = state.category === "Todos" || product.tipo === state.category;
    const matchesSearch = `${product.nome} ${product.tipo}`.toLocaleLowerCase("pt-BR")
      .includes(state.search.toLocaleLowerCase("pt-BR"));
    return matchesCategory && matchesSearch;
  });
}

function renderCategories() {
  const categories = ["Todos", ...new Set(state.products.map((product) => product.tipo))];
  if (!categories.includes(state.category)) state.category = "Todos";
  $("#categories").innerHTML = categories.map((category) => `
    <button class="category-button${state.category === category ? " active" : ""}" type="button" data-category="${escapeHtml(category)}">${escapeHtml(category)}</button>
  `).join("");
}

function renderProducts() {
  const products = visibleProducts();
  $("#menu-message").hidden = products.length > 0;
  $("#menu-message").textContent = state.products.length
    ? "Não encontramos produtos com esse filtro."
    : "Nosso cardápio está vazio no momento.";
  $("#products").innerHTML = products.map((product) => `
    <article class="product-card">
      <div class="product-visual">
        <span class="product-chip">${escapeHtml(product.tipo)}</span>
        <img class="product-icon" src="assets/${iconFor(product.tipo)}" alt="">
      </div>
      <div class="product-info">
        <h3>${escapeHtml(product.nome)}</h3>
        <p>Preparado na hora com ingredientes selecionados.</p>
        <div class="product-buy">
          <span class="product-price">${currency.format(product.preco)}</span>
          <button class="add-button" type="button" data-add="${product.id}" aria-label="Adicionar ${escapeHtml(product.nome)}">+</button>
        </div>
      </div>
    </article>
  `).join("");
}

function cartTotals() {
  let count = 0;
  let total = 0;
  for (const [productId, quantity] of state.cart) {
    const product = state.products.find((item) => item.id === productId);
    if (!product) continue;
    count += quantity;
    total += product.preco * quantity;
  }
  return { count, total };
}

function renderCart() {
  const items = [...state.cart.entries()].filter(([id]) => state.products.some((product) => product.id === id));
  const { count, total } = cartTotals();
  $("#cart-count").textContent = count;
  $("#cart-empty").hidden = items.length > 0;
  $("#cart-items").innerHTML = items.map(([id, quantity]) => {
    const product = state.products.find((item) => item.id === id);
    return `
      <div class="cart-line">
        <div><div class="cart-line-name">${escapeHtml(product.nome)}</div><div class="cart-line-price">${currency.format(product.preco * quantity)}</div></div>
        <div class="quantity-control">
          <button type="button" data-quantity="-1" data-id="${id}" aria-label="Remover um ${escapeHtml(product.nome)}">−</button>
          <span>${quantity}</span>
          <button type="button" data-quantity="1" data-id="${id}" aria-label="Adicionar um ${escapeHtml(product.nome)}">+</button>
        </div>
      </div>`;
  }).join("");
  $("#cart-bottom").hidden = items.length === 0;
  $("#cart-total").textContent = currency.format(total);
  $("#checkout-total").textContent = currency.format(total);
}

async function loadProducts() {
  $("#menu-message").hidden = false;
  try {
    state.products = await api("/api/produtos");
    renderCategories();
    renderProducts();
    renderCart();
  } catch (error) {
    $("#menu-message").textContent = `Não foi possível carregar o cardápio: ${error.message}`;
    showToast("Confira se a API está disponível e tente atualizar a página.");
  }
}

function changeQuantity(productId, delta) {
  const quantity = (state.cart.get(productId) || 0) + delta;
  if (quantity <= 0) state.cart.delete(productId);
  else state.cart.set(productId, quantity);
  renderCart();
}

function updateAddressField() {
  const isDelivery = $("#order-local").value === "entrega";
  $("#address-field").hidden = !isDelivery;
  $("#address-field input").required = isDelivery;
}

async function submitCheckout(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const values = new FormData(form);
  const errorElement = $("#checkout-error");
  const button = form.querySelector('button[type="submit"]');
  errorElement.textContent = "";
  button.disabled = true;
  button.textContent = "Enviando pedido...";
  try {
    const order = await api("/api/pedidos", {
      method: "POST",
      body: JSON.stringify({
        local: values.get("local"),
        cliente: {
          nome: values.get("nome"),
          contato: values.get("contato"),
          endereco: values.get("endereco"),
        },
        itens: [...state.cart].map(([produto_id, quantidade]) => ({ produto_id, quantidade })),
      }),
    });
    state.cart.clear();
    renderCart();
    form.reset();
    updateAddressField();
    $("#checkout-modal").close();
    $("#confirmation-copy").textContent =
      `Pedido #${order.id} recebido. Total de ${currency.format(order.total)}. A equipe já vai preparar tudo!`;
    $("#confirmation-modal").showModal();
  } catch (error) {
    errorElement.textContent = error.message;
  } finally {
    button.disabled = false;
    button.innerHTML = 'Enviar pedido <span aria-hidden="true">→</span>';
  }
}

function showAdminPane(name) {
  document.querySelectorAll(".admin-tab[data-tab]").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.tab === name);
  });
  $("#orders-pane").hidden = name !== "orders";
  $("#products-pane").hidden = name !== "products";
}

async function loadAdminOrders() {
  const container = $("#admin-orders");
  container.innerHTML = '<p class="admin-empty">Carregando pedidos...</p>';
  try {
    const orders = await api("/api/pedidos", {}, true);
    container.innerHTML = orders.length ? orders.map((order) => `
      <article class="admin-order">
        <div class="admin-order-head"><span>Pedido #${order.id} · ${escapeHtml(order.cliente_nome)}</span><span>${escapeHtml(statusNames[order.status] || order.status)}</span></div>
        <div class="admin-order-meta">${escapeHtml(order.local)} · ${escapeHtml(new Date(order.data_hora).toLocaleString("pt-BR"))}<br>${escapeHtml(order.cliente_contato)}${order.endereco_entrega ? ` · ${escapeHtml(order.endereco_entrega)}` : ""}</div>
        <div class="admin-order-items">${order.itens.map((item) => `${item.quantidade}× ${escapeHtml(item.nome)}`).join(" · ")}</div>
        <div class="admin-order-bottom"><strong>${currency.format(order.total)}</strong>
          <select data-status-order="${order.id}" aria-label="Atualizar status do pedido ${order.id}">
            ${Object.entries(statusNames).map(([value, name]) => `<option value="${value}"${value === order.status ? " selected" : ""}>${name}</option>`).join("")}
          </select>
        </div>
      </article>
    `).join("") : '<p class="admin-empty">Ainda não há pedidos.</p>';
    return true;
  } catch (error) {
    container.innerHTML = `<p class="admin-empty">${escapeHtml(error.message)}</p>`;
    return false;
  }
}

async function loadAdminProducts() {
  const container = $("#admin-products");
  container.innerHTML = '<p class="admin-empty">Carregando produtos...</p>';
  try {
    const products = await api("/api/produtos");
    container.innerHTML = products.map((product) => `
      <div class="admin-product">
        <div><strong>${escapeHtml(product.nome)}</strong><br><span>${escapeHtml(product.tipo)} · ${currency.format(product.preco)}</span></div>
        <button class="delete-product" type="button" data-delete-product="${product.id}">Excluir</button>
      </div>
    `).join("");
  } catch (error) {
    container.innerHTML = `<p class="admin-empty">${escapeHtml(error.message)}</p>`;
  }
}

async function enterAdmin(token) {
  state.adminToken = token;
  sessionStorage.setItem("lanchotech-admin-token", token);
  $("#admin-login").hidden = true;
  $("#admin-content").hidden = false;
  $("#admin-error").textContent = "";
  showAdminPane("orders");
  if (!await loadAdminOrders()) {
    state.adminToken = "";
    sessionStorage.removeItem("lanchotech-admin-token");
    $("#admin-content").hidden = true;
    $("#admin-login").hidden = false;
    $("#admin-error").textContent = $("#admin-orders").textContent;
  }
}

$("#categories").addEventListener("click", (event) => {
  const button = event.target.closest("[data-category]");
  if (!button) return;
  state.category = button.dataset.category;
  renderCategories();
  renderProducts();
});

$("#products").addEventListener("click", (event) => {
  const button = event.target.closest("[data-add]");
  if (!button) return;
  changeQuantity(Number(button.dataset.add), 1);
  showToast("Adicionado à sua sacola!");
});

$("#cart-items").addEventListener("click", (event) => {
  const button = event.target.closest("[data-quantity]");
  if (button) changeQuantity(Number(button.dataset.id), Number(button.dataset.quantity));
});

$("#search").addEventListener("input", (event) => {
  state.search = event.target.value;
  renderProducts();
});

$("#checkout-open").addEventListener("click", () => $("#checkout-modal").showModal());
$("#checkout-form").addEventListener("submit", submitCheckout);
$("#order-local").addEventListener("change", updateAddressField);
$("#admin-open").addEventListener("click", () => {
  $("#admin-modal").showModal();
  const savedToken = sessionStorage.getItem("lanchotech-admin-token");
  if (savedToken) enterAdmin(savedToken);
});
$("#admin-login").addEventListener("submit", async (event) => {
  event.preventDefault();
  const token = new FormData(event.currentTarget).get("token").trim();
  await enterAdmin(token);
});

document.querySelectorAll(".admin-tab[data-tab]").forEach((tab) => {
  tab.addEventListener("click", () => {
    showAdminPane(tab.dataset.tab);
    if (tab.dataset.tab === "orders") loadAdminOrders();
    else loadAdminProducts();
  });
});
$("#admin-logout").addEventListener("click", () => {
  state.adminToken = "";
  sessionStorage.removeItem("lanchotech-admin-token");
  $("#admin-content").hidden = true;
  $("#admin-login").hidden = false;
  $("#admin-login").reset();
});
$("#refresh-orders").addEventListener("click", loadAdminOrders);
$("#admin-orders").addEventListener("change", async (event) => {
  const select = event.target.closest("[data-status-order]");
  if (!select) return;
  try {
    await api(`/api/pedidos/${select.dataset.statusOrder}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: select.value }),
    }, true);
    showToast("Status do pedido atualizado.");
    await loadAdminOrders();
  } catch (error) {
    showToast(error.message);
    await loadAdminOrders();
  }
});
$("#product-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const values = new FormData(form);
  try {
    await api("/api/produtos", {
      method: "POST",
      body: JSON.stringify({
        nome: values.get("nome"),
        tipo: values.get("tipo"),
        preco: Number(values.get("preco")),
      }),
    }, true);
    form.reset();
    showToast("Produto adicionado ao cardápio.");
    await Promise.all([loadAdminProducts(), loadProducts()]);
  } catch (error) {
    showToast(error.message);
  }
});
$("#admin-products").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-delete-product]");
  if (!button || !window.confirm("Excluir este produto do cardápio?")) return;
  try {
    await api(`/api/produtos/${button.dataset.deleteProduct}`, { method: "DELETE" }, true);
    showToast("Produto excluído.");
    await Promise.all([loadAdminProducts(), loadProducts()]);
  } catch (error) {
    showToast(error.message);
  }
});
document.querySelectorAll("[data-close]").forEach((button) => {
  button.addEventListener("click", () => $(`#${button.dataset.close}`).close());
});
document.querySelectorAll("dialog").forEach((dialog) => {
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
});

updateAddressField();
loadProducts();
