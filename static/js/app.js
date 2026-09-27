// ===============================
// GLOBAL STATE
// ===============================
let prices = {};
let time = 60;
let pollInterval = null;
let currentProgressStep = 0;  // ✅ monotonic guard — UI can only move forward

// ===============================
// COIN ID MAPPING
// CoinGecko IDs (used as dropdown values and for price lookups)
// mapped to ChangeNOW ticker symbols (sent to backend/provider)
// ===============================
const COIN_TICKERS = {
  litecoin:     "ltc",
  bitcoin:      "btc",
  ethereum:     "eth",
  monero:       "xmr",
  "bitcoin-cash": "bch",
  dogecoin:     "doge",
  cardano:      "ada",
  solana:       "sol",
  tron:         "trx",
};

function toTicker(coingeckoId) {
  return COIN_TICKERS[coingeckoId] || coingeckoId;
}

// ===============================
// DOM READY
// ===============================
document.addEventListener("DOMContentLoaded", () => {

  // --- Element references ---
  const ltcInput = document.getElementById("ltc-input");
  const xmrOutput = document.getElementById("xmr-output");
  const ltcGbpLabel = document.getElementById("ltc-gbp");
  const xmrGbpLabel = document.getElementById("xmr-gbp");
  const status = document.getElementById("connection-status");
  const timerBar = document.getElementById("timer-bar");
  const timerText = document.getElementById("secs");
  const fromCoin = document.getElementById("from-coin");
  const toCoin = document.getElementById("to-coin");
  const swapBtn = document.getElementById("swap-button");
  const copyBtn = document.getElementById("copy-btn");

  console.log("✅ app.js loaded and DOM ready");

  // ✅ Restore form fields from localStorage on page load
  const savedAmount = localStorage.getItem("swap_amount");
  const savedFromCoin = localStorage.getItem("swap_from_coin");
  const savedToCoin = localStorage.getItem("swap_to_coin");
  const savedReceiveAddress = localStorage.getItem("swap_receive_address");
  const savedEmail = localStorage.getItem("swap_email"); // ✅ NEW

  if (savedAmount)         ltcInput.value = savedAmount;
  if (savedFromCoin)       fromCoin.value = savedFromCoin;
  if (savedToCoin)         toCoin.value = savedToCoin;
  if (savedReceiveAddress) document.getElementById("receive-address").value = savedReceiveAddress;
  if (savedEmail)          document.getElementById("email-input").value = savedEmail; // ✅ NEW
  updateReceiveAddressPlaceholder(); // set correct coin placeholder on load

  // ✅ Restore active swap after refresh
  const savedSwapId = localStorage.getItem("active_swap_id");
  if (savedSwapId && !localStorage.getItem("active_swap_token")) {
  // Swap saved by an older version of the site, without an access token
    clearSwapStorage();
  } else if (savedSwapId) {
    showDepositSection();
    restoreSwapUI(savedSwapId);
    pollSwapStatus(savedSwapId);
  }

  // --- Price fetching ---
  async function fetchPrices() {
    try {
      const res = await fetch(
//         "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,litecoin,monero,bitcoin-cash,dogecoin,cardano,solana,tron&vs_currencies=gbp"
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,litecoin,monero,bitcoin-cash,dogecoin,cardano,solana,tron&vs_currencies=gbp,usd"
      );
      prices = await res.json();

      status.innerText = "● Prices Connected (GBP/USD)";
      status.style.color = "#28a745";

      updateGbp();

      // ✅ NEW: re-fetch quote after prices load, so "you receive" restores correctly on refresh
      if (localStorage.getItem("active_swap_id") || ltcInput.value) {
        getSwapQuote();
      }

  //  } catch (err) {
  //    console.error(err);
  //    status.innerText = "X Price Connection Failed";
  //    status.style.color = "red";
  //  }
    } catch (err) {
      console.error(err);
      status.innerText = "⚠ Price data unavailable — rates may not display correctly";
      status.style.color = "#f57c00";
    }
  }
  
  function playSwoosh() {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(ctx.destination);

      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(300, ctx.currentTime);
      oscillator.frequency.exponentialRampToValueAtTime(800, ctx.currentTime + 0.15);
      oscillator.frequency.exponentialRampToValueAtTime(200, ctx.currentTime + 0.4);
    
      gainNode.gain.setValueAtTime(0.3, ctx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
    
      oscillator.start(ctx.currentTime);
      oscillator.stop(ctx.currentTime + 0.4);
 }

  // updateGbp is defined globally below — call it from here too
  // (no local definition needed)

  // --- Timers & listeners ---
  ltcInput.addEventListener("input", () => {
    updateGbp();
    clearTimeout(window.qTimer);
    window.qTimer = setTimeout(getSwapQuote, 800);
  });

  fromCoin.addEventListener("change", () => { userMadeSelection = false; updateReceiveAddressPlaceholder(); getSwapQuote(); });
  toCoin.addEventListener("change",   () => { userMadeSelection = false; updateReceiveAddressPlaceholder(); getSwapQuote(); showAddressError(""); });

  // Live address validation on input
  document.getElementById("receive-address").addEventListener("input", () => {
    const toCoinTicker = toTicker(document.getElementById("to-coin").value);
    const address = document.getElementById("receive-address").value;
    if (!address) { showAddressError(""); return; }
    const result = validateAddress(address, toCoinTicker);
    showAddressError(result.valid ? "" : result.message);
  });

  setInterval(() => {
    if (time <= 0) {
      time = 60;
      getSwapQuote();
      fetchPrices();
    } else {
      time--;
    }
    timerText.innerText = time;
    timerBar.style.width = (time / 60 * 100) + "%";
  }, 1000);

  fetchPrices();

  // --- Swap + copy buttons ---
//  if (swapBtn) swapBtn.addEventListener("click", startSwap);
  if (swapBtn) swapBtn.addEventListener("click", () => {
      playSwoosh();
      startSwap();
    });
  if (copyBtn) copyBtn.addEventListener("click", copyDepositAddress);
});

// ===============================
// GBP LABEL UPDATER (GLOBAL)
// Uses getElementById so it can be called from anywhere
// ===============================
function updateGbp() {
  const inputVal    = parseFloat(document.getElementById("ltc-input").value) || 0;
  const fromCoinVal = document.getElementById("from-coin").value;
  const toCoinVal   = document.getElementById("to-coin").value;
  const fromPrice   = prices[fromCoinVal]?.gbp || 0;
  const toPrice     = prices[toCoinVal]?.gbp || 0;

  // Get output from selected quote if available
  const selectedQuote = currentQuotes.find(q => q.provider === selectedProvider);
  const outputVal = selectedQuote ? selectedQuote.output : 0;

//   document.getElementById("ltc-gbp").innerText = `≈ £${(inputVal * fromPrice).toFixed(2)} GBP`;
//   document.getElementById("xmr-gbp").innerText = `≈ £${(outputVal * toPrice).toFixed(2)} GBP`;
  const fromUsd = prices[fromCoinVal]?.usd || 0;
  const toUsd   = prices[toCoinVal]?.usd || 0;
  document.getElementById("ltc-gbp").innerText = `≈ £${(inputVal * fromPrice).toFixed(2)} GBP / $${(inputVal * fromUsd).toFixed(2)} USD`;
  document.getElementById("xmr-gbp").innerText = `≈ £${(outputVal * toPrice).toFixed(2)} GBP / $${(outputVal * toUsd).toFixed(2)} USD`;
  
}

// ===============================
// QUOTE STATE
// ===============================
let selectedProvider  = null;
let userMadeSelection = false;  // true only when user clicks Select
let currentQuotes     = [];

// ===============================
// ADDRESS VALIDATION
// ===============================
const ADDRESS_PATTERNS = {
  btc:  /^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,59}$/,
  ltc:  /^(L|M|3)[A-Za-z0-9]{33}$|^(ltc1)[0-9A-Za-z]{39}$/,
  eth:  /^(0x)[0-9A-Fa-f]{40}$/,
  xmr:  /^[48][0-9A-Za-z]{94,104}$/,
  bch:  /^(bitcoincash:)?(q|p)[a-z0-9]{41}$|^[13][a-zA-HJ-NP-Z0-9]{25,34}$/,
  doge: /^D[5-9A-HJ-NP-U][1-9A-HJ-NP-Za-km-z]{32}$/,
  ada:  /^(addr1)[a-z0-9]{53,98}$|^(DdzFF|Ae2)[a-zA-Z0-9]{54,100}$/,
  sol:  /^[1-9A-HJ-NP-Za-km-z]{32,44}$/,
  trx:  /^T[a-zA-Z0-9]{33}$/,
};

