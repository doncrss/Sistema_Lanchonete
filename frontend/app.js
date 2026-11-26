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
    <button class="category-button${state.category === category ? " active" : ""}" type="button" data-category="${escapeHtml(category)}">${category === "Combo" ? "Combos" : escapeHtml(category)}</button>
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
        ${product.descricao ? `<p class="product-description">${escapeHtml(product.descricao)}</p>` : ""}
        ${product.itens_combo?.length ? `<p class="combo-contents">${product.itens_combo.map((item) => `${item.quantidade}× ${escapeHtml(item.nome)}${item.variacao ? ` · ${escapeHtml(item.variacao)}` : ""}`).join(" · ")}</p>` : ""}
        ${renderVariationSelectors(product)}
        <div class="product-buy">
          <span class="product-price" data-price-for="${product.id}">${currency.format(product.preco)}</span>
          <button class="add-button" type="button" data-add="${product.id}" data-combo="${product.combo_id || ""}" aria-label="Adicionar ${escapeHtml(product.nome)}">+</button>
        </div>
      </div>
    </article>
  `).join("");
}

function renderVariationSelectors(product) {
  if (!product.variacoes?.length) return "";
  const groups = [...new Set(product.variacoes.map((option) => option.nome))];
  return `<div class="variation-options">${groups.map((group) => `
    <label class="variation-label">${escapeHtml(group)}
      <select class="variation-select" data-product="${product.id}" data-group="${escapeHtml(group)}">
        ${product.variacoes.filter((option) => option.nome === group).map((option) => `
          <option value="${option.id}">${escapeHtml(option.valor)}${option.adicional ? ` (+ ${currency.format(option.adicional)})` : ""}</option>
        `).join("")}
      </select>
    </label>
  `).join("")}</div>`;
}

function optionsForProduct(productId) {
  const card = [...document.querySelectorAll(".product-card")].find((item) =>
    item.querySelector(`[data-add="${productId}"]`),
  );
  if (!card) return [];
  return [...card.querySelectorAll(".variation-select")].map((select) => Number(select.value));
}

function selectedOptions(product, optionIds) {
  return (product.variacoes || []).filter((option) => optionIds.includes(option.id));
}

function productPrice(product, optionIds = []) {
  return product.preco + selectedOptions(product, optionIds)
    .reduce((total, option) => total + option.adicional, 0);
}

function cartTotals() {
  let count = 0;
  let total = 0;
  for (const line of state.cart.values()) {
    const product = state.products.find((item) => item.id === line.productId);
    if (!product) continue;
    count += line.quantity;
    total += productPrice(product, line.variationIds) * line.quantity;
  }
  return { count, total };
}

function renderCart() {
  const items = [...state.cart.entries()].filter(([, line]) =>
    state.products.some((product) => product.id === line.productId),
  );
  const { count, total } = cartTotals();
  $("#cart-count").textContent = count;
  $("#cart-empty").hidden = items.length > 0;
  $("#cart-items").innerHTML = items.map(([key, line]) => {
    const product = state.products.find((item) => item.id === line.productId);
    const variationNames = selectedOptions(product, line.variationIds)
      .map((option) => `${option.nome}: ${option.valor}`);
    return `
      <div class="cart-line">
        <div><div class="cart-line-name">${escapeHtml(product.nome)}</div>
          ${variationNames.length ? `<div class="cart-line-option">${variationNames.map(escapeHtml).join(" · ")}</div>` : ""}
          <div class="cart-line-price">${currency.format(productPrice(product, line.variationIds) * line.quantity)}</div>
        </div>
        <div class="quantity-control">
          <button type="button" data-quantity="-1" data-key="${key}" aria-label="Remover um ${escapeHtml(product.nome)}">−</button>
          <span>${line.quantity}</span>
          <button type="button" data-quantity="1" data-key="${key}" aria-label="Adicionar um ${escapeHtml(product.nome)}">+</button>
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
  const line = state.cart.get(productId);
  if (!line) return;
  line.quantity += delta;
  if (line.quantity <= 0) state.cart.delete(productId);
  renderCart();
}

