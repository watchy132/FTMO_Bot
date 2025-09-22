import os, os, asyncio, json, time
from typing import Any, Dict
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

BRIDGE_TIMEOUT = int(os.environ.get("BRIDGE_TIMEOUT", "60"))
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")

# BRIDGE_ENV_FALLBACK
if not os.getenv("OPENAI_API_KEY"):
    try:
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("OPENAI_API_KEY="):
                    os.environ["OPENAI_API_KEY"] = line.strip().split("=", 1)[1]
                    break
    except Exception:
        pass

app = FastAPI(title="FTMO GPT Bridge", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _ok(data: Dict[str, Any]) -> JSONResponse:
    return JSONResponse({"ok": True, **data})


def _err(msg: str, code: str = "ERROR") -> JSONResponse:
    return JSONResponse({"ok": False, "code": code, "error": msg}, status_code=400)


@app.get("/health")
def health():
    return _ok(
        {
            "service": "bridge",
            "ts": _now_ms(),
            "has_key": bool(OPENAI_KEY),
            "timeout_s": BRIDGE_TIMEOUT,
        }
    )


# essayer d'importer gpt_bridge.decide
_gb_decide = None
try:
    import gpt_bridge  # type: ignore

    _gb_decide = getattr(gpt_bridge, "decide", None)
except Exception:
    _gb_decide = None


async def _call_decide(payload: Dict[str, Any]) -> Dict[str, Any]:
    if payload.get("probe") is True:
        return {"status": "OK", "why": "probe", "echo": True}

    if _gb_decide is None:
        return {
            "status": "SKIP",
            "why": "gpt_bridge.decide indisponible",
            "note": "Bridge répond mais sans logique GPT",
        }

    try:
        if asyncio.iscoroutinefunction(_gb_decide):
            return await asyncio.wait_for(_gb_decide(payload), timeout=BRIDGE_TIMEOUT)
        else:
            loop = asyncio.get_running_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(None, _gb_decide, payload), timeout=BRIDGE_TIMEOUT
            )
    except asyncio.TimeoutError:
        return {"status": "SKIP", "why": f"timeout>{BRIDGE_TIMEOUT}s"}
    except Exception as e:
        return {"status": "SKIP", "why": f"bridge-error: {type(e).__name__}: {e}"}