function validateAddress(address, coinTicker) {
  if (!address || address.trim() === "") return { valid: false, message: "Address is required" };
  const pattern = ADDRESS_PATTERNS[coinTicker.toLowerCase()];
  if (!pattern) return { valid: true, message: "" }; // no pattern = skip validation
  const trimmed = address.trim();
  if (!pattern.test(trimmed)) {
    return { valid: false, message: `Invalid ${coinTicker.toUpperCase()} address format` };
  }
  return { valid: true, message: "" };
}

function showAddressError(message) {
  const input = document.getElementById("receive-address");
  let errEl = document.getElementById("address-error");
  if (!errEl) {
    errEl = document.createElement("div");
    errEl.id = "address-error";
    errEl.style.cssText = "color:#e53935; font-size:12px; margin-top:4px;";
    input.parentNode.insertBefore(errEl, input.nextSibling);
  }
  errEl.innerText = message;
  input.style.borderColor = message ? "#e53935" : "";
}

const PROVIDER_INFO = {
//   changenow: { label: "ChangeNOW", badge: "✓ Established", badgeClass: "badge-changenow", nokyc: false },
  changenow: { label: "ChangeNOW", badge: "✓ Established", badge2: "✓ Fast", badgeClass: "badge-changenow", nokyc: false },
//   godex:     { label: "Godex",     badge: "🔒 No KYC",     badgeClass: "badge-godex",      nokyc: true  },
//   godex:     { label: "Godex",     badge: "✓ No KYC",     badgeClass: "badge-godex",      nokyc: true  },  
  godex: { label: "Godex", badge: "✓ No KYC", badge2: "✓ No Limits", badgeClass: "badge-godex", nokyc: true },
  mock:      { label: "Mock (dev)", badge: "",              badgeClass: "",                 nokyc: false },
};

