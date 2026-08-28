const functions = require("firebase-functions");
const admin = require("firebase-admin");
const crypto = require("crypto");
const axios = require("axios");

// Initialize Firebase Admin with your project database URL
admin.initializeApp({
  databaseURL: "https://trail-724e9-default-rtdb.firebaseio.com"
});

const db = admin.database();

// ==============================================================================
// CONFIGURATION (Set via functions config or replace directly)
// ==============================================================================
// Delta Environment: 'india' (https://api.india.delta.exchange) or 'global' (https://api.delta.exchange)
const DELTA_ENVIRONMENT = process.env.DELTA_ENVIRONMENT || "india";
const BASE_URL = DELTA_ENVIRONMENT === "india" 
  ? "https://api.india.delta.exchange" 
  : "https://api.delta.exchange";

const DELTA_API_KEY = process.env.DELTA_API_KEY || "";
const DELTA_API_SECRET = process.env.DELTA_API_SECRET || "";
const WEBHOOK_PASSPHRASE = process.env.WEBHOOK_PASSPHRASE || "supersecretpassphrase123";
const DEFAULT_SYMBOL = "BTCUSD";
const DEFAULT_SIZE = 1;

/**
 * Generate Delta Exchange HMAC-SHA256 signature
 */
function generateSignature(secret, method, path, timestamp, payload = null) {
  let bodyStr = "";
  if (payload) {
    bodyStr = typeof payload === "string" ? payload : JSON.stringify(payload);
  }
  const signatureData = `${method.toUpperCase()}${timestamp}${path}${bodyStr}`;
  return crypto.createHmac("sha256", secret).update(signatureData).digest("hex");
}

/**
 * Make authenticated request to Delta Exchange API
 */
async function deltaRequest(method, path, payload = null) {
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const signature = generateSignature(DELTA_API_SECRET, method, path, timestamp, payload);

  const headers = {
    "Content-Type": "application/json",
    "User-Agent": "Firebase-DeltaBot/1.0",
    "api-key": DELTA_API_KEY,
    "timestamp": timestamp,
    "signature": signature
  };

  const config = {
    method: method.toUpperCase(),
    url: `${BASE_URL}${path}`,
    headers: headers,
    timeout: 10000
  };

  if (payload) {
    config.data = payload;
  }

  try {
    const response = await axios(config);
    return response.data;
  } catch (error) {
    const errMsg = error.response ? error.response.data : error.message;
    console.error(`Delta API Error on ${method} ${path}:`, errMsg);
    return { success: false, error: errMsg };
  }
}

/**
 * Get Product ID for symbol
 */
async function getProductId(symbol) {
  try {
    const res = await axios.get(`${BASE_URL}/v2/products`, { timeout: 10000 });
    const products = res.data.result || [];
    const product = products.find(p => p.symbol && p.symbol.toUpperCase() === symbol.toUpperCase());
    return product ? product.id : null;
  } catch (error) {
    console.error("Failed to fetch products:", error.message);
    return null;
  }
}

/**
 * Get active open position for product
 */
async function getOpenPosition(productId) {
  const res = await deltaRequest("GET", "/v2/positions/margined");
  if (res && res.result && Array.isArray(res.result)) {
    return res.result.find(p => p.product_id === productId && Math.abs(parseFloat(p.size || 0)) > 0) || null;
  }
  return null;
}

/**
 * Close open position using reduce_only market order
 */
async function closePosition(symbol, productId) {
  const pos = await getOpenPosition(productId);
  if (!pos) {
    return { success: true, message: `No active position to close on ${symbol}` };
  }

  const currentSize = parseFloat(pos.size || 0);
  const closeSide = currentSize > 0 ? "sell" : "buy";
  const absSize = Math.abs(parseInt(currentSize));

  return await deltaRequest("POST", "/v2/orders", {
    product_id: productId,
    size: absSize,
    side: closeSide,
    order_type: "market_order",
    reduce_only: true
  });
}