@app.post("/decide")
async def decide_endpoint(req: Request):
    try:
        payload = await req.json()
        if not isinstance(payload, dict):
            return _err("JSON body must be an object", "BAD_REQUEST")
    except Exception:
        return _err("Invalid JSON", "BAD_JSON")

    result = await _call_decide(payload)
    if not isinstance(result, dict):
        result = {"status": "SKIP", "why": "non-dict response from decide()"}
    result.setdefault("ts", _now_ms())
    return _ok(result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("bridge_server:app", host="127.0.0.1", port=8765, reload=False)


from fastapi import Request
import gpt_bridge as _gb


@app.post("/normalize")
async def normalize(request: Request):
    body = await request.json()
    valids, reasons = _gb.normalize_setups(body)
    return {
        "ok": True,
        "setups": valids,
        "reasons": reasons,
        "ts": __import__("time").time_ns() // 1_000_000,
    }


@app.post("/reload_engine")
def reload_engine():
    import importlib, decide_trade_once

    importlib.reload(decide_trade_once)
    return {"ok": True, "engine": decide_trade_once.__file__}


from fastapi import Request
import gpt_bridge as _gb
from importlib import reload as _reload

# retire routes existantes
try:
    app.router.routes = [
        r
        for r in app.router.routes
        if not (
            getattr(r, "path", None) in ("/normalize", "/decide", "/reload_engine")
            and ({"POST", "GET"} & set(getattr(r, "methods", set())))
        )
    ]
except Exception:
    pass


@app.post("/normalize")
async def _normalize(request: Request):
    body = await request.json()
    setups, reasons = _gb.normalize_setups(body)
    return {
        "ok": True,
        "setups": setups,
        "reasons": reasons,
        "ts": __import__("time").time_ns() // 1_000_000,
    }


@app.post("/decide")
async def _decide(request: Request):
    body = await request.json()
    valids, reasons = _gb.normalize_setups(body)
    try:
        from decide_trade_once import decide as _engine

        decisions = _engine(valids) or []
        if decisions:
            return {
                "ok": True,
                "decisions": decisions,
                "ts": __import__("time").time_ns() // 1_000_000,
            }
    except Exception as e:
        return {
            "ok": True,
            "decisions": [
                {"action": "skip", "reason": f"engine_error:{e}", "setups": []}
            ],
            "ts": __import__("time").time_ns() // 1_000_000,
        }
    return {
        "ok": True,
        "decisions": [
            {
                "action": "preview",
                "reason": (reasons[0] if reasons else "OK"),
                "setups": valids,
            }
        ],
        "ts": __import__("time").time_ns() // 1_000_000,
    }


@app.post("/reload_engine")
async def _reload_engine():
    try:
        import decide_trade_once as m

        _reload(m)
        return {"ok": True, "engine": getattr(m, "__file__", "decide_trade_once.py")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# === end override ===


from fastapi import Request
import gpt_bridge as _gb
from importlib import reload as _reload

# retire routes existantes
try:
    app.router.routes = [
        r
        for r in app.router.routes
        if not (
            getattr(r, "path", None) in ("/normalize", "/decide", "/reload_engine")
            and ({"POST", "GET"} & set(getattr(r, "methods", set())))
        )
    ]
except Exception:
    pass


@app.post("/normalize")
async def _normalize(request: Request):
    body = await request.json()
    setups, reasons = _gb.normalize_setups(body)
    return {
        "ok": True,
        "setups": setups,
        "reasons": reasons,
        "ts": __import__("time").time_ns() // 1_000_000,
    }


@app.post("/decide")
async def _decide(request: Request):
    body = await request.json()
    valids, reasons = _gb.normalize_setups(body)
    try:
        from decide_trade_once import decide as _engine

        decisions = _engine(valids) or []
        if decisions:
            return {
                "ok": True,
                "decisions": decisions,
                "ts": __import__("time").time_ns() // 1_000_000,
            }
    except Exception as e:
        return {
            "ok": True,
            "decisions": [
                {"action": "skip", "reason": f"engine_error:{e}", "setups": []}
            ],
            "ts": __import__("time").time_ns() // 1_000_000,
        }
    return {
        "ok": True,
        "decisions": [
            {
                "action": "preview",
                "reason": (reasons[0] if reasons else "OK"),
                "setups": valids,
            }
        ],
        "ts": __import__("time").time_ns() // 1_000_000,
    }


@app.post("/reload_engine")
async def _reload_engine():
    try:
        import decide_trade_once as m

        _reload(m)
        return {"ok": True, "engine": getattr(m, "__file__", "decide_trade_once.py")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# === end override ===


from fastapi import Request
import gpt_bridge as _gb
from importlib import reload as _reload

# retire routes existantes
try:
    app.router.routes = [
        r
        for r in app.router.routes
        if not (
            getattr(r, "path", None) in ("/normalize", "/decide", "/reload_engine")
            and ({"POST", "GET"} & set(getattr(r, "methods", set())))
        )
    ]
except Exception:
    pass


@app.post("/normalize")
async def _normalize(request: Request):
    body = await request.json()
    setups, reasons = _gb.normalize_setups(body)
    return {
        "ok": True,
        "setups": setups,
        "reasons": reasons,
        "ts": __import__("time").time_ns() // 1_000_000,
    }


@app.post("/decide")
async def _decide(request: Request):
    body = await request.json()
    valids, reasons = _gb.normalize_setups(body)
    try:
        from decide_trade_once import decide as _engine

        decisions = _engine(valids) or []
        if decisions:
            return {
                "ok": True,
                "decisions": decisions,
                "ts": __import__("time").time_ns() // 1_000_000,
            }
    except Exception as e:
        return {
            "ok": True,
            "decisions": [
                {"action": "skip", "reason": f"engine_error:{e}", "setups": []}
            ],
            "ts": __import__("time").time_ns() // 1_000_000,
        }
    return {
        "ok": True,
        "decisions": [
            {
                "action": "preview",
                "reason": (reasons[0] if reasons else "OK"),
                "setups": valids,
            }
        ],
        "ts": __import__("time").time_ns() // 1_000_000,
    }


@app.post("/reload_engine")
async def _reload_engine():
    try:
        import decide_trade_once as m

        _reload(m)
        return {"ok": True, "engine": getattr(m, "__file__", "decide_trade_once.py")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# === end override ===


# === override normalize/decide/reload v2 ===
from fastapi import Request, Header
from fastapi.responses import JSONResponse
from importlib import reload as _reload
import gpt_bridge as _gb
import os
from uuid import uuid4

# retire routes existantes ciblées
try:
    app.router.routes = [
        r
        for r in app.router.routes
        if not (
            getattr(r, "path", None) in ("/normalize", "/decide", "/reload_engine")
            and ({"POST", "GET"} & set(getattr(r, "methods", set())))
        )
    ]
except Exception:
    pass


# request-id middleware
@app.middleware("http")
async def _reqid_mw(request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid4())
    request.state.request_id = rid
    resp = await call_next(request)
    resp.headers["x-request-id"] = rid
    return resp


@app.post("/normalize")
async def _normalize(request: Request):
    try:
        body = await request.json()
    except Exception as e:
        return JSONResponse(
            {"ok": False, "code": "BAD_JSON", "error": str(e)}, status_code=400
        )
    setups, reasons = _gb.normalize_setups(body)
    return {
        "ok": True,
        "setups": setups,
        "reasons": reasons,
        "ts": __import__("time").time_ns() // 1_000_000,
    }


@app.post("/decide")
async def _decide(request: Request):
    try:
        body = await request.json()
    except Exception as e:
        return JSONResponse(
            {"ok": False, "code": "BAD_JSON", "error": str(e)}, status_code=400
        )
    valids, reasons = _gb.normalize_setups(body)
    try:
        from decide_trade_once import decide as _engine

        decisions = _engine(valids) or []
        if decisions:
            return {
                "ok": True,
                "decisions": decisions,
                "ts": __import__("time").time_ns() // 1_000_000,
            }
    except Exception as e:
        return {
            "ok": True,
            "decisions": [
                {"action": "skip", "reason": f"engine_error:{e}", "setups": []}
            ],
            "ts": __import__("time").time_ns() // 1_000_000,
        }
    return {
        "ok": True,
        "decisions": [
            {
                "action": "preview",
                "reason": (reasons[0] if reasons else "OK"),
                "setups": valids,
            }
        ],
        "ts": __import__("time").time_ns() // 1_000_000,
    }


@app.post("/reload_engine")
async def _reload_engine(x_admin_token: str = Header(None)):
    want = os.getenv("ADMIN_TOKEN")
    if want and x_admin_token != want:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    import decide_trade_once as m

    _reload(m)
    return {"ok": True, "engine": getattr(m, "__file__", "decide_trade_once.py")}


# === end override v2 ===


# === security middlewares ===
import os, time
from collections import defaultdict, deque
from fastapi import Request
from fastapi.responses import JSONResponse

_RATE_BUCKETS = defaultdict(lambda: deque(maxlen=256))
RATE_WINDOW_S = float(os.getenv("RATE_WINDOW_S", "10"))
RATE_LIMIT_DECIDE = int(os.getenv("RATE_LIMIT_DECIDE", "20"))
RATE_LIMIT_RELOAD = int(os.getenv("RATE_LIMIT_RELOAD", "5"))


def _too_many(ip: str, path: str, limit: int) -> bool:
    now = time.time()
    dq = _RATE_BUCKETS[(ip, path)]
    while dq and (now - dq[0]) > RATE_WINDOW_S:
        dq.popleft()
    if len(dq) >= limit:
        return True
    dq.append(now)
    return False


@app.middleware("http")
async def _rate_limit_mw(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    path = request.url.path
    if path == "/decide" and _too_many(ip, path, RATE_LIMIT_DECIDE):
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
    if path == "/reload_engine" and _too_many(ip, path, RATE_LIMIT_RELOAD):
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
    return await call_next(request)


# === end security middlewares ===