// ===============================
// QUOTE FUNCTION (GLOBAL)
// ===============================
async function getSwapQuote() {
  const ltcInput  = document.getElementById("ltc-input");
  const fromCoin  = document.getElementById("from-coin");
  const toCoin    = document.getElementById("to-coin");
  const container = document.getElementById("quotes-container");

  const amount = parseFloat(ltcInput.value);
  if (!amount || amount <= 0) {
    if (container) container.innerHTML = "";
    selectedProvider = null;
    currentQuotes    = [];
    return;
  }
  if (fromCoin.value === toCoin.value) {
    if (container) container.innerHTML = "<p class='quote-error'>Cannot swap a coin for itself.</p>";
    return;
  }

  if (container) container.innerHTML = "<p class='quote-loading'>Fetching rates…</p>";

  const fromTicker_ = toTicker(fromCoin.value);
  const toTicker__  = toTicker(toCoin.value);
  console.log(`[quote] requesting: ${amount} ${fromCoin.value} (${fromTicker_}) → ${toCoin.value} (${toTicker__})`);

  try {
    const res  = await fetch(`/swap?amount=${amount}&fromCoin=${fromTicker_}&toCoin=${toTicker__}`);
    const data = await res.json();

    if (!data.success) {
      if (container) container.innerHTML = `<p class='quote-error'>Error: ${data.error || "Quote failed"}</p>`;
      return;
    }

    currentQuotes = data.quotes || [];

    // Auto-select best valid quote unless user has manually chosen
    const validQuotes = currentQuotes.filter(q => q.output > 0 && !q.error);
    if (validQuotes.length && !userMadeSelection) {
      // Always pick best (first in sorted list) unless user clicked Select
      selectedProvider = validQuotes[0].provider;
    } else if (validQuotes.length && !validQuotes.find(q => q.provider === selectedProvider)) {
      // User's selection is no longer available — fall back to best
      selectedProvider = validQuotes[0].provider;
      userMadeSelection = false;
    }

    renderQuoteCards(fromTicker_, toTicker__);
    updateGbp();
    console.log(`[quote] ${currentQuotes.length} quote(s) received, selected: ${selectedProvider}`);

  } catch (err) {
    if (container) container.innerHTML = "<p class='quote-error'>Could not fetch quotes.</p>";
    console.error("[quote] fetch error:", err);
  }
}