/**
 * Log trade execution to Firebase Realtime Database
 */
async function logTradeToFirebase(action, symbol, details) {
  try {
    await db.ref("bot_logs").push({
      timestamp: Date.now(),
      isoDate: new Date().toISOString(),
      action: action,
      symbol: symbol,
      details: details
    });
  } catch (err) {
    console.error("Firebase RTDB logging failed:", err.message);
  }
}

// ==============================================================================
// HTTPS CLOUD FUNCTION: Webhook Receiver for TradingView Alerts
// ==============================================================================
exports.deltaWebhook = functions.https.onRequest(async (req, res) => {
  // Health check on GET
  if (req.method === "GET") {
    return res.status(200).json({
      status: "online",
      service: "Firebase Delta Exchange Webhook Receiver",
      project: "trail-724e9",
      environment: DELTA_ENVIRONMENT
    });
  }

  if (req.method !== "POST") {
    return res.status(405).send("Method Not Allowed");
  }

  try {
    const data = req.body || {};
    const passphrase = data.passphrase;

    // Verify passphrase
    if (WEBHOOK_PASSPHRASE && passphrase !== WEBHOOK_PASSPHRASE) {
      console.warn("Unauthorized webhook attempt:", passphrase);
      return res.status(401).json({ error: "Unauthorized: Invalid Passphrase" });
    }

    const action = String(data.action || "").toUpperCase();
    const symbol = String(data.symbol || DEFAULT_SYMBOL).toUpperCase();
    const size = parseInt(data.size || DEFAULT_SIZE);
    const price = data.price || null;

    console.log(`===> [${action}] received for ${symbol} (Size: ${size}, Price: ${price})`);

    const productId = await getProductId(symbol);
    if (!productId) {
      return res.status(400).json({ error: `Symbol '${symbol}' not found on Delta Exchange` });
    }

    const existingPos = await getOpenPosition(productId);
    const existingSize = existingPos ? parseFloat(existingPos.size || 0) : 0;

    let tradeResult = {};

    if (action === "BUY") {
      // Close short if open
      if (existingSize < 0) {
        console.log(`Closing existing SHORT (${existingSize}) before BUY...`);
        await closePosition(symbol, productId);
      }
      tradeResult = await deltaRequest("POST", "/v2/orders", {
        product_id: productId,
        size: size,
        side: "buy",
        order_type: "market_order",
        reduce_only: false
      });

    } else if (action === "SELL") {
      // Close long if open
      if (existingSize > 0) {
        console.log(`Closing existing LONG (${existingSize}) before SELL...`);
        await closePosition(symbol, productId);
      }
      tradeResult = await deltaRequest("POST", "/v2/orders", {
        product_id: productId,
        size: size,
        side: "sell",
        order_type: "market_order",
        reduce_only: false
      });

    } else if (action === "EXIT_LONG") {
      if (existingSize > 0) {
        tradeResult = await closePosition(symbol, productId);
      } else {
        tradeResult = { message: "No open LONG position to exit" };
      }

    } else if (action === "EXIT_SHORT") {
      if (existingSize < 0) {
        tradeResult = await closePosition(symbol, productId);
      } else {
        tradeResult = { message: "No open SHORT position to exit" };
      }

    } else if (action === "CLOSE") {
      tradeResult = await closePosition(symbol, productId);

    } else {
      return res.status(400).json({ error: `Invalid action '${action}'` });
    }

    // Record execution to your Firebase Realtime Database
    await logTradeToFirebase(action, symbol, {
      price: price,
      size: size,
      tradeResult: tradeResult
    });

    return res.status(200).json({
      success: true,
      action: action,
      symbol: symbol,
      data: tradeResult
    });

  } catch (error) {
    console.error("Webhook processing failed:", error);
    return res.status(500).json({ error: error.message });
  }
});