function addToCart(product, variationIds) {
  const key = `${product.id}-${product.combo_id || 0}-${variationIds.join(".")}`;
  const line = state.cart.get(key);
  if (line) line.quantity += 1;
  else state.cart.set(key, {
    productId: product.id,
    comboId: product.combo_id,
    variationIds,
    quantity: 1,
  });
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
        itens: [...state.cart.values()].map((line) => ({
          produto_id: line.productId,
          quantidade: line.quantity,
          combo_id: line.comboId,
          variacao_ids: line.variationIds,
        })),
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
  $("#combos-pane").hidden = name !== "combos";
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
        <div class="admin-order-items">${order.itens.map((item) => `${item.quantidade}× ${escapeHtml(item.nome)}${item.variacao ? ` (${escapeHtml(item.variacao)})` : ""}`).join(" · ")}</div>
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
      <article class="admin-product">
        <div class="admin-product-heading">
          <div><strong>${escapeHtml(product.nome)}</strong><br><span>${escapeHtml(product.tipo)} · ${currency.format(product.preco)}</span></div>
          ${product.combo_id
            ? `<button class="delete-product" type="button" data-delete-combo="${product.combo_id}">Excluir combo</button>`
            : `<button class="delete-product" type="button" data-delete-product="${product.id}">Excluir</button>`}
        </div>
        ${product.combo_id
          ? `<p class="admin-option-list">${product.itens_combo.map((item) => `${item.quantidade}× ${escapeHtml(item.nome)}${item.variacao ? ` · ${escapeHtml(item.variacao)}` : ""}`).join(" · ")}</p>`
          : `<details class="variation-manager">
              <summary>Variações (${product.variacoes.length})</summary>
              <div class="admin-option-list">${product.variacoes.map((option) => `
                <span>${escapeHtml(option.nome)}: ${escapeHtml(option.valor)}${option.adicional ? ` (+ ${currency.format(option.adicional)})` : ""}
                  <button class="delete-product" type="button" data-delete-variation="${option.id}">Remover</button>
                </span>
              `).join("") || "<span>Sem opções cadastradas.</span>"}</div>
              <form class="variation-form" data-variation-product="${product.id}">
                <input name="nome" required minlength="2" maxlength="50" placeholder="Grupo (ex.: Tamanho)" aria-label="Grupo da variação">
                <input name="valor" required maxlength="60" placeholder="Opção (ex.: Grande)" aria-label="Nome da opção">
                <input name="adicional" type="number" min="0" max="10000" step="0.01" value="0" aria-label="Adicional de preço">
                <button class="button button-outline" type="submit">Adicionar opção</button>
              </form>
            </details>`}
      </article>
    `).join("");
  } catch (error) {
    container.innerHTML = `<p class="admin-empty">${escapeHtml(error.message)}</p>`;
  }
}

function addComboItemRow() {
  const products = state.products.filter((product) => !product.combo_id);
  if (!products.length) {
    showToast("Cadastre produtos antes de montar um combo.");
    return;
  }
  const row = document.createElement("div");
  row.className = "combo-item-row";
  row.innerHTML = `
    <select name="produto_id" required aria-label="Produto do combo">
      ${products.map((product) => `<option value="${product.id}">${escapeHtml(product.nome)}</option>`).join("")}
    </select>
    <input name="quantidade" type="number" min="1" max="50" value="1" required aria-label="Quantidade">
    <div class="combo-item-volume"></div>
    <button type="button" data-remove-combo-item aria-label="Remover produto do combo">Remover</button>
  `;
  $("#combo-item-rows").append(row);
  updateComboVolume(row);
}

function updateComboVolume(row) {
  const productId = Number(row.querySelector('[name="produto_id"]').value);
  const product = state.products.find((item) => item.id === productId);
  const volumes = (product?.variacoes || []).filter((option) => option.nome === "Volume");
  const container = row.querySelector(".combo-item-volume");
  container.innerHTML = volumes.length
    ? `<select name="variacao_id" aria-label="Volume do item no combo">${volumes.map((option) => `
        <option value="${option.id}">${escapeHtml(option.valor)}</option>
      `).join("")}</select>`
    : "";
}

async function loadAdminCombos() {
  const container = $("#admin-combos");
  container.innerHTML = '<p class="admin-empty">Carregando combos...</p>';
  try {
    const products = await api("/api/produtos");
    const combos = products.filter((product) => product.combo_id);
    container.innerHTML = combos.length ? combos.map((combo) => `
      <article class="admin-combo">
        <div class="admin-combo-heading">
          <strong>${escapeHtml(combo.nome)} · ${currency.format(combo.preco)}</strong>
          <button class="delete-product" type="button" data-delete-combo="${combo.combo_id}">Excluir</button>
        </div>
        <p>${escapeHtml(combo.descricao || "")}</p>
        <span>${combo.itens_combo.map((item) => `${item.quantidade}× ${escapeHtml(item.nome)}${item.variacao ? ` · ${escapeHtml(item.variacao)}` : ""}`).join(" · ")}</span>
      </article>
    `).join("") : '<p class="admin-empty">Ainda não há combos cadastrados.</p>';
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
  const product = state.products.find((item) => item.id === Number(button.dataset.add));
  if (!product) return;
  addToCart(product, optionsForProduct(product.id));
  showToast("Adicionado à sua sacola!");
});

$("#cart-items").addEventListener("click", (event) => {
  const button = event.target.closest("[data-quantity]");
  if (button) changeQuantity(button.dataset.key, Number(button.dataset.quantity));
});

$("#products").addEventListener("change", (event) => {
  const select = event.target.closest(".variation-select");
  if (!select) return;
  const product = state.products.find((item) => item.id === Number(select.dataset.product));
  if (!product) return;
  const price = productPrice(product, optionsForProduct(product.id));
  $(`[data-price-for="${product.id}"]`).textContent = currency.format(price);
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
    else if (tab.dataset.tab === "products") loadAdminProducts();
    else {
      loadAdminCombos();
      if ($("#combo-item-rows").children.length === 0) {
        addComboItemRow();
        addComboItemRow();
      }
    }
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
  const removeVariation = event.target.closest("[data-delete-variation]");
  if (removeVariation) {
    try {
      await api(`/api/variacoes/${removeVariation.dataset.deleteVariation}`, { method: "DELETE" }, true);
      showToast("Variação removida.");
      await Promise.all([loadAdminProducts(), loadProducts()]);
    } catch (error) {
      showToast(error.message);
    }
    return;
  }
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
$("#admin-products").addEventListener("submit", async (event) => {
  const form = event.target.closest("[data-variation-product]");
  if (!form) return;
  event.preventDefault();
  const values = new FormData(form);
  try {
    await api(`/api/produtos/${form.dataset.variationProduct}/variacoes`, {
      method: "POST",
      body: JSON.stringify({
        nome: values.get("nome"),
        valor: values.get("valor"),
        adicional: Number(values.get("adicional")),
      }),
    }, true);
    showToast("Variação adicionada.");
    await Promise.all([loadAdminProducts(), loadProducts()]);
  } catch (error) {
    showToast(error.message);
  }
});
$("#add-combo-item").addEventListener("click", addComboItemRow);
$("#combo-item-rows").addEventListener("change", (event) => {
  if (!event.target.matches('[name="produto_id"]')) return;
  updateComboVolume(event.target.closest(".combo-item-row"));
});
$("#combo-item-rows").addEventListener("click", (event) => {
  const button = event.target.closest("[data-remove-combo-item]");
  if (!button) return;
  if ($("#combo-item-rows").children.length <= 2) {
    showToast("Um combo precisa ter pelo menos dois produtos.");
    return;
  }
  button.closest(".combo-item-row").remove();
});
$("#combo-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const values = new FormData(form);
  const items = [...$("#combo-item-rows").querySelectorAll(".combo-item-row")].map((row) => ({
    produto_id: Number(row.querySelector('[name="produto_id"]').value),
    quantidade: Number(row.querySelector('[name="quantidade"]').value),
    variacao_id: Number(row.querySelector('[name="variacao_id"]')?.value) || null,
  }));
  $("#combo-error").textContent = "";
  try {
    await api("/api/combos", {
      method: "POST",
      body: JSON.stringify({
        nome: values.get("nome"),
        descricao: values.get("descricao"),
        preco: Number(values.get("preco")),
        itens: items,
      }),
    }, true);
    form.reset();
    $("#combo-item-rows").replaceChildren();
    addComboItemRow();
    addComboItemRow();
    showToast("Combo adicionado ao cardápio.");
    await Promise.all([loadAdminCombos(), loadProducts(), loadAdminProducts()]);
  } catch (error) {
    $("#combo-error").textContent = error.message;
  }
});
$("#admin-modal").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-delete-combo]");
  if (!button || !window.confirm("Excluir este combo do cardápio?")) return;
  try {
    await api(`/api/combos/${button.dataset.deleteCombo}`, { method: "DELETE" }, true);
    showToast("Combo excluído.");
    await Promise.all([loadAdminCombos(), loadProducts(), loadAdminProducts()]);
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