function renderQuoteCards(fromTicker_, toTicker__) {
  const container = document.getElementById("quotes-container");
  if (!container) return;
  const toCoinUpper = toTicker__.toUpperCase();
  container.innerHTML = "";

  currentQuotes.forEach(q => {
    const info       = PROVIDER_INFO[q.provider] || { label: q.provider, badge: "", badgeClass: "", nokyc: false };
    const isSelected = q.provider === selectedProvider;
    const hasError   = !!(q.error || q.output === 0);

    const card = document.createElement("div");
    card.className = `quote-card${isSelected ? " quote-selected" : ""}${hasError ? " quote-unavailable" : ""}`;
    card.dataset.provider = q.provider;

    let bodyHtml;
    if (hasError) {
      const minMsg = q.min_amount
        ? `Minimum: ${q.min_amount} ${fromTicker_.toUpperCase()}`
        : (q.error || "Unavailable");
      bodyHtml = `<span class="quote-output">Unavailable</span><span class="quote-min">${minMsg}</span>`;
    } else {
      const rate = q.rate ? parseFloat(q.rate).toFixed(6) : "---";
      bodyHtml = `
        <span class="quote-output">${q.output.toFixed(5)} ${toCoinUpper}</span>
        <span class="quote-rate">Rate: ${rate}</span>`;
    }
 
    card.innerHTML = `
      <div class="quote-header">
        <span class="quote-provider-name">${info.label}</span>
        ${info.badge ? `<span class="quote-badge ${info.badgeClass}">${info.badge}</span>` : ""}
        ${info.badge2 ? `<span class="quote-badge ${info.badgeClass}">${info.badge2}</span>` : ""}
        ${!hasError ? `<button class="quote-select-btn${isSelected ? " selected" : ""}"
            onclick="selectProvider('${q.provider}')">${isSelected ? "✓ Selected" : "Select"}</button>` : ""}
      </div>
      <div class="quote-body">${bodyHtml}</div>`;

    container.appendChild(card);
  });
}

function selectProvider(providerName) {
  selectedProvider  = providerName;
  userMadeSelection = true;
  console.log(`[quote] provider manually selected: ${providerName}`);
  const fromTicker_ = toTicker(document.getElementById("from-coin").value);
  const toTicker__  = toTicker(document.getElementById("to-coin").value);
  renderQuoteCards(fromTicker_, toTicker__);
  updateGbp();
}

// ===============================
// SWAP FLOW
// ===============================
function startSwap() {
  const amount         = document.getElementById("ltc-input").value;
  const receiveAddress = document.getElementById("receive-address").value;
  const email          = document.getElementById("email-input").value;
  const fromCoin       = document.getElementById("from-coin").value;
  const toCoin         = document.getElementById("to-coin").value;

//   if (!amount || Number(amount) <= 0) return alert("Enter valid amount");
//   if (!receiveAddress) return alert("Enter your receiving address");
//   if (!selectedProvider) return alert("Please wait for quotes to load and select a provider");
  
  if (!amount || Number(amount) <= 0) return alert("Enter valid amount");
 //  if (!selectedProvider) return alert("Please wait for quotes to load and select a provider");
  if (!selectedProvider && currentQuotes.length === 0) return alert("Please wait for quotes to load");
  
  // Check if selected quote is valid
  const quote = currentQuotes.find(q => q.provider === selectedProvider);
  if (!quote || !quote.output || quote.output <= 0) {
    alert("No providers are available for this amount. Please try a different amount.");
    return;
  }
  
  if (!receiveAddress) return alert("Enter your receiving address");

  // Validate address format before submitting
  const toCoinTicker = toTicker(document.getElementById("to-coin").value);
  const addrCheck = validateAddress(receiveAddress, toCoinTicker);
  if (!addrCheck.valid) {
    showAddressError(addrCheck.message);
    document.getElementById("receive-address").focus();
    return;
  }
  showAddressError(""); // clear any error

  // Find the selected quote to get rate and withdrawal_amount
 //  const quote = currentQuotes.find(q => q.provider === selectedProvider);
//   
  // Block swap if selected quote is unavailable
  if (!quote || !quote.output || quote.output <= 0) {
    alert("No providers are available for this amount. Please try a different amount.");
    return;
  }

// 02-05-26 add memory of refund address  
  localStorage.setItem("swap_amount", amount);
  localStorage.setItem("swap_from_coin", fromCoin);
  localStorage.setItem("swap_to_coin", toCoin);
  localStorage.setItem("swap_receive_address", receiveAddress);
  localStorage.setItem("swap_email", email);
  localStorage.setItem("swap_refund_address", document.getElementById("refund-address").value);

  showDepositSection();

  createSwap(amount, email, quote).then(data => {
    localStorage.setItem("active_swap_id", data.swap_id);
    localStorage.setItem("active_swap_token", data.access_token);
    setDepositDetails(data);
    setProgressStep(1);
    pollSwapStatus(data.swap_id);
  });
}

function createSwap(amount, email, quote) {
  const fromCoinId = document.getElementById("from-coin").value;
  const toCoinId   = document.getElementById("to-coin").value;
  console.log(`[createSwap] ${amount} ${fromCoinId} → ${toCoinId} via ${selectedProvider}`);

  return fetch("/create_swap", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
// 01-05-26 adding gbp values for vales at time of swap for hmrc
// 02-05-26 adding refund address 
  body: JSON.stringify({
      amount,
      email,
      from_coin:          toTicker(fromCoinId),
      to_coin:            toTicker(toCoinId),
      receive_address:    document.getElementById("receive-address").value,
      refund_address:     document.getElementById("refund-address").value || "",
      provider:           selectedProvider,
      rate:               quote ? quote.rate : null,
      withdrawal_amount:  quote ? quote.output : null,
      from_coin_gbp_rate: prices[fromCoinId]?.gbp || null,
      to_coin_gbp_rate:   prices[toCoinId]?.gbp || null,
      from_coin_usd_rate: prices[fromCoinId]?.usd || null,
      to_coin_usd_rate:   prices[toCoinId]?.usd || null,
    })
  }).then(res => res.json());
}



// ===============================
// STATUS POLLING
// ===============================

// Each swap has a secret access token so only its creator can look it up
function swapUrl(swapId) {
  const token = localStorage.getItem("active_swap_token") || "";
  return `/swap/${swapId}?token=${encodeURIComponent(token)}`;
}

function pollSwapStatus(swapId) {

  // ✅ Stop any existing poller before starting a new one
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }

  pollInterval = setInterval(async () => {
  //  const res = await fetch(`/swap/${swapId}`);
    const res = await fetch(swapUrl(swapId));
    const data = await res.json();

    console.log("🔄 swap status:", data.status);

    if (data.status === "awaiting_deposit") setProgressStep(2);
    if (data.status === "deposit_received")  setProgressStep(3);
    if (data.status === "swapping")          setProgressStep(4);
    if (data.status === "completed") {
      setProgressStep(5);
      clearInterval(pollInterval);
      pollInterval = null;
      clearSwapStorage(); // ✅ wipe everything cleanly on completion
    }
    if (data.status === "failed") {
      alert("Swap failed. Please try again.");
      clearInterval(pollInterval);
      pollInterval = null;
      clearSwapStorage(); // ✅ wipe everything cleanly on failure too
    }
    if (data.status === "hold") {
      document.getElementById("hold-message").style.display = "block";
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }, 3000);
}

// ===============================
// RESTORE UI AFTER REFRESH
// ===============================
async function restoreSwapUI(swapId) {
//  const res = await fetch(`/swap/${swapId}`);
  const res = await fetch(swapUrl(swapId));

  // If swap no longer exists (e.g. DB was wiped), clear stale storage and bail
  if (!res.ok) {
    console.warn(`[restore] swap ${swapId} not found — clearing stale localStorage`);
    clearSwapStorage();
    return;
  }

  const data = await res.json();

  if (data.error) {
    console.warn(`[restore] swap ${swapId} error: ${data.error} — clearing stale localStorage`);
    clearSwapStorage();
    return;
  }

  setDepositDetails(data);

  if (data.status === "awaiting_deposit") setProgressStep(2);
  if (data.status === "deposit_received")  setProgressStep(3);
  if (data.status === "swapping")          setProgressStep(4);
  if (data.status === "completed")         setProgressStep(5);
}

// ===============================
// STORAGE HELPERS
// ===============================

// ✅ Wipe all swap-related localStorage on completion or failure
function clearSwapStorage() {
  localStorage.removeItem("active_swap_id");
  localStorage.removeItem("active_swap_token");
  localStorage.removeItem("swap_amount");
  localStorage.removeItem("swap_from_coin");
  localStorage.removeItem("swap_to_coin");
  localStorage.removeItem("swap_receive_address");
  localStorage.removeItem("swap_email"); // ✅ NEW
}

// ===============================
// UI HELPERS
// ===============================
// function updateReceiveAddressPlaceholder() {
//   const toCoin = document.getElementById("to-coin").value;
//   const ticker = toTicker(toCoin).toUpperCase();
//   document.getElementById("receive-address").placeholder = `Enter your ${ticker} address`;
// }


function showDepositSection() {
  document.getElementById("deposit-section").style.display = "block";
  document.getElementById("progress-tracker").style.display = "block";
}

function updateReceiveAddressPlaceholder() {
  const toCoin   = document.getElementById("to-coin").value;
  const fromCoin = document.getElementById("from-coin").value;
  const toTicker_   = toTicker(toCoin).toUpperCase();
  const fromTicker_ = toTicker(fromCoin).toUpperCase();
  document.getElementById("receive-address").placeholder = `Enter your ${toTicker_} address`;
  document.getElementById("refund-address").placeholder  = `Your ${fromTicker_} address for refunds`;
}


function setDepositDetails(data) {
  document.getElementById("deposit-address").value = data.deposit_address;
  const coinLabel = (data.from_coin || "?").toUpperCase();
  document.getElementById("deposit-amount").textContent =
    `Amount Required: ${data.amount} ${coinLabel}`;

  // Show provider transaction ID link
  if (data.provider_execution_id) {
    const trackingUrls = {
      changenow: `https://changenow.io/exchange/txs/${data.provider_execution_id}`,
      godex:     `https://godex.io/exchange/waiting/${data.provider_execution_id}`,
    };
    const url = trackingUrls[data.provider] || "#";
    const link = document.getElementById("tx-id-link");
    link.href = url;
    link.textContent = data.provider_execution_id;
    document.getElementById("tx-id-section").style.display = "block";
  }
}


// ✅ Monotonic guard — step can only increase, never go back
function setProgressStep(step) {
  if (step <= currentProgressStep) return;
  currentProgressStep = step;

  const total = 5;
  for (let i = 1; i <= total; i++) {
    const el = document.getElementById(`p${i}`);
    if (!el) continue;
    el.className = "";
    if (i < step)        el.classList.add("progress-done");
    else if (i === step) el.classList.add("progress-active");
    else                 el.classList.add("progress-pending");
  }
}

function adjustAmount(delta) {
  const input = document.getElementById("ltc-input");
  const current = parseFloat(input.value) || 0;
  const newVal = Math.max(0, Math.round((current + delta) * 1000) / 1000);
  input.value = newVal;
  updateGbp();
  clearTimeout(window.qTimer);
  window.qTimer = setTimeout(getSwapQuote, 800);
}

function copyDepositAddress() {
  navigator.clipboard.writeText(
    document.getElementById("deposit-address").value
  );
  const btn = document.getElementById("copy-btn");
  btn.textContent = "Copied!";
  btn.classList.add("copied");
  setTimeout(() => {
    btn.textContent = "Copy";
    btn.classList.remove("copied");
  }, 2000);
}
